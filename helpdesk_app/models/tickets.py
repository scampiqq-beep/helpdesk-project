import json
from datetime import timedelta

from .base import db, utcnow, ticket_shared_departments, ticket_tags

class TicketAttachment(db.Model):
    __tablename__ = 'ticket_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('ticket_messages.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    size = db.Column(db.Integer)
    url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=utcnow)
    
    # Используем другое имя для обратной ссылки
    message_rel = db.relationship('TicketMessage', backref=db.backref('file_attachments', lazy=True))


class TicketMessage(db.Model):
    __tablename__ = 'ticket_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    message = db.Column(db.Text)
    is_operator = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    is_pinned = db.Column(db.Boolean, default=False)
    attachments = db.Column(db.Text)
    is_pinned_as_result = db.Column(db.Boolean, default=False, nullable=False)
    edited_at = db.Column(db.DateTime, nullable=True)
    edited_by_id = db.Column(db.Integer, nullable=True)
    
    # Связи - ЯВНО указываем foreign_keys
    ticket_rel = db.relationship('SupportTicket', backref=db.backref('messages', lazy=True), foreign_keys=[ticket_id])
    
    @property
    def attachments_list(self):
        """Геттер для получения вложений как списка"""
        # Сначала пробуем получить из связанной таблицы
        if hasattr(self, 'file_attachments') and self.file_attachments:
            attachments = []
            for att in self.file_attachments:
                attachments.append({
                    'id': att.id,
                    'filename': att.filename,
                    'original_name': att.original_name,
                    'size': att.size,
                    'url': att.url or f"/uploads/attachments/{att.filename}",
                    'created_at': att.created_at.isoformat() if att.created_at else None
                })
            return attachments
        
        # Если нет в связанной таблице, пробуем парсить старое поле
        if self.attachments:
            try:
                import json
                data = json.loads(self.attachments)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return [data]
            except:
                pass
        
        return []


class Ticket(db.Model):
    __tablename__ = 'tickets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=True)
    helpful = db.Column(db.Boolean, nullable=True)
    
    # Добавьте эти поля для закрепленного результата
    pinned_result_id = db.Column(db.Integer, db.ForeignKey('ticket_messages.id'), nullable=True)
    
    user_rel = db.relationship('User', backref='tickets')
    # Добавьте relationship для закрепленного сообщения
    pinned_result = db.relationship('TicketMessage', foreign_keys=[pinned_result_id])


class CommentLike(db.Model):
    __tablename__ = 'comment_likes'
    
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('ticket_messages.id'), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    
    __table_args__ = (db.UniqueConstraint('comment_id', 'user_id', name='unique_comment_like'),)
    
    comment_rel = db.relationship('TicketMessage', backref=db.backref('likes_relation', lazy=True))


class TicketHistory(db.Model):
    __tablename__ = 'ticket_history'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=utcnow, nullable=False)
    field = db.Column(db.String(100), nullable=False)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    note = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<TicketHistory {self.ticket_id} [{self.field}] {self.old_value} → {self.new_value}>"


