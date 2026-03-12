from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user
from helpdesk_app.models.notifications import Notification
from helpdesk_app.models.tickets import SupportTicket
from helpdesk_app.models.users import User


class NotificationService:
    """Сервис уведомлений поверх текущих legacy-моделей.

    На этом шаге выносим list/open/mark-read из монолита, но не меняем схему БД.
    """

    @staticmethod
    def _legacy():
        from helpdesk_app.runtime import get_runtime
        return get_runtime()

    @classmethod
    def render_page(cls):
        legacy = cls._legacy()
        recipient_type, recipient_id = legacy._recipient_key(current_user)
        page = request.args.get('page', type=int, default=1)
        per_page = 30
        accessible_ids = legacy._accessible_ticket_ids_for_notifications(current_user)

        qs = (
            Notification.query
            .filter_by(recipient_type=recipient_type, recipient_id=recipient_id)
            .order_by(Notification.created_at.desc())
        )

        if accessible_ids is None:
            qs_vis = qs
        else:
            if accessible_ids:
                qs_vis = qs.filter(
                    legacy.or_(
                        Notification.ticket_id.is_(None),
                        Notification.ticket_id.in_(list(accessible_ids)),
                    )
                )
            else:
                qs_vis = qs.filter(Notification.ticket_id.is_(None))

        total = qs_vis.count()
        pages = (total + per_page - 1) // per_page if total else 1
        items = qs_vis.offset((page - 1) * per_page).limit(per_page).all()
        items = legacy._filter_notifications_for_user(current_user, items)
        opchat_threads = []
        if isinstance(current_user, User):
            opchat_threads = legacy._opchat_unread_threads_for_user(current_user.id, limit=20)

        return render_template(
            'notifications.html',
            items=items,
            page=page,
            pages=pages,
            total=total,
            opchat_threads=opchat_threads,
        )

    @classmethod
    def open_notification(cls, notification_id: int):
        legacy = cls._legacy()
        try:
            recipient_type, recipient_id = legacy._recipient_key(current_user)
            notification = Notification.query.filter_by(
                id=notification_id,
                recipient_type=recipient_type,
                recipient_id=recipient_id,
            ).first_or_404()

            notification.is_read = True
            legacy.db.session.commit()

            ticket_id = legacy._notification_ticket_id(notification)
            if ticket_id:
                ticket = SupportTicket.query.get(ticket_id)
                if not ticket or not legacy._user_has_access_to_ticket_for_notifications(current_user, ticket):
                    legacy.flash_msg('Доступ к заявке запрещён — уведомление скрыто из списка', 'warning')
                    return redirect(url_for('notifications_page'))

            if notification.url:
                return redirect(notification.url)
        except Exception:
            legacy.db.session.rollback()
        return redirect(url_for('ticket_list'))

    @classmethod
    def mark_all_read(cls):
        legacy = cls._legacy()
        try:
            recipient_type, recipient_id = legacy._recipient_key(current_user)
            Notification.query.filter_by(
                recipient_type=recipient_type,
                recipient_id=recipient_id,
                is_read=False,
            ).update({'is_read': True})
            legacy.db.session.commit()
            legacy.flash_msg('Уведомления отмечены как прочитанные', 'success')
        except Exception:
            legacy.db.session.rollback()
            legacy.flash_msg('Не удалось отметить уведомления', 'error')
        return redirect(request.referrer or url_for('ticket_list'))
