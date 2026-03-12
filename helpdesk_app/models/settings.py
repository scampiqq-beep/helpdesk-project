from .base import db

class Settings(db.Model):
    """Простая таблица настроек key/value (храним идентификаторы отделов, флаги и т.п.)"""
    __tablename__ = 'settings'
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<Settings {self.key}={self.value}>"


class WorkCalendarDay(db.Model):
    __tablename__ = 'work_calendar_days'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False, index=True)
    day_type = db.Column(db.String(20), nullable=False, default='workday')  # workday/weekend/holiday/short_day
    name = db.Column(db.String(120), nullable=True)
    manual_override = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<WorkCalendarDay {self.date} {self.day_type}>"


class BitrixSettings(db.Model):
    __tablename__ = 'bitrix_settings'
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(100), unique=True, nullable=False, index=True)
    responsible_id = db.Column(db.String(50), nullable=False, default='4519')
    accomplices = db.Column(db.Text, nullable=False, default='')
    webhook_url = db.Column(db.String(300)) 

    def get_accomplices_list(self):
        return [x.strip() for x in self.accomplices.split(',') if x.strip()]

    def __repr__(self):
        return f"<BitrixSettings {self.department}: resp={self.responsible_id}, accomp={self.accomplices}>"
