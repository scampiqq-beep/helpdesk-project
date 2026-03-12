from __future__ import annotations

from flask import render_template
from flask_login import login_required

from helpdesk_app.services.admin_automation_preview_ui_service import AdminAutomationPreviewUIService
from helpdesk_app.services.admin_service import AdminAccessDenied, AdminService


@login_required
def admin_automation_preview(ticket_id: int):
    try:
        AdminService.ensure_admin_or_operator()
    except AdminAccessDenied:
        return AdminService.deny_response()
    ctx = AdminAutomationPreviewUIService.preview_ticket(ticket_id)
    return render_template("admin_automation_preview.html", **ctx)


EXTRACTED_ENDPOINTS = {
    'admin_automation_preview': admin_automation_preview,
}
