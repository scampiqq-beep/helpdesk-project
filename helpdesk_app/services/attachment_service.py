from __future__ import annotations

import os
from typing import Any, Iterable

from helpdesk_app.utils.files import allowed_file, safe_upload_name


class AttachmentService:
    """Единая работа с вложениями тикетов.

    Пока использует legacy-модели, но убирает файловую логику из TicketService.
    """

    @staticmethod
    def _legacy():
        from helpdesk_app.runtime import get_runtime
        return get_runtime()

    @classmethod
    def _upload_root(cls) -> str:
        return os.path.join('static', 'uploads', 'attachments')

    @classmethod
    def save_comment_files(cls, message_id: int, uploaded_files: Iterable[Any] | None = None) -> list[Any]:
        legacy = cls._legacy()
        upload_root = cls._upload_root()
        os.makedirs(upload_root, exist_ok=True)

        created: list[Any] = []
        for uploaded_file in (uploaded_files or []):
            if not uploaded_file:
                continue
            original_name = getattr(uploaded_file, 'filename', '') or ''
            if not str(original_name).strip():
                continue
            if not allowed_file(original_name):
                raise ValueError(f'Недопустимый тип файла: {original_name}')

            unique_name = safe_upload_name(original_name)
            file_path = os.path.join(upload_root, unique_name)
            uploaded_file.save(file_path)
            attachment = TicketAttachment(
                message_id=message_id,
                filename=unique_name,
                original_name=original_name,
                size=os.path.getsize(file_path),
                url=legacy.url_for('static', filename=f'uploads/attachments/{unique_name}'),
            )
            db.session.add(attachment)
            created.append(attachment)
        return created

    @classmethod
    def delete_attachments(cls, attachment_ids: Iterable[int] | None = None, *, message_id: int | None = None) -> list[int]:
        legacy = cls._legacy()
        deleted_ids: list[int] = []

        query = TicketAttachment.query
        if attachment_ids:
            query = query.filter(TicketAttachment.id.in_(list(attachment_ids)))
        elif message_id is not None:
            query = query.filter_by(message_id=message_id)
        else:
            return deleted_ids

        attachments = query.all()
        for att in attachments:
            cls.delete_attachment_model(att)
            deleted_ids.append(att.id)
        return deleted_ids

    @classmethod
    def delete_attachment_model(cls, attachment: Any) -> None:
        legacy = cls._legacy()
        for base in [cls._upload_root(), os.path.join('uploads', 'attachments')]:
            try:
                fp = os.path.join(base, attachment.filename)
                if os.path.exists(fp):
                    os.remove(fp)
            except Exception:
                pass
        db.session.delete(attachment)

    @classmethod
    def get_message_attachments(cls, message_id: int) -> list[Any]:
        legacy = cls._legacy()
        return TicketAttachment.query.filter_by(message_id=message_id).order_by(TicketAttachment.id.asc()).all()
