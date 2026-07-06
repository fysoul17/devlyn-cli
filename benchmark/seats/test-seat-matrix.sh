#!/usr/bin/env bash
# Regression tests for seat-matrix.py.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MATRIX="$SCRIPT_DIR/seat-matrix.py"
TMP_DIR="$(mktemp -d /tmp/seat-matrix-test.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT
ROOT="$TMP_DIR/root"
mkdir -p "$ROOT/benchmark/probes/results" \
  "$ROOT/benchmark/probes/judge-quality/cases" \
  "$ROOT/benchmark/probes/judge-quality/results/sonnet" \
  "$ROOT/benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/F1/codex" \
  "$ROOT/benchmark/auto-resolve/results/stub-frozen-verify/solo"

cat > "$ROOT/benchmark/probes/results/iter0058-base-matrix.json" <<'JSON'
{
  "matrix": {
    "sonnet": {
      "DB-silent-catch-root-cause": {
        "reps": 4,
        "violations": 1,
        "violation_reps": [2],
        "flip_band": 1
      }
    }
  },
  "models": ["sonnet"],
  "probes": ["DB-silent-catch-root-cause"],
  "run_prefix": "synthetic",
  "totals": {"sonnet": {"violations": 1, "reps": 4}}
}
JSON

mkdir -p "$ROOT/benchmark/probes/results/synthetic/compliance/codex-small"
cat > "$ROOT/benchmark/probes/results/synthetic/compliance/codex-small/compliance-check.json" <<'JSON'
{
  "cli": "codex",
  "assertions": {"state_found": {"pass": true}},
  "overall": "PASS",
  "failed_assertions": []
}
JSON

cat > "$ROOT/benchmark/probes/judge-quality/cases/WD1.json" <<'JSON'
{
  "id": "WD1",
  "task": "Fix root cause.",
  "authorized_files": ["src/a.js"],
  "diff": "diff --git a/src/a.js b/src/a.js",
  "ground_truth": {"type": "defect", "class": "no_workaround", "file": "src/a.js"}
}
JSON
cat > "$ROOT/benchmark/probes/judge-quality/cases/WD1-CLEAN.json" <<'JSON'
{
  "id": "WD1-CLEAN",
  "task": "Fix root cause.",
  "authorized_files": ["src/a.js"],
  "diff": "diff --git a/src/a.js b/src/a.js",
  "ground_truth": {"type": "clean"}
}
JSON
cat > "$ROOT/benchmark/probes/judge-quality/results/sonnet/WD1-rep1.json" <<'JSON'
{"case": "WD1", "rep": 1, "error": null, "parsed": {"findings": []}, "hit": true, "false_positive": null}
JSON
cat > "$ROOT/benchmark/probes/judge-quality/results/sonnet/WD1-CLEAN-rep1.json" <<'JSON'
{"case": "WD1-CLEAN", "rep": 1, "error": null, "parsed": {"findings": []}, "hit": null, "false_positive": false}
JSON

cat > "$ROOT/benchmark/auto-resolve/results/swebench-lite-proof-gate-n11.json" <<'JSON'
{
  "engine_alias": "codex",
  "model_version": "codex-cli fake/gpt-fake",
  "rows": [
    {"pair_verdict_lift": false, "pair_internal_verdict_lift": true}
  ]
}
JSON
cat > "$ROOT/benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.json" <<'JSON'
{
  "engine_alias": "codex",
  "model_version": "codex-cli fake/gpt-fake",
  "fixtures_total": 1,
  "fixtures_passed": 1,
  "rows": [{"fixture": "F1", "status": "PASS"}]
}
JSON
cat > "$ROOT/benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/F1/judge.json" <<'JSON'
{
  "scores_by_arm": {"codex": 88},
  "_judge_cli": "codex-cli fake",
  "_judge_model": "gpt-fake"
}
JSON
cat > "$ROOT/benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/F1/codex/result.json" <<'JSON'
{"verify_score": 0.9}
JSON
: > "$ROOT/benchmark/auto-resolve/results/stub-frozen-verify/solo/setup.log"

OUT1="$TMP_DIR/out-current"
python3 "$MATRIX" \
  --repo-root "$ROOT" \
  --out-dir "$OUT1" \
  --date 2026-07-07 \
  --engine-versions '{"codex":"codex-cli fake/gpt-fake","sonnet":"claude fake/sonnet"}' \
  > "$TMP_DIR/current.stdout"

python3 - "$OUT1/seat-matrix-2026-07-07.json" "$OUT1/seat-matrix-2026-07-07.md" <<'PY'
import json
import pathlib
import sys

data = json.loads(pathlib.Path(sys.argv[1]).read_text())
md = pathlib.Path(sys.argv[2]).read_text()
cells = data["cells"]
seats = {cell["seat"] for cell in cells}
required = {
    "orchestrator",
    "drift_resistance",
    "verify_primary_judge",
    "verify_pair_judge",
    "implement_executor",
    "plan_ideate_designer",
}
missing = required - seats
if missing:
    raise SystemExit(f"missing seats: {sorted(missing)}")
alias_only = [
    cell for cell in cells
    if cell["seat"] in {"orchestrator", "drift_resistance"} and cell["model_version"]["value"] is None
]
if not alias_only or any(cell["status"] != "stale" for cell in alias_only):
    raise SystemExit("alias-only cells must be stale")
if data["recommendation"]["executor"] != "codex":
    raise SystemExit(data["recommendation"])
if data["recommendation"]["pair_judge_priority"] != ["codex"]:
    raise SystemExit(data["recommendation"])
if not any(cell["seat"] == "implement_executor" and cell["engine_alias"] == "codex" and cell["status"] == "current" for cell in cells):
    raise SystemExit("exact-version implement cell did not become current")
if "stub-frozen-verify" in json.dumps(data):
    raise SystemExit("stub frozen-verify directory was incorrectly treated as evidence")
if "plan_ideate_designer" not in md or "unmeasured" not in md:
    raise SystemExit("unmeasured plan seat not rendered")
PY

OUT2="$TMP_DIR/out-stale"
python3 "$MATRIX" \
  --repo-root "$ROOT" \
  --out-dir "$OUT2" \
  --date 2026-07-08 \
  --engine-versions '{"codex":"different-codex","sonnet":"different-sonnet"}' \
  > "$TMP_DIR/stale.stdout"

python3 - "$OUT2/seat-matrix-2026-07-08.json" <<'PY'
import json
import pathlib
import sys

data = json.loads(pathlib.Path(sys.argv[1]).read_text())
rec = data["recommendation"]
if rec["executor"] != {"recommendation": "recert required", "seat": "implement_executor"}:
    raise SystemExit(rec)
if rec["pair_judge_priority"] != {"recommendation": "recert required", "seat": "verify_pair_judge"}:
    raise SystemExit(rec)
PY

echo "PASS test-seat-matrix"
