# mail_parser.py
import email
import hashlib
import html
import imaplib
import json
import os
import re
import ssl
import uuid
from datetime import datetime, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from helpdesk_app.models.base import db
from helpdesk_app.models.reference import Department, TicketCategory
from helpdesk_app.models.settings import Settings
from helpdesk_app.models.tickets import SupportTicket, TicketAttachment, TicketHistory, TicketMessage
from helpdesk_app.models.users import User

URGENT_RE = re.compile(r'\b(срочно|urgent|critical|критично)\b', re.IGNORECASE)
TICKET_SUBJECT_RE = re.compile(r'(?:ticket|тикет|заявк[аи])\s*#\s*(\d+)|#(\d+)', re.IGNORECASE)
REPLY_PREFIX_RE = re.compile(r'^(?:\s*(?:re|fw|fwd|aw|sv)\s*:\s*|\s*(?:ответ|переслать|пересылка)\s*:\s*)+', re.IGNORECASE)

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')


class CustomIMAP4_SSL(imaplib.IMAP4_SSL):
    def __init__(self, host, port, ssl_context):
        self.ssl_context = ssl_context
        super().__init__(host, port)

    def _create_ssl_context(self):
        return self.ssl_context


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _instance_dir() -> Path:
    root = Path(__file__).resolve().parent
    path = root / 'instance'
    path.mkdir(parents=True, exist_ok=True)
    return path


def _state_path() -> Path:
    return _instance_dir() / 'mail_parser_state.json'


def _log_path() -> Path:
    return _instance_dir() / 'mail_parser_log.json'


def _load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        pass
    return default


def _save_json(path: Path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def _append_log(level: str, action: str, message: str, **extra):
    items = _load_json(_log_path(), [])
    row = {
        'ts': _utc_now().isoformat(),
        'level': level,
        'action': action,
        'message': message,
    }
    row.update({k: v for k, v in extra.items() if v not in (None, '')})
    items.insert(0, row)
    del items[1000:]
    _save_json(_log_path(), items)


def get_recent_mail_parser_log(limit: int = 30):
    items = _load_json(_log_path(), [])
    return items[: max(int(limit or 0), 0)]


def get_mail_parser_log_page(page: int = 1, per_page: int = 50):
    items = _load_json(_log_path(), [])
    per_page = max(1, min(int(per_page or 50), 200))
    total = len(items)
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(int(page or 1), pages))
    start = (page - 1) * per_page
    end = start + per_page
    return {
        'items': items[start:end],
        'page': page,
        'per_page': per_page,
        'pages': pages,
        'total': total,
        'has_prev': page > 1,
        'has_next': page < pages,
        'prev_num': page - 1,
        'next_num': page + 1,
    }


def clear_mail_parser_log():
    _save_json(_log_path(), [])


def _load_state():
    return _load_json(
        _state_path(),
        {
            'processed_keys': {},
            'message_links': {},
            'subject_links': {},
            'last_run': None,
            'last_summary': {},
        },
    )


def _save_state(state):
    processed = state.get('processed_keys') or {}
    if len(processed) > 2000:
        ordered = sorted(processed.items(), key=lambda x: x[1], reverse=True)[:2000]
        state['processed_keys'] = dict(ordered)

    message_links = state.get('message_links') or {}
    if len(message_links) > 5000:
        ordered = sorted(message_links.items(), key=lambda x: str(x[1].get('ts') or ''), reverse=True)[:5000]
        state['message_links'] = dict(ordered)

    subject_links = state.get('subject_links') or {}
    if len(subject_links) > 2000:
        ordered = sorted(subject_links.items(), key=lambda x: str(x[1].get('ts') or ''), reverse=True)[:2000]
        state['subject_links'] = dict(ordered)

    _save_json(_state_path(), state)


def _remember_processed(key: str):
    state = _load_state()
    processed = state.setdefault('processed_keys', {})
    processed[key] = _utc_now().isoformat()
    _save_state(state)


def _normalize_message_id(value: str | None) -> str:
    raw = (value or '').strip().strip('<>').strip().lower()
    return raw


