from __future__ import annotations

import json
from typing import Any

from .sanitize import sanitize


def format_event(event: dict[str, Any]) -> str:
    return json.dumps(sanitize(event), sort_keys=True)
