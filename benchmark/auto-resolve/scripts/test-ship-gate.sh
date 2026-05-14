#!/usr/bin/env bash
# Regression tests for ship-gate.py summary semantics.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BENCH_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GATE="$SCRIPT_DIR/ship-gate.py"
COMPILE="$SCRIPT_DIR/compile-report.py"
TMP_DIR="$(mktemp -d /tmp/ship-gate-test.XXXXXX)"
BASELINE="$BENCH_ROOT/history/baselines/shipped.json"
BASELINE_BACKUP="$TMP_DIR/shipped.backup.json"
BASELINE_EXISTED=0

restore_baseline() {
  rm -rf "$BENCH_ROOT/results/$RUN_PREFIX"*
  if [ "$BASELINE_EXISTED" -eq 1 ]; then
    mkdir -p "$(dirname "$BASELINE")"
    cp "$BASELINE_BACKUP" "$BASELINE"
  else
    rm -f "$BASELINE"
    rmdir "$BENCH_ROOT/history/baselines" "$BENCH_ROOT/history" 2>/dev/null || true
  fi
  rm -rf "$TMP_DIR"
}

RUN_PREFIX="ship-gate-test-$(basename "$TMP_DIR")"
if [ -f "$BASELINE" ]; then
  BASELINE_EXISTED=1
  cp "$BASELINE" "$BASELINE_BACKUP"
fi
trap restore_baseline EXIT

write_summary() {
  local run_id="$1"
  local non_edge_passes="$2"
  local f8_score="${3:-80}"
  local run_dir="$BENCH_ROOT/results/$run_id"
  mkdir -p "$run_dir"
  python3 - "$run_dir/summary.json" "$run_id" "$non_edge_passes" "$f8_score" <<'PY'
import json
import sys

out, run_id, non_edge_passes, f8_score = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
rows = []
for i in range(1, non_edge_passes):
    rows.append({
        "fixture": f"F{i}",
        "category": "trivial",
        "variant_score": 90,
        "margin": 5,
        "margins": {"solo_over_bare": 5},
        "arms": {
            "bare": {"score": 50},
            "solo_claude": {"score": 55, "disqualifier": False},
        },
    })
rows.append({
    "fixture": "F9-e2e-ideate-to-resolve",
    "category": "e2e",
    "variant_score": 90,
    "margin": 5,
    "margins": {"solo_over_bare": 5},
    "arms": {
        "bare": {"score": 50},
        "solo_claude": {"score": 55, "disqualifier": False},
    },
})
rows.append({
    "fixture": "F8-known-limit-ambiguous",
    "category": "edge",
    "variant_score": f8_score,
    "margin": 5,
    "margins": {"solo_over_bare": 5},
    "arms": {
        "bare": {"score": 50},
        "solo_claude": {"score": 55, "disqualifier": False},
    },
})
summary = {
    "run_id": run_id,
    "hard_floor_violations": 0,
    "margin_ge_5_count": 7,
    "gated_fixtures": 7,
    "margin_avg": 5,
    "arms_present": {"solo_claude": True},
    "margins_avg": {"solo_over_bare": 5},
    "rows": rows,
}
with open(out, "w", encoding="utf8") as fh:
    json.dump(summary, fh)
PY
}

expect_fail_contains() {
  local label="$1"
  local needle="$2"
  shift 2
  local out="$TMP_DIR/$label.out"
  if "$@" > "$out" 2>&1; then
    echo "expected failure for $label" >&2
    cat "$out" >&2
    exit 1
  fi
  if ! grep -Fq "$needle" "$out"; then
    echo "missing expected text for $label: $needle" >&2
    cat "$out" >&2
    exit 1
  fi
}

expect_pass() {
  local label="$1"
  shift
  local out="$TMP_DIR/$label.out"
  if ! "$@" > "$out" 2>&1; then
    echo "expected pass for $label" >&2
    cat "$out" >&2
    exit 1
  fi
}

MALFORMED_SUMMARY_RUN="$RUN_PREFIX-malformed-summary"
mkdir -p "$BENCH_ROOT/results/$MALFORMED_SUMMARY_RUN"
printf '["not", "a", "dict"]\n' > "$BENCH_ROOT/results/$MALFORMED_SUMMARY_RUN/summary.json"
expect_fail_contains malformed-summary \
  "measurement invalid: malformed summary.json (expected object)" \
  python3 "$GATE" --run-id "$MALFORMED_SUMMARY_RUN"

NAN_SUMMARY_RUN="$RUN_PREFIX-nan-summary"
mkdir -p "$BENCH_ROOT/results/$NAN_SUMMARY_RUN"
cat > "$BENCH_ROOT/results/$NAN_SUMMARY_RUN/summary.json" <<'JSON'
{"hard_floor_violations": 0, "margin_avg": NaN, "rows": []}
JSON
expect_fail_contains nan-summary \
  "measurement invalid: malformed summary.json (invalid JSON)" \
  python3 "$GATE" --run-id "$NAN_SUMMARY_RUN"

