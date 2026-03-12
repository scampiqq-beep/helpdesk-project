# SLA v2 — Step 1

На этом шаге введён единый `helpdesk_app/services/sla_service.py` как центральный SLA-layer.

Что изменено:
- чтение SLA-настроек теперь идёт через `Settings` + `SLAService`, а не напрямую из разных мест;
- `ticket_detail_service` получает `sla_view` и `sla_policy` через новый сервис;
- `ticket_list_service` перестал напрямую вызывать `legacy.build_ticket_sla_views(...)`;
- `admin_sla_calendar_service` теперь рендерит текущую SLA-конфигурацию через `SLAService.get_policy_context()`.

Что это даёт:
- единый источник SLA-конфигурации;
- подготовка к следующему шагу: first response / resolution timers / pause-resume.
