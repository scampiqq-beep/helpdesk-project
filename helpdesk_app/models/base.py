from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, UTC

# UTC helper (Python 3.14+: utcnow() deprecated)
def utcnow():
    """Naive UTC datetime for DB fields that historically stored UTC without tzinfo."""
    return datetime.now(UTC).replace(tzinfo=None)

db = SQLAlchemy()

# Связь операторов с несколькими отделами (many-to-many)
user_departments = db.Table(
    'user_departments',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('department_id', db.Integer, db.ForeignKey('departments.id'), primary_key=True),
)

# Теги для заявок (many-to-many)
ticket_tags = db.Table(
    'ticket_tags',
    db.Column('ticket_id', db.Integer, db.ForeignKey('support_tickets.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
)

# Дополнительные отделы для заявки (multi-delegate):
# Позволяет ТП делегировать заявку сразу в несколько отделов, сохраняя один "основной" department_id.
ticket_shared_departments = db.Table(
    'ticket_shared_departments',
    db.Column('ticket_id', db.Integer, db.ForeignKey('support_tickets.id', ondelete='CASCADE'), primary_key=True),
    db.Column('department_id', db.Integer, db.ForeignKey('departments.id', ondelete='CASCADE'), primary_key=True),
)

__all__ = ['db', 'utcnow', 'user_departments', 'ticket_tags', 'ticket_shared_departments']
