Шаг 4: вынос реальных ticket-actions в services

Что вынесено:
- accept_ticket
- edit_ticket_comment
- delete_ticket_comment
- update_ticket_department
- update_ticket_priority
- toggle_ticket_critical

Что изменилось:
- route handlers в helpdesk_app/routes/tickets.py теперь тонкие и вызывают TicketService
- повторяющаяся логика прав/валидации/commit вынесена в helpdesk_app/services/ticket_service.py
- карта URL не менялась: endpoints подменяются через attach_extracted_routes(app)

Следующий шаг:
- вынести создание комментариев, вложения, ticket detail POST-actions и SLA pause/resume
- начать перенос сложной логики ticket_detail() в отдельные service-функции
