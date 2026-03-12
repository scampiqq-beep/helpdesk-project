from __future__ import annotations

from enum import StrEnum


class TimelineEventKind(StrEnum):
    COMMENT = 'comment'
    HISTORY = 'history'
    SYSTEM = 'system'
    ATTACHMENT = 'attachment'


DEFAULT_STATUS_LABELS = {
    'Новая': 'Новая',
    'Принята': 'Принята',
    'В работе': 'В работе',
    'Ожидание': 'Ожидание',
    'Ожидание клиента': 'Ожидание клиента',
    'Завершена': 'Завершена',
    'Спам': 'Спам',
    'Дубликат': 'Дубликат',
    'Ошибочная': 'Ошибочная',
    'Ошибочно': 'Ошибочная',
    'Отозвана': 'Отозвана',
}

DEFAULT_PRIORITY_LABELS = {
    'low': 'Низкий',
    'medium': 'Средний',
    'high': 'Высокий',
    'critical': 'Критический',
}

CLOSE_REASON_LABELS = {
    'mark_spam': 'Спам',
    'spam': 'Спам',
    'close_mistake': 'Ошибочная',
    'mistake': 'Ошибочная',
    'close_withdrawn': 'Отозвана',
    'withdrawn': 'Отозвана',
    'close_duplicate': 'Дубликат',
    'duplicate': 'Дубликат',
    'resolved': 'Решено',
}

CLOSE_REASON_CODES = tuple(sorted(CLOSE_REASON_LABELS.keys()))
TERMINAL_STATUSES = ('Завершена', 'Спам', 'Дубликат', 'Ошибочная', 'Ошибочно', 'Отозвана')
OPERATOR_CLOSED_STATUSES = ('Завершена', 'Спам', 'Дубликат', 'Ошибочная', 'Отозвана')
SLA_PAUSED_STATUSES = ('Ожидание', 'Ожидание клиента')


def normalize_status(status: str | None) -> str:
    value = (status or '').strip()
    if not value:
        return ''
    return DEFAULT_STATUS_LABELS.get(value, value)



def normalize_priority(priority: str | None) -> str:
    value = (priority or '').strip().lower()
    if not value:
        return ''
    return DEFAULT_PRIORITY_LABELS.get(value, value)



def normalize_close_reason(reason: str | None) -> str:
    value = (reason or '').strip()
    if not value:
        return ''
    return CLOSE_REASON_LABELS.get(value, value)
