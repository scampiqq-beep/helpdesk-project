from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from helpdesk_app.domain.ticketing import (
    CLOSE_REASON_LABELS,
    DEFAULT_PRIORITY_LABELS,
    DEFAULT_STATUS_LABELS,
    normalize_close_reason,
    normalize_priority,
    normalize_status,
)


@dataclass(slots=True)
class ChoiceItem:
    value: str
    label: str
    raw: Any = None


class ReferenceDataService:
    """Единая точка доступа к доменным справочникам поверх legacy-функций.

    Нужен как bridge-слой: новые сервисы и шаблоны берут справочники из одного места,
    а не напрямую из legacy.* helper-ов.
    """

    @staticmethod
    def _legacy():
        from helpdesk_app.runtime import get_runtime
        return get_runtime()

    @classmethod
    def get_status_choices(cls) -> list[ChoiceItem]:
        legacy = cls._legacy()
        choices: list[ChoiceItem] = []
        try:
            items = legacy.get_active_statuses() or []
        except Exception:
            items = []
        seen: set[str] = set()
        for item in items:
            value = (getattr(item, 'name', None) or str(item) or '').strip()
            if not value or value in seen:
                continue
            seen.add(value)
            choices.append(ChoiceItem(value=value, label=normalize_status(value), raw=item))
        if not choices:
            for value, label in DEFAULT_STATUS_LABELS.items():
                if value in seen:
                    continue
                choices.append(ChoiceItem(value=value, label=label, raw=None))
        return choices

    @classmethod
    def get_priority_choices(cls) -> list[ChoiceItem]:
        legacy = cls._legacy()
        choices: list[ChoiceItem] = []
        try:
            items = legacy.get_active_priorities() or []
        except Exception:
            items = []
        seen: set[str] = set()
        for item in items:
            value = (getattr(item, 'name', None) or str(item) or '').strip().lower()
            if not value or value in seen:
                continue
            seen.add(value)
            choices.append(ChoiceItem(value=value, label=normalize_priority(value), raw=item))
        if not choices:
            for value, label in DEFAULT_PRIORITY_LABELS.items():
                if value in seen:
                    continue
                choices.append(ChoiceItem(value=value, label=label, raw=None))
        return choices

    @classmethod
    def get_close_reason_choices(cls) -> list[ChoiceItem]:
        legacy = cls._legacy()
        choices: list[ChoiceItem] = []
        try:
            items = legacy.get_active_close_reasons() or []
        except Exception:
            items = []
        seen: set[str] = set()
        for item in items:
            code = (getattr(item, 'code', None) or getattr(item, 'name', None) or str(item) or '').strip()
            if not code or code in seen:
                continue
            seen.add(code)
            label = normalize_close_reason(getattr(item, 'name', None) or code)
            choices.append(ChoiceItem(value=code, label=label or code, raw=item))
        if not choices:
            for value, label in CLOSE_REASON_LABELS.items():
                if value in seen:
                    continue
                choices.append(ChoiceItem(value=value, label=label, raw=None))
        return choices

    @classmethod
    def get_categories(cls):
        legacy = cls._legacy()
        try:
            return TicketCategory.query.filter_by(is_active=True).order_by(TicketCategory.sort_order).all()
        except Exception:
            return []

    @classmethod
    def get_tags(cls):
        legacy = cls._legacy()
        try:
            return legacy.get_active_tags()
        except Exception:
            return []

    @classmethod
    def get_departments(cls):
        legacy = cls._legacy()
        try:
            return Department.query.order_by(Department.name).all()
        except Exception:
            return []
