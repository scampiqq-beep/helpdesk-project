from __future__ import annotations

import json
import os
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from typing import Any


DEFAULT_TEMPLATES = {
    'ticket_created': {
        'title': 'Подтверждение создания заявки',
        'description': 'Отправляется клиенту после создания заявки из портала или входящего письма.',
        'subject': '[#{{ticket_id}}] Заявка принята в работу',
        'body': (
            'Здравствуйте!\n\n'
            'Ваша заявка #{{ticket_id}} успешно зарегистрирована.\n'
            'Тема: {{ticket_title}}\n\n'
            'Вы можете ответить на это письмо, и ответ автоматически попадёт в заявку.\n'
            '{{ticket_link}}\n'
        ),
    },
    'operator_reply': {
        'title': 'Ответ оператора',
        'description': 'Отправляется клиенту, когда оператор добавляет внешний комментарий.',
        'subject': '[#{{ticket_id}}] Ответ по вашей заявке',
        'body': (
            'Здравствуйте!\n\n'
            'По заявке #{{ticket_id}} добавлен новый ответ.\n\n'
            '{{comment}}\n\n'
            'Если нужно продолжить общение, просто ответьте на это письмо.\n'
            '{{ticket_link}}\n'
        ),
    },
    'status_changed': {
        'title': 'Изменение статуса',
        'description': 'Отправляется клиенту при смене статуса заявки, если это включено.',
        'subject': '[#{{ticket_id}}] Изменён статус заявки',
        'body': (
            'Здравствуйте!\n\n'
            'Статус заявки #{{ticket_id}} изменён на: {{ticket_status}}.\n'
            'Тема: {{ticket_title}}\n\n'
            '{{ticket_link}}\n'
        ),
    },
    'ticket_closed': {
        'title': 'Закрытие заявки',
        'description': 'Отправляется клиенту при закрытии заявки.',
        'subject': '[#{{ticket_id}}] Заявка закрыта',
        'body': (
            'Здравствуйте!\n\n'
            'Заявка #{{ticket_id}} закрыта.\n'
            'Если проблема повторится, просто ответьте на это письмо.\n\n'
            '{{ticket_link}}\n'
        ),
    },
    'sla_warning': {
        'title': 'Предупреждение по SLA',
        'description': 'Служебное письмо о приближении нарушения SLA или фактической просрочке.',
        'subject': '[#{{ticket_id}}] Внимание: SLA по заявке',
        'body': (
            'Внимание!\n\n'
            'По заявке #{{ticket_id}} требуется действие.\n'
            'Тема: {{ticket_title}}\n'
            'Текущий статус: {{ticket_status}}\n\n'
            '{{ticket_link}}\n'
        ),
    },
}


@dataclass
class SMTPTestResult:
    ok: bool
    message: str


