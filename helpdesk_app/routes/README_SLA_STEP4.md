SLA v2 — шаг 3.

Что изменено:
- `SLAService` теперь сам считает два независимых SLA-состояния:
  - первый ответ;
  - решение заявки.
- Для списка заявок добавлен пакетный расчёт `first_response` через `TicketMessage`.
- `ticket.sla_view` и `sla_view` возвращают совместимую со старым UI структуру:
  - `first_response.label`
  - `first_response.deadline_text`
  - `first_response.timer_text`
  - `resolve.label`
  - `resolve.deadline_text`
  - `resolve.timer_text`
  - `summary`
  - `summary_status`
- Сохранил совместимость `/admin/sla-calendar` с шаблоном, где `cfg.workdays` должен быть CSV-строкой.
