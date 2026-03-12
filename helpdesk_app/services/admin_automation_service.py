from __future__ import annotations

from helpdesk_app.services.automation_service import AutomationService


class AdminAutomationService:
    """Подготовка к UI админки правил.

    В этом шаге — только безопасные helpers для следующего этапа.
    """

    @staticmethod
    def get_rule_templates():
        return AutomationService.default_rule_templates()

    @staticmethod
    def get_rule_builder_context():
        templates = AutomationService.default_rule_templates()
        return {
            "templates": templates,
            "condition_types": [
                "status_equals",
                "priority_equals",
                "category_equals",
                "department_equals",
                "source_equals",
                "customer_type_equals",
                "title_contains",
                "description_contains",
                "sla_breached",
            ],
            "action_types": [
                "set_priority",
                "set_department",
                "set_assignee_email",
                "add_tag",
                "add_internal_note",
                "set_critical",
                "set_status",
            ],
        }
