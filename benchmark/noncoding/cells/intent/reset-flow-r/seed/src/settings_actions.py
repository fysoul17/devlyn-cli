from __future__ import annotations

from typing import Any


DEFAULT_SETTINGS: dict[str, Any] = {"compact": False, "page_size": 25}


def activate_reset(settings: dict[str, Any], confirmed: bool | None = None) -> dict[str, Any]:
    """Handle activation of the Reset settings action."""
    return {"status": "unavailable", "settings": dict(settings)}
