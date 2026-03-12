from __future__ import annotations

from typing import Any, Dict, Iterable

import os
from html import escape

from helpdesk_app.models.base import db, utcnow
from helpdesk_app.models.tickets import SupportTicket, TicketAttachment, TicketHistory, TicketMessage
from helpdesk_app.services.automation_runtime_service import AutomationRuntimeService


class TicketServiceError(Exception):
    pass


class ValidationError(TicketServiceError):
    pass


class PermissionDenied(TicketServiceError):
    pass


class TicketService:
    @staticmethod
    def apply_automation_on_create(ticket: Any) -> Dict[str, Any]:
        return AutomationRuntimeService.run_for_ticket(ticket)

    @staticmethod
    def apply_automation_on_update(ticket: Any) -> Dict[str, Any]:
        return AutomationRuntimeService.run_for_ticket(ticket)

    @staticmethod
    def collect_automation_context(ticket: Any) -> Dict[str, Any]:
        return {
            "assignee_email": getattr(ticket, "_automation_assignee_email", None),
            "tags_to_add": list(getattr(ticket, "_automation_tags_to_add", []) or []),
            "internal_notes": list(getattr(ticket, "_automation_internal_notes", []) or []),
        }

    @staticmethod
    def wire_create_flow(ticket: Any) -> Dict[str, Any]:
        from helpdesk_app.services.ticket_workflow_service import TicketWorkflowService
        payload = TicketWorkflowService.before_create(ticket)
        TicketWorkflowService.attach_runtime_payload(ticket, payload)
        return payload

    @staticmethod
    def wire_update_flow(ticket: Any) -> Dict[str, Any]:
        from helpdesk_app.services.ticket_workflow_service import TicketWorkflowService
        payload = TicketWorkflowService.before_update(ticket)
        TicketWorkflowService.attach_runtime_payload(ticket, payload)
        return payload

    @staticmethod
    def _ensure_operator(actor: Any) -> None:
        role = (getattr(actor, 'role', None) or '').strip().lower()
        if role not in {'operator', 'admin'}:
            raise PermissionDenied('Недостаточно прав')

    @staticmethod
    def _translate_priority(priority: str | None) -> str:
        if not priority:
            return '—'
        raw = (priority or '').strip()
        mapping = {
            'critical': 'Критический',
            'high': 'Высокий',
            'medium': 'Обычный',
            'normal': 'Обычный',
            'low': 'Низкий',
        }
        return mapping.get(raw.lower(), raw)

    @classmethod
    def update_priority(cls, ticket_id: int, actor: Any, priority_value: str | None) -> Dict[str, Any]:
        cls._ensure_operator(actor)
        ticket = SupportTicket.query.get_or_404(ticket_id)

        raw = (priority_value or '').strip().lower()
        mapping = {
            'low': 'low',
            'medium': 'medium',
            'normal': 'normal',
            'high': 'high',
            'critical': 'critical',
            'низкий': 'low',
            'обычный': 'normal',
            'средний': 'medium',
            'высокий': 'high',
            'критический': 'critical',
        }
        if raw not in mapping:
            raise ValidationError('Некорректный приоритет')

        old_priority = (ticket.priority or '').strip() or None
        ticket.priority = mapping[raw]
        if old_priority != ticket.priority:
            db.session.add(TicketHistory(
                ticket_id=ticket.id,
                user_id=actor.id,
                field='priority',
                old_value=cls._translate_priority(old_priority),
                new_value=cls._translate_priority(ticket.priority),
            ))
        db.session.commit()
        return {
            'priority': ticket.priority,
            'priority_display': cls._translate_priority(ticket.priority),
        }

    @classmethod
    def toggle_critical(cls, ticket_id: int, actor: Any) -> Dict[str, Any]:
        cls._ensure_operator(actor)
        ticket = SupportTicket.query.get_or_404(ticket_id)

        old_value = (ticket.priority or '').strip()
        was_on = old_value.lower() in {'critical', 'критический'}
        new_is_on = not was_on
        ticket.priority = 'critical' if new_is_on else 'normal'

        db.session.add(TicketHistory(
            ticket_id=ticket.id,
            user_id=actor.id,
            field='important_task',
            old_value='Да' if was_on else 'Нет',
            new_value='Да' if new_is_on else 'Нет',
        ))
        db.session.commit()
        return {
            'is_important': new_is_on,
            'is_critical': new_is_on,
            'priority': ticket.priority,
            'priority_display': cls._translate_priority(ticket.priority),
        }


    @staticmethod
    def _can_access_ticket(ticket: Any, actor: Any) -> bool:
        role = (getattr(actor, 'role', None) or '').strip().lower()
        if role in {'admin', 'operator'}:
            return True
        actor_email = (getattr(actor, 'email', None) or '').strip().lower()
        ticket_email = (getattr(ticket, 'email', None) or '').strip().lower()
        return bool(actor_email and ticket_email and actor_email == ticket_email) or getattr(ticket, 'client_id', None) == getattr(actor, 'id', None)

    @classmethod
    def _get_ticket_for_actor(cls, ticket_id: int, actor: Any) -> Any:
        ticket = SupportTicket.query.get_or_404(ticket_id)
        if not cls._can_access_ticket(ticket, actor):
            raise PermissionDenied('Недостаточно прав')
        return ticket

    @classmethod
    def finish_modal(cls, ticket_id: int, actor: Any, finish_choice: str | None, finish_comment: str | None) -> Dict[str, Any]:
        cls._ensure_operator(actor)
        ticket = SupportTicket.query.get_or_404(ticket_id)
        choice = (finish_choice or '').strip().lower()
        comment = (finish_comment or '').strip()

        if choice == 'waiting':
            if not getattr(ticket, 'pinned_result_id', None):
                raise ValidationError('Нельзя перевести в ожидание без закрепленного результата в комментариях')
            old_status = ticket.status
            ticket.status = 'Ожидание'
            ticket.waiting_for_client_feedback = True
            ticket.marked_as_completed_at = utcnow()
            ticket.close_reason = None
            ticket.is_spam = False
            db.session.add(TicketHistory(
                ticket_id=ticket.id,
                user_id=actor.id,
                field='status',
                old_value=old_status,
                new_value='Ожидание',
                note='Ожидание подтверждения от клиента',
            ))
            db.session.commit()
            return {'ticket': ticket, 'status': ticket.status}

        reason_map = {
            'spam': 'Спам',
            'duplicate': 'Дубликат',
            'wrong': 'Ошибочная',
            'withdrawn': 'Отозванная',
        }
        if choice not in reason_map:
            raise ValidationError('Выберите причину закрытия')

        old_status = ticket.status
        ticket.status = 'Завершена'
        ticket.waiting_for_client_feedback = False
        ticket.closed_at = utcnow()
        ticket.is_resolved = True
        ticket.close_reason = choice
        ticket.is_spam = (choice == 'spam')
        system_message = f"<p><strong>Заявка закрыта оператором.</strong> Причина: <strong>{reason_map[choice]}</strong></p>"
        if comment:
            system_message += f"<div class='mt-2'><strong>Комментарий:</strong><br>{escape(comment)}</div>"
        db.session.add(TicketMessage(
            ticket_id=ticket.id,
            user_id=actor.id,
            message=system_message,
            is_operator=True,
        ))
        db.session.add(TicketHistory(
            ticket_id=ticket.id,
            user_id=actor.id,
            field='status',
            old_value=old_status,
            new_value='Завершена',
            note=f'Закрыто: {choice}',
        ))
        db.session.commit()
        return {'ticket': ticket, 'status': ticket.status, 'close_reason': choice}

    @classmethod
    def add_comment(cls, ticket_id: int, actor: Any, message_text: str | None, uploaded_files: Iterable[Any] | None = None) -> Dict[str, Any]:
        ticket = cls._get_ticket_for_actor(ticket_id, actor)
        text = (message_text or '').strip()
        files = [f for f in (uploaded_files or []) if getattr(f, 'filename', '') and str(f.filename).strip()]
        if not text and not files:
            raise ValidationError('Комментарий пустой')
        if (ticket.status or '').strip() == 'Завершена':
            raise ValidationError('Нельзя добавлять комментарии в закрытой заявке')

        role = (getattr(actor, 'role', None) or '').strip().lower()
        is_operator = role in {'operator', 'admin'}
        message = TicketMessage(
            ticket_id=ticket.id,
            user_id=actor.id,
            message=text,
            is_operator=is_operator,
        )
        db.session.add(message)
        db.session.flush()

        upload_root = os.path.join('static', 'uploads', 'attachments')
        os.makedirs(upload_root, exist_ok=True)
        from helpdesk_app.utils.files import allowed_file, safe_upload_name
        for uploaded_file in files:
            original_name = str(getattr(uploaded_file, 'filename', '') or '').strip()
            if not allowed_file(original_name):
                raise ValidationError(f'Недопустимый тип файла: {original_name}')
            unique_name = safe_upload_name(original_name)
            file_path = os.path.join(upload_root, unique_name)
            uploaded_file.save(file_path)
            db.session.add(TicketAttachment(
                message_id=message.id,
                filename=unique_name,
                original_name=original_name,
                size=os.path.getsize(file_path),
                url=f'/static/uploads/attachments/{unique_name}',
            ))

        db.session.add(TicketHistory(
            ticket_id=ticket.id,
            user_id=actor.id,
            field='comment',
            old_value=None,
            new_value='Комментарий добавлен',
            note='Комментарий добавлен через карточку заявки',
        ))
        db.session.commit()
        return {'ticket': ticket, 'message': message}
