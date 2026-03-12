from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, UTC
from typing import Any, Iterable

from sqlalchemy import func

from helpdesk_app.models.base import db
from helpdesk_app.models.settings import Settings, WorkCalendarDay
from helpdesk_app.models.tickets import SupportTicket, TicketMessage, TicketHistory


@dataclass
class SLAPolicySnapshot:
    timezone: str = 'Asia/Yekaterinburg'
    work_start: str = '09:00'
    work_end: str = '18:00'
    workdays: str = '0,1,2,3,4'
    first_response_minutes: int = 60
    resolve_minutes: int = 1440
    pause_statuses: str = 'Ожидание клиента'

    @property
    def workdays_list(self) -> list[int]:
        out: list[int] = []
        for x in (self.workdays or '').split(','):
            x = str(x).strip()
            if x.isdigit():
                out.append(int(x))
        return out or [0, 1, 2, 3, 4]

    @property
    def pause_statuses_set(self) -> set[str]:
        return {
            SLAService.normalize_status_name(x)
            for x in (self.pause_statuses or '').split(',')
            if SLAService.normalize_status_name(x)
        }


class SLAService:
    DEFAULTS = {
        'timezone': 'Asia/Yekaterinburg',
        'work_start': '09:00',
        'work_end': '18:00',
        'workdays': '0,1,2,3,4',
        'first_response_minutes': '60',
        'resolve_minutes': '1440',
        'pause_statuses': 'Ожидание клиента',
    }

    PRIORITY_RULE_KEYS = ('low', 'medium', 'high', 'critical')
    PRIORITY_LABELS = {
        'low': 'Низкий',
        'medium': 'Средний',
        'high': 'Высокий',
        'critical': 'Критический',
    }
    PRIORITY_ALIASES = {
        'low': 'low',
        'низкий': 'low',
        'medium': 'medium',
        'normal': 'medium',
        'средний': 'medium',
        'обычный': 'medium',
        'high': 'high',
        'высокий': 'high',
        'critical': 'critical',
        'критический': 'critical',
        'urgent': 'critical',
        'срочный': 'critical',
    }

    @staticmethod
    def _legacy():
        from helpdesk_app.runtime import get_runtime
        return get_runtime()

    @staticmethod
    def normalize_status_name(value: Any) -> str:
        return (value or '').strip().lower()

    @classmethod
    def _safe_int(cls, value: Any, default: int = 0) -> int:
        try:
            return int(str(value).strip())
        except Exception:
            return default

    @classmethod
    def _get_json_setting(cls, key: str, default: Any):
        row = Settings.query.filter_by(key=key).first()
        if not row or row.value in (None, ''):
            return default
        try:
            return json.loads(row.value)
        except Exception:
            return default

    @classmethod
    def normalize_priority_code(cls, value: Any) -> str:
        normalized = (value or '').strip().lower()
        return cls.PRIORITY_ALIASES.get(normalized, normalized if normalized in cls.PRIORITY_RULE_KEYS else 'medium')

    @classmethod
    def get_policy_snapshot(cls) -> SLAPolicySnapshot:
        values: dict[str, Any] = {}
        for key, default in cls.DEFAULTS.items():
            row = Settings.query.filter_by(key=f'sla.{key}').first()
            values[key] = (row.value if row and row.value not in (None, '') else default)
        values['first_response_minutes'] = cls._safe_int(values.get('first_response_minutes') or 60, 60)
        values['resolve_minutes'] = cls._safe_int(values.get('resolve_minutes') or 1440, 1440)
        return SLAPolicySnapshot(**values)

    @classmethod
    def get_rule_settings(cls) -> dict[str, Any]:
        priority_rules_raw = cls._get_json_setting('sla.priority_rules', {}) or {}
        category_rules_raw = cls._get_json_setting('sla.category_rules', {}) or {}
        important_rule_raw = cls._get_json_setting('sla.important_rule', {}) or {}

        priority_rules: dict[str, dict[str, int | str | None]] = {}
        for code in cls.PRIORITY_RULE_KEYS:
            payload = priority_rules_raw.get(code) or {}
            priority_rules[code] = {
                'first_response_minutes': cls._safe_int(payload.get('first_response_minutes'), 0),
                'resolve_minutes': cls._safe_int(payload.get('resolve_minutes'), 0),
                'label': cls.PRIORITY_LABELS.get(code, code),
            }

        category_rules: dict[str, dict[str, int]] = {}
        for category_id, payload in category_rules_raw.items():
            payload = payload or {}
            category_rules[str(category_id)] = {
                'first_response_minutes': cls._safe_int(payload.get('first_response_minutes'), 0),
                'resolve_minutes': cls._safe_int(payload.get('resolve_minutes'), 0),
            }

        important_rule = {
            'enabled': bool(important_rule_raw.get('enabled')),
            'first_response_minutes': cls._safe_int(important_rule_raw.get('first_response_minutes'), 0),
            'resolve_minutes': cls._safe_int(important_rule_raw.get('resolve_minutes'), 0),
        }

        return {
            'priority_rules': priority_rules,
            'category_rules': category_rules,
            'important_rule': important_rule,
        }

    @classmethod
    def get_policy_context(cls) -> dict[str, Any]:
        snap = cls.get_policy_snapshot()
        rule_settings = cls.get_rule_settings()
        return {
            'timezone': snap.timezone,
            'work_start': snap.work_start,
            'work_end': snap.work_end,
            'workdays': snap.workdays,
            'workdays_list': snap.workdays_list,
            'first_response_minutes': snap.first_response_minutes,
            'resolve_minutes': snap.resolve_minutes,
            'pause_statuses': snap.pause_statuses,
            'priority_rules': rule_settings['priority_rules'],
            'category_rules': rule_settings['category_rules'],
            'important_rule': rule_settings['important_rule'],
        }

    @staticmethod
    def parse_hhmm(value: str, fallback: time) -> time:
        try:
            hh, mm = str(value or '').split(':', 1)
            return time(int(hh), int(mm))
        except Exception:
            return fallback

    @classmethod
    def get_calendar_row(cls, day: date):
        return WorkCalendarDay.query.filter_by(date=day).first()

    @classmethod
    def is_business_day(cls, day: date, snap: SLAPolicySnapshot | None = None) -> bool:
        snap = snap or cls.get_policy_snapshot()
        row = cls.get_calendar_row(day)
        if row is not None:
            return row.day_type in ('workday', 'short_day')
        return day.weekday() in set(snap.workdays_list)

    @classmethod
    def business_bounds(cls, day: date, snap: SLAPolicySnapshot | None = None):
        snap = snap or cls.get_policy_snapshot()
        tz = cls._legacy().get_runtime_timezone()
        start_t = cls.parse_hhmm(snap.work_start, time(9, 0))
        end_t = cls.parse_hhmm(snap.work_end, time(18, 0))
        start = datetime.combine(day, start_t, tzinfo=tz)
        end = datetime.combine(day, end_t, tzinfo=tz)
        row = cls.get_calendar_row(day)
        if row is not None and row.day_type == 'short_day':
            end = end - timedelta(hours=1)
        return start, end

    @classmethod
    def add_business_minutes(cls, start_dt: datetime | None, minutes: int | None, snap: SLAPolicySnapshot | None = None):
        if not start_dt or not minutes:
            return start_dt
        snap = snap or cls.get_policy_snapshot()
        current = cls._legacy().to_local(start_dt)
        remaining = max(0, int(minutes))
        tz = cls._legacy().get_runtime_timezone()
        while remaining > 0:
            if not cls.is_business_day(current.date(), snap):
                current = datetime.combine(current.date() + timedelta(days=1), time(0, 0), tzinfo=tz)
                continue
            start_bound, end_bound = cls.business_bounds(current.date(), snap)
            if current < start_bound:
                current = start_bound
            if current >= end_bound:
                current = datetime.combine(current.date() + timedelta(days=1), time(0, 0), tzinfo=tz)
                continue
            chunk = min(remaining, int((end_bound - current).total_seconds() // 60))
            if chunk <= 0:
                current = datetime.combine(current.date() + timedelta(days=1), time(0, 0), tzinfo=tz)
                continue
            current += timedelta(minutes=chunk)
            remaining -= chunk
        return current.astimezone(UTC).replace(tzinfo=None)

    @staticmethod
    def first_operator_reply_map(ticket_ids: Iterable[int]) -> dict[int, datetime]:
        ids = [int(x) for x in (ticket_ids or []) if x]
        if not ids:
            return {}
        rows = (
            db.session.query(TicketMessage.ticket_id, func.min(TicketMessage.created_at))
            .filter(TicketMessage.ticket_id.in_(ids), TicketMessage.is_operator.is_(True))
            .group_by(TicketMessage.ticket_id)
            .all()
        )
        return {int(ticket_id): created_at for ticket_id, created_at in rows}

    @staticmethod
    def ticket_closed_at_value(ticket: SupportTicket):
        return getattr(ticket, 'closed_at', None) or getattr(ticket, 'auto_closed_at', None) or getattr(ticket, 'marked_as_completed_at', None)

    @classmethod
    def is_paused(cls, ticket: SupportTicket, snap: SLAPolicySnapshot | None = None) -> bool:
        snap = snap or cls.get_policy_snapshot()
        return cls.normalize_status_name(getattr(ticket, 'status', '')) in snap.pause_statuses_set

    @staticmethod
    def _humanize_minutes(mins: int) -> str:
        mins = max(0, int(mins))
        days, rem = divmod(mins, 60 * 24)
        hours, minutes = divmod(rem, 60)
        parts = []
        if days:
            parts.append(f'{days} д')
        if hours:
            parts.append(f'{hours} ч')
        if minutes or not parts:
            parts.append(f'{minutes} мин')
        return ' '.join(parts[:2])

    @staticmethod
    def _format_compact_minutes(mins: int | None, *, signed: bool = False) -> str:
        if mins is None:
            return '—'
        mins = int(mins)
        sign = ''
        if signed and mins < 0:
            sign = '-'
        mins_abs = abs(mins)
        days, rem = divmod(mins_abs, 60 * 24)
        hours, minutes = divmod(rem, 60)
        if days:
            return f'{sign}{days} д {hours} ч' if hours else f'{sign}{days} д'
        if hours:
            return f'{sign}{hours} ч'
        return f'{sign}{max(1, minutes)} мин'

    @classmethod
    def _timer_visual_state(cls, diff_min: int | None, *, paused: bool = False, completed: bool = False) -> tuple[str, str]:
        if paused:
            return 'paused', 'На паузе'
        if diff_min is None:
            return 'normal', '—'
        if completed:
            if diff_min < 0:
                return 'overdue', f'-{cls._format_compact_minutes(abs(diff_min))}'
            return 'ok', cls._format_compact_minutes(diff_min)
        if diff_min < 0:
            return 'overdue', f'-{cls._format_compact_minutes(abs(diff_min))}'
        if diff_min <= 120:
            return 'warning', cls._format_compact_minutes(diff_min)
        return 'ok', cls._format_compact_minutes(diff_min)

    @staticmethod
    def _priority_rank(priority: Any) -> int:
        code = SLAService.normalize_priority_code(priority)
        order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
        return order.get(code, 1)

    @classmethod
    def _record_auto_escalation(cls, ticket: SupportTicket, old_priority: str, target_priority: str, stage: str, overdue_minutes: int) -> None:
        from helpdesk_app.models.users import User

        actor_id = getattr(ticket, 'assigned_to_id', None) or getattr(ticket, 'locked_by', None) or getattr(ticket, 'created_by_operator_id', None)
        if not actor_id:
            actor_id = db.session.query(User.id).filter(User.role.in_(['admin', 'operator'])).order_by(User.id.asc()).limit(1).scalar()
        if not actor_id:
            return
        note = f'Автоэскалация по сроку «{stage}»: просрочка {cls._humanize_minutes(abs(overdue_minutes))}'
        db.session.add(TicketHistory(
            ticket_id=ticket.id,
            user_id=actor_id,
            field='sla_auto_escalation',
            old_value=cls.PRIORITY_LABELS.get(cls.normalize_priority_code(old_priority), old_priority or '—'),
            new_value=cls.PRIORITY_LABELS.get(target_priority, target_priority),
            note=note,
        ))

    @classmethod
    def maybe_auto_escalate_ticket(cls, ticket: SupportTicket, *, now_local: datetime | None = None, snap: SLAPolicySnapshot | None = None) -> bool:
        return False

    @classmethod
    def maybe_auto_escalate_tickets(cls, tickets: Iterable[SupportTicket], *, now_local: datetime | None = None, snap: SLAPolicySnapshot | None = None) -> bool:
        return False

    @staticmethod
    def _format_duration(seconds: float | int | None) -> str:
        if seconds is None:
            return 'Нет данных'
        seconds = float(seconds)
        if seconds < 60:
            return f"{int(seconds)} сек"
        if seconds < 3600:
            return f"{int(seconds/60)} мин"
        if seconds < 86400:
            return f"{int(seconds/3600)} ч {int((seconds%3600)/60)} м"
        return f"{int(seconds/86400)} д {int((seconds%86400)/3600)} ч"

    @classmethod
    def _apply_rule_minutes(cls, current_value: int, rule_value: Any) -> int:
        parsed = cls._safe_int(rule_value, 0)
        if parsed <= 0:
            return current_value
        return min(current_value, parsed) if current_value > 0 else parsed

    @classmethod
    def get_effective_targets(cls, ticket: SupportTicket, snap: SLAPolicySnapshot | None = None) -> dict[str, Any]:
        snap = snap or cls.get_policy_snapshot()
        rules = cls.get_rule_settings()
        first_minutes = snap.first_response_minutes
        resolve_minutes = snap.resolve_minutes
        matched_rules: list[str] = []

        priority_code = cls.normalize_priority_code(getattr(ticket, 'priority', None))
        priority_rule = (rules.get('priority_rules') or {}).get(priority_code) or {}
        new_first = cls._apply_rule_minutes(first_minutes, priority_rule.get('first_response_minutes'))
        new_resolve = cls._apply_rule_minutes(resolve_minutes, priority_rule.get('resolve_minutes'))
        if new_first != first_minutes or new_resolve != resolve_minutes:
            matched_rules.append(f"Приоритет «{cls.PRIORITY_LABELS.get(priority_code, priority_code)}»")
            first_minutes, resolve_minutes = new_first, new_resolve

        category_id = getattr(ticket, 'category_id', None)
        category_rule = (rules.get('category_rules') or {}).get(str(category_id)) if category_id else None
        if category_rule:
            new_first = cls._apply_rule_minutes(first_minutes, category_rule.get('first_response_minutes'))
            new_resolve = cls._apply_rule_minutes(resolve_minutes, category_rule.get('resolve_minutes'))
            if new_first != first_minutes or new_resolve != resolve_minutes:
                category_name = getattr(getattr(ticket, 'category_rel', None), 'name', None) or f'Категория #{category_id}'
                matched_rules.append(f"Категория «{category_name}»")
                first_minutes, resolve_minutes = new_first, new_resolve

        important_rule = (rules.get('important_rule') or {})
        is_important = priority_code == 'critical'
        if is_important and important_rule.get('enabled'):
            new_first = cls._apply_rule_minutes(first_minutes, important_rule.get('first_response_minutes'))
            new_resolve = cls._apply_rule_minutes(resolve_minutes, important_rule.get('resolve_minutes'))
            if new_first != first_minutes or new_resolve != resolve_minutes:
                matched_rules.append('Правило для важной задачи')
                first_minutes, resolve_minutes = new_first, new_resolve

        return {
            'first_response_minutes': first_minutes,
            'resolve_minutes': resolve_minutes,
            'priority_code': priority_code,
            'is_important': is_important,
            'matched_rules': matched_rules,
        }

    @classmethod
    def build_one_state(cls, deadline: datetime | None, fact_dt: datetime | None, now_local: datetime, *, paused: bool = False, started_at: datetime | None = None, target_minutes: int | None = None):
        if not deadline:
            return {
                'status': 'normal',
                'label': '—',
                'title': 'Крайний срок не настроен',
                'deadline': None,
                'deadline_text': '—',
                'timer_text': '—',
                'compact_label': '—',
                'chip_status': 'normal',
                'breached': False,
                'diff_minutes': None,
                'completed': bool(fact_dt),
                'paused': paused,
                'target_minutes': target_minutes,
                'progress_percent': 0,
            }
        compare_dt = fact_dt or now_local
        diff_min = int((deadline - compare_dt).total_seconds() // 60)
        breached = diff_min < 0
        if fact_dt:
            status = 'ok' if diff_min >= 0 else 'overdue'
            label = 'В срок' if diff_min >= 0 else 'Нарушено'
            title = (
                f'Выполнено в срок, запас {cls._humanize_minutes(diff_min)}'
                if diff_min >= 0 else
                f'Нарушено на {cls._humanize_minutes(abs(diff_min))}'
            )
            timer_text = title
            chip_status, compact_label = cls._timer_visual_state(diff_min, completed=True)
        else:
            if paused:
                status = 'paused'
                label = 'На паузе'
                title = 'Таймер крайнего срока остановлен для текущего статуса'
                timer_text = 'Таймер остановлен'
                breached = False
                chip_status, compact_label = cls._timer_visual_state(diff_min, paused=True)
            elif diff_min < 0:
                status = 'overdue'
                label = f'Просрочено {cls._humanize_minutes(abs(diff_min))}'
                title = f'Просрочено на {cls._humanize_minutes(abs(diff_min))}'
                timer_text = title
                chip_status, compact_label = cls._timer_visual_state(diff_min)
            else:
                status = 'ok'
                label = f'Осталось {cls._humanize_minutes(diff_min)}'
                title = f'До истечения срока {cls._humanize_minutes(diff_min)}'
                timer_text = title
                chip_status, compact_label = cls._timer_visual_state(diff_min)
        progress_percent = 0
        if target_minutes and target_minutes > 0 and deadline:
            if fact_dt:
                elapsed_minutes = max(0, int(((fact_dt - started_at).total_seconds() // 60) if started_at else target_minutes - diff_min))
            else:
                elapsed_minutes = max(0, int(target_minutes - diff_min))
            progress_percent = max(0, min(100, int(round((elapsed_minutes / max(1, target_minutes)) * 100))))
            if diff_min < 0 and not paused:
                progress_percent = 100
        return {
            'status': status,
            'label': label,
            'title': title,
            'deadline': deadline,
            'deadline_text': cls._legacy().format_local(deadline) if deadline else '—',
            'timer_text': timer_text,
            'compact_label': compact_label,
            'chip_status': chip_status,
            'breached': breached,
            'diff_minutes': diff_min,
            'completed': bool(fact_dt),
            'paused': paused,
            'target_minutes': target_minutes,
            'progress_percent': progress_percent,
        }

    @classmethod
    def build_ticket_view(cls, ticket: SupportTicket, *, first_reply_at: datetime | None = None, now_local: datetime | None = None, snap: SLAPolicySnapshot | None = None):
        snap = snap or cls.get_policy_snapshot()
        if now_local is None:
            now_local = cls._legacy().utcnow()
        cls.maybe_auto_escalate_ticket(ticket, now_local=now_local, snap=snap)
        if first_reply_at is None:
            first_reply_at = cls.first_operator_reply_map([ticket.id]).get(ticket.id)

        effective = cls.get_effective_targets(ticket, snap)
        first_deadline = cls.add_business_minutes(ticket.created_at, effective['first_response_minutes'], snap)
        resolve_deadline = cls.add_business_minutes(ticket.created_at, effective['resolve_minutes'], snap)
        closed_at = cls.ticket_closed_at_value(ticket)
        paused = cls.is_paused(ticket, snap) and not closed_at
        first_view = cls.build_one_state(first_deadline, first_reply_at, now_local, paused=False, started_at=ticket.created_at, target_minutes=effective['first_response_minutes'])
        resolve_view = cls.build_one_state(resolve_deadline, closed_at, now_local, paused=paused, started_at=ticket.created_at, target_minutes=effective['resolve_minutes'])
        summary = resolve_view['compact_label']
        summary_status = resolve_view.get('chip_status') or resolve_view['status']
        summary_title = f"Крайний срок решения: {resolve_view.get('title') or resolve_view['label']}"
        summary_deadline_type = 'resolve'
        if first_reply_at is None and first_view.get('deadline'):
            summary = first_view['compact_label']
            summary_status = first_view.get('chip_status') or first_view['status']
            summary_title = f"Крайний срок ответа: {first_view.get('title') or first_view['label']}"
            summary_deadline_type = 'first_response'
        if first_view['status'] == 'overdue' and not closed_at:
            summary = first_view['compact_label']
            summary_status = first_view.get('chip_status') or 'overdue'
            summary_title = f"Крайний срок первого ответа: {first_view.get('title') or first_view['label']}"
            summary_deadline_type = 'first_response'
        return {
            'first_response': first_view,
            'resolve': resolve_view,
            'summary': summary,
            'summary_status': summary_status,
            'summary_title': summary_title,
            'summary_deadline_type': summary_deadline_type,
            'first_deadline': first_deadline,
            'resolve_deadline': resolve_deadline,
            'paused': paused,
            'breached': first_view['breached'] or resolve_view['breached'],
            'effective': effective,
            'policy': cls.get_policy_context(),
        }

    @classmethod
    def build_ticket_views(cls, tickets: Iterable[SupportTicket]) -> dict[int, dict[str, Any] | None]:
        items = list(tickets or [])
        if not items:
            return {}
        snap = cls.get_policy_snapshot()
        ids = [getattr(t, 'id', None) for t in items if getattr(t, 'id', None)]
        reply_map = cls.first_operator_reply_map(ids)
        now_local = cls._legacy().utcnow()
        cls.maybe_auto_escalate_tickets(items, now_local=now_local, snap=snap)
        out: dict[int, dict[str, Any] | None] = {}
        for t in items:
            try:
                out[t.id] = cls.build_ticket_view(t, first_reply_at=reply_map.get(t.id), now_local=now_local, snap=snap)
            except Exception:
                out[t.id] = None
        return out

    @classmethod
    def sync_deadline_to_ticket(cls, ticket: SupportTicket):
        view = cls.build_ticket_view(ticket)
        ticket.sla_deadline = view.get('resolve_deadline')
        return ticket.sla_deadline

    @classmethod
    def build_report_metrics(cls, tickets: Iterable[SupportTicket], *, start: datetime, end: datetime) -> dict[str, Any]:
        items = list(tickets or [])
        views = cls.build_ticket_views(items)

        def resolved_at(t: SupportTicket):
            return cls.ticket_closed_at_value(t)

        def in_range(d: datetime | None):
            return d is not None and start <= d < end

        created = [t for t in items if in_range(getattr(t, 'created_at', None))]
        resolved = [t for t in items if in_range(resolved_at(t))]

        first_on_time = 0
        first_overdue = 0
        resolve_on_time = 0
        resolve_overdue = 0
        frt_total = 0.0
        frt_cnt = 0
        mttr_total = 0.0
        mttr_cnt = 0

        reply_map = cls.first_operator_reply_map([t.id for t in created if getattr(t, 'id', None)])
        for t in created:
            view = views.get(t.id) or {}
            first = view.get('first_response') or {}
            replied = reply_map.get(t.id)
            if replied:
                if first.get('breached'):
                    first_overdue += 1
                else:
                    first_on_time += 1
                sec = (replied - t.created_at).total_seconds()
                if sec >= 0:
                    frt_total += sec
                    frt_cnt += 1

        for t in resolved:
            view = views.get(t.id) or {}
            rview = view.get('resolve') or {}
            if rview.get('breached'):
                resolve_overdue += 1
            else:
                resolve_on_time += 1
            ra = resolved_at(t)
            if ra and t.created_at:
                sec = (ra - t.created_at).total_seconds()
                if sec >= 0:
                    mttr_total += sec
                    mttr_cnt += 1

        total_first = first_on_time + first_overdue
        total_resolve = resolve_on_time + resolve_overdue
        return {
            'first_response_on_time': first_on_time,
            'first_response_overdue': first_overdue,
            'first_response_percent': round((first_on_time / total_first * 100), 1) if total_first else 0.0,
            'resolve_on_time': resolve_on_time,
            'resolve_overdue': resolve_overdue,
            'resolve_percent': round((resolve_on_time / total_resolve * 100), 1) if total_resolve else 0.0,
            'frt_avg': cls._format_duration((frt_total / frt_cnt) if frt_cnt else None),
            'mttr_avg': cls._format_duration((mttr_total / mttr_cnt) if mttr_cnt else None),
            'views': views,
        }
