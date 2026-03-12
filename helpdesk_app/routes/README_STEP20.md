# Step 20 — runtime/bootstrap cleanup + model import facade

Что сделано:

- добавлен `helpdesk_app/models/__init__.py` как единая точка импорта моделей;
- `app.py` больше не работает напрямую с сырой runtime-module и не содержит ошибки с `legacy`;
- `helpdesk_app/runtime.py` получил `RuntimeFacade`, `get_runtime_facade()` и `sync_extensions()`;
- `helpdesk_app/__init__.py` теперь использует фасад runtime вместо ручной синхронизации;
- `helpdesk_app/extensions.py`, `ticket_list_service.py` и `mail_parser.py` переведены на импорт моделей через `helpdesk_app.models`.

Что это даёт:

- меньше жёсткой связности с корневым `models.py`;
- точка входа стала стабильнее и чище;
- следующий шаг — переносить сами ORM-модели из корня проекта в `helpdesk_app/models/*` без массового переписывания импортов.
