from __future__ import annotations

from flask import Blueprint, redirect, request, url_for
from flask_login import login_required

from helpdesk_app.services import NotificationService, ProfileService

bp = Blueprint('client_bp', __name__)


@login_required
def create_manual_ticket():
    return redirect(url_for('create_ticket'))


@login_required
def user_profile():
    return ProfileService.handle_request()


@login_required
def notifications_page():
    return NotificationService.render_page()


@login_required
def open_notification(notification_id: int):
    return NotificationService.open_notification(notification_id)


@login_required
def notifications_mark_all_read():
    return NotificationService.mark_all_read()


EXTRACTED_ENDPOINTS = {
    'create_manual_ticket': create_manual_ticket,
    'user_profile': user_profile,
    'notifications_page': notifications_page,
    'open_notification': open_notification,
    'notifications_mark_all_read': notifications_mark_all_read,
}
