"""Catalog transport response classification."""

import json


class InvalidPayload(ValueError):
    pass


class UpstreamUnavailable(RuntimeError):
    pass


def decode_items(body: str) -> list[dict]:
    """Decode and validate one catalog response body."""
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise InvalidPayload("response body is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise InvalidPayload("response body must be an object")

    items = payload.get("items")
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise InvalidPayload("response items must be a list of objects")

    return [dict(item) for item in items]


def classify_response(status: int, body: str) -> list[dict]:
    """Classify one response for catalog synchronization."""
    raise NotImplementedError("response classification is not implemented")