def _extract_reference_message_ids(msg) -> list[str]:
    items: list[str] = []
    for header in ('Message-ID', 'In-Reply-To', 'References'):
        raw = str(msg.get(header) or '')
        if not raw:
            continue
        for match in re.findall(r'<([^>]+)>', raw):
            normalized = _normalize_message_id(match)
            if normalized and normalized not in items:
                items.append(normalized)
        normalized_raw = _normalize_message_id(raw)
        if normalized_raw and normalized_raw not in items and '@' in normalized_raw:
            items.append(normalized_raw)
    return items


def _subject_link_key(from_email: str, subject: str) -> str | None:
    normalized_subject = _normalize_subject(subject)
    email_value = (from_email or '').strip().lower()
    if not email_value or not normalized_subject:
        return None
    return f"{email_value}|{normalized_subject}"


def _remember_ticket_thread(ticket_id: int, msg, from_email: str, subject: str):
    state = _load_state()
    ts = _utc_now().isoformat()

    message_links = state.setdefault('message_links', {})
    for message_id in _extract_reference_message_ids(msg):
        message_links[message_id] = {'ticket_id': int(ticket_id), 'ts': ts}

    subject_key = _subject_link_key(from_email, subject)
    if subject_key:
        state.setdefault('subject_links', {})[subject_key] = {'ticket_id': int(ticket_id), 'ts': ts}

    _save_state(state)


def _find_ticket_by_thread_links(msg, from_email: str, subject: str):
    state = _load_state()

    for message_id in _extract_reference_message_ids(msg):
        row = (state.get('message_links') or {}).get(message_id)
        if not row:
            continue
        ticket_id = row.get('ticket_id')
        if ticket_id:
            ticket = SupportTicket.query.get(ticket_id)
            if ticket:
                return ticket

    subject_key = _subject_link_key(from_email, subject)
    if subject_key:
        row = (state.get('subject_links') or {}).get(subject_key)
        if row and row.get('ticket_id'):
            ticket = SupportTicket.query.get(row.get('ticket_id'))
            if ticket:
                return ticket

    return None


def update_last_summary(summary: dict):
    state = _load_state()
    state['last_run'] = _utc_now().isoformat()
    state['last_summary'] = summary or {}
    _save_state(state)


def _get_setting(key, default=''):
    row = Settings.query.filter_by(key=key).first()
    if row and row.value is not None:
        return row.value
    return default


def _get_bool_setting(key, default=False):
    val = str(_get_setting(key, 'true' if default else 'false')).strip().lower()
    return val in {'1', 'true', 'on', 'yes'}


def _get_int_setting(key, default=0):
    raw = str(_get_setting(key, str(default)) or str(default)).strip()
    try:
        return int(raw)
    except Exception:
        return int(default)

def _get_json_setting(key: str, default):
    raw = _get_setting(key, '')
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _normalize_lines(value: str) -> list[str]:
    items = []
    for row in (value or '').replace(';', '\n').splitlines():
        item = row.strip()
        if item:
            items.append(item)
    return items


def _get_important_ticket_rules() -> dict:
    data = _get_json_setting('ticket_importance.rules', {}) or {}
    return {
        'keywords': _normalize_lines('\n'.join(data.get('keywords') or [])),
        'emails': [x.lower() for x in _normalize_lines('\n'.join(data.get('emails') or []))],
        'inns': [_normalize_inn(x) for x in _normalize_lines('\n'.join(data.get('inns') or [])) if _normalize_inn(x)],
    }


def _is_important_by_rules(*, subject: str, body: str, from_email: str, inn: str | None) -> bool:
    rules = _get_important_ticket_rules()
    haystack = f"{subject}\n{body}".lower()
    email_value = (from_email or '').strip().lower()
    inn_value = _normalize_inn(inn or '')
    if email_value and email_value in set(rules.get('emails') or []):
        return True
    if inn_value and inn_value in set(rules.get('inns') or []):
        return True
    for keyword in rules.get('keywords') or []:
        if keyword.lower() in haystack:
            return True
    return False