MALFORMED_SUMMARY_ROWS_RUN="$RUN_PREFIX-malformed-summary-rows"
mkdir -p "$BENCH_ROOT/results/$MALFORMED_SUMMARY_ROWS_RUN"
cat > "$BENCH_ROOT/results/$MALFORMED_SUMMARY_ROWS_RUN/summary.json" <<'JSON'
{
  "hard_floor_violations": 0,
  "margin_ge_5_count": 7,
  "gated_fixtures": 7,
  "rows": ["not-a-row"]
}
JSON
expect_fail_contains malformed-summary-rows \
  "summary rows contain non-object entries" \
  python3 "$GATE" --run-id "$MALFORMED_SUMMARY_ROWS_RUN" --accept-missing

MALFORMED_SUMMARY_COUNTS_RUN="$RUN_PREFIX-malformed-summary-counts"
mkdir -p "$BENCH_ROOT/results/$MALFORMED_SUMMARY_COUNTS_RUN"
cat > "$BENCH_ROOT/results/$MALFORMED_SUMMARY_COUNTS_RUN/summary.json" <<'JSON'
{
  "hard_floor_violations": "zero",
  "margin_ge_5_count": 7,
  "gated_fixtures": 7,
  "rows": []
}
JSON
expect_fail_contains malformed-summary-counts \
  "summary hard_floor_violations missing or malformed" \
  python3 "$GATE" --run-id "$MALFORMED_SUMMARY_COUNTS_RUN" --accept-missing

MALFORMED_SUMMARY_FIELD_TYPES_RUN="$RUN_PREFIX-malformed-summary-field-types"
mkdir -p "$BENCH_ROOT/results/$MALFORMED_SUMMARY_FIELD_TYPES_RUN"
cat > "$BENCH_ROOT/results/$MALFORMED_SUMMARY_FIELD_TYPES_RUN/summary.json" <<'JSON'
{
  "hard_floor_violations": 0,
  "margin_ge_5_count": 7,
  "gated_fixtures": 7,
  "arms_present": {"solo_claude": true},
  "margins_avg": {"solo_over_bare": "bad"},
  "rows": [
    {
      "fixture": "F9-e2e-ideate-to-resolve",
      "category": 123,
      "margin": "bad",
      "margins": {"solo_over_bare": "bad"},
      "_axis_validation_unmapped_out_of_range_count": "bad",
      "arms": {
        "variant": {"_axis_validation_out_of_range_count": "bad"},
        "bare": {"score": 50, "_axis_validation_out_of_range_count": "bad"},
        "solo_claude": {"score": 55, "disqualifier": false, "_axis_validation_out_of_range_count": "bad"}
      }
    }
  ]
}
JSON
expect_fail_contains malformed-summary-field-types \
  "variant axis count malformed" \
  python3 "$GATE" --run-id "$MALFORMED_SUMMARY_FIELD_TYPES_RUN" --accept-missing

MALFORMED_ARMS_PRESENT_WRAPPER_RUN="$RUN_PREFIX-malformed-arms-present-wrapper"
write_summary "$MALFORMED_ARMS_PRESENT_WRAPPER_RUN" 7
python3 - "$BENCH_ROOT/results/$MALFORMED_ARMS_PRESENT_WRAPPER_RUN/summary.json" <<'PY'
import json
import sys

path = sys.argv[1]
summary = json.load(open(path, encoding="utf8"))
summary["arms_present"] = ["not", "an", "object"]
json.dump(summary, open(path, "w", encoding="utf8"), indent=2)
PY
expect_fail_contains malformed-arms-present-wrapper \
  "summary arms_present malformed" \
  python3 "$GATE" --run-id "$MALFORMED_ARMS_PRESENT_WRAPPER_RUN"

MALFORMED_MARGINS_AVG_WRAPPER_RUN="$RUN_PREFIX-malformed-margins-avg-wrapper"
write_summary "$MALFORMED_MARGINS_AVG_WRAPPER_RUN" 7
python3 - "$BENCH_ROOT/results/$MALFORMED_MARGINS_AVG_WRAPPER_RUN/summary.json" <<'PY'
import json
import sys

path = sys.argv[1]
summary = json.load(open(path, encoding="utf8"))
summary["margins_avg"] = ["not", "an", "object"]
json.dump(summary, open(path, "w", encoding="utf8"), indent=2)
PY
expect_fail_contains malformed-margins-avg-wrapper \
  "summary margins_avg malformed" \
  python3 "$GATE" --run-id "$MALFORMED_MARGINS_AVG_WRAPPER_RUN"

MALFORMED_ARMS_PRESENT_RUN="$RUN_PREFIX-malformed-arms-present"
write_summary "$MALFORMED_ARMS_PRESENT_RUN" 7
python3 - "$BENCH_ROOT/results/$MALFORMED_ARMS_PRESENT_RUN/summary.json" <<'PY'
import json
import sys

path = sys.argv[1]
summary = json.load(open(path, encoding="utf8"))
summary["arms_present"]["solo_claude"] = "false"
json.dump(summary, open(path, "w", encoding="utf8"), indent=2)
PY
expect_fail_contains malformed-arms-present \
  "summary arms_present.solo_claude malformed" \
  python3 "$GATE" --run-id "$MALFORMED_ARMS_PRESENT_RUN"

