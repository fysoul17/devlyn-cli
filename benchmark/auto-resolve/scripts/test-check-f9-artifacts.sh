#!/usr/bin/env bash
# Regression tests for check-f9-artifacts.py.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CHECK="$SCRIPT_DIR/check-f9-artifacts.py"
TMP_DIR="$(mktemp -d /tmp/check-f9-artifacts-test.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

write_result() {
  local arm="$1"
  local result_dir="$TMP_DIR/results/run/F9-e2e-ideate-to-resolve/$arm"
  local work_dir="$TMP_DIR/work/$arm"
  mkdir -p "$result_dir" "$work_dir/docs/specs/F9-e2e-ideate-to-resolve" "$work_dir/.devlyn"
  cat > "$result_dir/timing.json" <<EOF
{"work_dir": "$work_dir"}
EOF
  cat > "$work_dir/docs/specs/F9-e2e-ideate-to-resolve/spec.md" <<'EOF'
# F9
EOF
  cat > "$work_dir/docs/specs/F9-e2e-ideate-to-resolve/spec.expected.json" <<'EOF'
{"verification_commands": []}
EOF
  cat > "$work_dir/.devlyn/pipeline.state.json" <<'EOF'
{
  "mode": "spec",
  "source": {
    "type": "spec",
    "spec_path": "docs/specs/F9-e2e-ideate-to-resolve/spec.md"
  }
}
EOF
  cat > "$result_dir/transcript.txt" <<'EOF'
spec ready - /devlyn:resolve --spec docs/specs/F9-e2e-ideate-to-resolve/spec.md
EOF
  printf '%s\n' "$result_dir"
}

risk_result="$(write_result l2_risk_probes)"
python3 "$CHECK" --result-dir "$risk_result"
grep -Fq '"arm": "l2_risk_probes"' "$risk_result/check-f9-artifacts.json"
grep -Fq '"pass": true' "$risk_result/check-f9-artifacts.json"

malformed_timing_result="$(write_result solo_claude)"
printf '["not", "a", "dict"]\n' > "$malformed_timing_result/timing.json"
if python3 "$CHECK" --result-dir "$malformed_timing_result"; then
  echo "expected malformed timing.json to fail" >&2
  exit 1
fi
grep -Fq '"name": "work-dir-resolvable"' "$malformed_timing_result/check-f9-artifacts.json"
grep -Fq '"pass": false' "$malformed_timing_result/check-f9-artifacts.json"

malformed_state_result="$(write_result l2_gated)"
work_dir="$(python3 - "$malformed_state_result/timing.json" <<'PY'
import json
import sys
print(json.load(open(sys.argv[1], encoding="utf8"))["work_dir"])
PY
)"
printf '["not", "a", "dict"]\n' > "$work_dir/.devlyn/pipeline.state.json"
if python3 "$CHECK" --result-dir "$malformed_state_result"; then
  echo "expected malformed pipeline.state.json to fail" >&2
  exit 1
fi
grep -Fq '"name": "pipeline.state.json-parses"' "$malformed_state_result/check-f9-artifacts.json"
grep -Fq '"reason": "expected JSON object"' "$malformed_state_result/check-f9-artifacts.json"

nan_state_result="$(write_result l2_forced)"
nan_work_dir="$(python3 - "$nan_state_result/timing.json" <<'PY'
import json
import sys
print(json.load(open(sys.argv[1], encoding="utf8"))["work_dir"])
PY
)"
cat > "$nan_work_dir/.devlyn/pipeline.state.json" <<'EOF'
{"mode": NaN, "source": {"type": "spec", "spec_path": "docs/specs/F9-e2e-ideate-to-resolve/spec.md"}}
EOF
if python3 "$CHECK" --result-dir "$nan_state_result"; then
  echo "expected NaN pipeline.state.json to fail" >&2
  exit 1
fi
grep -Fq '"name": "pipeline.state.json-parses"' "$nan_state_result/check-f9-artifacts.json"
grep -Fq 'invalid JSON numeric constant: NaN' "$nan_state_result/check-f9-artifacts.json"

bare_result="$TMP_DIR/results/run/F9-e2e-ideate-to-resolve/bare"
mkdir -p "$bare_result"
python3 "$CHECK" --result-dir "$bare_result"
grep -Fq '"exempt": true' "$bare_result/check-f9-artifacts.json"

echo "PASS test-check-f9-artifacts"
