from __future__ import annotations

from typing import Any

from flask import flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash
from flask_login import current_user
from helpdesk_app.models.base import db
from helpdesk_app.models.users import User


class AdminAccessDenied(Exception):
    pass


class AdminService:
    """Bridge-сервис для admin UI.

    На этом этапе не ломаем рабочий legacy-код, но выносим admin-flow в одну
    точку: доступ, dashboard context, users list и безопасные fallback'и.
    """

    @staticmethod
    def _legacy():
        from helpdesk_app.runtime import get_runtime
        return get_runtime()

    @classmethod
    def ensure_admin(cls, actor: Any | None = None):
        actor = actor or current_user
        if getattr(actor, 'role', None) != 'admin':
            raise AdminAccessDenied('Доступ запрещён')
        return actor

    @classmethod
    def ensure_admin_or_operator(cls, actor: Any | None = None):
        actor = actor or current_user
        legacy = cls._legacy()
        is_admin = getattr(actor, 'role', None) == 'admin'
        can_manage = bool(is_admin or legacy.is_tp_operator(actor))
        if not can_manage:
            raise AdminAccessDenied('Доступ запрещён')
        return actor

    @classmethod
    def deny_response(cls, actor: Any | None = None):
        actor = actor or current_user
        legacy = cls._legacy()
        flash('Доступ запрещён', 'error')
        if isinstance(actor, getattr(legacy, 'User', object)) and getattr(actor, 'role', None) != 'client':
            return redirect(url_for('kanban'))
        return redirect(url_for('ticket_list'))

    @classmethod
    def dashboard_context(cls):
        actor = cls.ensure_admin_or_operator()
        legacy = cls._legacy()
        user_model = User
        SupportTicket = legacy.SupportTicket
        is_admin = getattr(actor, 'role', None) == 'admin'
        is_operator = bool(legacy.is_tp_operator(actor))
        return {
            'new_tickets': SupportTicket.query.filter_by(status='Новая').order_by(SupportTicket.created_at.desc()).all(),
            'total_tickets': SupportTicket.query.count(),
            'resolved_count': SupportTicket.query.filter_by(status='Завершена').count(),
            'operators_count': user_model.query.filter(user_model.role.in_(['admin', 'operator'])).count(),
            'is_admin': is_admin,
            'is_operator': is_operator,
        }

    @classmethod
    def render_dashboard(cls):
        return render_template('admin_dashboard.html', **cls.dashboard_context())

    @classmethod
    def render_charts(cls):
        cls.ensure_admin()
        return render_template('admin_charts.html')

    @classmethod
    def render_audit(cls):
        cls.ensure_admin()
        from helpdesk_app.services.audit_service import AuditService
        action = request.args.get('action', '')
        actor = request.args.get('actor', '')
        target_type = request.args.get('target_type', '')
        logs = AuditService.list_records(action=action, actor=actor, target_type=target_type)
        return render_template(
            'admin_audit.html',
            logs=logs,
            action=action,
            actor=actor,
            target_type=target_type,
        )


    @classmethod
    def _back_args(cls):
        return {
            'q': request.args.get('q') or None,
            'role': request.args.get('role') or None,
            'sort': request.args.get('sort') or None,
            'dir': request.args.get('dir') or None,
            'page': request.args.get('page') or None,
            'per_page': request.args.get('per_page') or None,
        }

    @classmethod
    def _back_users(cls):
        return redirect(url_for('admin_users', **cls._back_args()))

    @classmethod
    def handle_users_post(cls):
        actor = cls.ensure_admin_or_operator()
        legacy = cls._legacy()
        user_model = User
        Department = legacy.Department
        is_admin = getattr(actor, 'role', None) == 'admin'
        action = (request.form.get('action') or '').strip()
        if action not in {'reset_user_password', 'delete_user', 'add_user', 'edit_user'}:
            return None

        if action == 'reset_user_password':
            if not is_admin:
                flash('Недостаточно прав', 'error')
                return cls._back_users()
            user_id = request.form.get('user_id')
            user = legacy.db.session.get(user_model, user_id) if user_id else None
            if user and user.id != actor.id:
                user.password = generate_password_hash('new_password', method='pbkdf2:sha256')
                db.session.commit()
                flash('Пароль сброшен на: new_password', 'success')
            return cls._back_users()

        if action == 'delete_user':
            if not is_admin:
                flash('Недостаточно прав', 'error')
                return cls._back_users()
            user_id = request.form.get('user_id')
            user = legacy.db.session.get(user_model, user_id) if user_id else None
            if not user:
                flash('Пользователь не найден', 'error')
                return cls._back_users()
            if user.id == actor.id:
                flash('Нельзя удалить текущего пользователя', 'error')
                return cls._back_users()
            if getattr(user, 'role', None) == 'admin':
                flash('Нельзя удалить администратора', 'error')
                return cls._back_users()
            try:
                db.session.delete(user)
                db.session.commit()
                flash('Пользователь удалён', 'success')
            except Exception as exc:
                db.session.rollback()
                flash(f'Ошибка удаления: {exc}', 'error')
            return cls._back_users()

        if action == 'add_user':
            add_errors = {}
            role = (request.form.get('role') or 'client').strip().lower()
            if role not in ('client', 'operator', 'admin'):
                role = 'client'
            if not is_admin:
                role = 'client'
            email = (request.form.get('email') or '').strip().lower() or None
            username = (request.form.get('username') or '').strip() or (email or '')
            password = (request.form.get('password') or '').strip()
            name_raw = request.form.get('name') or ''
            last_name_raw = request.form.get('last_name') or ''
            patronymic_raw = request.form.get('patronymic') or ''
            phone_raw = request.form.get('phone') or ''
            organization_raw = request.form.get('organization') or ''
            position = legacy._norm_text(request.form.get('position') or '') or None
            inn_raw = request.form.get('inn') or ''
            address_raw = request.form.get('address') or ''
            if role == 'client':
                ok, last_name = legacy.validate_person_part(last_name_raw)
                if not ok: add_errors['last_name'] = last_name
                ok, name = legacy.validate_person_part(name_raw)
                if not ok: add_errors['name'] = name
                ok, patronymic = legacy.validate_person_part(patronymic_raw)
                if not ok: add_errors['patronymic'] = patronymic
            else:
                last_name = legacy._norm_text(last_name_raw) or None
                name = legacy._norm_text(name_raw) or None
                patronymic = legacy._norm_text(patronymic_raw) or None
            ok, phone = legacy.normalize_phone(phone_raw)
            if not ok: add_errors['phone'] = phone
            ok, organization = legacy.validate_org(organization_raw)
            if not ok: add_errors['organization'] = organization
            ok, inn = legacy.validate_inn_ru(inn_raw, required=False)
            if not ok: add_errors['inn'] = inn
            ok, address = legacy.validate_address(address_raw, required=False)
            if not ok: add_errors['address'] = address
            email_verified = bool(request.form.get('email_verified') == 'on')
            department_ids = request.form.getlist('department_ids') if is_admin else []
            if not username:
                add_errors['username'] = 'Логин обязателен'
            if not email:
                add_errors['email'] = 'Email обязателен'
            if not password:
                add_errors['password'] = 'Пароль обязателен'
            elif len(password) < 6:
                add_errors['password'] = 'Минимум 6 символов'
            if username and user_model.query.filter_by(username=username).first():
                add_errors['username'] = 'Логин уже занят'
            if email and user_model.query.filter(legacy.db.func.lower(user_model.email) == email.lower()).first():
                add_errors['email'] = 'Email уже используется'
            if add_errors:
                flash('Проверьте поля формы', 'error')
                add_data = {k: request.form.get(k) or '' for k in ('role','username','email','last_name','name','patronymic','phone','organization','position','inn','address')}
                return cls.render_users_page(open_add_modal=True, add_errors=add_errors, add_data=add_data)
            try:
                user = user_model(
                    username=username,
                    name=(name or None),
                    last_name=(last_name or None),
                    patronymic=(patronymic or None),
                    email=email,
                    password=generate_password_hash(password, method='pbkdf2:sha256'),
                    role=role,
                    email_verified=email_verified if role == 'client' else True,
                    phone=(phone or None),
                    organization=(organization or None),
                    position=position,
                    inn=(inn or None),
                    address=(address or None),
                )
                db.session.add(user)
                legacy.db.session.flush()
                if role in ('operator', 'admin') and department_ids:
                    dept_ids = [int(x) for x in department_ids if str(x).isdigit()]
                    departments = Department.query.filter(Department.id.in_(dept_ids)).all()
                    if departments:
                        user.department_id = departments[0].id
                        user.departments = departments
                db.session.commit()
                flash('Пользователь создан', 'success')
            except Exception as exc:
                db.session.rollback()
                flash(f'Ошибка при создании: {exc}', 'error')
            return cls._back_users()

        if action == 'edit_user':
            user_id = request.form.get('user_id')
            user = legacy.db.session.get(user_model, user_id) if user_id else None
            if not user:
                flash('Пользователь не найден', 'error')
                return cls._back_users()
            if not is_admin and (getattr(user, 'role', None) or 'client') != 'client':
                flash('Недостаточно прав для редактирования этого пользователя', 'error')
                return cls._back_users()
            role = (request.form.get('role') or user.role or 'client').strip().lower()
            if role not in ('client', 'operator', 'admin'):
                role = user.role
            if not is_admin:
                role = 'client'
            username = (request.form.get('username') or '').strip()
            email = (request.form.get('email') or '').strip().lower() or None
            if not username:
                flash('Логин обязателен', 'error')
                return cls._back_users()
            if not email:
                flash('Email обязателен', 'error')
                return cls._back_users()
            if user_model.query.filter(user_model.username == username, user_model.id != user.id).first():
                flash('Логин уже занят', 'error')
                return cls._back_users()
            if user_model.query.filter(legacy.db.func.lower(user_model.email) == email.lower(), user_model.id != user.id).first():
                flash('Email уже используется', 'error')
                return cls._back_users()
            name_raw = request.form.get('name') or ''
            last_name_raw = request.form.get('last_name') or ''
            patronymic_raw = request.form.get('patronymic') or ''
            phone_raw = request.form.get('phone') or ''
            organization_raw = request.form.get('organization') or ''
            position = legacy._norm_text(request.form.get('position') or '') or None
            inn_raw = request.form.get('inn') or ''
            address_raw = request.form.get('address') or ''
            if role == 'client':
                ok, last_name = legacy.validate_person_part(last_name_raw)
                if not ok: flash(f'Фамилия: {last_name}', 'error'); return cls._back_users()
                ok, name = legacy.validate_person_part(name_raw)
                if not ok: flash(f'Имя: {name}', 'error'); return cls._back_users()
                ok, patronymic = legacy.validate_person_part(patronymic_raw)
                if not ok: flash(f'Отчество: {patronymic}', 'error'); return cls._back_users()
            else:
                for label, raw in (('Фамилия', last_name_raw), ('Имя', name_raw), ('Отчество', patronymic_raw)):
                    if legacy._norm_text(raw):
                        ok, value = legacy.validate_person_part(raw)
                        if not ok:
                            flash(f'{label}: {value}', 'error')
                            return cls._back_users()
                last_name = legacy._norm_text(last_name_raw) or None
                name = legacy._norm_text(name_raw) or None
                patronymic = legacy._norm_text(patronymic_raw) or None
            ok, phone = legacy.normalize_phone(phone_raw)
            if not ok: flash(phone, 'error'); return cls._back_users()
            ok, organization = legacy.validate_org(organization_raw)
            if not ok: flash(f'Организация: {organization}', 'error'); return cls._back_users()
            ok, inn = legacy.validate_inn_ru(inn_raw, required=False)
            if not ok: flash(f'ИНН: {inn}', 'error'); return cls._back_users()
            ok, address = legacy.validate_address(address_raw, required=False)
            if not ok: flash(f'Адрес: {address}', 'error'); return cls._back_users()
            try:
                user.username = username
                user.email = email
                user.role = role
                user.name = name or None
                user.last_name = last_name or None
                user.patronymic = patronymic or None
                user.phone = phone or None
                user.organization = organization or None
                user.position = position
                user.inn = inn or None
                user.address = address or None
                new_pass = (request.form.get('new_password') or '').strip()
                if new_pass and is_admin:
                    user.password = generate_password_hash(new_pass, method='pbkdf2:sha256')
                user.email_verified = bool(request.form.get('email_verified') == 'on') if role == 'client' else True
                department_ids = request.form.getlist('department_ids') if is_admin else []
                if role in ('operator', 'admin') and department_ids:
                    dept_ids = [int(x) for x in department_ids if str(x).isdigit()]
                    departments = Department.query.filter(Department.id.in_(dept_ids)).all()
                    user.department_id = departments[0].id if departments else None
                    user.departments = departments
                else:
                    user.department_id = None
                    user.departments = []
                db.session.commit()
                flash('Изменения сохранены', 'success')
            except Exception as exc:
                db.session.rollback()
                flash(f'Ошибка сохранения: {exc}', 'error')
            return cls._back_users()

        return None

    @classmethod
    def render_users_page(cls, open_add_modal: bool = False, add_errors: dict | None = None, add_data: dict | None = None):
        """GET-only версия списка пользователей, вынесенная из legacy.

        POST-действия пока остаются в legacy, чтобы не ломать рабочие формы.
        """
        actor = cls.ensure_admin_or_operator()
        legacy = cls._legacy()
        user_model = User
        Department = legacy.Department
        is_admin = getattr(actor, 'role', None) == 'admin'
        can_manage_users = bool(is_admin or legacy.is_tp_operator(actor))
        departments = Department.query.order_by(Department.name.asc()).all()

        q = (request.args.get('q') or '').strip().lower()
        role_filter = (request.args.get('role') or '').strip().lower()
        if role_filter not in ('', 'client', 'operator', 'admin'):
            role_filter = ''
        sort = (request.args.get('sort') or 'created_at').strip().lower()
        direction = (request.args.get('dir') or 'desc').strip().lower()
        if direction not in ('asc', 'desc'):
            direction = 'desc'

        try:
            page = int(request.args.get('page') or 1)
        except Exception:
            page = 1
        try:
            per_page = int(request.args.get('per_page') or 25)
        except Exception:
            per_page = 25
        if per_page not in (10, 25, 50, 100):
            per_page = 25
        if page < 1:
            page = 1

        base = user_model.query
        if q:
            base = base.filter(
                legacy.db.or_(
                    legacy.db.func.lower(user_model.username).contains(q),
                    legacy.db.func.lower(user_model.email).contains(q),
                    legacy.db.func.lower(user_model.name).contains(q),
                    legacy.db.func.lower(user_model.last_name).contains(q),
                )
            )
        if role_filter:
            base = base.filter(user_model.role == role_filter)

        if sort == 'id':
            order_col = user_model.id
        elif sort == 'role':
            order_col = legacy.db.case((user_model.role == 'admin', 0), (user_model.role == 'operator', 1), else_=2)
        else:
            sort = 'created_at'
            order_col = user_model.created_at

        if direction == 'asc':
            base = base.order_by(order_col.asc(), user_model.id.asc())
        else:
            base = base.order_by(order_col.desc(), user_model.id.desc())

        try:
            pagination = base.paginate(page=page, per_page=per_page, error_out=False)
            users = pagination.items
        except Exception:
            pagination = None
            users = base.all()

        return render_template(
            'admin_users.html',
            users=users,
            pagination=pagination,
            departments=departments,
            q=q,
            role_filter=role_filter,
            sort=sort,
            direction=direction,
            page=page,
            per_page=per_page,
            total_departments=len(departments),
            USER_ROLES=getattr(legacy, 'USER_ROLES', {}),
            is_admin=is_admin,
            can_manage_users=can_manage_users,
            open_add_modal=open_add_modal,
            add_errors=add_errors,
            add_data=add_data,
        )

    @classmethod
    def call_legacy(cls, endpoint_name: str, *args, **kwargs):
        legacy = cls._legacy()
        return getattr(legacy, endpoint_name)(*args, **kwargs)
