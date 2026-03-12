# Step 18 (safe transition variant)

Что сделано на этом шаге:

- тяжёлый монолит перенесён из `legacy_app.py` в `legacy_monolith.py`;
- `legacy_app.py` оставлен как тонкий compatibility shim без собственной бизнес-логики;
- `create_app()` и точки входа больше привязаны к `legacy_monolith.py`, а не к тяжёлому `legacy_app.py`;
- удалены bridge-модули `helpdesk_app/legacy_adapter.py` и `helpdesk_app/utils/legacy_fallback.py`.

Что ещё НЕ заявляется выполненным:

- полное удаление зависимости сервисов от compatibility-import `legacy_app`;
- перенос всех helper-функций из монолита в отдельные модульные сервисы;
- полный отказ от `legacy_monolith.py`.

Итог:

Это безопасный переходный этап, который реально уменьшает legacy-слой, но не
претендует на полностью завершённый zero-legacy refactor.
