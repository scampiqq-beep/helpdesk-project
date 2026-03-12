Step 23: switched modern modules from aggregate model imports to direct thematic model modules.

What changed:
- app.py imports User/db from helpdesk_app.models.users/base
- mail_parser.py imports models from thematic modules
- extensions.py imports db from base
- ticket_list_service.py imports ticket_shared_departments from base

Compatibility shims remain in place:
- models.py
- helpdesk_app/models/core.py

This keeps legacy/runtime compatibility while reducing dependency on aggregate imports.
