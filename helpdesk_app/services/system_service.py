from __future__ import annotations

from flask import jsonify

from helpdesk_app.utils.time import APP_TZ_NAME, local_now


class SystemService:
    @staticmethod
    def system_time_response():
        now = local_now()
        return jsonify({
            'tz': APP_TZ_NAME,
            'iso': now.isoformat(),
            'date': now.strftime('%d.%m.%Y'),
            'time': now.strftime('%H:%M'),
            'display': now.strftime('%d.%m.%Y %H:%M'),
        })
