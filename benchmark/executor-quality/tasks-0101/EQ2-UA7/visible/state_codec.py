"""Canonical byte encoding for transfer-ledger state."""

from __future__ import annotations

import json


def _canonical(value: object) -> object:
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    return value


def encode_state(value: dict[str, object]) -> bytes:
    return (json.dumps(_canonical(value), separators=(",", ":")) + "\n").encode()


def decode_state(payload: bytes) -> dict[str, object]:
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("stock ledger root must be an object")
    return value
