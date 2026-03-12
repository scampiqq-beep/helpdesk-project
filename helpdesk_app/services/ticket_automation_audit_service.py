from __future__ import annotations

from typing import Any, Dict, List


class TicketAutomationAuditService:
    """Bridge-layer для вывода automation runtime payload в UI/audit.

    Ничего не пишет в БД. Только читает runtime-поля, если они уже были
    прикреплены к тикету workflow-слоем.
    """

    @staticmethod
    def build_ticket_payload(ticket: Any) -> Dict[str, Any]:
        execution = getattr(ticket, "_automation_execution", None) or {}
        history = list(getattr(ticket, "_automation_history", []) or [])
        audit = getattr(ticket, "_automation_audit", None) or {}
        context = getattr(ticket, "_automation_context", None) or {}

        return {
            "execution": execution,
            "history": history,
            "audit": audit,
            "context": context,
            "matched_rules": list(execution.get("matched_rules", []) or []),
            "execution_log": list(execution.get("execution_log", []) or []),
        }

    @staticmethod
    def build_ticket_timeline_items(ticket: Any) -> List[Dict[str, Any]]:
        payload = TicketAutomationAuditService.build_ticket_payload(ticket)
        items: List[Dict[str, Any]] = []

        for row in payload.get("execution_log", []):
            if not row.get("matched"):
                continue
            items.append(
                {
                    "type": "automation.rule_matched",
                    "title": f"Automation rule matched: {row.get('rule_key')}",
                    "details": ", ".join(row.get("applied_actions", []) or []),
                }
            )
        return items
