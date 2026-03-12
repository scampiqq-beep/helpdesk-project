# Step 15 — profile / notifications / reports services

На этом шаге из legacy_app вынесены ещё три пользовательских слоя:

- `user_profile` → `ProfileService`
- `notifications_page`, `open_notification`, `notifications_mark_all_read` → `NotificationService`
- `admin_statistics`, `admin_reports`, `admin_reports_export_xlsx`, `admin_analytics_export` → `ReportService`

Что это даёт:

- профиль пользователя больше не живёт целиком в монолите;
- уведомления вынесены в отдельный сервисный слой без изменения БД;
- аналитика и Excel-экспорт теперь централизованы через bridge-service;
- старые URL и endpoint-имена сохранены.
