from __future__ import annotations

from helpdesk_app.config import Config
from helpdesk_app.utils.files import ensure_upload_dirs
from helpdesk_app.routes import attach_extracted_routes
from helpdesk_app.jinja import register_jinja_helpers
from helpdesk_app.runtime import get_runtime_facade, sync_extensions


def create_app():
    # Временный bridge: runtime пока ещё опирается на legacy-монолит,
    # но create_app уже работает через RuntimeFacade.
    runtime = get_runtime_facade()
    app = runtime.app
    app.config.from_object(Config)
    ensure_upload_dirs(app.config['UPLOAD_FOLDER'])

    sync_extensions()

    # Шаг 2+: часть маршрутов уже обслуживается вынесенными модулями routes/*.
    attach_extracted_routes(app)
    register_jinja_helpers(app)

    return app
