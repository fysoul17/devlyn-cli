#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


if len(sys.argv) != 3:
    raise SystemExit("usage: behavior-check.py WORKSPACE CONFORMANCE_JSON")
workspace = Path(sys.argv[1]).resolve()
conformance = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
reference = next((channel for channel in conformance["channels"] if channel.get("id") == "reference-behavior"), None)
if reference is None or not isinstance(reference.get("values"), list) or not reference["values"]:
    raise SystemExit("conformance reference-behavior.values[0] is required")
expected_offset_timestamp = reference["values"][0]
if not isinstance(expected_offset_timestamp, str):
    raise SystemExit("conformance reference-behavior.values[0] must be a string")
module_path = workspace / "src/exporter.py"
spec = importlib.util.spec_from_file_location("candidate_exporter", module_path)
if spec is None or spec.loader is None:
    raise SystemExit("cannot load src/exporter.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

source = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=2)))
if module.format_last_seen(source) != expected_offset_timestamp:
    raise SystemExit("last_seen is not normalized to UTC with Z")
if module.format_last_seen(datetime(2025, 1, 2, tzinfo=timezone.utc)) != "2025-01-02T00:00:00Z":
    raise SystemExit("UTC last_seen does not use Z")
try:
    module.format_last_seen(datetime(2025, 1, 2))
except ValueError:
    pass
else:
    raise SystemExit("naive last_seen was accepted")
