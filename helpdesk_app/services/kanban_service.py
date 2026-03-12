from __future__ import annotations

from typing import Any
from datetime import timedelta

from flask import jsonify, render_template

from helpdesk_app.services.ticket_service import PermissionDenied


class KanbanService:
    """Bridge-сервис для kanban и связанных API."""

    @staticmethod
    def _legacy():
        from helpdesk_app.runtime import get_runtime
        return get_runtime()

    @classmethod
    def _check_access(cls, actor: Any) -> None:
        legacy = cls._legacy()
        if not isinstance(actor, legacy.User):
            raise PermissionDenied('Доступ запрещён')
        is_admin = actor.role == 'admin'
        is_tp = legacy.is_tp_operator(actor)
        if not (is_admin or is_tp):
            raise PermissionDenied('У вас нет доступа к Kanban-доске')

    @classmethod
    def build_page_context(cls, actor: Any) -> dict[str, Any]:
        legacy = cls._legacy()
        cls._check_access(actor)
        departments = legacy.Department.query.all()
        return {'departments': [{'id': d.id, 'name': d.name} for d in departments]}

    @classmethod
    def render_page(cls, actor: Any):
        context = cls.build_page_context(actor)
        return render_template('admin_kanban.html', **context)

    @classmethod
    def build_ticket_groups(cls, actor: Any) -> dict[str, list[dict[str, Any]]]:
        legacy = cls._legacy()
        cls._check_access(actor)
        tickets = legacy.SupportTicket.query.options(
            legacy.joinedload(legacy.SupportTicket.department_rel),
            legacy.joinedload(legacy.SupportTicket.locked_by_rel),
            legacy.joinedload(legacy.SupportTicket.assigned_to_rel),
        ).all()

        try:
            t_ids = [t.id for t in tickets]
            last_is_op_map: dict[int, bool] = {}
            if t_ids:
                tm = legacy.TicketMessage
                last_cte = legacy.db.session.query(
                    tm.ticket_id.label('t_id'),
                    legacy.func.max(tm.created_at).label('mx')
                ).filter(tm.ticket_id.in_(t_ids)).group_by(tm.ticket_id).subquery('last_msg_kanban')
                tm_last = legacy.aliased(tm, name='tm_last_kanban')
                rows = legacy.db.session.query(tm_last.ticket_id, tm_last.is_operator, tm_last.user_id).join(
                    last_cte,
                    legacy.db.and_(tm_last.ticket_id == last_cte.c.t_id, tm_last.created_at == last_cte.c.mx)
                ).all()
                for tid, is_op, user_id in rows:
                    last_is_op_map[int(tid)] = (bool(is_op), user_id)

            for ticket in tickets:
                last_meta = last_is_op_map.get(int(ticket.id))
                last_is_op = last_meta[0] if last_meta else None
                last_user_id = last_meta[1] if last_meta else None
                code, title = legacy.compute_ticket_indicator(ticket, last_is_op, last_user_id, getattr(actor, 'id', None))
                ticket.state_indicator = code
                ticket.state_indicator_title = title
        except Exception:
            for ticket in tickets:
                ticket.state_indicator = 'green'
                ticket.state_indicator_title = getattr(legacy, '_INDICATOR_LABELS', {}).get('green', 'Новая заявка')

        ticket_ids = [int(t.id) for t in tickets]
        unread_map: dict[int, int] = {}
        presence_map: dict[int, list[str]] = {}

        try:
            if ticket_ids and getattr(actor, 'id', None):
                Msg = legacy.TicketOperatorChatMessage
                Read = legacy.TicketOperatorChatRead
                sub_last = (legacy.db.session.query(Read.ticket_id.label('t_id'), Read.last_read_message_id.label('lr'))
                            .filter(Read.user_id == actor.id, Read.ticket_id.in_(ticket_ids))
                            .subquery('kanban_opchat_last'))
                unread_rows = (legacy.db.session.query(
                                    Msg.ticket_id,
                                    legacy.func.count(Msg.id).label('unread')
                                )
                                .outerjoin(sub_last, sub_last.c.t_id == Msg.ticket_id)
                                .filter(
                                    Msg.ticket_id.in_(ticket_ids),
                                    Msg.user_id != actor.id,
                                    Msg.id > legacy.func.coalesce(sub_last.c.lr, 0)
                                )
                                .group_by(Msg.ticket_id)
                                .all())
                unread_map = {int(ticket_id): int(unread or 0) for ticket_id, unread in unread_rows}
        except Exception:
            unread_map = {}

        try:
            if ticket_ids:
                cutoff = legacy.utcnow() - timedelta(seconds=20)
                presence_rows = (legacy.TicketPresence.query
                                 .filter(legacy.TicketPresence.ticket_id.in_(ticket_ids), legacy.TicketPresence.last_seen >= cutoff)
                                 .order_by(legacy.TicketPresence.ticket_id.asc(), legacy.TicketPresence.last_seen.desc())
                                 .all())
                for row in presence_rows:
                    lst = presence_map.setdefault(int(row.ticket_id), [])
                    if row.display_name not in lst:
                        lst.append(row.display_name)
        except Exception:
            presence_map = {}

        grouped: dict[str, list[dict[str, Any]]] = {}
        for ticket in tickets:
            data = legacy.ticket_to_dict(ticket)
            active_viewers = presence_map.get(int(ticket.id), [])
            data.update({
                'opchat_unread': unread_map.get(int(ticket.id), 0),
                'presence_names': active_viewers,
                'presence_count': len(active_viewers),
                'has_presence': bool(active_viewers),
                'responsible_name': getattr(ticket.assigned_to_rel, 'username', None) or getattr(ticket.locked_by_rel, 'username', None),
                'lock_owner_name': getattr(ticket.locked_by_rel, 'username', None),
            })
            dept_id = str(ticket.department_id or 0)
            grouped.setdefault(dept_id, []).append(data)
        return grouped

    @classmethod
    def render_data(cls, actor: Any):
        try:
            return jsonify(cls.build_ticket_groups(actor))
        except PermissionDenied as exc:
            return jsonify({'error': str(exc)}), 403
