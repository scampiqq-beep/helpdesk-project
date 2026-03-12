from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash
from helpdesk_app.models.users import User

from helpdesk_app.services.auth_service import AuthService
from helpdesk_app.services.system_service import SystemService

bp = Blueprint('auth_bp', __name__)


def login():
    from helpdesk_app.runtime import get_runtime
    legacy = get_runtime()
    db = legacy.db

    if current_user.is_authenticated:
        return redirect(url_for('ticket_list'))

    if request.method == 'POST':
        identifier = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()

        user = None
        ident = identifier.strip()

        if '@' in ident and '.' in ident:
            candidate = User.query.filter(db.func.lower(User.email) == ident.lower()).first()
        else:
            candidate = None

        if not candidate:
            candidate = User.query.filter_by(username=ident).first()

        if candidate and check_password_hash(candidate.password, password):
            if not candidate.is_active:
                flash('Аккаунт заблокирован', 'error')
            elif candidate.is_client() and not candidate.email_verified:
                login_user(candidate)
                flash('Подтвердите email', 'warning')
                return redirect(url_for('unverified'))
            else:
                user = candidate

        if user:
            login_user(user)
            return redirect(url_for('ticket_list'))

        flash('Неверный email/логин или пароль', 'error')

    return render_template('login.html')


@login_required
def unverified():
    if getattr(current_user, 'role', None) == 'client' and current_user.email_verified:
        return redirect(url_for('ticket_list'))
    return render_template('unverified.html')


@login_required
def resend_verification():
    from helpdesk_app.runtime import get_runtime
    legacy = get_runtime()

    if getattr(current_user, 'role', None) == 'client' and not current_user.email_verified:
        legacy.send_email_verification(current_user)
        flash('Письмо с подтверждением отправлено повторно. Проверьте почту (включая папку «Спам»).', 'info')
    return redirect(url_for('unverified'))


def register():
    return AuthService.register()


def confirm_email(token):
    return AuthService.confirm_email(token)


def api_system_time():
    return SystemService.system_time_response()



def api_system_health():
    from helpdesk_app.services.system_health_service import SystemHealthService
    payload = SystemHealthService.get_health_payload()
    status = 200 if payload.get('ok') else 503
    return jsonify(payload), status


def logout():
    logout_user()
    return redirect(url_for('login'))


EXTRACTED_ENDPOINTS = {
    'login': login,
    'register': register,
    'confirm_email': confirm_email,
    'unverified': unverified,
    'resend_verification': resend_verification,
    'api_system_time': api_system_time,
    'api_system_health': api_system_health,
    'logout': logout,
}
