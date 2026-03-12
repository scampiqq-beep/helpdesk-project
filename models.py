"""Совместимый shim для ORM-моделей проекта.

Начиная с шага 21 физические определения моделей живут в
``helpdesk_app.models.core``. Этот файл оставлен для обратной
совместимости со старым кодом и внешними импортами.
"""

from helpdesk_app.models.core import *  # noqa: F401,F403
from helpdesk_app.models.core import db

__all__ = [name for name in globals().keys() if not name.startswith('_')]
