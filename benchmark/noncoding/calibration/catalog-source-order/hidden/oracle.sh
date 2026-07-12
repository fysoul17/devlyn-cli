#!/usr/bin/env bash
set -euo pipefail

python3 - "$FIXTURE_HIDDEN_DIR/conformance.json" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

declaration = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
values = {channel["id"]: channel["values"] for channel in declaration["channels"]}
source_path = Path("config/commands.json")
generated_path = Path("generated/commands.json")
source = json.loads(source_path.read_text(encoding="utf-8"))
generated_before = generated_path.read_bytes()

sync = source["commands"]["sync"]
assert sync["retry_limit"] == values["retry-limit"][0]
assert type(sync["retry_limit"]) is int
assert sync["formats"] == values["sync-formats"][0].split(",")
assert source["commands"]["export"] == {
    "formats": ["json", "csv"],
    "timeout_seconds": 60,
}

subprocess.run([sys.executable, "tools/render_catalog.py"], check=True)
assert generated_path.read_bytes() == generated_before
generated = json.loads(generated_before)
assert generated["commands"] == source["commands"]
PY

python3 -m unittest discover -s tests -q
