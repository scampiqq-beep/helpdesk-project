Шаг 13 — тяжелая POST-логика админки вынесена в bridge-сервисы.

Что сделано:
- admin_users POST теперь обслуживается через AdminService.handle_users_post()
  для действий add/edit/delete/reset_user_password.
- admin_settings POST теперь частично обслуживается через
  AdminSettingsService:
  - save_mail
  - save_notifications_settings
  - save_system / set_default_intake_department
  - save_bitrix
  - add/rename/delete_department
  - add/edit/delete_tag
  - run_mail_parser_now
- admin_sla_calendar полностью переведён на AdminSLACalendarService
  для GET и основных POST-действий.

Зачем:
- убрать тяжёлую админскую POST-ветку из legacy-монолита;
- централизовать проверки прав, commit/rollback и redirect-flow;
- сохранить безопасный fallback в legacy для редких/неперенесённых действий.