MALFORMED_L1_DQ_SUMMARY_RUN="$RUN_PREFIX-malformed-l1-dq-summary"
write_summary "$MALFORMED_L1_DQ_SUMMARY_RUN" 7
python3 - "$BENCH_ROOT/results/$MALFORMED_L1_DQ_SUMMARY_RUN/summary.json" <<'PY'
import json
import sys

path = sys.argv[1]
summary = json.load(open(path, encoding="utf8"))
summary["rows"][0]["arms"]["solo_claude"]["disqualifier"] = "false"
json.dump(summary, open(path, "w", encoding="utf8"), indent=2)
PY
expect_fail_contains malformed-l1-dq-summary \
  "F1 L1 disqualifier malformed" \
  python3 "$GATE" --run-id "$MALFORMED_L1_DQ_SUMMARY_RUN"

write_summary "$RUN_PREFIX-edge-cannot-count-for-l1" 6 90
expect_fail_contains edge-cannot-count-for-l1 \
  "L1: only 6 of 6 headroom-available fixtures" \
  python3 "$GATE" --run-id "$RUN_PREFIX-edge-cannot-count-for-l1"

mkdir -p "$(dirname "$BASELINE")"
cat > "$BASELINE" <<'JSON'
{
  "margin_avg": 5,
  "rows": [
    {"fixture": "F8-known-limit-ambiguous", "category": "edge", "variant_score": 90, "margin": 5}
  ]
}
JSON
write_summary "$RUN_PREFIX-edge-regression-excluded" 7 80
expect_pass edge-regression-excluded \
  python3 "$GATE" --run-id "$RUN_PREFIX-edge-regression-excluded"
grep -Fq "known-limit margin +5 outside expected [-3,+3] range" "$TMP_DIR/edge-regression-excluded.out"

AXIS_RUN="$RUN_PREFIX-axis-invalid"
AXIS_DIR="$BENCH_ROOT/results/$AXIS_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$AXIS_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare variant; do
  cat > "$AXIS_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$AXIS_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "variant", "seed": 1},
  "_axis_validation": {
    "out_of_range_count": 1,
    "out_of_range_cells": [{"breakdown": "a_breakdown", "axis": "quality", "value": 26}],
    "axis_range": [0, 25]
  },
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "margins": {"solo_over_bare": 10, "variant_over_bare": 20, "variant_over_solo": 10},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$AXIS_RUN" > "$TMP_DIR/axis-compile.out" 2>&1
grep -Fq '| Fixture | Category | variant (L2) | solo_claude (L1) | bare (L0) | variant-bare | solo_claude-bare | variant-solo_claude | Winner | Wall variant/solo_claude/bare | Wall variant/solo_claude | Wall variant/bare |' \
  "$TMP_DIR/axis-compile.out"
grep -Fq '| F9-e2e-ideate-to-resolve | e2e | 70 | 60 | 50 | +20 | +10 | +10 | variant | 10s/10s/10s | 1.0x | 1.0x |' \
  "$TMP_DIR/axis-compile.out"
grep -Fq '**Fixtures with margin ≥ +5:**   1 / 1 (gate: ≥ 7)' "$TMP_DIR/axis-compile.out"
grep -Fq '**variant (L2) vs bare (L0) margin avg:** +20.0' "$TMP_DIR/axis-compile.out"
grep -Fq '**solo_claude (L1) vs bare (L0) margin avg:** +10.0' "$TMP_DIR/axis-compile.out"
grep -Fq '**variant (L2) vs solo_claude (L1) margin avg:** +10.0' "$TMP_DIR/axis-compile.out"
grep -Fq '**Wall ratio variant (L2) / solo_claude (L1):** 1.0x' "$TMP_DIR/axis-compile.out"
if grep -Fq 'gate: ≥ 7 of 9' "$TMP_DIR/axis-compile.out"; then
  echo "compile report must not use stale 7-of-9 gate wording" >&2
  cat "$TMP_DIR/axis-compile.out" >&2
  exit 1
fi
python3 - "$BENCH_ROOT/results/$AXIS_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
count = row["arms"]["solo_claude"].get("_axis_validation_out_of_range_count")
if count != 1:
    raise SystemExit(f"expected solo_claude axis count 1, got {count!r}")
PY
NO_JUDGE_RUN="$RUN_PREFIX-no-judge-row"
NO_JUDGE_DIR="$BENCH_ROOT/results/$NO_JUDGE_RUN/F0-no-judge"
mkdir -p "$NO_JUDGE_DIR"
python3 "$COMPILE" --run-id "$NO_JUDGE_RUN" > "$TMP_DIR/no-judge-compile.out" 2>&1
grep -Fq '| F0-no-judge | — | — | — | — | — | — | — | NO_JUDGE | — | — | — |' \
  "$TMP_DIR/no-judge-compile.out"

expect_fail_contains axis-invalid-through-compile \
  "L1 axis-invalid: 1 fixture(s)" \
  python3 "$GATE" --run-id "$AXIS_RUN" --accept-missing

