from datetime import datetime, UTC
from zoneinfo import ZoneInfo

APP_TZ_NAME = 'Asia/Yekaterinburg'
APP_TZ = ZoneInfo(APP_TZ_NAME)


def utcnow_naive() -> datetime:
    """Naive UTC для legacy-полей в SQLite."""
    return datetime.now(UTC).replace(tzinfo=None)


def local_now() -> datetime:
    return datetime.now(APP_TZ)


def to_local(dt: datetime | None, assume_local_for_naive: bool = True) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(APP_TZ)


def format_local(dt: datetime | None, fmt: str = '%d.%m.%Y %H:%M') -> str:
    local_dt = to_local(dt)
    return local_dt.strftime(fmt) if local_dt else ''
