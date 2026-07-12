#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
source = json.loads((ROOT / "config/commands.json").read_text(encoding="utf-8"))
rendered = {"commands": source["commands"], "generated_by": "tools/render_catalog.py"}
(ROOT / "generated/commands.json").write_text(
    json.dumps(rendered, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
