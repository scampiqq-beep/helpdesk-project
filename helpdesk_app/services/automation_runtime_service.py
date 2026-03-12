from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from flask import current_app

from helpdesk_app.services.automation_service import AutomationService
from helpdesk_app.services.automation_execution_log_service import AutomationExecutionLogService


class AutomationRuntimeService:
    """Runtime wiring для применения правил к тикету и записи тех. лога."""

    @staticmethod
    def run_for_ticket(
        ticket: Any,
        rules: Optional[Iterable[dict]] = None,
        *,
        apply_mutations: bool = True,
        source: str = "runtime",
    ) -> Dict[str, Any]:
        active_rules = list(rules) if rules is not None else AutomationRuntimeService.load_runtime_rules()
        result = AutomationService.evaluate_rules(ticket, active_rules)
        if apply_mutations:
            AutomationRuntimeService.apply_mutations(ticket, result.get("mutations") or {})
        AutomationRuntimeService.log_execution(ticket, result, source=source, apply_mutations=apply_mutations)
        return result

    @staticmethod
    def load_runtime_rules() -> List[dict]:
        try:
            from helpdesk_app.services.admin_automation_ui_service import AdminAutomationUIService
            return AdminAutomationUIService.load_rules()
        except Exception:
            return AutomationService.default_rule_templates()

    @staticmethod
    def _resolve_department(value: Any):
        if value in [None, ""]:
            return None
        try:
            from helpdesk_app.models.reference import Department
        except Exception:
            return None

        try:
            text = str(value).strip()
            if not text:
                return None
            if text.isdigit():
                return Department.query.get(int(text))
            return Department.query.filter(Department.name.ilike(text)).first()
        except Exception:
            return None

    @staticmethod
    def apply_mutations(ticket: Any, mutations: Dict[str, Any]) -> None:
        if "priority" in mutations and mutations["priority"] is not None:
            setattr(ticket, "priority", mutations["priority"])

        if "department" in mutations and mutations["department"] is not None:
            department = AutomationRuntimeService._resolve_department(mutations["department"])
            if department is not None:
                setattr(ticket, "department_id", getattr(department, "id", None))
                setattr(ticket, "department_rel", department)
            else:
                current_app.logger.warning("Automation department not found: %s", mutations["department"])

        if "status" in mutations and mutations["status"] is not None:
            setattr(ticket, "status", mutations["status"])

        if "is_critical" in mutations:
            setattr(ticket, "is_critical", bool(mutations["is_critical"]))

        if mutations.get("assignee_email") is not None:
            setattr(ticket, "_automation_assignee_email", mutations["assignee_email"])

        if mutations.get("tags_to_add"):
            existing = list(getattr(ticket, "_automation_tags_to_add", []) or [])
            existing.extend(mutations["tags_to_add"])
            setattr(ticket, "_automation_tags_to_add", existing)

        if mutations.get("internal_notes"):
            existing = list(getattr(ticket, "_automation_internal_notes", []) or [])
            existing.extend(mutations["internal_notes"])
            setattr(ticket, "_automation_internal_notes", existing)

    @staticmethod
    def log_execution(ticket: Any, result: Dict[str, Any], *, source: str, apply_mutations: bool) -> None:
        try:
            AutomationExecutionLogService.append_entry({
                "source": source,
                "ticket_id": getattr(ticket, "id", None),
                "ticket_subject": getattr(ticket, "subject", None),
                "matched_rules": list(result.get("matched_rules", []) or []),
                "execution_log": list(result.get("execution_log", []) or []),
                "mutations": dict(result.get("mutations") or {}),
                "applied": bool(apply_mutations),
            })
        except Exception:
            current_app.logger.exception("Automation execution log write failed")
