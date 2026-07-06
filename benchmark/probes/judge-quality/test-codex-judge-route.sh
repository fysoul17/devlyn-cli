#!/usr/bin/env bash
# Regression test for the injectable codex judge route.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNNER="$SCRIPT_DIR/run_judge_quality.py"
TMP_DIR="$(mktemp -d /tmp/codex-judge-route-test.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT
FAKEBIN="$TMP_DIR/fakebin"
mkdir -p "$FAKEBIN"
cat > "$FAKEBIN/codex" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "--version" ]; then
  echo "codex-cli fake"
  exit 0
fi
if [ "${1:-}" != "exec" ]; then
  echo "unexpected fake codex args: $*" >&2
  exit 2
fi
state="${FAKE_CODEX_STATE:?}"
count=0
[ ! -f "$state" ] || count="$(cat "$state")"
count=$((count + 1))
printf '%s\n' "$count" > "$state"
if [ "$count" -eq 1 ]; then
  echo "not json on first attempt"
else
  echo '{"findings":[]}'
fi
EOF
chmod +x "$FAKEBIN/codex"

env CODEX_MODEL=gpt-fake FAKE_CODEX_STATE="$TMP_DIR/calls" \
  python3 "$RUNNER" \
    --reps 1 \
    --judges codex \
    --run-id codex-route-test \
    --results-dir "$TMP_DIR/results" \
    --codex-command "$FAKEBIN/codex" \
  > "$TMP_DIR/stdout.log" 2> "$TMP_DIR/stderr.log"

python3 - "$TMP_DIR/results" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
identity = json.loads((root / "codex" / "identity.json").read_text())
if identity != {
    "cli_version": "codex-cli fake",
    "model_id_or_alias": "gpt-fake",
    "recorded_at_run_id": "codex-route-test",
}:
    raise SystemExit(identity)
summary = json.loads((root / "summary.json").read_text())
records = summary.get("codex")
if not isinstance(records, list) or len(records) != 12:
    raise SystemExit("expected 12 codex records")
first = records[0]
if len(first.get("attempts", [])) != 2:
    raise SystemExit("parse retry was not recorded")
if first.get("parsed") != {"findings": []}:
    raise SystemExit(first.get("parsed"))
stdout_files = sorted((root / "codex").glob("*attempt*.stdout.txt"))
stderr_files = sorted((root / "codex").glob("*attempt*.stderr.txt"))
if not stdout_files or not stderr_files:
    raise SystemExit("codex stdout/stderr artifacts missing")
PY

echo "PASS test-codex-judge-route"
