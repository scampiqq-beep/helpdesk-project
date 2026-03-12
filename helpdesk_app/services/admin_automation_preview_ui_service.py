from __future__ import annotations

from typing import Any, Dict

from helpdesk_app.models.tickets import SupportTicket
from helpdesk_app.services.admin_automation_ui_service import AdminAutomationUIService
from helpdesk_app.services.automation_preview_service import AutomationPreviewService


class AdminAutomationPreviewUIService:
    @staticmethod
    def preview_ticket(ticket_id: int) -> Dict[str, Any]:
        ticket = SupportTicket.query.get_or_404(ticket_id)
        rules = AdminAutomationUIService.load_rules()
        preview = AutomationPreviewService.preview_ticket(ticket, rules=rules)
        return {
            "ticket": ticket,
            "preview": preview,
            "matched_rules_count": len(preview.get("matched_rules", []) or []),
            "execution_log_count": len(preview.get("execution_log", []) or []),
            "recent_tickets": SupportTicket.query.order_by(SupportTicket.created_at.desc()).limit(10).all(),
        }
