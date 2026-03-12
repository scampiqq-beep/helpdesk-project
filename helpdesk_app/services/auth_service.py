from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash
from helpdesk_app.models.base import db
from helpdesk_app.models.users import User


class AuthService:
    @staticmethod
    def _legacy():
        from helpdesk_app.runtime import get_runtime
        return get_runtime()

    @classmethod
    def register(cls):
        legacy = cls._legacy()

        if request.method == 'POST':
            email = (request.form.get('email') or '').strip().lower()
            password = (request.form.get('password') or '').strip()
            password2 = (request.form.get('password2') or '').strip()

            if not email:
                flash('Email обязателен', 'error')
            elif not password:
                flash('Пароль обязателен', 'error')
            elif len(password) < 6:
                flash('Пароль должен содержать не менее 6 символов', 'error')
            elif password != password2:
                flash('Пароли не совпадают', 'error')
            elif User.query.filter(db.func.lower(User.email) == email.lower()).first():
                flash('Email уже зарегистрирован', 'error')
            else:
                user = User(
                    username=email,
                    email=email,
                    password=generate_password_hash(password, method='pbkdf2:sha256'),
                    is_active=True,
                    role='client',
                    email_verified=False,
                )
                db.session.add(user)
                db.session.commit()
                legacy.send_email_verification(user)
                flash('Регистрация успешна! Проверьте почту для подтверждения.', 'success')
                return redirect(url_for('login'))

            return render_template('register.html', email=email)

        return render_template('register.html')

    @classmethod
    def confirm_email(cls, token: str):
        legacy = cls._legacy()
        email = legacy.confirm_token(token)
        if not email:
            flash('Ссылка недействительна или устарела.', 'error')
            return redirect(url_for('login'))

        user = User.query.filter(db.func.lower(User.email) == email.lower()).first()
        if not user:
            flash('Пользователь не найден.', 'error')
            return redirect(url_for('login'))

        if user.email_verified:
            flash('Ваш email уже подтверждён.', 'info')
        else:
            user.email_verified = True
            legacy.db.session.commit()
            flash('Email успешно подтверждён!', 'success')

        return redirect(url_for('login'))