VARIANT_AXIS_RUN="$RUN_PREFIX-variant-axis-invalid"
VARIANT_AXIS_DIR="$BENCH_ROOT/results/$VARIANT_AXIS_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$VARIANT_AXIS_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare variant; do
  cat > "$VARIANT_AXIS_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$VARIANT_AXIS_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "variant", "seed": 1},
  "_axis_validation": {
    "out_of_range_count": 1,
    "out_of_range_cells": [{"breakdown": "c_breakdown", "axis": "quality", "value": 26}],
    "axis_range": [0, 25]
  },
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "margins": {"solo_over_bare": 10, "variant_over_bare": 20, "variant_over_solo": 10},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$VARIANT_AXIS_RUN" > "$TMP_DIR/variant-axis-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$VARIANT_AXIS_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
count = row["arms"]["variant"].get("_axis_validation_out_of_range_count")
if count != 1:
    raise SystemExit(f"expected variant axis count 1, got {count!r}")
PY
expect_fail_contains variant-axis-invalid-through-compile \
  "variant axis-invalid: 1 fixture(s)" \
  python3 "$GATE" --run-id "$VARIANT_AXIS_RUN" --accept-missing

BARE_AXIS_RUN="$RUN_PREFIX-bare-axis-invalid"
BARE_AXIS_DIR="$BENCH_ROOT/results/$BARE_AXIS_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$BARE_AXIS_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare variant; do
  cat > "$BARE_AXIS_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$BARE_AXIS_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "variant", "seed": 1},
  "_axis_validation": {
    "out_of_range_count": 1,
    "out_of_range_cells": [{"breakdown": "b_breakdown", "axis": "quality", "value": 26}],
    "axis_range": [0, 25]
  },
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "margins": {"solo_over_bare": 10, "variant_over_bare": 20, "variant_over_solo": 10},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$BARE_AXIS_RUN" > "$TMP_DIR/bare-axis-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$BARE_AXIS_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
count = row["arms"]["bare"].get("_axis_validation_out_of_range_count")
if count != 1:
    raise SystemExit(f"expected bare axis count 1, got {count!r}")
PY
expect_fail_contains bare-axis-invalid-through-compile \
  "bare axis-invalid: 1 fixture(s)" \
  python3 "$GATE" --run-id "$BARE_AXIS_RUN" --accept-missing

UNMAPPED_AXIS_RUN="$RUN_PREFIX-unmapped-axis-invalid"
UNMAPPED_AXIS_DIR="$BENCH_ROOT/results/$UNMAPPED_AXIS_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$UNMAPPED_AXIS_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare variant; do
  cat > "$UNMAPPED_AXIS_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$UNMAPPED_AXIS_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "l2_forced", "seed": 1},
  "_axis_validation": {
    "out_of_range_count": 1,
    "out_of_range_cells": [{"breakdown": "c_breakdown", "axis": "quality", "value": 26}],
    "axis_range": [0, 25]
  },
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "margins": {"solo_over_bare": 10, "variant_over_bare": 20, "variant_over_solo": 10},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$UNMAPPED_AXIS_RUN" > "$TMP_DIR/unmapped-axis-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$UNMAPPED_AXIS_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
count = row.get("_axis_validation_unmapped_out_of_range_count")
if count != 1:
    raise SystemExit(f"expected unmapped axis count 1, got {count!r}")
PY
expect_fail_contains unmapped-axis-invalid-through-compile \
  "judge axis-invalid unmapped: 1 fixture(s)" \
  python3 "$GATE" --run-id "$UNMAPPED_AXIS_RUN" --accept-missing

VARIANT_MAPPING_RUN="$RUN_PREFIX-variant-mapping-missing"
VARIANT_MAPPING_DIR="$BENCH_ROOT/results/$VARIANT_MAPPING_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$VARIANT_MAPPING_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare variant; do
  cat > "$VARIANT_MAPPING_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$VARIANT_MAPPING_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "l2_forced", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "margins": {"solo_over_bare": 10, "variant_over_bare": 20, "variant_over_solo": 10},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$VARIANT_MAPPING_RUN" > "$TMP_DIR/variant-mapping-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$VARIANT_MAPPING_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
variant = row["arms"]["variant"]
if variant.get("blind_mapping_arm_missing") is not True:
    raise SystemExit("expected variant score without blind mapping to be marked")
if row["variant_disqualifier"] is not True:
    raise SystemExit("expected variant score without blind mapping to disqualify")
PY
expect_fail_contains variant-mapping-disqualifies \
  "variant disqualifier(s)" \
  python3 "$GATE" --run-id "$VARIANT_MAPPING_RUN" --accept-missing

SOLO_MAPPING_RUN="$RUN_PREFIX-solo-mapping-missing"
SOLO_MAPPING_DIR="$BENCH_ROOT/results/$SOLO_MAPPING_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$SOLO_MAPPING_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare variant; do
  cat > "$SOLO_MAPPING_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$SOLO_MAPPING_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "variant", "B": "bare", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "margins": {"solo_over_bare": 10, "variant_over_bare": 20, "variant_over_solo": 10},
  "winner_arm": "solo_claude",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$SOLO_MAPPING_RUN" > "$TMP_DIR/solo-mapping-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$SOLO_MAPPING_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
solo = row["arms"]["solo_claude"]
if solo.get("blind_mapping_arm_missing") is not True:
    raise SystemExit("expected solo score without blind mapping to be marked")
if solo.get("score") is not None:
    raise SystemExit("solo score without blind mapping must not be displayed")
