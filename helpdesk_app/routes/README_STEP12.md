# STEP 12 — admin workflows bridge

Что вынесено на этом шаге:
- admin_support_list alias теперь идёт через новый ticket list layer;
- admin_users GET собран через AdminService (поиск, сортировка, пагинация, роли);
- admin_settings / admin_sla_calendar / admin_user_edit* заведены через единый admin bridge;
- централизован admin access guard и deny redirect.

Что пока специально оставлено в legacy:
- POST-обработчики admin_users;
- тяжёлая бизнес-логика admin_settings и admin_sla_calendar;
- часть CRUD по справочникам и настройкам.
