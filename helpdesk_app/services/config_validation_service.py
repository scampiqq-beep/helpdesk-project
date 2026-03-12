from __future__ import annotations

import os
from typing import Dict, List


class ConfigValidationService:
    @staticmethod
    def validate(app) -> Dict[str, object]:
        warnings: List[str] = []
        errors: List[str] = []

        secret_key = app.config.get('SECRET_KEY')
        if not secret_key:
            errors.append('SECRET_KEY не задан')

        upload_folder = app.config.get('UPLOAD_FOLDER')
        if not upload_folder:
            errors.append('UPLOAD_FOLDER не задан')
        elif not os.path.isdir(upload_folder):
            warnings.append(f'Каталог загрузок отсутствует: {upload_folder}')

        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        if not db_uri:
            errors.append('SQLALCHEMY_DATABASE_URI не задан')

        timezone_name = app.config.get('APP_TIMEZONE') or app.config.get('TIMEZONE')
        if not timezone_name:
            warnings.append('Часовой пояс приложения не задан явно')

        mail_server = app.config.get('MAIL_SERVER')
        if not mail_server:
            warnings.append('MAIL_SERVER не настроен')

        return {
            'ok': not errors,
            'errors': errors,
            'warnings': warnings,
        }
