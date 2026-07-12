from __future__ import annotations

import json
from pathlib import Path


CATALOG = Path(__file__).resolve().parents[1] / "generated" / "commands.json"


def command(name: str) -> dict[str, object]:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    return data["commands"][name]
