# Step 21 — physical ORM move into helpdesk_app.models

Что сделано:
- физические определения ORM-моделей перенесены в `helpdesk_app/models/core.py`;
- корневой `models.py` превращён в compatibility shim;
- `helpdesk_app.models` теперь импортирует модели напрямую из локального пакета, а не из корня.

Что это даёт:
- модульный слой теперь меньше зависит от корневой структуры проекта;
- следующий шаг можно делать уже как разбиение `core.py` на тематические модули (`user.py`, `ticket.py`, `knowledge.py`, ...);
- legacy и новый код продолжают работать через прежние импорты `from models import ...`.
