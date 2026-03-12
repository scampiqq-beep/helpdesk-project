import os
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif', 'webp',
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'zip', 'rar'
}


def allowed_file(filename: str, allowed_extensions: set[str] | None = None) -> bool:
    allowed = allowed_extensions or ALLOWED_EXTENSIONS
    return bool(filename and '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed)


def safe_upload_name(filename: str) -> str:
    cleaned = secure_filename(filename or '')
    ext = cleaned.rsplit('.', 1)[1].lower() if '.' in cleaned else ''
    token = uuid.uuid4().hex
    return f'{token}.{ext}' if ext else token


def ensure_upload_dirs(base_upload_dir: str | os.PathLike) -> None:
    base = Path(base_upload_dir)
    for rel in ('', 'attachments', 'comments', 'avatars', 'tickets'):
        (base / rel).mkdir(parents=True, exist_ok=True)
