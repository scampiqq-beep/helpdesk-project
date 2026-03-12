# Step 17

Что добавлено:
- `helpdesk_app/legacy_adapter.py` — централизованный доступ к оставшимся legacy-вызовам.
- `helpdesk_app/utils/legacy_fallback.py` — единая точка fallback в legacy.
- `helpdesk_app/services/config_validation_service.py` — проверка базовой конфигурации.
- `helpdesk_app/services/system_health_service.py` — health-check состояния системы.
- `/api/system/health` — JSON endpoint для проверки доступности приложения.

Этот шаг не ломает старые URL и подготавливает проект к дальнейшей чистке `legacy_app.py`.
