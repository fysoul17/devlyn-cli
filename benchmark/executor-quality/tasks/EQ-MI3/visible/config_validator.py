"""Validation helpers for route configuration documents."""

from __future__ import annotations

import json
from typing import Any


def validate_config(config: Any) -> dict[str, Any]:
    """Validate one decoded configuration object."""
    if not isinstance(config, dict) or not isinstance(config.get("name"), str):
        return {"ok": False, "error": "invalid_name"}

    routes = config.get("routes")
    if not isinstance(routes, list) or not all(isinstance(route, str) for route in routes):
        return {"ok": False, "error": "invalid_routes"}
    if len(routes) != len(set(routes)):
        return {"ok": False, "error": "duplicate_route"}

    return {"ok": True, "name": config["name"]}


def validate_document(text: str) -> dict[str, Any]:
    """Parse and validate one configuration document."""
    try:
        config = json.loads(text)
    except json.JSONDecodeError:
        return {"ok": False, "error": "invalid_json"}
    return validate_config(config)
