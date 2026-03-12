"""Compatibility shim for legacy imports.

Model definitions were split into thematic modules on step 22.
This file re-exports them to preserve imports like
`from helpdesk_app.models.core import SupportTicket`.
"""

from .base import *  # noqa: F401,F403
from .reference import *  # noqa: F401,F403
from .settings import *  # noqa: F401,F403
from .users import *  # noqa: F401,F403
from .knowledge import *  # noqa: F401,F403
from .tickets import *  # noqa: F401,F403
from .notifications import *  # noqa: F401,F403

__all__ = [name for name in globals().keys() if not name.startswith('_')]
