from flask_login import UserMixin

from .base import db, utcnow, user_departments

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=True)
    last_name = db.Column(db.String(120), nullable=True)
    patronymic = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    # Исторически подтверждение email было у клиента. Теперь это в общей таблице users.
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    # admin | operator | client
    role = db.Column(db.String(20), nullable=False, default='client')
    created_at = db.Column(db.DateTime, default=utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    department = db.relationship('Department', back_populates='users')
    # Дополнительные отделы (оператор может быть в нескольких)
    departments = db.relationship('Department', secondary=user_departments, back_populates='operators')

    phone = db.Column(db.String(20), nullable=True)
    organization = db.Column(db.String(200))
    inn = db.Column(db.String(12))      # ИНН — 10 или 12 цифр
    address = db.Column(db.String(300))

    # Предложенные реквизиты (из CRM/парсеров). Не перетирают введённые пользователем,
    # должны быть подтверждены вручную (клиентом или оператором).
    suggested_organization = db.Column(db.String(200), nullable=True)
    suggested_inn = db.Column(db.String(12), nullable=True)
    suggested_address = db.Column(db.String(300), nullable=True)
    # Должность/позиция (в первую очередь для клиентов)
    position = db.Column(db.String(100), nullable=True)

    # Настройки уведомлений (In-app)
    notify_inapp_enabled = db.Column(db.Boolean, default=True, nullable=False)
    notify_event_assigned = db.Column(db.Boolean, default=True, nullable=False)
    notify_event_customer_reply = db.Column(db.Boolean, default=True, nullable=False)
    notify_event_status = db.Column(db.Boolean, default=True, nullable=False)

    # UI preference: light | dark
    ui_theme = db.Column(db.String(12), nullable=True, default='light')

    def get_id(self):
        # Новый формат: числовой id.
        # load_user() в app.py по-прежнему поддерживает legacy сессии op_* / user_*.
        return str(self.id)

    def is_admin(self):
        return (self.role or '').lower() == 'admin'

    def is_operator(self):
        r = (self.role or '').lower()
        return r in ('operator', 'admin')

    def is_client(self):
        return (self.role or '').lower() == 'client'


class UserUIState(db.Model):
    """Персистентные UI-настройки/фильтры (в стиле Bitrix) для каждого пользователя.

    Храним JSON, чтобы не плодить столбцы под каждый экран.
    """
    __tablename__ = 'user_ui_state'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    data = db.Column(db.Text, nullable=False, default='{}')
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False, index=True)

    user = db.relationship('User', backref=db.backref('ui_state', uselist=False, lazy=True))

    def get(self, key: str, default=None):
        try:
            obj = json.loads(self.data or '{}')
            return obj.get(key, default)
        except Exception:
            return default

    def set(self, key: str, value):
        try:
            obj = json.loads(self.data or '{}')
        except Exception:
            obj = {}
        obj[key] = value
        self.data = json.dumps(obj, ensure_ascii=False)
