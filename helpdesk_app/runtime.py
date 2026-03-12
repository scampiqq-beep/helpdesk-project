from __future__ import annotations

from functools import lru_cache
from types import ModuleType
from typing import Any


@lru_cache(maxsize=1)
def get_runtime() -> ModuleType:
    """Единая точка доступа к текущему runtime-контексту проекта."""
    import legacy_monolith
    return legacy_monolith


class RuntimeFacade:
    """Небольшой фасад над legacy runtime.

    Нужен, чтобы точки входа и новые модули зависели не от имени файла
    монолита, а от понятного набора операций: получить app, socketio,
    запустить scheduler и прочитать runtime timezone.
    """

    def __init__(self, module: ModuleType):
        self._module = module

    @property
    def module(self) -> ModuleType:
        return self._module

    @property
    def app(self):
        return self._module.app

    @property
    def socketio(self):
        return getattr(self._module, 'socketio', None)

    @property
    def login_manager(self):
        return getattr(self._module, 'login_manager', None)

    @property
    def mail(self):
        return getattr(self._module, 'mail', None)

    @property
    def migrate(self):
        return getattr(self._module, 'migrate', None)

    def start_scheduler(self) -> None:
        starter = getattr(self._module, 'start_scheduler', None)
        if callable(starter):
            starter()

    def get_timezone(self):
        getter = getattr(self._module, 'get_runtime_timezone', None)
        if callable(getter):
            return getter()
        return None

    def __getattr__(self, item: str) -> Any:
        return getattr(self._module, item)


@lru_cache(maxsize=1)
def get_runtime_facade() -> RuntimeFacade:
    return RuntimeFacade(get_runtime())


def sync_extensions() -> None:
    """Синхронизирует helpdesk_app.extensions с текущим runtime."""
    from helpdesk_app import extensions

    runtime = get_runtime_facade()
    extensions.login_manager = runtime.login_manager
    extensions.mail = runtime.mail
    extensions.migrate = runtime.migrate
    extensions.socketio = runtime.socketio


def reset_runtime_cache() -> None:
    get_runtime.cache_clear()
    get_runtime_facade.cache_clear()
