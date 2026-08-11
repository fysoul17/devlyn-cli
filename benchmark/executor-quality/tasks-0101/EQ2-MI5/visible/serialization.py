"""Canonical byte encoding for the return store."""

from __future__ import annotations

import json


def encode_store(value: dict[str, object]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def decode_store(payload: bytes) -> dict[str, object]:
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("order store root must be an object")
    return value
