from .base import db, user_departments

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False, index=True)
    color = db.Column(db.String(20), nullable=True)  # опционально: bootstrap color / hex
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<Tag {self.name}>"


class TicketStatus(db.Model):
    __tablename__ = 'ticket_statuses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<TicketStatus {self.name}>"


class TicketCloseReason(db.Model):
    """Справочник причин закрытия (подстатусов для состояния 'Завершена').

    Вариант A: основные состояния фиксированы (Новая/В работе/Ожидание/Завершена),
    а детализация закрытия живёт здесь.
    """
    __tablename__ = 'ticket_close_reasons'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)  # spam/duplicate/wrong/withdrawn
    name = db.Column(db.String(80), nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    require_comment = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<TicketCloseReason {self.code}:{self.name}>"


class TicketPriority(db.Model):
    __tablename__ = 'ticket_priorities'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)   # low/medium/high/urgent
    name = db.Column(db.String(60), unique=True, nullable=False)   # Низкий/Средний/...
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<TicketPriority {self.code}:{self.name}>"


class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    # Основной отдел (совместимость со старым кодом)
    users = db.relationship('User', back_populates='department')
    # Операторы, у которых этот отдел включён в список доступных
    operators = db.relationship('User', secondary=user_departments, back_populates='departments')
    
    def to_dict(self):
        return {"id": self.id, "name": self.name}


class TicketCategory(db.Model):
    __tablename__ = 'ticket_categories'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)  # issue / task / ...
    name = db.Column(db.String(100), unique=True, nullable=False)  # "Обращение", "Задача"
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<TicketCategory {self.code}:{self.name}>"


class ResponseTemplate(db.Model):
    __tablename__ = 'response_templates'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text, nullable=False)
    files = db.Column(db.Text, nullable=True)
    department = db.Column(db.String(50), nullable=True)


# =========================
# Knowledge Base (Категории -> Статьи)
# =========================


class FAQ(db.Model):
    __tablename__ = 'faq'
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default="Общее")
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)


class TicketTemplate(db.Model):
    __tablename__ = 'ticket_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    department = db.Column(db.String(50), nullable=False)
