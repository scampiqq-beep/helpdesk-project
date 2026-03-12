from __future__ import annotations

from typing import Any, Dict

from helpdesk_app.services.ticket_service import TicketService
from helpdesk_app.services.history_service import HistoryService
from helpdesk_app.services.audit_service import AuditService


class TicketWorkflowService:
    """Bridge-layer для подключения automation к рабочим сценариям тикета."""

    @staticmethod
    def before_create(ticket: Any) -> Dict[str, Any]:
        execution = TicketService.apply_automation_on_create(ticket)
        return {
            "automation_execution": execution,
            "automation_history": HistoryService.build_automation_history_entries(execution),
            "automation_audit": AuditService.build_automation_audit_snapshot(execution),
            "automation_context": TicketService.collect_automation_context(ticket),
        }

    @staticmethod
    def before_update(ticket: Any) -> Dict[str, Any]:
        execution = TicketService.apply_automation_on_update(ticket)
        return {
            "automation_execution": execution,
            "automation_history": HistoryService.build_automation_history_entries(execution),
            "automation_audit": AuditService.build_automation_audit_snapshot(execution),
            "automation_context": TicketService.collect_automation_context(ticket),
        }

    @staticmethod
    def attach_runtime_payload(ticket: Any, payload: Dict[str, Any]) -> None:
        setattr(ticket, "_automation_execution", payload.get("automation_execution"))
        setattr(ticket, "_automation_history", payload.get("automation_history"))
        setattr(ticket, "_automation_audit", payload.get("automation_audit"))
        setattr(ticket, "_automation_context", payload.get("automation_context"))
