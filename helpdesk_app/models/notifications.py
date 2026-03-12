from .base import db, utcnow

class NotificationGlobalSettings(db.Model):
    __tablename__ = 'notification_global_settings'
    id = db.Column(db.Integer, primary_key=True)
    # Глобальные переключатели
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    enabled_for_operators = db.Column(db.Boolean, default=True, nullable=False)
    enabled_for_clients = db.Column(db.Boolean, default=True, nullable=False)

    # Какие события включены (для in-app)
    event_assigned = db.Column(db.Boolean, default=True, nullable=False)
    event_customer_reply = db.Column(db.Boolean, default=True, nullable=False)
    event_operator_reply = db.Column(db.Boolean, default=True, nullable=False)
    event_status = db.Column(db.Boolean, default=True, nullable=False)
    event_priority = db.Column(db.Boolean, default=True, nullable=False)
    event_opchat = db.Column(db.Boolean, default=True, nullable=False)
    event_new_ticket = db.Column(db.Boolean, default=True, nullable=False)
    event_important = db.Column(db.Boolean, default=True, nullable=False)
    event_sla = db.Column(db.Boolean, default=True, nullable=False)

    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    @staticmethod
    def get_or_create():
        s = NotificationGlobalSettings.query.get(1)
        if not s:
            s = NotificationGlobalSettings(id=1)
            db.session.add(s)
            db.session.commit()
        return s


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)

    recipient_type = db.Column(db.String(20), nullable=False)  # 'user' / 'end_user'
    recipient_id = db.Column(db.Integer, nullable=False, index=True)

    event_type = db.Column(db.String(50), nullable=False)  # assigned / customer_reply / status / ...
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(400), nullable=True)

    # Если уведомление относится к заявке — храним ticket_id явно (быстрее и надёжнее, чем regex по url)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id'), nullable=True, index=True)

    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    dedupe_key = db.Column(db.String(120), nullable=True, index=True)

    def __repr__(self):
        return f"<Notification {self.id} {self.recipient_type}:{self.recipient_id} {self.event_type}>"
