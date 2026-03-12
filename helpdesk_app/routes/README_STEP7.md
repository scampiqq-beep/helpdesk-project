# STEP 7 — History / Timeline / Attachments services

На этом шаге выделены отдельные сервисы:

- `helpdesk_app/services/history_service.py`
- `helpdesk_app/services/attachment_service.py`

Что переведено на новый слой:

- добавление вложений к комментариям;
- удаление вложений при редактировании комментария;
- удаление вложений вместе с комментарием;
- системные сообщения по заявке;
- история по статусам/отделам для части вынесенных ticket-actions;
- единый helper `TicketService.get_ticket_timeline()` для следующего этапа очистки GET `ticket_detail()`.

Цель шага:

1. убрать файловую логику из `TicketService`;
2. перестать размазывать работу с `TicketHistory` и `TicketMessage` по монолиту;
3. подготовить почву под следующий этап — вынос timeline/history блока из legacy GET `ticket_detail()`.
