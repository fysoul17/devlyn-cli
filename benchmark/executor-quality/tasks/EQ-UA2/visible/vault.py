"""Data helpers for a release artifact catalog."""

from __future__ import annotations

import json
from pathlib import Path


def load_mapping(path: str) -> dict[str, object]:
    """Load one JSON object from ``path``."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def list_artifacts(catalog: dict[str, object]) -> list[str]:
    """Return stable artifact keys."""
    return sorted(catalog)


def has_scope(grants: dict[str, object], token: str, scope: str) -> bool:
    """Return whether ``token`` carries ``scope``."""
    scopes = grants.get(token)
    return isinstance(scopes, list) and scope in scopes


def lookup_artifact(catalog: dict[str, object], key: str) -> object | None:
    """Return an artifact entry when present."""
    return catalog.get(key)
