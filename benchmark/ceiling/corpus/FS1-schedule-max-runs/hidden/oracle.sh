#!/usr/bin/env bash
set -euo pipefail

ORACLE_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$ORACLE_DIR/test_max_runs_oracle.py" ./test_max_runs_oracle.py
uv venv --python 3.11 .venv
# uv venvs ship without pip — install via uv against the venv python.
uv pip install -q --python .venv/bin/python pytest

hidden_exit=0
upstream_exit=0
.venv/bin/python -m pytest -q test_max_runs_oracle.py || hidden_exit=$?
if [ -f test_schedule.py ]; then
  .venv/bin/python -m pytest -q test_schedule.py || upstream_exit=$?
else
  echo "missing test_schedule.py" >&2
  upstream_exit=1
fi
[ "$hidden_exit" -eq 0 ] && [ "$upstream_exit" -eq 0 ]
