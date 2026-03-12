# Performance + SLA alignment — Step 2

This patch focuses on the main hotspots observed in the current project:

1. `ticket_list` runtime cost
   - avoids unconditional join with `departments`
   - uses direct `SLAService.build_ticket_views(...)` instead of legacy SLA builder
   - adds `load_only(...)` and `selectinload(...)` to reduce row width and lazy loads

2. `reports` / `statistics` SLA alignment
   - keeps the legacy analytics payload for compatibility
   - recalculates SLA compliance, FRT and MTTR through the new `SLAService`
   - exposes `sla_alignment_meta` and `sla_compliance_breakdown`

This is a safe patch layer. It does not change the DB schema.