if solo.get("disqualifier") is not True:
    raise SystemExit("expected solo score without blind mapping to disqualify")
if row["margins"].get("solo_over_bare") is not None:
    raise SystemExit("solo_over_bare margin without solo blind mapping must be null")
if row["margins"].get("variant_over_solo") is not None:
    raise SystemExit("variant_over_solo margin without solo blind mapping must be null")
if row["margins"].get("variant_over_bare") != 20:
    raise SystemExit("variant_over_bare should remain available when variant and bare are mapped")
if row.get("winner") is not None:
    raise SystemExit("winner without blind-mapped trusted score must be null")
PY
expect_fail_contains solo-mapping-disqualifies \
  "L1 disqualifier(s): 1" \
  python3 "$GATE" --run-id "$SOLO_MAPPING_RUN" --accept-missing

STALE_MARGIN_RUN="$RUN_PREFIX-stale-margin"
STALE_MARGIN_DIR="$BENCH_ROOT/results/$STALE_MARGIN_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$STALE_MARGIN_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare variant; do
  cat > "$STALE_MARGIN_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$STALE_MARGIN_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "variant", "B": "bare", "C": "solo_claude", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "margins": {"solo_over_bare": 999, "variant_over_bare": 888, "variant_over_solo": 777},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$STALE_MARGIN_RUN" > "$TMP_DIR/stale-margin-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$STALE_MARGIN_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
expected = {
    "solo_over_bare": 10,
    "variant_over_bare": 20,
    "variant_over_solo": 10,
}
if row["margins"] != expected:
    raise SystemExit(f"stale judge margins must be recomputed from trusted scores: {row['margins']}")
if row["margin"] != 20:
    raise SystemExit("legacy margin must also be recomputed from trusted scores")
if summary["margins_avg"] != expected:
    raise SystemExit(f"summary margin averages must use recomputed margins: {summary['margins_avg']}")
PY

MALFORMED_SCORES_RUN="$RUN_PREFIX-malformed-scores"
MALFORMED_SCORES_DIR="$BENCH_ROOT/results/$MALFORMED_SCORES_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$MALFORMED_SCORES_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare variant; do
  cat > "$MALFORMED_SCORES_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$MALFORMED_SCORES_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "variant", "B": "bare", "C": "solo_claude", "seed": 1},
  "scores_by_arm": ["not", "a", "dict"],
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$MALFORMED_SCORES_RUN" > "$TMP_DIR/malformed-scores-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$MALFORMED_SCORES_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
for arm in ("variant", "bare", "solo_claude"):
    if row["arms"][arm]["score"] is not None:
        raise SystemExit(f"malformed scores_by_arm must not expose {arm} score")
if any(value is not None for value in row["margins"].values()):
    raise SystemExit(f"malformed scores_by_arm must null margins: {row['margins']}")
if row.get("winner") is not None:
    raise SystemExit("winner without trusted score must be null")
PY

OVERRANGE_SCORES_RUN="$RUN_PREFIX-overrange-scores"
OVERRANGE_SCORES_DIR="$BENCH_ROOT/results/$OVERRANGE_SCORES_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$OVERRANGE_SCORES_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare variant; do
  cat > "$OVERRANGE_SCORES_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$OVERRANGE_SCORES_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "variant", "B": "bare", "C": "solo_claude", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 101},
  "variant_score": 101,
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$OVERRANGE_SCORES_RUN" > "$TMP_DIR/overrange-scores-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$OVERRANGE_SCORES_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
if row["arms"]["variant"]["score"] is not None:
    raise SystemExit("out-of-range scores_by_arm must not expose variant score")
if row.get("variant_score") is not None:
    raise SystemExit("legacy variant_score must also be null for out-of-range scores")
if row.get("winner") is not None:
    raise SystemExit("winner without trusted score must be null for out-of-range scores")
if row["margins"]["variant_over_bare"] is not None:
    raise SystemExit("out-of-range variant score must null dependent margins")
PY

BOOLEAN_SCORES_RUN="$RUN_PREFIX-boolean-scores"
BOOLEAN_SCORES_DIR="$BENCH_ROOT/results/$BOOLEAN_SCORES_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$BOOLEAN_SCORES_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare variant; do
  cat > "$BOOLEAN_SCORES_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$BOOLEAN_SCORES_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "variant", "B": "bare", "C": "solo_claude", "seed": 1},
  "scores_by_arm": {"solo_claude": true, "bare": 50, "variant": 70},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$BOOLEAN_SCORES_RUN" > "$TMP_DIR/boolean-scores-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$BOOLEAN_SCORES_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
if row["arms"]["solo_claude"]["score"] is not None:
    raise SystemExit("boolean scores_by_arm must not expose solo score")
if row["margins"]["solo_over_bare"] is not None:
    raise SystemExit("boolean solo score must null dependent margins")
PY

