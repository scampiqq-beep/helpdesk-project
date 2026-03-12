from __future__ import annotations

from flask import request
from flask_login import login_required

from helpdesk_app.services.organization_service import OrganizationService


@login_required
def admin_organizations():
    if request.method == 'POST':
        return OrganizationService.handle_list_post(request.form)
    return OrganizationService.render_list(request.args.get('q'))


@login_required
def admin_organization_card(inn: str):
    return OrganizationService.render_card(inn)


EXTRACTED_ENDPOINTS = {
    'admin_organizations': admin_organizations,
    'admin_organization_card': admin_organization_card,
}
