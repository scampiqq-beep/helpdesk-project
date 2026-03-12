# forms.py
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired
from flask_wtf.file import FileField, FileAllowed, MultipleFileField

class MessageForm(FlaskForm):
    message = TextAreaField('Сообщение', validators=[DataRequired()])
    files = MultipleFileField('Прикрепить файлы', validators=[
        FileAllowed(['pdf', 'png', 'jpg', 'jpeg', 'txt', 'doc', 'docx', 'xlsx', 'zip'], 'Недопустимый формат')
    ])
    submit = SubmitField('Отправить')