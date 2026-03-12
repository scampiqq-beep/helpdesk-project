# Automation Engine — Step 2 (Ticket wiring)

Этот шаг подключает движок правил к реальным операциям с заявкой.

Что входит:
- helper для применения automation-result к тикету
- безопасный pre-save wiring для create/update flows
- bridge-layer без обязательной миграции БД
- подготовка к admin UI на следующем шаге

Что НЕ входит:
- отдельная таблица правил
- полноценная админка правил
- фоновые cron/queue правила
