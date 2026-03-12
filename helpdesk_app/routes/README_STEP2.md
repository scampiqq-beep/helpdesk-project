# Step 2 — extraction of route groups from monolith

This iteration keeps the old URL map intact but moves part of the handlers into dedicated modules:

- `auth.py`
- `client.py`
- `admin.py`
- `reports.py`

To preserve backward compatibility, `create_app()` swaps `app.view_functions[...]` for the extracted handlers.
That means:

- URLs and templates remain unchanged
- behavior stays stable
- handlers already live outside `legacy_app.py`

Next step:
- move ticket routes to `tickets.py`
- move heavy business logic to `services/`
- replace compatibility swapping with full blueprint registration


Step 3 additions:
- `tickets.py` extracted for core ticket endpoints (`ticket_list`, `ticket_detail`, `create_ticket`, `kanban`, `api_user_tickets`, `accept_ticket`)
- `services/ticket_service.py` introduced as first service layer for reusable ticket operations
- `services/sla_service.py` introduced as a single entry-point for SLA badge formatting