BOOLEAN_WALL_RUN="$RUN_PREFIX-boolean-wall"
BOOLEAN_WALL_DIR="$BENCH_ROOT/results/$BOOLEAN_WALL_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$BOOLEAN_WALL_DIR"/{solo_claude,bare,variant}
cat > "$BOOLEAN_WALL_DIR/variant/result.json" <<'JSON'
{"elapsed_seconds": true, "verify_score": true, "files_changed": 1, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
for arm in solo_claude bare; do
  cat > "$BOOLEAN_WALL_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$BOOLEAN_WALL_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "variant", "B": "bare", "C": "solo_claude", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$BOOLEAN_WALL_RUN" > "$TMP_DIR/boolean-wall-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$BOOLEAN_WALL_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
variant = row["arms"]["variant"]
if variant["wall_s"] is not None or variant["verify_score"] is not None:
    raise SystemExit("boolean result numeric fields must not appear in compile summary")
if row["wall_ratios"]["variant_over_bare"] is not None:
    raise SystemExit("boolean wall time must null dependent wall ratios")
PY

MALFORMED_RESULT_BOOL_RUN="$RUN_PREFIX-malformed-result-bool"
MALFORMED_RESULT_BOOL_DIR="$BENCH_ROOT/results/$MALFORMED_RESULT_BOOL_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$MALFORMED_RESULT_BOOL_DIR"/{solo_claude,bare,variant}
cat > "$MALFORMED_RESULT_BOOL_DIR/variant/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "timed_out": "false", "disqualifier": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
for arm in solo_claude bare; do
  cat > "$MALFORMED_RESULT_BOOL_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "disqualifier": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$MALFORMED_RESULT_BOOL_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "variant", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$MALFORMED_RESULT_BOOL_RUN" > "$TMP_DIR/malformed-result-bool-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$MALFORMED_RESULT_BOOL_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
variant = summary["rows"][0]["arms"]["variant"]
if variant["timed_out"] is not False:
    raise SystemExit("malformed timed_out must not become exact true")
if variant["malformed_boolean_fields"] != ["timed_out"]:
    raise SystemExit("malformed timed_out must be recorded")
if variant["dq_deterministic"] is not True or variant["disqualifier"] is not True:
    raise SystemExit("malformed boolean artifact must disqualify deterministically")
PY

MALFORMED_JUDGE_BOOL_RUN="$RUN_PREFIX-malformed-judge-bool"
MALFORMED_JUDGE_BOOL_DIR="$BENCH_ROOT/results/$MALFORMED_JUDGE_BOOL_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$MALFORMED_JUDGE_BOOL_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare variant; do
  cat > "$MALFORMED_JUDGE_BOOL_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "disqualifier": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$MALFORMED_JUDGE_BOOL_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "variant", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": "false"}
  }
}
JSON
python3 "$COMPILE" --run-id "$MALFORMED_JUDGE_BOOL_RUN" > "$TMP_DIR/malformed-judge-bool-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$MALFORMED_JUDGE_BOOL_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
variant = summary["rows"][0]["arms"]["variant"]
if variant["dq_judge_malformed"] is not True:
    raise SystemExit("malformed judge disqualifier must be recorded")
if variant["dq_judge"] is not True or variant["disqualifier"] is not True:
    raise SystemExit("malformed judge disqualifier must fail closed")
PY

MALFORMED_MAPPING_RUN="$RUN_PREFIX-malformed-mapping"
MALFORMED_MAPPING_DIR="$BENCH_ROOT/results/$MALFORMED_MAPPING_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$MALFORMED_MAPPING_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare variant; do
  cat > "$MALFORMED_MAPPING_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$MALFORMED_MAPPING_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": "not-a-dict",
  "_axis_validation": {
    "out_of_range_count": 1,
    "out_of_range_cells": [{"breakdown": "c_breakdown", "axis": "quality", "value": 26}],
    "axis_range": [0, 25]
  },
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "margins": {"solo_over_bare": 10, "variant_over_bare": 20, "variant_over_solo": 10},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$MALFORMED_MAPPING_RUN" > "$TMP_DIR/malformed-mapping-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$MALFORMED_MAPPING_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
if row.get("_axis_validation_unmapped_out_of_range_count") != 1:
    raise SystemExit("expected malformed mapping axis cell to be unmapped")
for arm in ("solo_claude", "bare", "variant"):
    payload = row["arms"][arm]
    if payload.get("blind_mapping_arm_missing") is not True:
        raise SystemExit(f"expected {arm} score without dict blind mapping to be marked")
    if payload.get("score") is not None:
        raise SystemExit(f"{arm} score without dict blind mapping must not be displayed")
    if payload.get("disqualifier") is not True:
        raise SystemExit(f"expected {arm} score without dict blind mapping to disqualify")
for key, value in row["margins"].items():
    if value is not None:
        raise SystemExit(f"{key} without dict blind mapping must be null")
PY
expect_fail_contains malformed-mapping-disqualifies \
  "judge axis-invalid unmapped: 1 fixture(s)" \
  python3 "$GATE" --run-id "$MALFORMED_MAPPING_RUN" --accept-missing

VARIANT_TIMEOUT_RUN="$RUN_PREFIX-variant-timeout"
VARIANT_TIMEOUT_DIR="$BENCH_ROOT/results/$VARIANT_TIMEOUT_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$VARIANT_TIMEOUT_DIR"/{solo_claude,bare,variant}
cat > "$VARIANT_TIMEOUT_DIR/variant/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "timed_out": true, "disqualifier": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
for arm in solo_claude bare; do
  cat > "$VARIANT_TIMEOUT_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "disqualifier": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$VARIANT_TIMEOUT_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "variant", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "margins": {"solo_over_bare": 10, "variant_over_bare": 20, "variant_over_solo": 10},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$VARIANT_TIMEOUT_RUN" > "$TMP_DIR/variant-timeout-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$VARIANT_TIMEOUT_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