class MailAdminService:
    LOG_FILENAME = 'mail_outgoing_log.json'

    @staticmethod
    def _legacy():
        from helpdesk_app.runtime import get_runtime
        return get_runtime()

    @classmethod
    def _instance_dir(cls) -> str:
        legacy = cls._legacy()
        root = getattr(legacy, 'app', None)
        if root is not None and getattr(root, 'instance_path', None):
            instance_path = root.instance_path
        else:
            instance_path = os.path.join(os.getcwd(), 'instance')
        os.makedirs(instance_path, exist_ok=True)
        return instance_path

    @classmethod
    def _log_path(cls) -> str:
        return os.path.join(cls._instance_dir(), cls.LOG_FILENAME)

    @classmethod
    def recent_logs(cls, limit: int = 50) -> list[dict[str, Any]]:
        path = cls._log_path()
        if not os.path.exists(path):
            return []
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            rows = data if isinstance(data, list) else []
        except Exception:
            return []
        return list(reversed(rows[-limit:]))

    @classmethod
    def append_log(cls, *, recipient: str = '', template_key: str = '', subject: str = '', status: str = 'queued', message: str = '', details: str = '') -> None:
        path = cls._log_path()
        rows = []
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as fh:
                    rows = json.load(fh) or []
            except Exception:
                rows = []
        rows.append({
            'ts': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            'recipient': recipient,
            'template_key': template_key,
            'subject': subject,
            'status': status,
            'message': message,
            'details': details,
        })
        rows = rows[-500:]
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=2)

    @classmethod
    def settings_dict(cls) -> dict[str, Any]:
        legacy = cls._legacy()
        def get_bool(key: str, default: str = 'false') -> bool:
            return (legacy.get_setting(key, default) or default).lower() == 'true'
        def get_int(key: str, default: str) -> int:
            try:
                return int(legacy.get_setting(key, default) or default)
            except Exception:
                return int(default)
        return {
            'enabled': get_bool('mail.outgoing.enabled', 'false'),
            'smtp_host': legacy.get_setting('mail.outgoing.smtp_host', legacy.get_setting('MAIL_SERVER', '') or '') or '',
            'smtp_port': get_int('mail.outgoing.smtp_port', str(legacy.get_setting('MAIL_PORT', '465') or '465')),
            'use_ssl': get_bool('mail.outgoing.use_ssl', 'true'),
            'use_starttls': get_bool('mail.outgoing.use_starttls', 'false'),
            'username': legacy.get_setting('mail.outgoing.username', legacy.get_setting('MAIL_USERNAME', '') or '') or '',
            'password': legacy.get_setting('mail.outgoing.password', legacy.get_setting('MAIL_PASSWORD', '') or '') or '',
            'sender_email': legacy.get_setting('mail.outgoing.sender_email', '') or '',
            'sender_name': legacy.get_setting('mail.outgoing.sender_name', 'Техническая поддержка') or 'Техническая поддержка',
            'timeout': get_int('mail.outgoing.timeout', '20'),
            'max_per_minute': get_int('mail.outgoing.max_per_minute', '30'),
            'retry_enabled': get_bool('mail.outgoing.retry_enabled', 'true'),
            'event_ticket_created': get_bool('mail.outgoing.event_ticket_created', 'true'),
            'event_operator_reply': get_bool('mail.outgoing.event_operator_reply', 'true'),
            'event_status_changed': get_bool('mail.outgoing.event_status_changed', 'false'),
            'event_ticket_closed': get_bool('mail.outgoing.event_ticket_closed', 'true'),
            'event_sla_warning': get_bool('mail.outgoing.event_sla_warning', 'false'),
            'suppress_auto_submitted': get_bool('mail.outgoing.suppress_auto_submitted', 'true'),
            'ignore_own_sender': get_bool('mail.outgoing.ignore_own_sender', 'true'),
            'test_recipient': legacy.get_setting('mail.outgoing.test_recipient', '') or '',
        }

    @classmethod
    def save_settings(cls, form) -> None:
        legacy = cls._legacy()
        def save(key: str, value: str) -> None:
            legacy.set_setting(key, value)
        save('mail.outgoing.enabled', 'true' if form.get('mail_outgoing_enabled') else 'false')
        save('mail.outgoing.smtp_host', (form.get('smtp_host') or '').strip())
        save('mail.outgoing.smtp_port', (form.get('smtp_port') or '465').strip() or '465')
        save('mail.outgoing.use_ssl', 'true' if form.get('smtp_use_ssl') else 'false')
        save('mail.outgoing.use_starttls', 'true' if form.get('smtp_use_starttls') else 'false')
        save('mail.outgoing.username', (form.get('smtp_username') or '').strip())
        pwd = (form.get('smtp_password') or '').strip()
        if pwd:
            save('mail.outgoing.password', pwd)
        save('mail.outgoing.sender_email', (form.get('sender_email') or '').strip())
        save('mail.outgoing.sender_name', (form.get('sender_name') or 'Техническая поддержка').strip() or 'Техническая поддержка')
        save('mail.outgoing.timeout', (form.get('smtp_timeout') or '20').strip() or '20')
        save('mail.outgoing.max_per_minute', (form.get('max_per_minute') or '30').strip() or '30')
        save('mail.outgoing.retry_enabled', 'true' if form.get('retry_enabled') else 'false')
        save('mail.outgoing.event_ticket_created', 'true' if form.get('event_ticket_created') else 'false')
        save('mail.outgoing.event_operator_reply', 'true' if form.get('event_operator_reply') else 'false')
        save('mail.outgoing.event_status_changed', 'true' if form.get('event_status_changed') else 'false')
        save('mail.outgoing.event_ticket_closed', 'true' if form.get('event_ticket_closed') else 'false')
        save('mail.outgoing.event_sla_warning', 'true' if form.get('event_sla_warning') else 'false')
        save('mail.outgoing.suppress_auto_submitted', 'true' if form.get('suppress_auto_submitted') else 'false')
        save('mail.outgoing.ignore_own_sender', 'true' if form.get('ignore_own_sender') else 'false')
        save('mail.outgoing.test_recipient', (form.get('test_recipient') or '').strip())

        # legacy compatibility keys
        save('MAIL_SERVER', (form.get('smtp_host') or '').strip())
        save('MAIL_PORT', (form.get('smtp_port') or '465').strip() or '465')
        save('MAIL_USERNAME', (form.get('smtp_username') or '').strip())
        if pwd:
            save('MAIL_PASSWORD', pwd)
        save('MAIL_USE_TLS', 'true' if form.get('smtp_use_starttls') else 'false')

    @classmethod
    def template_payloads(cls) -> list[dict[str, str]]:
        legacy = cls._legacy()
        rows = []
        for key, meta in DEFAULT_TEMPLATES.items():
            rows.append({
                'key': key,
                'title': meta['title'],
                'description': meta['description'],
                'subject': legacy.get_setting(f'mail.template.{key}.subject', meta['subject']) or meta['subject'],
                'body': legacy.get_setting(f'mail.template.{key}.body', meta['body']) or meta['body'],
            })
        return rows

    @classmethod
    def save_template(cls, template_key: str, subject: str, body: str) -> None:
        legacy = cls._legacy()
        if template_key not in DEFAULT_TEMPLATES:
            raise ValueError('Неизвестный шаблон письма')
        legacy.set_setting(f'mail.template.{template_key}.subject', subject)
        legacy.set_setting(f'mail.template.{template_key}.body', body)

    @classmethod
    def reset_template(cls, template_key: str) -> None:
        legacy = cls._legacy()
        if template_key not in DEFAULT_TEMPLATES:
            raise ValueError('Неизвестный шаблон письма')
        legacy.set_setting(f'mail.template.{template_key}.subject', DEFAULT_TEMPLATES[template_key]['subject'])
        legacy.set_setting(f'mail.template.{template_key}.body', DEFAULT_TEMPLATES[template_key]['body'])

    @classmethod
    def test_connection(cls) -> SMTPTestResult:
        settings = cls.settings_dict()
        host = settings['smtp_host']
        port = settings['smtp_port']
        username = settings['username']
        password = settings['password']
        timeout = settings['timeout']
        if not host or not port:
            return SMTPTestResult(False, 'Сначала заполните SMTP сервер и порт.')
        server = None
        try:
            if settings['use_ssl']:
                server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=ssl.create_default_context())
            else:
                server = smtplib.SMTP(host, port, timeout=timeout)
                if settings['use_starttls']:
                    server.starttls(context=ssl.create_default_context())
            server.ehlo()
            if username:
                server.login(username, password)
            return SMTPTestResult(True, 'Подключение к SMTP успешно.')
        except Exception as exc:
            return SMTPTestResult(False, f'Ошибка SMTP: {exc}')
        finally:
            try:
                if server is not None:
                    server.quit()
            except Exception:
                pass

    @classmethod
    def send_test_mail(cls, recipient: str) -> SMTPTestResult:
        settings = cls.settings_dict()
        if not recipient:
            return SMTPTestResult(False, 'Укажите email для тестового письма.')
        if not settings['smtp_host'] or not settings['sender_email']:
            return SMTPTestResult(False, 'Сначала заполните SMTP сервер и email отправителя.')
        message = EmailMessage()
        sender_name = settings['sender_name'].strip()
        sender = f'{sender_name} <{settings["sender_email"]}>' if sender_name else settings['sender_email']
        message['Subject'] = 'Тестовое письмо HelpDesk'
        message['From'] = sender
        message['To'] = recipient
        message['Message-ID'] = f'<helpdesk-test-{datetime.now().timestamp()}@local>'
        message.set_content(
            'Это тестовое письмо из модуля исходящей почты HelpDesk.\n\n'
            'Если вы получили это письмо, базовые SMTP настройки работают корректно.'
        )
        server = None
        try:
            if settings['use_ssl']:
                server = smtplib.SMTP_SSL(settings['smtp_host'], settings['smtp_port'], timeout=settings['timeout'], context=ssl.create_default_context())
            else:
                server = smtplib.SMTP(settings['smtp_host'], settings['smtp_port'], timeout=settings['timeout'])
                if settings['use_starttls']:
                    server.starttls(context=ssl.create_default_context())
            server.ehlo()
            if settings['username']:
                server.login(settings['username'], settings['password'])
            server.send_message(message)
            cls.append_log(recipient=recipient, template_key='test', subject=message['Subject'], status='sent', message='Тестовое письмо отправлено')
            return SMTPTestResult(True, 'Тестовое письмо отправлено.')
        except Exception as exc:
            cls.append_log(recipient=recipient, template_key='test', subject=message['Subject'], status='error', message='Ошибка тестовой отправки', details=str(exc))
            return SMTPTestResult(False, f'Ошибка отправки: {exc}')
        finally:
            try:
                if server is not None:
                    server.quit()
            except Exception:
                pass