def _get_mail_parser_department_id():
    explicit = str(_get_setting('mail_parser.department_id', '') or '').strip()
    if explicit.isdigit():
        dept = Department.query.get(int(explicit))
        if dept:
            return dept.id
    default_intake = str(_get_setting('default_intake_department_id', '') or '').strip()
    if default_intake.isdigit():
        dept = Department.query.get(int(default_intake))
        if dept:
            return dept.id
    preferred = Department.query.filter(Department.name.ilike('%требуется обработка%')).first()
    if preferred:
        return preferred.id
    return None


def decode_mime_words(s):
    if not s:
        return ''
    try:
        decoded_fragments = decode_header(s)
        decoded_string = ''
        for fragment, encoding in decoded_fragments:
            if isinstance(fragment, bytes):
                decoded_string += fragment.decode(encoding or 'utf-8', errors='replace')
            else:
                decoded_string += fragment
        return decoded_string
    except Exception as e:
        print(f"[DECODE ERROR] Не удалось декодировать '{s}': {e}")
        return s


def parse_email_address(addr):
    if not addr:
        return '', ''
    decoded_addr = decode_mime_words(addr)
    if '<' in decoded_addr and '>' in decoded_addr:
        name_part = decoded_addr.split('<')[0].strip().strip('"')
        email_part = decoded_addr.split('<')[1].split('>')[0].strip().lower()
        return email_part, name_part
    value = decoded_addr.strip()
    return value.lower(), value.split('@')[0] if '@' in value else 'Unknown'


def _strip_html(value: str) -> str:
    value = html.unescape(value or '')
    value = re.sub(r'(?is)<(script|style).*?>.*?</\1>', ' ', value)
    value = re.sub(r'(?i)<br\s*/?>', '\n', value)
    value = re.sub(r'(?i)</p\s*>', '\n', value)
    value = re.sub(r'(?s)<[^>]+>', ' ', value)
    value = re.sub(r'\r\n?', '\n', value)
    value = re.sub(r'\n{3,}', '\n\n', value)
    value = re.sub(r'[ \t]{2,}', ' ', value)
    return value.strip()


