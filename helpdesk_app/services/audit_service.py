from __future__ import annotations

from typing import Dict, Any


class AuditService:
    @staticmethod
    def build_automation_audit_snapshot(execution_result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "matched_rules": list(execution_result.get("matched_rules", []) or []),
            "execution_log": list(execution_result.get("execution_log", []) or []),
        }

    @staticmethod
    def list_records(action: str = "", actor: str = "", target_type: str = ""):
        """Пока audit log не вынесен в отдельную модель, отдаём безопасный пустой список.

        Это сохраняет рабочую страницу журнала и не ломает админку до полноценной
        реализации хранилища событий.
        """
        return []
