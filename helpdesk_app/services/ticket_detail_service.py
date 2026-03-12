from __future__ import annotations

from helpdesk_app.services.sla_service import SLAService
from helpdesk_app.services.ticket_service import PermissionDenied, TicketService


class TicketDetailService:
    @staticmethod
    def build_context(ticket):
        return {
            "ticket": ticket,
            "sla_view": SLAService.build_ticket_view(ticket),
        }

    @staticmethod
    def render_page(ticket_id: int, actor, org_mismatch_requested: bool = False):
        from helpdesk_app.runtime import get_runtime

        legacy = get_runtime()
        ticket = legacy.SupportTicket.query.get_or_404(ticket_id)
        if not TicketService._can_access_ticket(ticket, actor):
            raise PermissionDenied('Недостаточно прав')
        return legacy.ticket_detail(ticket_id)
