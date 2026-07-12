from __future__ import annotations

from typing import Any


SECRET_KEYS = {"password", "api_key"}


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[redacted]" if key.casefold() in SECRET_KEYS else sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value
