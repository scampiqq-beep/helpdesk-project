"""Compatibility shim for code that still imports legacy_app.

Step 18 moves the heavy monolith implementation to ``legacy_monolith.py`` so the
historical import path stays lightweight and explicit. This file intentionally
contains no business logic of its own.
"""
from __future__ import annotations

import legacy_monolith as _legacy_monolith

# Re-export the prebuilt Flask app for compatibility.
app = _legacy_monolith.app


def __getattr__(name: str):
    return getattr(_legacy_monolith, name)


def __dir__():
    return sorted(set(globals()) | set(dir(_legacy_monolith)))
