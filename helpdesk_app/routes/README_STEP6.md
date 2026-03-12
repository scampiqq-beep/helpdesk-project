STEP 6 — remaining ticket_detail POST-actions moved to service layer.

Moved from legacy_app.ticket_detail into helpdesk_app/services/ticket_service.py:
- reopen_ticket_operator
- reopen_ticket
- client_complete_ticket
- update_ticket_meta
- mark_spam
- close_mistake
- close_withdrawn
- close_duplicate
- complete_ticket
- delegate_ticket
- update_shared_departments
- update_departments_sidebar

helpdesk_app/routes/tickets.py now intercepts these POST actions before falling back to legacy_app.ticket_detail().
This keeps the current URLs and templates stable while shrinking the legacy ticket_detail() action block.
