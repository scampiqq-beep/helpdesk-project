from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from helpdesk_app.services.automation_runtime_service import AutomationRuntimeService
from helpdesk_app.services.ticket_service import TicketService


class AutomationPreviewService:
    @staticmethod
    def preview_ticket(ticket: Any, rules: Optional[Iterable[dict]] = None) -> Dict[str, Any]:
        before_state = {
            "status": getattr(ticket, "status", None),
            "priority": getattr(ticket, "priority", None),
            "department": getattr(getattr(ticket, "department_rel", None), "name", None) or getattr(getattr(ticket, "department", None), "name", None) or getattr(ticket, "department", None),
            "is_critical": bool(getattr(ticket, "is_critical", False)),
        }
        result = AutomationRuntimeService.run_for_ticket(ticket, rules=rules, apply_mutations=False, source="preview")
        mutations = dict(result.get("mutations") or {})
        after_state = {
            "status": mutations.get("status") if mutations.get("status") is not None else before_state.get("status"),
            "priority": mutations.get("priority") if mutations.get("priority") is not None else before_state.get("priority"),
            "department": mutations.get("department") if mutations.get("department") is not None else before_state.get("department"),
            "is_critical": mutations.get("is_critical") if "is_critical" in mutations else before_state.get("is_critical"),
        }
        return {
            "ticket_id": getattr(ticket, "id", None),
            "matched_rules": list(result.get("matched_rules", []) or []),
            "execution_log": list(result.get("execution_log", []) or []),
            "mutations": mutations,
            "automation_context": TicketService.collect_automation_context(ticket),
            "before_state": before_state,
            "after_state": after_state,
        }
