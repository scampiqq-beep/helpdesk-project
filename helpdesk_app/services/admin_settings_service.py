from __future__ import annotations

import json
from datetime import datetime, timezone

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user
from helpdesk_app.models.base import db
from helpdesk_app.models.reference import Department, Tag, TicketCategory
from helpdesk_app.models.settings import BitrixSettings, Settings
from mail_parser import clear_mail_parser_log, get_mail_parser_log_page, get_recent_mail_parser_log, test_mail_connection
from helpdesk_app.services.mail_admin_service import DEFAULT_TEMPLATES, MailAdminService
from helpdesk_app.utils.time import to_local


class AdminSettingsService:
    """Bridge-сервис для POST-логики admin settings.

    Обрабатывает наиболее часто используемые действия через новый сервисный слой.
    Всё остальное можно безопасно отдать в legacy.
    """

    HANDLED_ACTIONS = {
        'run_mail_parser_now',
        'save_mail',
        'save_outgoing_mail',
        'test_outgoing_mail_connection',
        'send_outgoing_test_mail',
        'save_mail_template',
        'reset_mail_template',
        'save_notifications_settings',
        'save_system',
        'set_default_intake_department',
        'save_bitrix',
        'add_department',
        'rename_department',
        'delete_department',
        'add_tag',
        'edit_tag',
        'delete_tag',
        'add_ticket_category',
        'edit_ticket_category',
        'delete_ticket_category',
        'save_mail_parser',
        'test_mail_parser_connection',
        'clear_mail_parser_log',
        'save_ticket_importance_rules',
    }

    @staticmethod
    def _legacy():
        from helpdesk_app.runtime import get_runtime
        return get_runtime()

    @classmethod
    def handles(cls, action: str) -> bool:
        return (action or '').strip() in cls.HANDLED_ACTIONS

    @classmethod
    def handle_post(cls):
        legacy = cls._legacy()
        action = (request.form.get('action') or '').strip()
        if not cls.handles(action):
            return None
        if getattr(current_user, 'role', None) != 'admin':
            flash('Доступ запрещён', 'error')
            return redirect(url_for('kanban'))

        try:
            if action == 'run_mail_parser_now':
                started = legacy.start_mail_check_async()
                if started:
                    flash('Проверка почты запущена. Обновите страницу через пару секунд.', 'success')
                else:
                    flash('Проверка почты уже выполняется.', 'info')
                return redirect(url_for('admin_settings_section', section='mail_parser'))


            if action == 'test_mail_parser_connection':
                result = test_mail_connection()
                flash(result.get('message') or ('Подключение успешно' if result.get('ok') else 'Ошибка подключения'), 'success' if result.get('ok') else 'error')
                return redirect(url_for('admin_settings_section', section='mail_parser'))

            if action == 'clear_mail_parser_log':
                clear_mail_parser_log()
                flash('Журнал обработки очищен.', 'success')
                return redirect(url_for('admin_settings_section', section='mail_parser'))

            if action == 'save_ticket_importance_rules':
                payload = {
                    'keywords': [x.strip() for x in (request.form.get('important_keywords') or '').splitlines() if x.strip()],
                    'emails': [x.strip().lower() for x in (request.form.get('important_emails') or '').splitlines() if x.strip()],
                    'inns': [x.strip() for x in (request.form.get('important_inns') or '').splitlines() if x.strip()],
                }
                legacy.set_setting('ticket_importance.rules', json.dumps(payload, ensure_ascii=False))
                db.session.commit()
                flash('Правила важности заявок сохранены.', 'success')
                return redirect(url_for('admin_settings_section', section='important_rules'))

            if action == 'save_mail':
                legacy.set_setting('MAIL_SERVER', (request.form.get('MAIL_SERVER') or '').strip())
                legacy.set_setting('MAIL_PORT', (request.form.get('MAIL_PORT') or '').strip())
                legacy.set_setting('MAIL_USE_TLS', request.form.get('MAIL_USE_TLS', 'False'))
                legacy.set_setting('MAIL_USERNAME', (request.form.get('MAIL_USERNAME') or '').strip())
                pwd = (request.form.get('MAIL_PASSWORD') or '').strip()
                if pwd:
                    legacy.set_setting('MAIL_PASSWORD', pwd)
                db.session.commit()
                flash('Почтовые настройки сохранены.', 'success')
                return redirect(url_for('admin_settings_section', section='mail'))

            if action == 'save_outgoing_mail':
                MailAdminService.save_settings(request.form)
                db.session.commit()
                flash('Настройки исходящей почты сохранены.', 'success')
                return redirect(url_for('admin_settings_section', section='mail_outgoing'))

            if action == 'test_outgoing_mail_connection':
                result = MailAdminService.test_connection()
                flash(result.message, 'success' if result.ok else 'error')
                return redirect(url_for('admin_settings_section', section='mail_outgoing'))

            if action == 'send_outgoing_test_mail':
                recipient = (request.form.get('test_recipient') or '').strip()
                result = MailAdminService.send_test_mail(recipient)
                flash(result.message, 'success' if result.ok else 'error')
                return redirect(url_for('admin_settings_section', section='mail_outgoing'))

            if action == 'save_mail_template':
                template_key = (request.form.get('template_key') or '').strip()
                subject = (request.form.get('template_subject') or '').strip()
                body = (request.form.get('template_body') or '').strip()
                if not subject or not body:
                    flash('Тема и тело шаблона обязательны.', 'error')
                    return redirect(url_for('admin_settings_section', section='mail_templates'))
                MailAdminService.save_template(template_key, subject, body)
                db.session.commit()
                flash('Шаблон письма сохранён.', 'success')
                return redirect(url_for('admin_settings_section', section='mail_templates'))

            if action == 'reset_mail_template':
                template_key = (request.form.get('template_key') or '').strip()
                MailAdminService.reset_template(template_key)
                db.session.commit()
                flash('Шаблон сброшен к значениям по умолчанию.', 'success')
                return redirect(url_for('admin_settings_section', section='mail_templates'))

            if action == 'save_notifications_settings':
                settings = legacy.NotificationGlobalSettings.get_or_create()
                settings.enabled = bool(request.form.get('notif_enabled') == 'on')
                settings.enabled_for_operators = bool(request.form.get('notif_ops') == 'on')
                settings.enabled_for_clients = bool(request.form.get('notif_clients') == 'on')
                settings.event_new_ticket = bool(request.form.get('event_new_ticket') == 'on')
                settings.event_assigned = bool(request.form.get('event_assigned') == 'on')
                settings.event_customer_reply = bool(request.form.get('event_customer_reply') == 'on')
                settings.event_operator_reply = bool(request.form.get('event_operator_reply') == 'on')
                settings.event_status = bool(request.form.get('event_status') == 'on')
                settings.event_priority = bool(request.form.get('event_priority') == 'on')
                settings.event_opchat = bool(request.form.get('event_opchat') == 'on')
                settings.event_important = bool(request.form.get('event_important') == 'on')
                settings.event_sla = bool(request.form.get('event_sla') == 'on')
                db.session.commit()
                flash('Настройки уведомлений сохранены', 'success')
                return redirect(url_for('admin_settings_section', section='notifications'))

            if action in {'save_system', 'set_default_intake_department'}:
                dept_id = (request.form.get('default_intake_department_id') or '').strip()
                if dept_id.isdigit() and Department.query.get(int(dept_id)):
                    legacy.set_setting('default_intake_department_id', dept_id)
                else:
                    flash('Некорректный отдел', 'error')
                    return redirect(url_for('admin_settings_section', section='system'))

                mode = (request.form.get('profile_enforcement_mode') or '').strip().lower()
                if mode in ('strict', 'soft', 'off'):
                    legacy.set_setting('profile_enforcement_mode', mode)
                else:
                    legacy.set_setting('profile_enforcement_mode', legacy.get_profile_enforcement_mode())
                db.session.commit()
                flash('Системные настройки сохранены', 'success')
                return redirect(url_for('admin_settings_section', section='system'))

            if action == 'save_bitrix':
                department = (request.form.get('department') or '').strip()
                if not department:
                    flash('Не выбран отдел для Bitrix-настроек', 'error')
                    return redirect(url_for('admin_settings_section', section='bitrix'))
                row = BitrixSettings.query.filter_by(department=department).first()
                if not row:
                    row = BitrixSettings(department=department)
                    db.session.add(row)
                row.responsible_id = (request.form.get('responsible_id') or '').strip() or '4519'
                accomplices = request.form.getlist('accomplices') or []
                if not accomplices:
                    raw = (request.form.get('accomplices') or '').strip()
                    accomplices = [x.strip() for x in raw.split(',') if x.strip()]
                row.accomplices = ','.join(accomplices)
                row.webhook_url = (request.form.get('webhook_url') or '').strip() or None
                db.session.commit()
                flash('Bitrix-настройки сохранены', 'success')
                return redirect(url_for('admin_settings_section', section='bitrix'))

            if action == 'add_department':
                dept_name = (request.form.get('dept_name') or '').strip()
                if not dept_name:
                    flash('Название отдела обязательно', 'error')
                    return redirect(url_for('admin_settings_section', section='departments'))
                if Department.query.filter_by(name=dept_name).first():
                    flash('Такой отдел уже существует', 'error')
                    return redirect(url_for('admin_settings_section', section='departments'))
                dept = Department(name=dept_name)
                db.session.add(dept)
                db.session.commit()
                if not BitrixSettings.query.filter_by(department=dept.name).first():
                    db.session.add(BitrixSettings(department=dept.name))
                    db.session.commit()
                flash('Отдел добавлен', 'success')
                return redirect(url_for('admin_settings_section', section='departments'))

            if action == 'rename_department':
                dept_id = request.form.get('dept_id')
                new_name = (request.form.get('new_name') or '').strip()
                dept = Department.query.get(dept_id) if dept_id else None
                if not dept or not new_name:
                    flash('Отдел или новое название не найдены', 'error')
                    return redirect(url_for('admin_settings_section', section='departments'))
                if Department.query.filter(Department.name == new_name, Department.id != dept.id).first():
                    flash('Отдел с таким названием уже существует', 'error')
                    return redirect(url_for('admin_settings_section', section='departments'))
                old_name = dept.name
                dept.name = new_name
                row = BitrixSettings.query.filter_by(department=old_name).first()
                if row:
                    row.department = new_name
                db.session.commit()
                flash('Отдел переименован', 'success')
                return redirect(url_for('admin_settings_section', section='departments'))

            if action == 'delete_department':
                dept_id = request.form.get('dept_id')
                dept = Department.query.get(dept_id) if dept_id else None
                if not dept:
                    flash('Отдел не найден', 'error')
                    return redirect(url_for('admin_settings_section', section='departments'))
                has_tickets = legacy.SupportTicket.query.filter_by(department_id=dept.id).first() is not None
                has_users_primary = legacy.User.query.filter_by(department_id=dept.id).first() is not None
                has_users_m2m = legacy.db.session.execute(
                    legacy.db.text('SELECT 1 FROM user_departments WHERE department_id = :dept_id LIMIT 1'),
                    {'dept_id': dept.id},
                ).first() is not None
                if has_tickets or has_users_primary or has_users_m2m:
                    flash('Нельзя удалить отдел: он используется в заявках или назначен операторам.', 'error')
                    return redirect(url_for('admin_settings_section', section='departments'))
                row = BitrixSettings.query.filter_by(department=dept.name).first()
                if row:
                    db.session.delete(row)
                db.session.delete(dept)
                db.session.commit()
                flash('Отдел удалён', 'success')
                return redirect(url_for('admin_settings_section', section='departments'))

            if action == 'add_tag':
                name = (request.form.get('tag_name') or '').strip()
                color = (request.form.get('tag_color') or '').strip() or None
                if not name:
                    flash('Название тега обязательно', 'error')
                    return redirect(url_for('admin_settings_section', section='tags'))
                if Tag.query.filter_by(name=name).first():
                    flash('Такой тег уже существует', 'error')
                    return redirect(url_for('admin_settings_section', section='tags'))
                db.session.add(Tag(name=name, color=color, is_active=True))
                db.session.commit()
                flash('Тег добавлен', 'success')
                return redirect(url_for('admin_settings_section', section='tags'))

            if action == 'edit_tag':
                tag_id = request.form.get('tag_id')
                tag = Tag.query.get(tag_id) if tag_id else None
                if not tag:
                    flash('Тег не найден', 'error')
                    return redirect(url_for('admin_settings_section', section='tags'))
                name = (request.form.get('tag_name') or '').strip()
                color = (request.form.get('tag_color') or '').strip() or None
                is_active = request.form.get('is_active') == '1'
                if not name:
                    flash('Название тега обязательно', 'error')
                    return redirect(url_for('admin_settings_section', section='tags'))
                if Tag.query.filter(Tag.name == name, Tag.id != tag.id).first():
                    flash('Название уже используется', 'error')
                    return redirect(url_for('admin_settings_section', section='tags'))
                tag.name = name
                tag.color = color
                tag.is_active = is_active
                db.session.commit()
                flash('Тег обновлён', 'success')
                return redirect(url_for('admin_settings_section', section='tags'))

            if action == 'delete_tag':
                tag_id = request.form.get('tag_id')
                tag = Tag.query.get(tag_id) if tag_id else None
                if not tag:
                    flash('Тег не найден', 'error')
                    return redirect(url_for('admin_settings_section', section='tags'))
                used = legacy.db.session.execute(
                    legacy.db.text('SELECT 1 FROM ticket_tags WHERE tag_id = :tag_id LIMIT 1'),
                    {'tag_id': tag.id},
                ).first() is not None
                if used:
                    flash('Нельзя удалить тег: он используется в заявках.', 'error')
                    return redirect(url_for('admin_settings_section', section='tags'))
                db.session.delete(tag)
                db.session.commit()
                flash('Тег удалён', 'success')
                return redirect(url_for('admin_settings_section', section='tags'))


            if action == 'add_ticket_category':
                code = (request.form.get('code') or '').strip()
                name = (request.form.get('name') or '').strip()
                sort_order = int((request.form.get('sort_order') or '0').strip() or '0')
                if not code or not name:
                    flash('Код и название категории обязательны', 'error')
                    return redirect(url_for('admin_settings_section', section='categories'))
                if TicketCategory.query.filter_by(code=code).first() or TicketCategory.query.filter_by(name=name).first():
                    flash('Категория с таким кодом или названием уже существует', 'error')
                    return redirect(url_for('admin_settings_section', section='categories'))
                db.session.add(TicketCategory(code=code, name=name, sort_order=sort_order, is_active=True))
                db.session.commit()
                flash('Категория добавлена', 'success')
                return redirect(url_for('admin_settings_section', section='categories'))

            if action == 'edit_ticket_category':
                cat_id = request.form.get('cat_id')
                cat = TicketCategory.query.get(cat_id) if cat_id else None
                if not cat:
                    flash('Категория не найдена', 'error')
                    return redirect(url_for('admin_settings_section', section='categories'))
                code = (request.form.get('code') or '').strip()
                name = (request.form.get('name') or '').strip()
                sort_order = int((request.form.get('sort_order') or '0').strip() or '0')
                is_active = request.form.get('is_active') == '1'
                if not code or not name:
                    flash('Код и название категории обязательны', 'error')
                    return redirect(url_for('admin_settings_section', section='categories'))
                if TicketCategory.query.filter(TicketCategory.code == code, TicketCategory.id != cat.id).first():
                    flash('Код категории уже используется', 'error')
                    return redirect(url_for('admin_settings_section', section='categories'))
                if TicketCategory.query.filter(TicketCategory.name == name, TicketCategory.id != cat.id).first():
                    flash('Название категории уже используется', 'error')
                    return redirect(url_for('admin_settings_section', section='categories'))
                cat.code = code
                cat.name = name
                cat.sort_order = sort_order
                cat.is_active = is_active
                db.session.commit()
                flash('Категория обновлена', 'success')
                return redirect(url_for('admin_settings_section', section='categories'))

            if action == 'delete_ticket_category':
                cat_id = request.form.get('cat_id')
                cat = TicketCategory.query.get(cat_id) if cat_id else None
                if not cat:
                    flash('Категория не найдена', 'error')
                    return redirect(url_for('admin_settings_section', section='categories'))
                used = legacy.SupportTicket.query.filter_by(category_id=cat.id).first() is not None
                if used:
                    flash('Нельзя удалить категорию: она используется в заявках.', 'error')
                    return redirect(url_for('admin_settings_section', section='categories'))
                db.session.delete(cat)
                db.session.commit()
                flash('Категория удалена', 'success')
                return redirect(url_for('admin_settings_section', section='categories'))

            if action == 'save_mail_parser':
                def save_key(key, value):
                    legacy.set_setting(key, value)
                save_key('mail_parser.enabled', 'true' if request.form.get('mail_parser_enabled') else 'false')
                save_key('mail_parser.imap_server', (request.form.get('imap_server') or '').strip())
                save_key('mail_parser.imap_port', (request.form.get('imap_port') or '').strip() or '993')
                save_key('mail_parser.imap_use_ssl', 'true' if request.form.get('imap_use_ssl') else 'false')
                save_key('mail_parser.imap_username', (request.form.get('imap_username') or '').strip())
                pwd = (request.form.get('imap_password') or '').strip()
                if pwd:
                    save_key('mail_parser.imap_password', pwd)
                save_key('mail_parser.folder', (request.form.get('mail_folder') or 'INBOX').strip() or 'INBOX')
                save_key('mail_parser.subject_filter', (request.form.get('subject_filter') or '').strip())
                dept_id = (request.form.get('mail_parser_department_id') or '').strip()
                if dept_id.isdigit() and Department.query.get(int(dept_id)):
                    save_key('mail_parser.department_id', dept_id)
                else:
                    save_key('mail_parser.department_id', '')
                save_key('mail_parser.mark_seen', 'true' if request.form.get('mark_seen') else 'false')
                save_key('mail_parser.only_unseen', 'true' if request.form.get('only_unseen') else 'false')
                save_key('mail_parser.check_interval', (request.form.get('check_interval') or '60').strip() or '60')
                save_key('mail_parser.max_per_run', (request.form.get('max_per_run') or '20').strip() or '20')
                save_key('mail_parser.allowed_domains', (request.form.get('allowed_domains') or '').strip())
                save_key('mail_parser.ignored_emails', (request.form.get('ignored_emails') or '').strip())
                save_key('mail_parser.strip_quotes', 'true' if request.form.get('strip_quotes') else 'false')
                save_key('mail_parser.append_to_ticket', 'true' if request.form.get('append_to_ticket') else 'false')
                db.session.commit()
                flash('Настройки парсера почты сохранены', 'success')
                return redirect(url_for('admin_settings_section', section='mail_parser'))

        except Exception as exc:
            db.session.rollback()
            flash(f'Ошибка сохранения настроек: {exc}', 'error')
            tab = (request.args.get('tab') or request.form.get('tab') or 'bitrix').strip().lower()
            return redirect(url_for('admin_settings_section', section=tab))

        return None


    SECTION_TITLES = {
        'bitrix': 'Bitrix24',
        'departments': 'Отделы',
        'tags': 'Теги',
        'categories': 'Категории заявок',
        'system': 'Система',
        'mail': 'Почта',
        'mail_parser': 'Парсер почты',
        'mail_outgoing': 'Исходящая почта',
        'mail_templates': 'Шаблоны писем',
        'mail_logs': 'Почтовый журнал',
        'notifications': 'Уведомления',
        'important_rules': 'Важность задач',
    }

    @classmethod
    def normalize_section(cls, section: str | None) -> str:
        section = (section or 'bitrix').strip().lower()
        return section if section in cls.SECTION_TITLES else 'bitrix'

    @staticmethod
    def _format_mail_parser_dt(value):
        if not value:
            return '—'
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return '—'
            try:
                value = datetime.fromisoformat(raw.replace('Z', '+00:00'))
            except Exception:
                return raw.split('+', 1)[0].split('.', 1)[0]
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            local_value = to_local(value)
            return local_value.strftime('%Y-%m-%d %H:%M:%S') if local_value else '—'
        return str(value)

    @classmethod
    def render_page(cls, section: str | None = None):
        legacy = cls._legacy()
        section = cls.normalize_section(section or request.args.get('tab'))
        from types import SimpleNamespace
        from helpdesk_app.models.notifications import NotificationGlobalSettings
        from helpdesk_app.models.reference import Department, Tag, TicketCategory

        departments = Department.query.order_by(Department.name).all()
        tags = Tag.query.order_by(Tag.name).all()
        ticket_categories = TicketCategory.query.order_by(TicketCategory.sort_order.asc(), TicketCategory.name.asc()).all()
        bitrix_settings = BitrixSettings.query.order_by(BitrixSettings.department).all()

        system_settings = {
            'default_intake_department_id': legacy.get_default_intake_department_id() or '',
            'profile_enforcement_mode': legacy.get_profile_enforcement_mode(),
        }

        mail_settings = SimpleNamespace(
            MAIL_SERVER=legacy.get_setting('MAIL_SERVER', '') or '',
            MAIL_PORT=int(legacy.get_setting('MAIL_PORT', '993') or '993'),
            MAIL_USERNAME=legacy.get_setting('MAIL_USERNAME', '') or '',
            MAIL_PASSWORD=legacy.get_setting('MAIL_PASSWORD', '') or '',
            MAIL_USE_TLS=(legacy.get_setting('MAIL_USE_TLS', 'False') or 'False').lower() == 'true',
            MAIL_USE_SSL=True,
            MAIL_FOLDER='INBOX',
            MAIL_CHECK_INTERVAL=60,
        )

        outgoing_mail_settings = SimpleNamespace(**MailAdminService.settings_dict())
        mail_templates = MailAdminService.template_payloads()
        mail_template_variables = [
            '{{ticket_id}}', '{{ticket_title}}', '{{ticket_status}}', '{{client_name}}', '{{comment}}', '{{ticket_link}}', '{{department}}'
        ]
        mail_logs = MailAdminService.recent_logs(100)

        important_rules_raw = legacy.get_setting('ticket_importance.rules', '') or ''
        try:
            important_rules_data = json.loads(important_rules_raw) if important_rules_raw else {}
        except Exception:
            important_rules_data = {}
        important_rules = SimpleNamespace(
            keywords='\n'.join(important_rules_data.get('keywords') or []),
            emails='\n'.join(important_rules_data.get('emails') or []),
            inns='\n'.join(important_rules_data.get('inns') or []),
        )

        mail_parser_settings = SimpleNamespace(
            enabled=(legacy.get_setting('mail_parser.enabled', 'false') or 'false').lower() == 'true',
            imap_server=legacy.get_setting('mail_parser.imap_server', legacy.get_setting('IMAP_SERVER', '') or '') or '',
            imap_port=int(legacy.get_setting('mail_parser.imap_port', legacy.get_setting('IMAP_PORT', '993') or '993') or '993'),
            imap_use_ssl=(legacy.get_setting('mail_parser.imap_use_ssl', legacy.get_setting('IMAP_USE_SSL', 'true') or 'true') or 'true').lower() == 'true',
            imap_username=legacy.get_setting('mail_parser.imap_username', legacy.get_setting('IMAP_USERNAME', '') or '') or '',
            imap_password=legacy.get_setting('mail_parser.imap_password', legacy.get_setting('IMAP_PASSWORD', '') or '') or '',
            folder=legacy.get_setting('mail_parser.folder', 'INBOX') or 'INBOX',
            subject_filter=legacy.get_setting('mail_parser.subject_filter', '') or '',
            department_id=str(legacy.get_setting('mail_parser.department_id', '') or ''),
            mark_seen=(legacy.get_setting('mail_parser.mark_seen', 'true') or 'true').lower() == 'true',
            only_unseen=(legacy.get_setting('mail_parser.only_unseen', 'true') or 'true').lower() == 'true',
            check_interval=int(legacy.get_setting('mail_parser.check_interval', '60') or '60'),
            max_per_run=int(legacy.get_setting('mail_parser.max_per_run', '0') or '0'),
            allowed_domains=legacy.get_setting('mail_parser.allowed_domains', '') or '',
            ignored_emails=legacy.get_setting('mail_parser.ignored_emails', '') or '',
            strip_quotes=(legacy.get_setting('mail_parser.strip_quotes', 'true') or 'true').lower() == 'true',
            append_to_ticket=(legacy.get_setting('mail_parser.append_to_ticket', 'true') or 'true').lower() == 'true',
        )

        mail_parser_log_page = get_mail_parser_log_page(request.args.get('log_page', 1), request.args.get('log_per_page', 50))
        mail_parser_state_raw = getattr(legacy, 'MAIL_PARSER_STATE', {}) or {}
        mail_parser_state = SimpleNamespace(
            running=bool(mail_parser_state_raw.get('running')),
            last_started_at=cls._format_mail_parser_dt(mail_parser_state_raw.get('last_started_at')),
            last_success_at=cls._format_mail_parser_dt(mail_parser_state_raw.get('last_success_at')),
            last_finished_at=cls._format_mail_parser_dt(mail_parser_state_raw.get('last_finished_at')),
            last_error=mail_parser_state_raw.get('last_error') or '—',
        )
        for row in mail_parser_log_page.get('items', []):
            row['ts'] = cls._format_mail_parser_dt(row.get('ts'))

        return render_template(
            'admin_settings.html',
            section=section,
            section_title=cls.SECTION_TITLES[section],
            sections=cls.SECTION_TITLES,
            departments=departments,
            ticket_categories=ticket_categories,
            tags=tags,
            bitrix_settings=bitrix_settings,
            system_settings=system_settings,
            mail_settings=mail_settings,
            mail_parser_state=mail_parser_state,
            mail_parser_settings=mail_parser_settings,
            mail_parser_log=mail_parser_log_page['items'],
            mail_parser_log_page=mail_parser_log_page,
            important_rules=important_rules,
            outgoing_mail_settings=outgoing_mail_settings,
            mail_templates=mail_templates,
            mail_template_variables=mail_template_variables,
            mail_logs=mail_logs,
            notif_settings=NotificationGlobalSettings.get_or_create(),
        )
