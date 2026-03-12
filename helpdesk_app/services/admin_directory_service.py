from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from helpdesk_app.services.admin_service import AdminAccessDenied, AdminService


class AdminDirectoryService:
    @staticmethod
    def _legacy():
        from helpdesk_app.runtime import get_runtime
        return get_runtime()

    @classmethod
    def ensure_admin(cls):
        return AdminService.ensure_admin()

    @classmethod
    def render_close_reasons(cls):
        cls.ensure_admin()
        legacy = cls._legacy()
        reasons = TicketCloseReason.query.order_by(
            TicketCloseReason.sort_order.asc(),
            TicketCloseReason.name.asc(),
        ).all()
        return render_template('admin_close_reasons.html', reasons=reasons)

    @classmethod
    def _parse_form(cls, reason=None):
        code = (request.form.get('code') or '').strip()
        name = (request.form.get('name') or '').strip()
        sort_order_raw = (request.form.get('sort_order') or '0').strip()
        sort_order = int(sort_order_raw) if sort_order_raw.lstrip('-').isdigit() else 0
        is_active = request.form.get('is_active') in ('1', 'on', 'true', 'yes')
        require_comment = request.form.get('require_comment') in ('1', 'on', 'true', 'yes')
        if reason is not None:
            reason.code = code
            reason.name = name
            reason.sort_order = sort_order
            reason.is_active = is_active
            reason.require_comment = require_comment
        return {
            'code': code,
            'name': name,
            'sort_order': sort_order,
            'is_active': is_active,
            'require_comment': require_comment,
        }

    @classmethod
    def create_close_reason(cls):
        cls.ensure_admin()
        legacy = cls._legacy()
        if request.method == 'POST':
            data = cls._parse_form()
            if not data['code'] or not data['name']:
                flash('Заполните code и name', 'error')
                return render_template('admin_close_reason_form.html', reason=None)
            exists = TicketCloseReason.query.filter(
                db.func.lower(TicketCloseReason.code) == data['code'].lower()
            ).first()
            if exists:
                flash('Такой code уже существует', 'error')
                return render_template('admin_close_reason_form.html', reason=None)
            try:
                db.session.add(TicketCloseReason(**data))
                db.session.commit()
                flash('Причина закрытия добавлена', 'success')
                return redirect(url_for('admin_close_reasons'))
            except Exception as exc:
                db.session.rollback()
                flash(f'Ошибка: {exc}', 'error')
        return render_template('admin_close_reason_form.html', reason=None)

    @classmethod
    def edit_close_reason(cls, reason_id: int):
        cls.ensure_admin()
        legacy = cls._legacy()
        reason = TicketCloseReason.query.get_or_404(reason_id)
        if request.method == 'POST':
            cls._parse_form(reason)
            if not reason.code or not reason.name:
                flash('Заполните code и name', 'error')
                return render_template('admin_close_reason_form.html', reason=reason)
            exists = TicketCloseReason.query.filter(
                db.func.lower(TicketCloseReason.code) == reason.code.lower(),
                TicketCloseReason.id != reason.id,
            ).first()
            if exists:
                flash('Такой code уже существует', 'error')
                return render_template('admin_close_reason_form.html', reason=reason)
            try:
                db.session.commit()
                flash('Сохранено', 'success')
                return redirect(url_for('admin_close_reasons'))
            except Exception as exc:
                db.session.rollback()
                flash(f'Ошибка: {exc}', 'error')
        return render_template('admin_close_reason_form.html', reason=reason)

    @classmethod
    def delete_close_reason(cls, reason_id: int):
        cls.ensure_admin()
        legacy = cls._legacy()
        reason = TicketCloseReason.query.get_or_404(reason_id)
        try:
            reason.is_active = False
            db.session.commit()
            flash('Причина выключена', 'success')
        except Exception as exc:
            db.session.rollback()
            flash(f'Ошибка: {exc}', 'error')
        return redirect(url_for('admin_close_reasons'))
