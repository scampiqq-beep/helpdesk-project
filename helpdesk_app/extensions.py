"""Точка совместимости для расширений.

Реальные объекты runtime сейчас инициализируются в legacy_monolith.py.
Этот модуль нужен как первый шаг к нормальной архитектуре и для новых модулей.
"""

from helpdesk_app.models.base import db

login_manager = None
mail = None
migrate = None
socketio = None
