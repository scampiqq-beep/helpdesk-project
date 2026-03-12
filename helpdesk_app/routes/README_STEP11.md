# Step 11 — Ticket list + Kanban service layer

На этом шаге из legacy вынесены основные read-only сценарии списка заявок и Kanban:

- `ticket_list`
- AJAX partial для `ticket_list`
- `kanban`
- `api_kanban_tickets`
- alias `admin_kanban`

Добавлены bridge-сервисы:

- `helpdesk_app/services/ticket_list_service.py`
- `helpdesk_app/services/kanban_service.py`

Что это даёт:

- список заявок теперь собирается через service layer;
- фильтры/сортировка/пагинация и UI state вынесены из монолитного route;
- Kanban-страница и JSON-данные для неё тоже идут через новый слой;
- при любой нестандартной ситуации сохранён безопасный fallback в `legacy_app`.
