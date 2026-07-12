#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


if len(sys.argv) != 3:
    raise SystemExit("usage: behavior-check.py WORKSPACE CONFORMANCE_JSON")
workspace = Path(sys.argv[1]).resolve()
conformance = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
reference = next((channel for channel in conformance["channels"] if channel.get("id") == "reference-behavior"), None)
if reference is None or not isinstance(reference.get("values"), list) or not reference["values"]:
    raise SystemExit("conformance reference-behavior.values[0] is required")
transition = reference["values"][0]
if not isinstance(transition, str) or transition.count("->") != 1:
    raise SystemExit("conformance reference-behavior.values[0] must be a pending->confirmed transition")
pending_status, confirmed_status = transition.split("->")
if not pending_status or not confirmed_status:
    raise SystemExit("conformance transition statuses must be non-empty")
module_path = workspace / "src/settings_actions.py"
spec = importlib.util.spec_from_file_location("candidate_settings_actions", module_path)
if spec is None or spec.loader is None:
    raise SystemExit("cannot load src/settings_actions.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

current = {"compact": True, "page_size": 100}
pending = module.activate_reset(current)
if pending != {"status": pending_status, "settings": current}:
    raise SystemExit("activation does not preserve settings and request confirmation")
cancelled = module.activate_reset(current, False)
if cancelled != {"status": "cancelled", "settings": current}:
    raise SystemExit("cancel does not preserve settings")
confirmed = module.activate_reset(current, True)
expected = {"status": confirmed_status, "settings": {"compact": False, "page_size": 25}}
if confirmed != expected:
    raise SystemExit("confirmation does not apply defaults")
if current != {"compact": True, "page_size": 100}:
    raise SystemExit("handler mutated caller settings")
