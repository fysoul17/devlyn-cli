#!/usr/bin/env bash
set -euo pipefail

python3 - "$FIXTURE_HIDDEN_DIR/conformance.json" <<'PY'
import json
import sys
from pathlib import Path

from src.format_event import format_event
from src.sanitize import sanitize

declaration = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
values = {channel["id"]: channel["values"] for channel in declaration["channels"]}
secret_keys = values["secret-key"]
preserved_keys = values["preserved-keys"]
secret_values = values["secret-values"]
preserved_values = values["preserved-values"]
replacement = values["replacement"][0]

payload = {
    secret_keys[0]: secret_values[0],
    "nested": [{secret_keys[1]: secret_values[1], preserved_keys[0]: preserved_values[0]}],
    preserved_keys[1]: preserved_values[1],
    "password": secret_values[0],
}
expected = {
    secret_keys[0]: replacement,
    "nested": [{secret_keys[1]: replacement, preserved_keys[0]: preserved_values[0]}],
    preserved_keys[1]: preserved_values[1],
    "password": replacement,
}
assert sanitize(payload) == expected
assert json.loads(format_event(payload)) == expected

adapter = Path("src/format_event.py").read_text(encoding="utf-8")
assert "access_token" not in adapter.casefold()
PY

python3 - <<'PY'
import sys
import unittest

suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
if suite.countTestCases() == 0:
    print("oracle error: unittest discovery ran zero tests", file=sys.stderr)
    raise SystemExit(1)
result = unittest.TextTestRunner(verbosity=0).run(suite)
raise SystemExit(not result.wasSuccessful())
PY
