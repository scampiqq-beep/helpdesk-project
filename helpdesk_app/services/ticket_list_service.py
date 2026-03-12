from __future__ import annotations

from typing import Any

from flask import jsonify, render_template, request, url_for
from sqlalchemy.orm import load_only, selectinload
from helpdesk_app.models.base import db, ticket_shared_departments
from helpdesk_app.models.reference import Department, TicketCategory
from helpdesk_app.models.tickets import SupportTicket, TicketMessage
from helpdesk_app.models.users import User, UserUIState
from helpdesk_app.services.sla_service import SLAService


class TicketListService:
    """Bridge-сервис для вынесения ticket_list() из legacy.

    Пока опирается на существующие legacy-модели и helper'ы, но собирает контекст
    страницы уже вне монолитного route-handler.
    """

    @staticmethod
    def _legacy():
        from helpdesk_app.runtime import get_runtime
        return get_runtime()

    @classmethod
    def _get_ui_state(cls, actor: Any):
        legacy = cls._legacy()
        ui_state = None
        saved: dict[str, Any] = {}
        if isinstance(actor, User):
            try:
                ui_state = UserUIState.query.get(actor.id)
                if ui_state is None:
                    ui_state = UserUIState(user_id=actor.id, data='{}')
                    db.session.add(ui_state)
                    db.session.commit()
                saved = ui_state.get('ticket_list', {}) or {}
            except Exception:
                saved = {}
        return ui_state, saved

    @classmethod
    def _save_ui_state(cls, ui_state: Any, saved: dict[str, Any], *, current_sort: str, current_dir: str, show: int, compact: bool | None = None) -> dict[str, Any]:
        legacy = cls._legacy()
        if ui_state is None:
            return saved
        try:
            new_saved = {
                'id': (request.args.get('id') or (saved.get('id') if isinstance(saved, dict) else '') or '').strip(),
                'subject': (request.args.get('subject') or (saved.get('subject') if isinstance(saved, dict) else '') or '').strip(),
                'email': (request.args.get('email') or (saved.get('email') if isinstance(saved, dict) else '') or '').strip(),
                'inn': (request.args.get('inn') or (saved.get('inn') if isinstance(saved, dict) else '') or '').strip(),
                'fio': (request.args.get('fio') or (saved.get('fio') if isinstance(saved, dict) else '') or '').strip(),
                'status': request.args.getlist('status') or (saved.get('status') if isinstance(saved, dict) else []) or [],
                'department': request.args.getlist('department') or (saved.get('department') if isinstance(saved, dict) else []) or [],
                'indicator': request.args.getlist('indicator') or (saved.get('indicator') if isinstance(saved, dict) else []) or [],
                'sort': current_sort,
                'dir': current_dir,
                'show': show,
                'compact': bool(compact) if compact is not None else bool((saved.get('compact') if isinstance(saved, dict) else False)),
            }
            ui_state.set('ticket_list', new_saved)
            db.session.commit()
            return new_saved
        except Exception:
            return saved

    @classmethod
    def save_preferences(cls, actor: Any, *, compact: bool | None = None, show: int | None = None) -> dict[str, Any]:
        ui_state, saved = cls._get_ui_state(actor)
        if ui_state is None:
            return {'compact': bool(compact), 'show': show or 10}
        try:
            current = dict(saved or {})
            if compact is not None:
                current['compact'] = bool(compact)
            if show in (10, 25, 50):
                current['show'] = int(show)
            ui_state.set('ticket_list', current)
            db.session.commit()
            return current
        except Exception:
            db.session.rollback()
            return dict(saved or {})

    @classmethod
    def _apply_access_scope(cls, query: Any, actor: Any, *, is_client: bool, is_admin: bool):
        legacy = cls._legacy()
        page_title = 'Заявки'

        if is_client:
            query = query.filter(SupportTicket.email == actor.email)
            return query, page_title

        if is_admin:
            return query, '📋 Все обращения'

        if isinstance(actor, User) and legacy.is_tp_operator(actor):
            return query, '📋 Все обращения'

        dep_ids = legacy.user_department_ids(actor)
        if dep_ids:
            try:
                from helpdesk_app.models.base import ticket_shared_departments
                shared_ticket_ids = legacy.db.session.query(ticket_shared_departments.c.ticket_id).filter(
                    ticket_shared_departments.c.department_id.in_(dep_ids)
                )
                query = query.filter(
                    db.or_(SupportTicket.department_id.in_(dep_ids), SupportTicket.id.in_(shared_ticket_ids))
                )
            except Exception:
                query = query.filter(SupportTicket.department_id.in_(dep_ids))
        else:
            query = query.filter(db.text('1=0'))
        return query, page_title

    @classmethod
    def _apply_client_filters(cls, query: Any):
        legacy = cls._legacy()
        ticket_id = request.args.get('id', '').strip()
        subject = request.args.get('subject', '').strip()
        statuses = request.args.getlist('status')

        if ticket_id.isdigit():
            query = query.filter(SupportTicket.id == int(ticket_id))
        if subject:
            query = query.filter(SupportTicket.subject.ilike(f'%{subject}%'))
        if statuses:
            query = query.filter(SupportTicket.status.in_(statuses))
        return query

    @classmethod
    def _apply_operator_filters(cls, query: Any, actor: Any, saved: dict[str, Any]):
        legacy = cls._legacy()
        applied_sorting = False

        ticket_id = request.args.get('id', '').strip()
        subject = request.args.get('subject', '').strip()
        client_email = request.args.get('email', '').strip()
        client_inn = request.args.get('inn', '').strip()
        client_fio = request.args.get('fio', '').strip()
        statuses = request.args.getlist('status')
        departments = request.args.getlist('department')
        categories = request.args.getlist('category')
        indicators = request.args.getlist('indicator')
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()

        if saved:
            if not ticket_id and saved.get('id'):
                ticket_id = str(saved.get('id') or '').strip()
            if not subject and saved.get('subject'):
                subject = str(saved.get('subject') or '').strip()
            if not client_email and saved.get('email'):
                client_email = str(saved.get('email') or '').strip()
            if not client_inn and saved.get('inn'):
                client_inn = str(saved.get('inn') or '').strip()
            if not client_fio and saved.get('fio'):
                client_fio = str(saved.get('fio') or '').strip()
            if not statuses and saved.get('status'):
                statuses = list(saved.get('status') or [])
            if not departments and saved.get('department'):
                departments = list(saved.get('department') or [])
            if not indicators and saved.get('indicator'):
                indicators = list(saved.get('indicator') or [])

        if isinstance(statuses, str):
            statuses = [s for s in statuses.split(',') if s.strip()]
        if isinstance(departments, str):
            departments = [s for s in departments.split(',') if s.strip()]
        if isinstance(indicators, str):
            indicators = [s for s in indicators.split(',') if s.strip()]

        if ticket_id.isdigit():
            query = query.filter(SupportTicket.id == int(ticket_id))
        if subject:
            query = query.filter(SupportTicket.subject.ilike(f'%{subject}%'))
        if client_email:
            query = query.filter(SupportTicket.email.ilike(f'%{client_email}%'))
        if client_inn:
            query = query.filter(SupportTicket.inn.ilike(f'%{client_inn}%'))
        if client_fio:
            query = query.filter(SupportTicket.name.ilike(f'%{client_fio}%'))
        if statuses:
            query = query.filter(SupportTicket.status.in_(statuses))

        if indicators:
            tm = TicketMessage
            last_cte = legacy.db.session.query(
                tm.ticket_id.label('t_id'),
                legacy.func.max(tm.created_at).label('mx')
            ).group_by(tm.ticket_id).subquery('last_msg')

            tm_last = legacy.aliased(tm, name='tm_last')
            query = query.outerjoin(last_cte, last_cte.c.t_id == SupportTicket.id)
            query = query.outerjoin(tm_last, db.and_(tm_last.ticket_id == SupportTicket.id, tm_last.created_at == last_cte.c.mx))

            rid = db.func.coalesce(SupportTicket.assigned_to_id, SupportTicket.locked_by, SupportTicket.created_by_operator_id)
            st_lower = db.func.lower(db.func.trim(SupportTicket.status))
            closed_pred = db.or_(
                st_lower.like('закры%'),
                st_lower.like('заверш%'),
                SupportTicket.is_resolved == True,
                SupportTicket.closed_at.isnot(None),
                SupportTicket.auto_closed_at.isnot(None),
                SupportTicket.marked_as_completed_at.isnot(None),
            )
            no_msg_pred = last_cte.c.mx.is_(None)
            last_is_op = tm_last.is_operator

            conds = []
            for ind in [i.strip() for i in indicators if (i or '').strip()]:
                if ind == 'black':
                    conds.append(closed_pred)
                elif ind == 'blue':
                    conds.append(db.and_(~closed_pred, no_msg_pred == False, last_is_op == True))
                elif ind == 'orange':
                    conds.append(db.and_(~closed_pred, (db.or_(no_msg_pred, last_is_op == False)), rid == actor.id))
                elif ind == 'yellow':
                    conds.append(db.and_(~closed_pred, (db.or_(no_msg_pred, last_is_op == False)), rid.isnot(None), rid != actor.id))
                elif ind == 'green':
                    conds.append(db.and_(~closed_pred, db.or_(rid.is_(None), rid == 0), db.or_(no_msg_pred, last_is_op == False)))
            if conds:
                query = query.filter(db.or_(*conds))

        if departments:
            dept_ids = legacy.db.session.query(Department.id).filter(Department.name.in_(departments)).all()
            dept_ids = [id_ for (id_,) in dept_ids]
            if dept_ids:
                query = query.filter(SupportTicket.department_id.in_(dept_ids))

        if categories:
            try:
                cat_ids = legacy.db.session.query(TicketCategory.id).filter(TicketCategory.name.in_(categories)).all()
                cat_ids = [cid for (cid,) in cat_ids]
                if cat_ids:
                    query = query.filter(SupportTicket.category_id.in_(cat_ids))
            except Exception:
                pass

        if date_from:
            try:
                dt = legacy.datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(SupportTicket.created_at >= dt)
            except ValueError:
                pass

        if date_to:
            try:
                dt = legacy.datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = query.filter(SupportTicket.created_at <= dt)
            except ValueError:
                pass

        current_sort = (request.args.get('sort') or '').strip() or (saved.get('sort') if isinstance(saved, dict) else None) or 'created'
        current_dir = (request.args.get('dir') or '').strip().lower() or (saved.get('dir') if isinstance(saved, dict) else None) or 'desc'
        if current_sort in ('created_desc', 'created_asc', 'updated_desc', 'updated_asc'):
            legacy_sort = current_sort
            if legacy_sort.startswith('created_'):
                current_sort = 'created'
                current_dir = 'asc' if legacy_sort.endswith('_asc') else 'desc'
            else:
                current_sort = 'updated'
                current_dir = 'asc' if legacy_sort.endswith('_asc') else 'desc'

        try:
            updated_expr = getattr(SupportTicket, 'updated_at', None)
            sort_map = {
                'id': SupportTicket.id,
                'subject': SupportTicket.subject,
                'organization': SupportTicket.organization,
                'inn': SupportTicket.inn,
                'created': SupportTicket.created_at,
                'updated': updated_expr if updated_expr is not None else SupportTicket.created_at,
                'department': Department.name,
                'status': SupportTicket.status,
                'sla': SupportTicket.sla_deadline,
            }
            expr = sort_map.get(current_sort) or SupportTicket.created_at
            if current_sort == 'department':
                query = query.outerjoin(Department, Department.id == SupportTicket.department_id)
            query = query.order_by(expr.asc() if current_dir == 'asc' else expr.desc())
            applied_sorting = True
        except Exception:
            pass

        return query, applied_sorting, current_sort, current_dir

    @classmethod
    def _enrich_tickets(cls, tickets: list[Any], actor: Any) -> None:
        legacy = cls._legacy()
        for ticket in tickets:
            try:
                ticket.display_user = getattr(ticket, 'client_rel', None) or getattr(ticket, 'end_user_rel', None)
            except Exception:
                ticket.display_user = None

        try:
            missing = [t for t in tickets if not getattr(t, 'display_user', None) and getattr(t, 'email', None)]
            if missing:
                emails = sorted({(t.email or '').strip().lower() for t in missing if (t.email or '').strip()})
                if emails:
                    with legacy.db.session.no_autoflush:
                        users = User.query.filter(User.role == 'client', db.func.lower(User.email).in_(emails)).all()
                    by_email = {(u.email or '').strip().lower(): u for u in users}
                    for t in missing:
                        user = by_email.get((t.email or '').strip().lower())
                        if user:
                            t.display_user = user
        except Exception:
            pass

        try:
            t_ids = [t.id for t in tickets]
            last_is_op_map = {}
            if t_ids:
                tm = TicketMessage
                last_cte = legacy.db.session.query(
                    tm.ticket_id.label('t_id'),
                    legacy.func.max(tm.created_at).label('mx')
                ).filter(tm.ticket_id.in_(t_ids)).group_by(tm.ticket_id).subquery('last_msg_page')

                tm_last = legacy.aliased(tm, name='tm_last_page')
                rows = legacy.db.session.query(tm_last.ticket_id, tm_last.is_operator, tm_last.user_id).join(
                    last_cte,
                    db.and_(tm_last.ticket_id == last_cte.c.t_id, tm_last.created_at == last_cte.c.mx)
                ).all()
                for tid, is_op, user_id in rows:
                    last_is_op_map[int(tid)] = (bool(is_op), user_id)

            for t in tickets:
                last_meta = last_is_op_map.get(int(t.id))
                last_is_op = last_meta[0] if last_meta else None
                last_user_id = last_meta[1] if last_meta else None
                code, title = legacy.compute_ticket_indicator(t, last_is_op, last_user_id, getattr(actor, 'id', None))
                t.state_indicator = code
                t.state_indicator_title = title
        except Exception:
            for t in tickets:
                t.state_indicator = 'green'
                t.state_indicator_title = getattr(legacy, '_INDICATOR_LABELS', {}).get('green', 'Новая заявка')

        try:
            sla_views = SLAService.build_ticket_views(tickets)
        except Exception:
            sla_views = {}
        for t in tickets:
            t.sla_view = sla_views.get(getattr(t, 'id', None))
            t.ui_is_overdue = bool(t.sla_view and t.sla_view.get('summary_status') == 'overdue')

    @classmethod
    def build_context(cls, actor: Any) -> dict[str, Any]:
        legacy = cls._legacy()
        is_client = getattr(actor, 'role', None) == 'client'
        is_operator = (not is_client) and (
            getattr(actor, 'role', None) in ['operator', 'admin'] or (isinstance(actor, User) and legacy.is_tp_operator(actor))
        )
        is_admin = is_operator and getattr(actor, 'role', None) == 'admin'
        can_manage_spam = legacy.can_manage_spam_user(actor)

        ui_state, saved = cls._get_ui_state(actor)
        if request.args.get('clear') == '1' and ui_state is not None:
            try:
                ui_state.set('ticket_list', {})
                db.session.commit()
                saved = {}
            except Exception:
                pass

        query = SupportTicket.query.options(
            load_only(
                SupportTicket.id,
                SupportTicket.email,
                SupportTicket.name,
                SupportTicket.subject,
                SupportTicket.created_at,
                SupportTicket.status,
                SupportTicket.organization,
                SupportTicket.inn,
                SupportTicket.department_id,
                SupportTicket.assigned_to_id,
                SupportTicket.locked_by,
                SupportTicket.created_by_operator_id,
                SupportTicket.closed_at,
                SupportTicket.auto_closed_at,
                SupportTicket.marked_as_completed_at,
                SupportTicket.is_resolved,
                SupportTicket.sla_deadline,
                SupportTicket.client_id,
            ),
            selectinload(SupportTicket.department_rel).load_only(Department.id, Department.name),
            selectinload(SupportTicket.client_rel).load_only(User.id, User.email, User.username),
        )
        if not can_manage_spam:
            try:
                query = query.filter(SupportTicket.is_spam == False)
            except Exception:
                pass

        query, page_title = cls._apply_access_scope(query, actor, is_client=is_client, is_admin=is_admin)
        if is_client:
            query = cls._apply_client_filters(query)
            current_sort = (request.args.get('sort') or '').strip() or 'created'
            current_dir = (request.args.get('dir') or '').strip().lower() or 'desc'
            applied_sorting = False
        else:
            query, applied_sorting, current_sort, current_dir = cls._apply_operator_filters(query, actor, saved)

        if not applied_sorting:
            query = query.order_by(SupportTicket.created_at.desc())

        page = request.args.get('page', 1, type=int)
        show = request.args.get('show', None, type=int)
        if show is None:
            try:
                show = int((saved.get('show') if isinstance(saved, dict) else None) or 10)
            except Exception:
                show = 10
        if show not in (10, 25, 50):
            show = 10

        compact_pref = bool((saved.get('compact') if isinstance(saved, dict) else False))
        saved = cls._save_ui_state(ui_state, saved, current_sort=current_sort, current_dir=current_dir, show=show, compact=compact_pref)

        try:
            pagination = query.paginate(page=page, per_page=show, error_out=False)
        except Exception:
            pagination = db.paginate(query, page=page, per_page=show, error_out=False)

        tickets = pagination.items
        cls._enrich_tickets(tickets, actor)

        base_args = request.args.to_dict(flat=False)
        base_args.pop('page', None)
        base_args.pop('ajax', None)

        def _url_with(**kwargs) -> str:
            args = {k: v[:] if isinstance(v, list) else v for k, v in base_args.items()}
            for k, v in kwargs.items():
                if v is None:
                    args.pop(k, None)
                    continue
                args[k] = v
            return url_for('ticket_list', **args)

        def page_url(p: int) -> str:
            return _url_with(page=p)

        def show_url(n: int) -> str:
            return _url_with(show=n, page=1)

        def sort_url(field: str) -> str:
            cur_field = current_sort or 'created'
            cur_dir_local = (current_dir or 'desc').strip().lower()
            ndir = 'asc' if cur_field != field or cur_dir_local == 'desc' else 'desc'
            return _url_with(sort=field, dir=ndir, page=1)

        statuses = legacy.get_active_statuses()
        departments = [dept.name for dept in Department.query.order_by(Department.name).all()]
        try:
            categories = [c.name for c in TicketCategory.query.filter_by(is_active=True).order_by(TicketCategory.sort_order, TicketCategory.name).all()]
        except Exception:
            categories = []

        return {
            'tickets': tickets,
            'pagination': pagination,
            'page_url': page_url,
            'show_url': show_url,
            'sort_url': sort_url,
            'current_sort': current_sort,
            'current_dir': current_dir,
            'show': show,
            'compact': compact_pref,
            'page_title': page_title,
            'is_client': is_client,
            'is_operator': is_operator,
            'is_admin': is_admin,
            'STATUSES': statuses,
            'DEPARTMENTS': departments,
            'CATEGORIES': categories,
        }

    @classmethod
    def render_page(cls, actor: Any):
        context = cls.build_context(actor)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax') == '1':
            html = render_template('partials/_ticket_list_content.html', **context)
            return jsonify(success=True, html=html)
        return render_template('ticket_list.html', **context)
