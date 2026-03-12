# Step 24 — direct thematic model imports across services

На этом шаге сервисы и route-модули ещё сильнее отвязаны от compatibility-слоя моделей.

Что сделано:
- основные новые модули переведены с `legacy.<Model>` и агрегирующих model-imports на прямые импорты из тематических файлов `helpdesk_app/models/*`;
- `db` теперь чаще берётся напрямую из `helpdesk_app.models.base`;
- `User`, `SupportTicket`, `TicketMessage`, `TicketHistory`, `Notification`, `Department`, `TicketCategory`, `Settings`, `Tag`, `TicketCloseReason`, knowledge-модели и календарные модели импортируются напрямую в сервисах.

Что это даёт:
- новый код меньше зависит от shim-слоя моделей;
- следующий шаг проще: дочистить оставшиеся вызовы runtime/legacy helper-функций уже без смешивания их с model-access слоем.


Step FINAL:
- removed compatibility shims `legacy_app.py`, `models.py`, `helpdesk_app/models/core.py`;
- legacy monolith now imports ORM models directly from `helpdesk_app.models`.
