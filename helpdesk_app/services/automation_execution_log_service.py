from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List

from flask import current_app


class AutomationExecutionLogService:
    STORAGE_FILENAME = "automation_execution_log.json"
    MAX_ENTRIES = 200

    @classmethod
    def storage_path(cls) -> str:
        instance_path = current_app.instance_path
        os.makedirs(instance_path, exist_ok=True)
        return os.path.join(instance_path, cls.STORAGE_FILENAME)

    @classmethod
    def load_entries(cls) -> List[Dict[str, Any]]:
        path = cls.storage_path()
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                return data
        except Exception:
            return []
        return []

    @classmethod
    def append_entry(cls, entry: Dict[str, Any]) -> None:
        items = cls.load_entries()
        items.insert(0, {
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            **dict(entry or {}),
        })
        items = items[: cls.MAX_ENTRIES]
        with open(cls.storage_path(), "w", encoding="utf-8") as fh:
            json.dump(items, fh, ensure_ascii=False, indent=2)

    @classmethod
    def recent_entries(cls, limit: int = 15) -> List[Dict[str, Any]]:
        return list(cls.load_entries()[: max(1, limit)])
