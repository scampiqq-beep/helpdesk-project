from __future__ import annotations

import json
from datetime import date, datetime
from types import SimpleNamespace

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from helpdesk_app.models.base import db
from helpdesk_app.models.reference import TicketCategory
from helpdesk_app.models.settings import WorkCalendarDay
from helpdesk_app.models.tickets import SupportTicket
from helpdesk_app.services.sla_service import SLAService


class AdminSLACalendarService:
    HANDLED_ACTIONS = {
        'save_sla_settings',
        'import_calendar',
        'set_day_type',
        'recalculate_open_tickets',
    }

    @staticmethod
    def _legacy():
        from helpdesk_app.runtime import get_runtime
        return get_runtime()

    @classmethod
    def ensure_admin(cls):
        if getattr(current_user, 'role', None) != 'admin':
            flash('Доступ запрещён', 'error')
            return False
        return True

    @staticmethod
    def _safe_int(value, default: int = 0) -> int:
        try:
            return int(str(value).strip())
        except Exception:
            return default

    @classmethod
    def _template_cfg(cls):
        raw = cls._legacy().get_sla_settings()
        policy = SLAService.get_policy_context()
        rules = SLAService.get_rule_settings()
        categories = TicketCategory.query.order_by(TicketCategory.sort_order.asc(), TicketCategory.name.asc()).all()
        priority_rows = []
        for code in SLAService.PRIORITY_RULE_KEYS:
            row = rules['priority_rules'].get(code) or {}
            priority_rows.append(
                {
                    'code': code,
                    'label': SLAService.PRIORITY_LABELS.get(code, code),
                    'first_response_minutes': row.get('first_response_minutes', 0),
                    'resolve_minutes': row.get('resolve_minutes', 0),
                }
            )
        category_rows = []
        for category in categories:
            row = rules['category_rules'].get(str(category.id)) or {}
            category_rows.append(
                {
                    'id': category.id,
                    'name': category.name,
                    'code': category.code,
                    'first_response_minutes': row.get('first_response_minutes', 0),
                    'resolve_minutes': row.get('resolve_minutes', 0),
                }
            )
        return SimpleNamespace(
            timezone=getattr(raw, 'timezone', policy['timezone']),
            work_start=getattr(raw, 'work_start', policy['work_start']),
            work_end=getattr(raw, 'work_end', policy['work_end']),
            first_response_minutes=getattr(raw, 'first_response_minutes', policy['first_response_minutes']),
            resolve_minutes=getattr(raw, 'resolve_minutes', policy['resolve_minutes']),
            pause_statuses=getattr(raw, 'pause_statuses', policy['pause_statuses']),
            workdays=getattr(raw, 'workdays', policy['workdays']),
            workdays_list=policy['workdays_list'],
            priority_rows=priority_rows,
            category_rows=category_rows,
            important_rule=rules['important_rule'],
        )

    @classmethod
    def _base_context(cls):
        if not cls.ensure_admin():
            return redirect(url_for('ticket_list'))
        legacy = cls._legacy()
        year = request.values.get('year', type=int) or datetime.now(legacy.get_runtime_timezone()).year
        selected_date_raw = (request.values.get('selected_date') or '').strip()
        try:
            selected_date = date.fromisoformat(selected_date_raw) if selected_date_raw else None
        except Exception:
            selected_date = None

        months = []
        month_titles = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        day_rows = WorkCalendarDay.query.filter(
            WorkCalendarDay.date >= date(year, 1, 1),
            WorkCalendarDay.date <= date(year, 12, 31),
        ).all()
        row_map = {r.date: r for r in day_rows}
        stats = {'workday': 0, 'weekend': 0, 'holiday': 0, 'short_day': 0, 'manual': 0}
        for r in day_rows:
            stats[r.day_type] = stats.get(r.day_type, 0) + 1
            if getattr(r, 'manual_override', False):
                stats['manual'] += 1
        if selected_date is None:
            selected_date = datetime.now(legacy.get_runtime_timezone()).date()
        selected_row = row_map.get(selected_date)
        if selected_date.year != year:
            selected_date = date(year, 1, 1)
            selected_row = row_map.get(selected_date)
        for m in range(1, 13):
            months.append({'num': m, 'title': month_titles[m - 1], 'weeks': legacy.calendar_month_view(year, m)})
        return {
            'year': year,
            'months': months,
            'cfg': cls._template_cfg(),
            'selected_date': selected_date,
            'selected_row': selected_row,
            'cal_stats': stats,
        }

    @classmethod
    def render_page(cls, page='sla'):
        ctx = cls._base_context()
        if not isinstance(ctx, dict):
            return ctx
        template = 'admin_sla_settings.html' if page == 'sla' else 'admin_work_calendar.html'
        return render_template(template, **ctx)

    @classmethod
    def _collect_priority_rules(cls) -> dict[str, dict[str, int]]:
        rules: dict[str, dict[str, int]] = {}
        for code in SLAService.PRIORITY_RULE_KEYS:
            rules[code] = {
                'first_response_minutes': max(0, cls._safe_int(request.form.get(f'priority_{code}_first_response'), 0)),
                'resolve_minutes': max(0, cls._safe_int(request.form.get(f'priority_{code}_resolve'), 0)),
            }
        return rules

    @classmethod
    def _collect_category_rules(cls) -> dict[str, dict[str, int]]:
        rules: dict[str, dict[str, int]] = {}
        categories = TicketCategory.query.order_by(TicketCategory.sort_order.asc(), TicketCategory.name.asc()).all()
        for category in categories:
            first_minutes = max(0, cls._safe_int(request.form.get(f'category_{category.id}_first_response'), 0))
            resolve_minutes = max(0, cls._safe_int(request.form.get(f'category_{category.id}_resolve'), 0))
            if first_minutes or resolve_minutes:
                rules[str(category.id)] = {
                    'first_response_minutes': first_minutes,
                    'resolve_minutes': resolve_minutes,
                }
        return rules

    @classmethod
    def _recalculate_open_tickets(cls) -> int:
        count = 0
        for ticket in SupportTicket.query.filter(SupportTicket.is_resolved.is_(False)).all():
            SLAService.sync_deadline_to_ticket(ticket)
            count += 1
        return count

    @classmethod
    def handle_post(cls, page='sla'):
        if not cls.ensure_admin():
            return redirect(url_for('ticket_list'))
        legacy = cls._legacy()
        year = request.values.get('year', type=int) or datetime.now(legacy.get_runtime_timezone()).year
        selected_date_raw = (request.values.get('selected_date') or '').strip()
        try:
            selected_date = date.fromisoformat(selected_date_raw) if selected_date_raw else None
        except Exception:
            selected_date = None
        action = (request.form.get('action') or '').strip()
        if action not in cls.HANDLED_ACTIONS:
            return None
        target_endpoint = 'admin_sla_settings' if page == 'sla' else 'admin_work_calendar'
        try:
            if action == 'save_sla_settings':
                timezone_name = (request.form.get('timezone') or legacy.SYSTEM_TZ_NAME).strip()
                legacy.set_setting('system.timezone', timezone_name)
                legacy.set_setting('sla.timezone', timezone_name)
                legacy.set_setting('sla.work_start', (request.form.get('work_start') or '09:00').strip())
                legacy.set_setting('sla.work_end', (request.form.get('work_end') or '18:00').strip())
                legacy.set_setting('sla.first_response_minutes', str(request.form.get('first_response_minutes') or '60'))
                legacy.set_setting('sla.resolve_minutes', str(request.form.get('resolve_minutes') or '1440'))
                legacy.set_setting('sla.pause_statuses', (request.form.get('pause_statuses') or '').strip())
                legacy.set_setting('sla.workdays', ','.join(request.form.getlist('workdays') or ['0', '1', '2', '3', '4']))

                priority_rules = cls._collect_priority_rules()
                category_rules = cls._collect_category_rules()
                important_rule = {
                    'enabled': request.form.get('important_rule_enabled') in {'1', 'on', 'true', 'True'},
                    'first_response_minutes': max(0, cls._safe_int(request.form.get('important_first_response'), 0)),
                    'resolve_minutes': max(0, cls._safe_int(request.form.get('important_resolve'), 0)),
                }
                legacy.set_setting('sla.priority_rules', json.dumps(priority_rules, ensure_ascii=False))
                legacy.set_setting('sla.category_rules', json.dumps(category_rules, ensure_ascii=False))
                legacy.set_setting('sla.important_rule', json.dumps(important_rule, ensure_ascii=False))
                recalculated = cls._recalculate_open_tickets()
                db.session.commit()
                flash(f'Настройки SLA сохранены. Пересчитано открытых заявок: {recalculated}.', 'success')
            elif action == 'import_calendar':
                imported = 0
                for item in legacy.fetch_production_calendar_year(year):
                    d = date.fromisoformat(item['date'])
                    row = WorkCalendarDay.query.filter_by(date=d).first()
                    if not row:
                        row = WorkCalendarDay(date=d)
                        db.session.add(row)
                    row.day_type = 'workday' if item.get('is_workday') else 'weekend'
                    row.manual_override = False
                    if not row.name:
                        row.name = None
                    imported += 1
                db.session.commit()
                flash(f'Календарь РФ за {year} импортирован: {imported} дней', 'success')
            elif action == 'set_day_type':
                d = date.fromisoformat(request.form.get('date'))
                row = WorkCalendarDay.query.filter_by(date=d).first()
                if not row:
                    row = WorkCalendarDay(date=d)
                    db.session.add(row)
                row.day_type = request.form.get('day_type') or 'workday'
                row.name = (request.form.get('name') or '').strip() or None
                row.manual_override = True
                db.session.commit()
                flash('День календаря обновлён', 'success')
                selected_date = d
            elif action == 'recalculate_open_tickets':
                cnt = cls._recalculate_open_tickets()
                db.session.commit()
                flash(f'Пересчитан SLA для {cnt} открытых заявок', 'success')
        except Exception as exc:
            legacy.db.session.rollback()
            flash(f'Ошибка SLA/календаря: {exc}', 'error')
        return redirect(url_for(target_endpoint, year=year, selected_date=(selected_date.isoformat() if selected_date else None)))
