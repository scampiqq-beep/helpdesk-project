Step: Performance + SLA alignment

Changes in this patch:
- ticket_list uses new SLAService instead of legacy SLA view builder
- lighter ticket list query with load_only/selectinload and conditional join for department sort
- reports/statistics still reuse legacy analytics payload for compatibility,
  but SLA/FRT/MTTR metrics are recomputed via helpdesk_app.services.sla_service
- admin reports/statistics templates display resolve SLA and first-response SLA together
