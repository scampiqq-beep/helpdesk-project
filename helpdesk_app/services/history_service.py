from __future__ import annotations

from typing import Any, Dict, List


class HistoryService:
    @staticmethod
    def build_automation_history_entries(execution_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        items = []
        for entry in execution_result.get("execution_log", []) or []:
            if not entry.get("matched"):
                continue
            items.append(
                {
                    "type": "automation.rule_matched",
                    "title": f"Automation rule matched: {entry.get('rule_key')}",
                    "details": ", ".join(entry.get("applied_actions", []) or []),
                }
            )
        return items