class SupportTicket(db.Model):
    __tablename__ = 'support_tickets'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    response = db.Column(db.Text, nullable=True)
    is_resolved = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Новая")
    # Legacy: исторически tickets ссылались на end_users.id
    user_id = db.Column(db.Integer, nullable=True)  # legacy (до миграции end_users)
    # Новая модель: единая таблица users (роль=client)
    client_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    bitrix_task_id = db.Column(db.String(50), nullable=True)
    bitrix_task_url = db.Column(db.String(300), nullable=True)
    sla_deadline = db.Column(db.DateTime, nullable=True)
    files = db.Column(db.Text, nullable=True)
    internal_comment = db.Column(db.Text, nullable=True)
    locked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    locked_at = db.Column(db.DateTime, nullable=True)
    organization = db.Column(db.String(255), nullable=True)
    inn = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    rating = db.Column(db.Integer, nullable=True)
    helpful = db.Column(db.Boolean, nullable=True)
    helpful_at = db.Column(db.DateTime, nullable=True)
    
    # Department relationship
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    department_rel = db.relationship('Department', backref='tickets', foreign_keys=[department_id])

    # Multi-delegate: дополнительные отделы (помимо основного department_id)
    shared_departments_rel = db.relationship(
        'Department',
        secondary=ticket_shared_departments,
        backref=db.backref('shared_tickets', lazy='select'),
        lazy='select'
    )
    
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    closed_at = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.String(20), default='medium')
    # Тип заявки (устаревшее поле, оставлено для совместимости): issue / task
    ticket_type = db.Column(db.String(20), nullable=False, default='issue')

    # Категория заявки (справочник)
    category_id = db.Column(db.Integer, db.ForeignKey('ticket_categories.id'), nullable=True)
    category_rel = db.relationship('TicketCategory', foreign_keys=[category_id])
    # Теги заявки
    tags_rel = db.relationship('Tag', secondary=ticket_tags, backref=db.backref('tickets', lazy='select'))
    # Дублирующиеся relationships на одно и то же поле locked_by были в исходном проекте.
    # Оставляем оба имени для обратной совместимости, но явно указываем overlaps,
    # чтобы SQLAlchemy не предупреждал о конфликте маппинга.
    locked_by_user = db.relationship('User', foreign_keys=[locked_by], overlaps="locked_by_rel")
    created_by_operator_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    # Добавьте поле для закрепленного результата
    pinned_result_id = db.Column(db.Integer, db.ForeignKey('ticket_messages.id'), nullable=True)
    
    # Связи с ЯВНЫМ указанием foreign_keys
    # Новое отношение к User (client)
    client_rel = db.relationship('User', foreign_keys=[client_id])
    assigned_to_rel = db.relationship('User', foreign_keys=[assigned_to_id])
    locked_by_rel = db.relationship('User', foreign_keys=[locked_by], overlaps="locked_by_user")
    history_rel = db.relationship('TicketHistory', backref='ticket', lazy='select', cascade="all, delete-orphan", foreign_keys=[TicketHistory.ticket_id])
    created_by_operator = db.relationship('User', foreign_keys=[created_by_operator_id], backref='created_tickets')
    
    # Relationship для закрепленного сообщения
    pinned_result = db.relationship('TicketMessage', foreign_keys=[pinned_result_id])
    
    # НОВЫЕ ПОЛЯ для системы завершения
    marked_as_completed_at = db.Column(db.DateTime, nullable=True)  # когда оператор отметил как завершено
    auto_closed_at = db.Column(db.DateTime, nullable=True)  # когда автоматически закрылось после 24ч
    waiting_for_client_feedback = db.Column(db.Boolean, default=False)  # ожидает обратной связи от клиента
    close_reason = db.Column(db.String(32), nullable=True)  # причина быстрого закрытия: spam/mistake
    is_spam = db.Column(db.Boolean, default=False, nullable=False)  # пометка СПАМ (скрывается в списке по умолчанию)



    # Удаляем department, так как уже есть department_rel
    # department = db.relationship('Department', backref='tickets')  # УДАЛИТЬ ЭТУ СТРОКУ

    @property
    def is_overdue(self):
        """Проверяет, просрочена ли задача"""
        if not self.sla_deadline:
            return False
        return utcnow() > self.sla_deadline
    
    def calculate_sla_deadline(self, attention_hours=1, default_hours=48):
        """Рассчитывает срок SLA"""
        if self.department_rel and hasattr(self.department_rel, 'name'):
            if self.department_rel.name == "ВНИМАНИЕ! Требуется обработка":
                self.sla_deadline = self.created_at + timedelta(hours=attention_hours)
            else:
                self.sla_deadline = self.created_at + timedelta(hours=default_hours)
        else:
            self.sla_deadline = self.created_at + timedelta(hours=default_hours)
        
        return self.sla_deadline

    def is_locked(self, current_admin_id=None, timeout_minutes=5):
        """Проверяет, заблокирована ли заявка"""
        if not self.locked_by or not self.locked_at:
            return False
        if current_admin_id and self.locked_by == current_admin_id:
            return False
        now = utcnow()
        return (now - self.locked_at).total_seconds() < timeout_minutes * 60

    @property
    def department(self):
        """Совместимость со старым кодом"""
        return self.department_rel


class TicketPresence(db.Model):
    __tablename__ = 'ticket_presence'

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id'), nullable=False, index=True)
    user_key = db.Column(db.String(64), nullable=False)  # 'op_12' / 'client_5'
    display_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'client' / 'operator' / 'admin'
    is_typing = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    ticket = db.relationship('SupportTicket', backref=db.backref('presence_entries', lazy='dynamic', cascade='all,delete-orphan'))

    __table_args__ = (
        db.UniqueConstraint('ticket_id', 'user_key', name='uq_ticket_presence_ticket_user'),
        {'extend_existing': True}
    )


class TicketOperatorChatMessage(db.Model):
    __tablename__ = 'ticket_operator_chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    ticket = db.relationship('SupportTicket', backref=db.backref('operator_chat_messages', lazy='dynamic', cascade='all,delete-orphan'))
    user = db.relationship('User')


class TicketOperatorChatRead(db.Model):
    """Позиция прочитанности операторского чата по тикету для пользователя."""
    __tablename__ = 'ticket_operator_chat_reads'

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    last_read_message_id = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False, index=True)

    __table_args__ = (
        db.UniqueConstraint('ticket_id', 'user_id', name='uq_opchat_read_ticket_user'),
    )
