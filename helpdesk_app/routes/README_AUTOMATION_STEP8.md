# Automation Engine — Step 8 (Preview + Audit/UI)

Этот шаг добавляет UI-слой для preview и audit по правилам автоматизации.

Что входит:
- route-модуль preview/audit
- service для подготовки preview payload по тикету
- partial-шаблоны для показа matched rules / mutations / execution log
- безопасный read-only режим: ничего не пишет в БД

Что важно:
- это именно preview/audit UI
- фактическое автоприменение правил уже подготовлено на прошлых шагах
- этот шаг помогает видеть, какие правила бы сработали и что бы они изменили
