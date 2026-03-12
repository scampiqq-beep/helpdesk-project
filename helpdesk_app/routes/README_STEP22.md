# Step 22

На этом шаге большой модельный монолит `helpdesk_app/models/core.py` разрезан
на тематические модули без изменения схемы БД и без поломки legacy-импортов.

Новые модули:
- `helpdesk_app/models/base.py`
- `helpdesk_app/models/reference.py`
- `helpdesk_app/models/settings.py`
- `helpdesk_app/models/users.py`
- `helpdesk_app/models/knowledge.py`
- `helpdesk_app/models/tickets.py`
- `helpdesk_app/models/notifications.py`

Совместимость сохранена:
- `helpdesk_app/models/core.py` остался как compatibility shim
- `models.py` продолжает работать как shim на пакет `helpdesk_app.models`
