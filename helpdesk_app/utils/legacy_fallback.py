from __future__ import annotations

from helpdesk_app.legacy_adapter import LegacyAdapter


def legacy_fallback(endpoint: str, *args, **kwargs):
    """Единая точка fallback в legacy-монолит."""
    return LegacyAdapter.call(endpoint, *args, **kwargs)
