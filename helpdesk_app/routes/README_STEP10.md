Шаг 10: domain/UI integration и единые справочники.

Что сделано:
- добавлен `ReferenceDataService` как единая точка доступа к статусам, приоритетам,
  причинам закрытия, категориям, тегам и отделам;
- добавлен `helpdesk_app/jinja.py`;
- зарегистрированы Jinja filters/tests/context helpers:
  - `ticket_status_label`
  - `ticket_priority_label`
  - `ticket_close_reason_label`
  - test `ticket_terminal_status`
  - test `ticket_sla_paused`
- `TicketDetailService` больше не тянет справочники напрямую из `legacy_app.*` helper-ов.

Что это даёт:
- доменный слой начинает использоваться не только в сервисах, но и в UI;
- шаблоны можно дальше чистить без дублирования форматирования статусов/приоритетов;
- подготовлен фундамент для следующего шага: вынос оставшихся legacy helper-ов и
  постепенная нормализация ticket_list / kanban / admin UI через reference/domain layer.
