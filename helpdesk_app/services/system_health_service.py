from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import current_app

from helpdesk_app.services.config_validation_service import ConfigValidationService


class SystemHealthService:
    @staticmethod
    def get_health_payload():
        app = current_app
        config_check = ConfigValidationService.validate(app)

        db_status = 'ok'
        db_error = None
        try:
            from helpdesk_app.runtime import get_runtime
            legacy.db.session.execute(legacy.db.text('SELECT 1'))
        except Exception as exc:  # pragma: no cover - safety fallback
            db_status = 'error'
            db_error = str(exc)

        upload_folder = app.config.get('UPLOAD_FOLDER')
        upload_exists = bool(upload_folder and os.path.isdir(upload_folder))

        tz_name = app.config.get('APP_TIMEZONE', 'UTC')
        try:
            local_now = datetime.now(ZoneInfo(tz_name)).isoformat()
        except Exception:
            local_now = None

        overall_ok = config_check['ok'] and db_status == 'ok' and upload_exists

        return {
            'ok': overall_ok,
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'timezone': tz_name,
            'local_time': local_now,
            'database': {
                'status': db_status,
                'error': db_error,
            },
            'uploads': {
                'path': upload_folder,
                'exists': upload_exists,
            },
            'config': config_check,
        }
