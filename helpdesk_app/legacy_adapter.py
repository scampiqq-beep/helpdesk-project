from __future__ import annotations

from typing import Any


class LegacyAdapter:
    """Централизованный доступ к оставшимся legacy-функциям.

    Нужен как переходный слой, чтобы новые сервисы не импортировали
    `legacy_app` хаотично из разных мест.
    """

    @staticmethod
    def module():
        import legacy_app
        return legacy_app

    @classmethod
    def get(cls, name: str, default: Any = None) -> Any:
        return getattr(cls.module(), name, default)

    @classmethod
    def call(cls, name: str, *args, **kwargs) -> Any:
        func = getattr(cls.module(), name)
        return func(*args, **kwargs)
