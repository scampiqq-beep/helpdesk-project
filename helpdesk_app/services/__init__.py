from helpdesk_app.services.ticket_service import (
    PermissionDenied,
    TicketService,
    TicketServiceError,
    ValidationError,
)

from helpdesk_app.services.automation_service import AutomationService
from helpdesk_app.services.automation_runtime_service import AutomationRuntimeService
from helpdesk_app.services.admin_automation_service import AdminAutomationService
from helpdesk_app.services.admin_automation_ui_service import AdminAutomationUIService
from helpdesk_app.services.automation_preview_service import AutomationPreviewService
from helpdesk_app.services.ticket_workflow_service import TicketWorkflowService
from helpdesk_app.services.ticket_automation_audit_service import TicketAutomationAuditService

# Admin compatibility exports expected by existing route modules
from helpdesk_app.services.admin_service import AdminAccessDenied, AdminService
from helpdesk_app.services.admin_settings_service import AdminSettingsService
from helpdesk_app.services.admin_sla_calendar_service import AdminSLACalendarService

# Client/profile/notifications/report compatibility exports
from helpdesk_app.services.notification_service import NotificationService
from helpdesk_app.services.profile_service import ProfileService
from helpdesk_app.services.report_service import ReportService
from helpdesk_app.services.knowledge_service import KnowledgeService
from helpdesk_app.services.reference_service import ReferenceDataService

# Ticket/detail/list/SLA compatibility exports
from helpdesk_app.services.sla_service import SLAService
from helpdesk_app.services.ticket_detail_service import TicketDetailService
from helpdesk_app.services.ticket_list_service import TicketListService
from helpdesk_app.services.history_service import HistoryService
from helpdesk_app.services.audit_service import AuditService
from helpdesk_app.services.kanban_service import KanbanService
from helpdesk_app.services.attachment_service import AttachmentService

from helpdesk_app.services.organization_service import OrganizationService
