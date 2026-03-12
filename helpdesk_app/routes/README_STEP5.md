# Step 5 — ticket_detail POST actions → services

На этом шаге из legacy `ticket_detail()` вынесены типовые POST-действия:

- добавление комментария;
- загрузка вложений к комментарию;
- перенос реквизитов организации из заявки в профиль клиента;
- finish-modal (`waiting` / закрытие с причиной);
- клиентские действия `accept_work` / `request_rework`.

## Что изменилось

- `helpdesk_app/routes/tickets.py` теперь перехватывает часть POST-логики и не отправляет её в монолит;
- `helpdesk_app/services/ticket_service.py` получил новые методы:
  - `copy_org_to_profile()`
  - `finish_modal()`
  - `add_comment()`
  - `apply_client_feedback()`
- legacy `ticket_detail()` по-прежнему используется для GET и для остальных POST-actions, которые ещё не вынесены.

## Следующий шаг

- вынести оставшиеся POST-actions из `ticket_detail()`:
  - `reopen_ticket_operator`
  - делегирование / shared departments
  - закрепление результата
  - смену статуса оператором
- после этого уже можно безопасно выносить timeline / history и отдельный attachment service.
