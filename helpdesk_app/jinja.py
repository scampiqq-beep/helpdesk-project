from __future__ import annotations

from helpdesk_app.domain.ticketing import (
    OPERATOR_CLOSED_STATUSES,
    SLA_PAUSED_STATUSES,
    normalize_close_reason,
    normalize_priority,
    normalize_status,
)
from helpdesk_app.services.reference_service import ReferenceDataService


def register_jinja_helpers(app):
    @app.template_filter('ticket_status_label')
    def ticket_status_label(value):
        return normalize_status(value)

    @app.template_filter('ticket_priority_label')
    def ticket_priority_label(value):
        return normalize_priority(value)

    @app.template_filter('ticket_close_reason_label')
    def ticket_close_reason_label(value):
        return normalize_close_reason(value)

    @app.template_test('ticket_terminal_status')
    def ticket_terminal_status(value):
        return normalize_status(value) in OPERATOR_CLOSED_STATUSES

    @app.template_test('ticket_sla_paused')
    def ticket_sla_paused(value):
        return normalize_status(value) in SLA_PAUSED_STATUSES

    @app.context_processor
    def inject_ticketing_helpers():
        return {
            'ticket_status_label': normalize_status,
            'ticket_priority_label': normalize_priority,
            'ticket_close_reason_label': normalize_close_reason,
            'ticket_status_choices': ReferenceDataService.get_status_choices,
            'ticket_priority_choices': ReferenceDataService.get_priority_choices,
            'ticket_close_reason_choices': ReferenceDataService.get_close_reason_choices,
        }