if row["variant_disqualifier"] is not True:
    raise SystemExit("expected variant timeout to become variant_disqualifier")
PY
expect_fail_contains variant-timeout-disqualifies \
  "variant disqualifier(s)" \
  python3 "$GATE" --run-id "$VARIANT_TIMEOUT_RUN" --accept-missing

VARIANT_VERIFY_SCORE_RUN="$RUN_PREFIX-variant-verify-score"
VARIANT_VERIFY_SCORE_DIR="$BENCH_ROOT/results/$VARIANT_VERIFY_SCORE_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$VARIANT_VERIFY_SCORE_DIR"/{solo_claude,bare,variant}
cat > "$VARIANT_VERIFY_SCORE_DIR/variant/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 0.75, "files_changed": 1, "disqualifier": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
for arm in solo_claude bare; do
  cat > "$VARIANT_VERIFY_SCORE_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "disqualifier": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$VARIANT_VERIFY_SCORE_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "variant", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "margins": {"solo_over_bare": 10, "variant_over_bare": 20, "variant_over_solo": 10},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$VARIANT_VERIFY_SCORE_RUN" > "$TMP_DIR/variant-verify-score-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$VARIANT_VERIFY_SCORE_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
if row["variant_disqualifier"] is not True:
    raise SystemExit("expected variant verify_score < 1.0 to become variant_disqualifier")
PY
expect_fail_contains variant-verify-score-disqualifies \
  "variant disqualifier(s)" \
  python3 "$GATE" --run-id "$VARIANT_VERIFY_SCORE_RUN" --accept-missing

VARIANT_VERDICT_RUN="$RUN_PREFIX-variant-verdict"
VARIANT_VERDICT_DIR="$BENCH_ROOT/results/$VARIANT_VERDICT_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$VARIANT_VERDICT_DIR"/{solo_claude,bare,variant}
cat > "$VARIANT_VERDICT_DIR/variant/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "disqualifier": false, "terminal_verdict": "BLOCKED:probe-derive-malformed", "verify_verdict": "BLOCKED"}
JSON
for arm in solo_claude bare; do
  cat > "$VARIANT_VERDICT_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "disqualifier": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$VARIANT_VERDICT_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "variant", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "margins": {"solo_over_bare": 10, "variant_over_bare": 20, "variant_over_solo": 10},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$VARIANT_VERDICT_RUN" > "$TMP_DIR/variant-verdict-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$VARIANT_VERDICT_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
if row["variant_disqualifier"] is not True:
    raise SystemExit("expected variant blocked verdict to become variant_disqualifier")
PY
expect_fail_contains variant-verdict-disqualifies \
  "variant disqualifier(s)" \
  python3 "$GATE" --run-id "$VARIANT_VERDICT_RUN" --accept-missing

SOLO_INVOKE_RUN="$RUN_PREFIX-solo-invoke-failure"
SOLO_INVOKE_DIR="$BENCH_ROOT/results/$SOLO_INVOKE_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$SOLO_INVOKE_DIR"/{solo_claude,bare,variant}
cat > "$SOLO_INVOKE_DIR/solo_claude/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "invoke_failure": true, "invoke_failure_reason": "provider_limit", "disqualifier": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
for arm in variant bare; do
  cat > "$SOLO_INVOKE_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "disqualifier": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$SOLO_INVOKE_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "variant", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "margins": {"solo_over_bare": 10, "variant_over_bare": 20, "variant_over_solo": 10},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$SOLO_INVOKE_RUN" > "$TMP_DIR/solo-invoke-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$SOLO_INVOKE_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
if row["arms"]["solo_claude"].get("disqualifier") is not True:
    raise SystemExit("expected solo invoke_failure to become arm disqualifier")
PY
expect_fail_contains solo-invoke-disqualifies \
  "L1 disqualifier(s): 1" \
  python3 "$GATE" --run-id "$SOLO_INVOKE_RUN" --accept-missing

MALFORMED_FINDINGS_RUN="$RUN_PREFIX-malformed-findings"
MALFORMED_FINDINGS_DIR="$BENCH_ROOT/results/$MALFORMED_FINDINGS_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$MALFORMED_FINDINGS_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare variant; do
  cat > "$MALFORMED_FINDINGS_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "disqualifier": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$MALFORMED_FINDINGS_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "variant", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "winner_arm": "variant",
  "findings_by_arm": {
    "variant": "single finding string",
    "solo_claude": ["structured finding"]
  },
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$MALFORMED_FINDINGS_RUN" > "$TMP_DIR/malformed-findings-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$MALFORMED_FINDINGS_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
if row["arms"]["variant"]["critical_findings"] != ["single finding string"]:
    raise SystemExit("non-list finding entry must become a one-item list")
if row["arms"]["solo_claude"]["critical_findings"] != ["structured finding"]:
    raise SystemExit("list finding entry must be preserved")
