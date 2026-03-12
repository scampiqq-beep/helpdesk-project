"""Новая точка входа проекта.

Архитектура нормализована через create_app(), при этом legacy-монолит
пока ещё используется как runtime-движок. Запуск по-прежнему совместим:

    python app.py
"""

from helpdesk_app import create_app
from helpdesk_app.models.base import db
from helpdesk_app.models.users import User
from helpdesk_app.runtime import get_runtime_facade, sync_extensions

app = create_app()


def main() -> None:
    runtime = get_runtime_facade()
    sync_extensions()

    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            db.session.commit()
        runtime.start_scheduler()

    socketio = runtime.socketio
    if socketio is not None:
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    else:
        app.run(host='0.0.0.0', port=5000, threaded=True, debug=True)


if __name__ == '__main__':
    main()
