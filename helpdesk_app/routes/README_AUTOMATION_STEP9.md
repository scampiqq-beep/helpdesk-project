# Automation Engine — Step 9 (Kanban export fix + ticket audit bridge)

Этот шаг:
- исправляет ImportError по `KanbanService` из `helpdesk_app.services`
- восстанавливает дополнительные compatibility-экспорты для ticket routes
- добавляет bridge-layer для показа automation audit/history в карточке заявки

Что входит:
- расширенный `services.__init__`
- `ticket_automation_audit_service.py`
- безопасный payload для ticket detail / admin audit
