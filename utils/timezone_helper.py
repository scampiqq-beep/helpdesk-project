
from datetime import datetime
from zoneinfo import ZoneInfo

LOCAL_TZ=ZoneInfo("Asia/Yekaterinburg")

def to_local(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=LOCAL_TZ)
    return dt.astimezone(LOCAL_TZ)

def format_local(dt):
    if not dt:
        return ""
    dt=to_local(dt)
    return dt.strftime("%d.%m.%Y %H:%M")
