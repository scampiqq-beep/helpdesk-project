# Step 19 — runtime context decoupling

На этом шаге модульные `routes/*` и `services/*` перестают импортировать `legacy_app` напрямую.

Что сделано:
- добавлен `helpdesk_app/runtime.py` — единая точка доступа к runtime-контексту;
- `helpdesk_app/__init__.py` и `app.py` используют `get_runtime()`;
- service/route-модули переведены с `import legacy_app` на `get_runtime()`;
- подготовлен следующий этап для реального удаления compatibility shim.

Что это даёт:
- меньше прямой связности с `legacy_app.py`;
- проще искать остаточные legacy-зависимости;
- следующий шаг можно делать уже по импорту `legacy_monolith`/`legacy_app` только в ограниченном числе мест.
