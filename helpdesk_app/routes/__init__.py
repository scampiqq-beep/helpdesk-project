from __future__ import annotations

from helpdesk_app.routes.auth import EXTRACTED_ENDPOINTS as AUTH_ENDPOINTS
from helpdesk_app.routes.admin import EXTRACTED_ENDPOINTS as ADMIN_ENDPOINTS
from helpdesk_app.routes.client import EXTRACTED_ENDPOINTS as CLIENT_ENDPOINTS
from helpdesk_app.routes.reports import EXTRACTED_ENDPOINTS as REPORT_ENDPOINTS
from helpdesk_app.routes.tickets import EXTRACTED_ENDPOINTS as TICKET_ENDPOINTS
from helpdesk_app.routes.knowledge import EXTRACTED_ENDPOINTS as KNOWLEDGE_ENDPOINTS
from helpdesk_app.routes.organizations import EXTRACTED_ENDPOINTS as ORGANIZATION_ENDPOINTS
from helpdesk_app.routes.admin_automation import EXTRACTED_ENDPOINTS as AUTOMATION_ENDPOINTS
from helpdesk_app.routes.admin_automation_preview import EXTRACTED_ENDPOINTS as AUTOMATION_PREVIEW_ENDPOINTS


ALL_EXTRACTED_ENDPOINTS = {}
ALL_EXTRACTED_ENDPOINTS.update(AUTH_ENDPOINTS)
ALL_EXTRACTED_ENDPOINTS.update(ADMIN_ENDPOINTS)
ALL_EXTRACTED_ENDPOINTS.update(CLIENT_ENDPOINTS)
ALL_EXTRACTED_ENDPOINTS.update(REPORT_ENDPOINTS)
ALL_EXTRACTED_ENDPOINTS.update(TICKET_ENDPOINTS)
ALL_EXTRACTED_ENDPOINTS.update(KNOWLEDGE_ENDPOINTS)
ALL_EXTRACTED_ENDPOINTS.update(ORGANIZATION_ENDPOINTS)
ALL_EXTRACTED_ENDPOINTS.update(AUTOMATION_ENDPOINTS)
ALL_EXTRACTED_ENDPOINTS.update(AUTOMATION_PREVIEW_ENDPOINTS)


def attach_extracted_routes(app):
    """Подменяет view_functions на вынесенные из монолита обработчики.

    Правила URL остаются прежними, поэтому ссылки и шаблоны не ломаются.
    Это безопасный промежуточный шаг перед полной регистрацией blueprint'ов.
    """
    for endpoint, view_func in ALL_EXTRACTED_ENDPOINTS.items():
        if endpoint in app.view_functions:
            app.view_functions[endpoint] = view_func

    # Новые системные endpoints, которых раньше в монолите не было.
    if 'api_system_health' not in app.view_functions:
        app.add_url_rule('/api/system/health', endpoint='api_system_health', view_func=AUTH_ENDPOINTS['api_system_health'])
    if 'admin_organizations' not in app.view_functions:
        app.add_url_rule('/admin/organizations', endpoint='admin_organizations', view_func=ORGANIZATION_ENDPOINTS['admin_organizations'], methods=['GET', 'POST'])
    if 'admin_organization_card' not in app.view_functions:
        app.add_url_rule('/admin/organizations/<string:inn>', endpoint='admin_organization_card', view_func=ORGANIZATION_ENDPOINTS['admin_organization_card'])

    if 'admin_settings_section' not in app.view_functions:
        app.add_url_rule('/admin/settings/<string:section>', endpoint='admin_settings_section', view_func=ADMIN_ENDPOINTS['admin_settings_section'], methods=['GET', 'POST'])
    if 'admin_automation_index' not in app.view_functions:
        app.add_url_rule('/admin/automation', endpoint='admin_automation_index', view_func=AUTOMATION_ENDPOINTS['admin_automation_index'])
    if 'admin_automation_create' not in app.view_functions:
        app.add_url_rule('/admin/automation/create', endpoint='admin_automation_create', view_func=AUTOMATION_ENDPOINTS['admin_automation_create'], methods=['POST'])
    if 'admin_automation_delete' not in app.view_functions:
        app.add_url_rule('/admin/automation/delete/<string:rule_key>', endpoint='admin_automation_delete', view_func=AUTOMATION_ENDPOINTS['admin_automation_delete'], methods=['POST'])
    if 'admin_automation_toggle' not in app.view_functions:
        app.add_url_rule('/admin/automation/toggle/<string:rule_key>', endpoint='admin_automation_toggle', view_func=AUTOMATION_ENDPOINTS['admin_automation_toggle'], methods=['POST'])
    if 'admin_automation_preview' not in app.view_functions:
        app.add_url_rule('/admin/automation/preview/<int:ticket_id>', endpoint='admin_automation_preview', view_func=AUTOMATION_PREVIEW_ENDPOINTS['admin_automation_preview'])
    if 'admin_sla_settings' not in app.view_functions:
        app.add_url_rule('/admin/sla', endpoint='admin_sla_settings', view_func=ADMIN_ENDPOINTS['admin_sla_settings'], methods=['GET', 'POST'])
    if 'admin_work_calendar' not in app.view_functions:
        app.add_url_rule('/admin/calendar', endpoint='admin_work_calendar', view_func=ADMIN_ENDPOINTS['admin_work_calendar'], methods=['GET', 'POST'])
    if 'save_ticket_list_preferences' not in app.view_functions:
        app.add_url_rule('/api/ui/ticket-list', endpoint='save_ticket_list_preferences', view_func=TICKET_ENDPOINTS['save_ticket_list_preferences'], methods=['POST'])

    return app
