#!/usr/bin/env bash
set -euo pipefail

: "${FINAL_MESSAGE_PATH:?FINAL_MESSAGE_PATH is required}"
: "${BASELINE_COMMIT_SHA:?BASELINE_COMMIT_SHA is required}"
: "${FIXTURE_HIDDEN_DIR:?FIXTURE_HIDDEN_DIR is required}"

python3 "$FIXTURE_HIDDEN_DIR/behavior-check.py" "$PWD" "$FIXTURE_HIDDEN_DIR/conformance.json"
python3 - "$FINAL_MESSAGE_PATH" <<'PY' | "$FIXTURE_HIDDEN_DIR/validate-message.py"
import json
import sys
from pathlib import Path
print(json.dumps(Path(sys.argv[1]).read_text(encoding="utf-8")))
PY
python3 -m unittest discover -s tests >/dev/null
