"""Validation helpers for publication drafts."""

from __future__ import annotations

import json
import re
from pathlib import Path


class DraftError(ValueError):
    """A draft does not satisfy the public shape."""


def load_json(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_draft(value: object) -> dict[str, str]:
    """Return a validated draft or raise ``DraftError``."""
    if not isinstance(value, dict) or set(value) != {"title", "slug"}:
        raise DraftError("draft must contain title and slug")
    title = value["title"]
    slug = value["slug"]
    if not isinstance(title, str) or not title.strip():
        raise DraftError("title must be non-empty")
    if not isinstance(slug, str) or re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) is None:
        raise DraftError("slug must be URL-safe")
    return {"title": title, "slug": slug}


def slug_is_taken(destinations: dict[str, object], channel: str, slug: str) -> bool:
    slugs = destinations[channel]
    if not isinstance(slugs, list):
        raise ValueError("channel slugs must be an array")
    return slug in slugs
