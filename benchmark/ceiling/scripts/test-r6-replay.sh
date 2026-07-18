#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 - "$SCRIPT_DIR/r6-replay-cell.py" <<'PY'
import ast
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
print("PASS r6 replay runner syntax")
PY
python3 "$SCRIPT_DIR/r6-replay-cell.py" self-test
