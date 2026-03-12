from __future__ import annotations

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from helpdesk_app.models.tickets import SupportTicket
from helpdesk_app.models.users import User


class ProfileService:
    """Вынесенная логика страницы профиля пользователя."""

    @staticmethod
    def _legacy():
        from helpdesk_app.runtime import get_runtime
        return get_runtime()

    @classmethod
    def _redirect(cls):
        return redirect(url_for('user_profile'))

    @classmethod
    def handle_request(cls):
        if request.method == 'POST':
            handled = cls.handle_post()
            if handled is not None:
                return handled
        return cls.render_page()

    @classmethod
    def handle_post(cls):
        legacy = cls._legacy()
        action = request.form.get('action')
        if not action:
            return None

        if action == 'update_profile':
            old_email = current_user.email
            name = request.form.get('name', '')
            last_name = request.form.get('last_name', '')
            patronymic = request.form.get('patronymic', '')
            email = request.form.get('email', '').strip().lower() or old_email

            for label, raw in (("Фамилия", last_name), ("Имя", name), ("Отчество", patronymic)):
                if legacy._norm_text(raw):
                    ok, value = legacy.validate_person_part(raw)
                    if not ok:
                        flash(f'{label}: {value}', 'error')
                        return cls._redirect()

            if getattr(current_user, 'role', None) == 'client' and not email:
                flash('Email обязателен', 'error')
                return cls._redirect()

            if email != old_email:
                existing = User.query.filter_by(email=email).first()
                if existing:
                    flash('Этот email уже используется', 'error')
                    return cls._redirect()

            current_user.name = legacy._norm_text(name) or None
            current_user.last_name = legacy._norm_text(last_name) or None
            current_user.patronymic = legacy._norm_text(patronymic) or None
            current_user.email = email
            try:
                legacy.db.session.commit()
                if email != old_email and hasattr(current_user, 'email_verified'):
                    current_user.email_verified = False
                    legacy.db.session.commit()
                    flash('На новый email отправлено письмо для подтверждения.', 'info')
                else:
                    flash('Профиль обновлён', 'success')
            except Exception:
                legacy.db.session.rollback()
                flash('Ошибка при сохранении профиля', 'error')
            return cls._redirect()

        if action == 'update_phone':
            ok, phone = legacy.normalize_phone(request.form.get('phone', ''))
            if not ok:
                flash(phone, 'error')
                return cls._redirect()
            current_user.phone = phone or None
            try:
                legacy.db.session.commit()
                flash('Телефон обновлён', 'success')
            except Exception:
                legacy.db.session.rollback()
                flash('Ошибка при сохранении телефона', 'error')
            return cls._redirect()

        if action == 'update_notifications':
            current_user.notify_inapp_enabled = request.form.get('notify_inapp_enabled') == 'on'
            current_user.notify_event_assigned = request.form.get('notify_event_assigned') == 'on'
            current_user.notify_event_customer_reply = request.form.get('notify_event_customer_reply') == 'on'
            current_user.notify_event_status = request.form.get('notify_event_status') == 'on'
            try:
                legacy.db.session.commit()
                flash('Настройки уведомлений сохранены', 'success')
            except Exception:
                legacy.db.session.rollback()
                flash('Ошибка при сохранении настроек уведомлений', 'error')
            return cls._redirect()

        if action == 'update_org':
            if getattr(current_user, 'role', None) != 'client':
                abort(403)
            organization_raw = request.form.get('organization', '')
            position_raw = request.form.get('position', '')
            inn_raw = request.form.get('inn', '')
            address_raw = request.form.get('address', '')

            ok, org_v = legacy.validate_org(organization_raw)
            if not ok:
                flash(f'Организация: {org_v}', 'error')
                return cls._redirect()
            ok, inn_v = legacy.validate_inn_ru(inn_raw, required=True)
            if not ok:
                flash(f'ИНН: {inn_v}', 'error')
                return cls._redirect()
            ok, addr_v = legacy.validate_address(address_raw, required=True)
            if not ok:
                flash(f'Адрес: {addr_v}', 'error')
                return cls._redirect()
            pos_v = legacy._norm_text(position_raw)
            if legacy._contains_url_like(pos_v) or legacy._contains_html_like(pos_v):
                flash('Должность: ссылки и HTML запрещены', 'error')
                return cls._redirect()

            current_user.organization = org_v or None
            current_user.position = pos_v or None
            current_user.inn = inn_v or None
            current_user.address = addr_v or None
            try:
                legacy.db.session.commit()
                flash('Реквизиты обновлены', 'success')
            except Exception:
                legacy.db.session.rollback()
                flash('Ошибка при сохранении реквизитов', 'error')
            return cls._redirect()

        if action == 'apply_suggested_org':
            if getattr(current_user, 'role', None) != 'client':
                abort(403)
            s_org = getattr(current_user, 'suggested_organization', None) or ''
            s_inn = getattr(current_user, 'suggested_inn', None) or ''
            s_addr = getattr(current_user, 'suggested_address', None) or ''
            ok, org_v = legacy.validate_org(s_org)
            ok_inn, inn_v = legacy.validate_inn_ru(s_inn, required=True)
            ok_addr, addr_v = legacy.validate_address(s_addr, required=True)
            if (not ok) or (not legacy._norm_text(org_v)) or (not ok_inn) or (not ok_addr):
                flash('Предложенные реквизиты неполные или некорректные. Заполните реквизиты вручную.', 'error')
                return cls._redirect()
            current_user.organization = org_v or None
            current_user.inn = inn_v or None
            current_user.address = addr_v or None
            current_user.suggested_organization = None
            current_user.suggested_inn = None
            current_user.suggested_address = None
            try:
                legacy.db.session.commit()
                flash('Реквизиты обновлены (принято из CRM).', 'success')
            except Exception:
                legacy.db.session.rollback()
                flash('Ошибка при сохранении реквизитов.', 'error')
            return cls._redirect()

        if action == 'dismiss_suggested_org':
            if getattr(current_user, 'role', None) != 'client':
                abort(403)
            current_user.suggested_organization = None
            current_user.suggested_inn = None
            current_user.suggested_address = None
            try:
                legacy.db.session.commit()
            except Exception:
                legacy.db.session.rollback()
            flash('Предложенные реквизиты скрыты.', 'info')
            return cls._redirect()

        if action == 'change_password':
            current_password = request.form.get('current_password', '').strip()
            new_password = request.form.get('new_password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()
            if not current_password or not new_password or not confirm_password:
                flash('Все поля обязательны', 'error')
                return cls._redirect()
            if not check_password_hash(current_user.password, current_password):
                flash('Текущий пароль неверен', 'error')
                return cls._redirect()
            if new_password != confirm_password:
                flash('Новые пароли не совпадают', 'error')
                return cls._redirect()
            min_length = 8 if isinstance(current_user, User) else 6
            if len(new_password) < min_length:
                flash(f'Пароль должен быть не менее {min_length} символов', 'error')
                return cls._redirect()
            current_user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
            try:
                legacy.db.session.commit()
                if getattr(current_user, 'role', None) == 'client':
                    logout_user()
                    flash('Пароль изменён. Пожалуйста, войдите снова', 'success')
                    return redirect(url_for('login'))
                flash('Пароль успешно изменён', 'success')
            except Exception:
                legacy.db.session.rollback()
                flash('Ошибка при смене пароля', 'error')
            return cls._redirect()

        return None

    @classmethod
    def render_page(cls):
        legacy = cls._legacy()
        tickets_count = 0
        resolved_count = 0
        operator_stats = {}
        if getattr(current_user, 'role', None) == 'client':
            tickets_count = SupportTicket.query.filter_by(email=current_user.email).count()
            resolved_count = SupportTicket.query.filter_by(email=current_user.email, is_resolved=True).count()
        elif isinstance(current_user, User):
            operator_stats = {
                'role_display': dict(legacy.USER_ROLES).get(current_user.role, current_user.role),
                'department': current_user.department.name if current_user.department else '—',
                'username': current_user.username,
            }
        return render_template(
            'user_profile.html',
            tickets_count=tickets_count,
            resolved_count=resolved_count,
            operator_stats=operator_stats,
        )