def _strip_quoted_reply(text: str) -> str:
    if not text:
        return ''
    patterns = [
        r'(?im)^>.*$',
        r'(?is)\n[-_]{2,}.*$ ',
        r'(?is)\n\s*С уважением,.*$',
        r'(?is)\n\s*--\s*\n.*$',
        r'(?is)\n\s*От: .*?\n\s*Отправлено: .*$',
        r'(?is)\n\s*From: .*?\n\s*Sent: .*$',
        r'(?is)\n\s*On .*?wrote:.*$',
    ]
    result = text
    for pattern in patterns:
        result = re.sub(pattern, '', result)
    lines = []
    for line in result.splitlines():
        if line.strip().startswith('>'):
            continue
        lines.append(line)
    result = '\n'.join(lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


def save_attachment_content(content: bytes, filename: str, upload_folder: str):
    os.makedirs(upload_folder, exist_ok=True)
    safe_name = secure_filename(filename or 'attachment.bin') or 'attachment.bin'
    unique = f"{uuid.uuid4().hex}_{safe_name}"
    filepath = os.path.join(upload_folder, unique)
    with open(filepath, 'wb') as f:
        f.write(content)
    return unique, filepath


def _extract_email_content(msg, upload_folder: str):
    text_parts = []
    html_parts = []
    attachments = []

    for part in msg.walk() if msg.is_multipart() else [msg]:
        content_type = part.get_content_type()
        content_disposition = str(part.get('Content-Disposition') or '')
        filename = part.get_filename()

        disposition = content_disposition.lower()
        is_inline = 'inline' in disposition
        content_id = str(part.get('Content-ID') or '').strip()
        if filename or 'attachment' in disposition or is_inline:
            payload = part.get_payload(decode=True) or b''
            decoded_name = decode_mime_words(filename) if filename else ''
            is_image = (content_type or '').lower().startswith('image/')
            # Не сохраняем картинки из подписи и прочие inline-изображения из HTML-писем.
            if is_image and (is_inline or content_id):
                continue
            if filename and payload:
                unique_name, filepath = save_attachment_content(payload, decoded_name, upload_folder)
                attachments.append({
                    'filename': unique_name,
                    'original_name': decoded_name,
                    'size': len(payload),
                    'path': filepath,
                })
            continue

        if content_type not in ('text/plain', 'text/html'):
            continue

        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        charset = part.get_content_charset() or 'utf-8'
        try:
            decoded = payload.decode(charset, errors='replace')
        except Exception:
            decoded = payload.decode('utf-8', errors='replace')

        if content_type == 'text/plain':
            text_parts.append(decoded)
        else:
            html_parts.append(decoded)

    body = '\n\n'.join([p for p in text_parts if p.strip()]).strip()
    if not body and html_parts:
        body = '\n\n'.join(_strip_html(p) for p in html_parts if p.strip()).strip()
    return body, attachments


def _normalize_inn(value: str) -> str:
    return re.sub(r'\D', '', value or '')


def get_company_from_bitrix(email_value, bitrix_webhook_url):
    if not bitrix_webhook_url:
        return None
    contact_url = bitrix_webhook_url.replace('/tasks.task.add', '/crm.contact.list')
    contact_data = {
        'filter': {'EMAIL': email_value},
        'select': ['ID', 'NAME', 'LAST_NAME', 'COMPANY_TITLE', 'UF_CRM_1738296475153', 'ADDRESS'],
    }
    try:
        response = requests.post(contact_url, json=contact_data, verify=False, timeout=10)
        if response.status_code == 200:
            result = response.json()
            contacts = result.get('result', [])
            if contacts:
                contact = contacts[0]
                return {
                    'company': contact.get('COMPANY_TITLE', ''),
                    'inn': contact.get('UF_CRM_1738296475153', ''),
                    'address': contact.get('ADDRESS', ''),
                }
    except Exception as e:
        print(f'[BITRIX CRM] Ошибка поиска клиента: {e}')
    return None


def _message_key(msg, email_uid: str, from_email: str, subject: str, body: str) -> str:
    message_id = (msg.get('Message-ID') or '').strip().lower()
    base = message_id or f'{email_uid}|{from_email}|{subject}|{body[:200]}'
    return hashlib.sha1(base.encode('utf-8', errors='ignore')).hexdigest()


def _detect_ticket_id(subject: str) -> int | None:
    m = TICKET_SUBJECT_RE.search(subject or '')
    if not m:
        return None
    value = m.group(1) or m.group(2)
    try:
        return int(value)
    except Exception:
        return None


def _normalize_subject(subject: str) -> str:
    value = decode_mime_words(subject or '')
    value = re.sub(r'\[[^\]]*#\d+[^\]]*\]', ' ', value, flags=re.IGNORECASE)
    value = TICKET_SUBJECT_RE.sub(' ', value)
    prev = None
    while prev != value:
        prev = value
        value = REPLY_PREFIX_RE.sub('', value).strip()
    value = re.sub(r'[\s\-–—_:;,.#]+', ' ', value.lower())
    return value.strip()


def _is_reply_like_message(msg, subject: str) -> bool:
    if (msg.get('In-Reply-To') or '').strip() or (msg.get('References') or '').strip():
        return True
    cleaned = decode_mime_words(subject or '').strip()
    return bool(REPLY_PREFIX_RE.match(cleaned))


def _find_existing_ticket_for_email(msg, from_email: str, subject: str):
    explicit_ticket_id = _detect_ticket_id(subject)
    if explicit_ticket_id:
        return SupportTicket.query.get(explicit_ticket_id)

    linked_ticket = _find_ticket_by_thread_links(msg, from_email, subject)
    if linked_ticket:
        return linked_ticket

    normalized_subject = _normalize_subject(subject)
    if not normalized_subject:
        return None

    reply_like = _is_reply_like_message(msg, subject)
    if not reply_like:
        return None

    candidates = (SupportTicket.query
        .filter(db.func.lower(SupportTicket.email) == from_email.lower())
        .order_by(SupportTicket.created_at.desc(), SupportTicket.id.desc())
        .limit(30)
        .all())

    open_matches = []
    closed_matches = []
    for ticket in candidates:
        ticket_subject = _normalize_subject(getattr(ticket, 'subject', '') or '')
        if not ticket_subject:
            continue
        if ticket_subject != normalized_subject:
            continue
        status = (getattr(ticket, 'status', '') or '').strip().lower()
        if status in {'завершена', 'закрыта', 'спам'}:
            closed_matches.append(ticket)
        else:
            open_matches.append(ticket)

    if open_matches:
        return open_matches[0]
    if len(closed_matches) == 1:
        return closed_matches[0]
    return None


def _pick_category_id(subject: str, body: str):
    default_cat = TicketCategory.query.filter_by(code='issue').first()
    text = f'{subject}\n{body}'.lower()
    if 'инцидент' in text:
        cat = TicketCategory.query.filter(TicketCategory.name.ilike('%инцидент%')).first()
        if cat:
            return cat.id
    if 'доступ' in text:
        cat = TicketCategory.query.filter(TicketCategory.name.ilike('%доступ%')).first()
        if cat:
            return cat.id
    return default_cat.id if default_cat else None


def _upsert_client(from_email: str, from_name: str, client_data: dict | None):
    user = User.query.filter(db.func.lower(User.email) == from_email.lower()).first()
    if not user:
        user = User(
            username=from_email,
            email=from_email,
            name=from_name or None,
            password=generate_password_hash(uuid.uuid4().hex, method='pbkdf2:sha256'),
            role='client',
            email_verified=True,
            is_active=True,
        )
        db.session.add(user)
        db.session.flush()

    if client_data:
        comp = (client_data.get('company') or '').strip()
        inn_digits = _normalize_inn(client_data.get('inn') or '')
        addr = (client_data.get('address') or '').strip()
        if comp:
            if not (user.organization or '').strip():
                user.organization = comp
            elif comp != (user.organization or '').strip():
                user.suggested_organization = comp
        if inn_digits and len(inn_digits) in (10, 12):
            if not (user.inn or '').strip():
                user.inn = inn_digits
            elif inn_digits != (user.inn or '').strip():
                user.suggested_inn = inn_digits
        if addr:
            if not (user.address or '').strip():
                user.address = addr
            elif addr != (user.address or '').strip():
                user.suggested_address = addr
    return user


def _create_ticket_message(ticket: SupportTicket, user: User, body: str, attachments: list[dict]):
    comment = TicketMessage(
        ticket_id=ticket.id,
        user_id=user.id,
        message=body,
        is_operator=False,
    )
    db.session.add(comment)
    db.session.flush()

    if getattr(ticket, 'status', None) in {'Завершена', 'Закрыта'}:
        ticket.status = 'Открыта'
    for item in attachments:
        db.session.add(
            TicketAttachment(
                message_id=comment.id,
                filename=item['filename'],
                original_name=item['original_name'],
                size=item['size'],
                url=f"/static/uploads/attachments/{item['filename']}",
            )
        )
    db.session.add(
        TicketHistory(
            ticket_id=ticket.id,
            user_id=user.id,
            field='email_reply',
            old_value=None,
            new_value='Комментарий из почты',
            note='Комментарий добавлен почтовым парсером',
        )
    )
    return comment


def _create_ticket(from_email: str, from_name: str, subject: str, body: str, user: User, client_data: dict | None, attachments: list[dict], parser_department_id: int | None, sla_attention_hours, sla_default_hours):
    ticket_inn = _normalize_inn((client_data or {}).get('inn') or user.inn or '')
    is_important = _is_important_by_rules(
        subject=subject or '',
        body=body or '',
        from_email=from_email or '',
        inn=ticket_inn,
    )
    priority = 'Критический' if is_important else 'Обычный'
    ticket = SupportTicket(
        name=from_name or from_email,
        email=from_email,
        subject=subject or 'Заявка из почты',
        message=(body or '').strip() or 'Письмо без текста',
        department_id=parser_department_id,
        ticket_type='issue',
        category_id=_pick_category_id(subject, body),
        status='Новая',
        priority=priority,
        client_id=user.id,
        created_at=datetime.utcnow(),
        organization=(client_data or {}).get('company') or user.organization,
        inn=ticket_inn,
        address=(client_data or {}).get('address') or user.address or '',
    )
    ticket.calculate_sla_deadline(sla_attention_hours, sla_default_hours)
    ticket.files = json.dumps([a['filename'] for a in attachments], ensure_ascii=False) if attachments else None
    db.session.add(ticket)
    db.session.flush()
    db.session.add(
        TicketHistory(
            ticket_id=ticket.id,
            user_id=user.id,
            field='ticket_created',
            old_value=None,
            new_value='Создана из почты',
            note='Заявка создана почтовым парсером',
        )
    )
    return ticket


def test_mail_connection():
    server = _get_setting('mail_parser.imap_server', '')
    port = int(_get_setting('mail_parser.imap_port', 993) or 993)
    use_ssl = _get_bool_setting('mail_parser.imap_use_ssl', True)
    username = _get_setting('mail_parser.imap_username', '')
    password = _get_setting('mail_parser.imap_password', '')
    folder = (_get_setting('mail_parser.folder', 'INBOX') or 'INBOX').strip()

    if not server or not username or not password:
        return {'ok': False, 'message': 'Не заполнены IMAP сервер, логин или пароль.'}

    mail = None
    try:
        mail = CustomIMAP4_SSL(server, port, ssl_context) if use_ssl else imaplib.IMAP4(server, port)
        mail.login(username, password)
        status, _ = mail.select(folder)
        if status != 'OK':
            return {'ok': False, 'message': f'Не удалось открыть папку {folder}.'}
        return {'ok': True, 'message': f'Подключение успешно. Папка {folder} доступна.'}
    except Exception as exc:
        return {'ok': False, 'message': f'Ошибка подключения: {exc}'}
    finally:
        try:
            if mail is not None:
                mail.logout()
        except Exception:
            pass


def check_incoming_emails(app, upload_folder, departments, sla_attention_hours, sla_default_hours, bitrix_webhook_url):
    summary = {
        'checked': 0,
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0,
    }
    mail = None
    try:
        with app.app_context():
            enabled = _get_bool_setting('mail_parser.enabled', False)
            server = _get_setting('mail_parser.imap_server', '')
            port = int(_get_setting('mail_parser.imap_port', 993) or 993)
            use_ssl = _get_bool_setting('mail_parser.imap_use_ssl', True)
            username = (_get_setting('mail_parser.imap_username', '') or '').strip()
            password = _get_setting('mail_parser.imap_password', '')
            folder = (_get_setting('mail_parser.folder', 'INBOX') or 'INBOX').strip()
            only_unseen = _get_bool_setting('mail_parser.only_unseen', True)
            mark_seen = _get_bool_setting('mail_parser.mark_seen', True)
            strip_quotes = _get_bool_setting('mail_parser.strip_quotes', True)
            append_to_ticket = _get_bool_setting('mail_parser.append_to_ticket', True)
            max_per_run = _get_int_setting('mail_parser.max_per_run', 0)
            allowed_domains = [x.strip().lower() for x in (_get_setting('mail_parser.allowed_domains', '') or '').split(',') if x.strip()]
            ignored_emails = [x.strip().lower() for x in (_get_setting('mail_parser.ignored_emails', '') or '').split(',') if x.strip()]

            if not enabled:
                _append_log('info', 'parser', 'Парсер почты выключен в настройках')
                update_last_summary(summary)
                return
            if not server or not username or not password:
                _append_log('error', 'parser', 'IMAP настройки не заданы в админке')
                update_last_summary(summary)
                return

            mail = CustomIMAP4_SSL(server, port, ssl_context) if use_ssl else imaplib.IMAP4(server, port)
            mail.login(username, password)
            mail.select(folder)

            status, messages = mail.search(None, 'UNSEEN' if only_unseen else 'ALL')
            if status != 'OK':
                raise RuntimeError('Ошибка поиска писем')

            email_ids = list(messages[0].split())
            if max_per_run > 0:
                email_ids = email_ids[:max_per_run]
            parser_department_id = _get_mail_parser_department_id()
            for email_id in email_ids:
                summary['checked'] += 1
                try:
                    status, msg_data = mail.fetch(email_id, '(RFC822 UID)')
                    if status != 'OK' or not msg_data:
                        raise RuntimeError('Не удалось получить содержимое письма')
                    raw_email = msg_data[0][1]
                    meta = msg_data[0][0].decode('utf-8', errors='ignore') if isinstance(msg_data[0][0], bytes) else str(msg_data[0][0])
                    uid_match = re.search(r'UID\s+(\d+)', meta)
                    email_uid = uid_match.group(1) if uid_match else str(email_id)
                    msg = email.message_from_bytes(raw_email)

                    subject = decode_mime_words(msg.get('Subject', '')).strip()
                    from_header = msg.get('From', '')
                    from_email, from_name = parse_email_address(from_header)
                    if not from_email:
                        summary['skipped'] += 1
                        _append_log('warning', 'skip', 'Пропущено письмо без email отправителя', subject=subject)
                        continue
                    if from_email.lower() == username.lower() or from_email.lower() in ignored_emails:
                        summary['skipped'] += 1
                        _append_log('info', 'skip', 'Пропущено письмо от служебного адреса', email=from_email, subject=subject)
                        continue
                    if allowed_domains:
                        domain = from_email.split('@')[-1].lower() if '@' in from_email else ''
                        if domain not in allowed_domains:
                            summary['skipped'] += 1
                            _append_log('info', 'skip', 'Пропущено письмо с недопустимого домена', email=from_email, subject=subject)
                            continue
                    # Собираем все письма вне зависимости от фильтра по теме.

                    body, attachments = _extract_email_content(msg, upload_folder)
                    if strip_quotes:
                        body = _strip_quoted_reply(body)
                    body = body.strip() or 'Письмо без текста'

                    key = _message_key(msg, email_uid, from_email, subject, body)
                    if _already_processed(key):
                        summary['skipped'] += 1
                        _append_log('info', 'skip', 'Пропущен дубликат письма', email=from_email, subject=subject)
                        if mark_seen:
                            mail.store(email_id, '+FLAGS', '\\Seen')
                        continue

                    client_data = get_company_from_bitrix(from_email, bitrix_webhook_url)
                    user = _upsert_client(from_email, from_name, client_data)

                    existing_ticket = None
                    if append_to_ticket:
                        existing_ticket = _find_existing_ticket_for_email(msg, from_email, subject)

                    if existing_ticket:
                        _create_ticket_message(existing_ticket, user, body, attachments)
                        _remember_ticket_thread(existing_ticket.id, msg, from_email, subject)
                        summary['updated'] += 1
                        _append_log('success', 'comment', 'Комментарий добавлен в существующую заявку', ticket_id=existing_ticket.id, email=from_email, subject=subject)
                    else:
                        ticket = _create_ticket(
                            from_email=from_email,
                            from_name=from_name,
                            subject=subject,
                            body=body,
                            user=user,
                            client_data=client_data,
                            attachments=attachments,
                            parser_department_id=parser_department_id,
                            sla_attention_hours=sla_attention_hours,
                            sla_default_hours=sla_default_hours,
                        )
                        _remember_ticket_thread(ticket.id, msg, from_email, subject)
                        summary['created'] += 1
                        _append_log('success', 'create', 'Создана заявка из письма', ticket_id=ticket.id, email=from_email, subject=subject)

                    db.session.commit()
                    _remember_processed(key)
                    if mark_seen:
                        mail.store(email_id, '+FLAGS', '\\Seen')
                except Exception as e:
                    db.session.rollback()
                    summary['errors'] += 1
                    _append_log('error', 'process', f'Ошибка обработки письма: {e}', email_id=str(email_id))
            update_last_summary(summary)
    except Exception as e:
        _append_log('error', 'critical', f'Критическая ошибка парсера: {e}')
        update_last_summary(summary)
        print(f'[MAIL PARSER] Критическая ошибка: {e}')
    finally:
        try:
            if mail is not None:
                mail.logout()
        except Exception:
            pass