PY
grep -Fq '**variant (L2):**' "$BENCH_ROOT/results/$MALFORMED_FINDINGS_RUN/report.md"
grep -Fq '**solo_claude (L1):**' "$BENCH_ROOT/results/$MALFORMED_FINDINGS_RUN/report.md"
grep -Fq -- '- single finding string' "$BENCH_ROOT/results/$MALFORMED_FINDINGS_RUN/report.md"

MALFORMED_FINDINGS_MAP_RUN="$RUN_PREFIX-malformed-findings-map"
MALFORMED_FINDINGS_MAP_DIR="$BENCH_ROOT/results/$MALFORMED_FINDINGS_MAP_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$MALFORMED_FINDINGS_MAP_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare variant; do
  cat > "$MALFORMED_FINDINGS_MAP_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "disqualifier": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$MALFORMED_FINDINGS_MAP_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "variant", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "winner_arm": "variant",
  "findings_by_arm": ["not", "a", "dict"],
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$MALFORMED_FINDINGS_MAP_RUN" > "$TMP_DIR/malformed-findings-map-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$MALFORMED_FINDINGS_MAP_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
for arm in ("variant", "solo_claude", "bare"):
    if row["arms"][arm]["critical_findings"]:
        raise SystemExit("non-dict findings_by_arm must be ignored")
PY

MALFORMED_AXIS_WRAPPER_RUN="$RUN_PREFIX-malformed-axis-wrapper"
MALFORMED_AXIS_WRAPPER_DIR="$BENCH_ROOT/results/$MALFORMED_AXIS_WRAPPER_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$MALFORMED_AXIS_WRAPPER_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare variant; do
  cat > "$MALFORMED_AXIS_WRAPPER_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "disqualifier": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$MALFORMED_AXIS_WRAPPER_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "variant", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "winner_arm": "variant",
  "_axis_validation": ["not", "a", "dict"],
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$MALFORMED_AXIS_WRAPPER_RUN" > "$TMP_DIR/malformed-axis-wrapper-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$MALFORMED_AXIS_WRAPPER_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
if row.get("_axis_validation_unmapped_out_of_range_count") != 0:
    raise SystemExit("non-dict _axis_validation wrapper must not crash or invent invalid cells")
for arm in ("variant", "solo_claude", "bare"):
    if row["arms"][arm]["_axis_validation_out_of_range_count"] != 0:
        raise SystemExit("non-dict _axis_validation wrapper must not mark arm axis invalid")
PY

MALFORMED_RESULT_RUN="$RUN_PREFIX-malformed-result-artifact"
MALFORMED_RESULT_DIR="$BENCH_ROOT/results/$MALFORMED_RESULT_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$MALFORMED_RESULT_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare; do
  cat > "$MALFORMED_RESULT_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "disqualifier": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
printf '["not", "a", "dict"]\n' > "$MALFORMED_RESULT_DIR/variant/result.json"
cat > "$MALFORMED_RESULT_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "variant", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$MALFORMED_RESULT_RUN" > "$TMP_DIR/malformed-result-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$MALFORMED_RESULT_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
if row["variant_disqualifier"] is not True:
    raise SystemExit("non-dict variant result.json must fail closed as a disqualifier")
if row["arms"]["variant"].get("wall_s") is not None:
    raise SystemExit("non-dict variant result.json must not expose timing fields")
PY
expect_fail_contains malformed-result-artifact-disqualifies \
  "variant disqualifier(s)" \
  python3 "$GATE" --run-id "$MALFORMED_RESULT_RUN" --accept-missing

NAN_RESULT_RUN="$RUN_PREFIX-nan-result-artifact"
NAN_RESULT_DIR="$BENCH_ROOT/results/$NAN_RESULT_RUN/F9-e2e-ideate-to-resolve"
mkdir -p "$NAN_RESULT_DIR"/{solo_claude,bare,variant}
for arm in solo_claude bare; do
  cat > "$NAN_RESULT_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 10, "verify_score": 1, "files_changed": 1, "disqualifier": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
done
cat > "$NAN_RESULT_DIR/variant/result.json" <<'JSON'
{"elapsed_seconds": NaN, "verify_score": NaN, "files_changed": 1, "disqualifier": false, "terminal_verdict": "PASS", "verify_verdict": "PASS"}
JSON
cat > "$NAN_RESULT_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "C": "variant", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "bare": 50, "variant": 70},
  "winner_arm": "variant",
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false},
    "variant": {"disqualifier": false}
  }
}
JSON
python3 "$COMPILE" --run-id "$NAN_RESULT_RUN" > "$TMP_DIR/nan-result-compile.out" 2>&1
python3 - "$BENCH_ROOT/results/$NAN_RESULT_RUN/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
row = summary["rows"][0]
if row["variant_disqualifier"] is not True:
    raise SystemExit("NaN variant result.json must fail closed as a disqualifier")
if row["arms"]["variant"].get("wall_s") is not None:
    raise SystemExit("NaN variant result.json must not expose timing fields")
PY
expect_fail_contains nan-result-artifact-disqualifies \
  "variant disqualifier(s)" \
  python3 "$GATE" --run-id "$NAN_RESULT_RUN" --accept-missing

echo "PASS test-ship-gate"
