#!/usr/bin/env bash
# Regression tests for iter-0033c-l1-summary.py score-source handling.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUMMARY="$SCRIPT_DIR/iter-0033c-l1-summary.py"
TMP_DIR="$(mktemp -d /tmp/iter-0033c-l1-summary-test.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

RUN_DIR="$TMP_DIR/results"
FIXTURE_DIR="$RUN_DIR/F1-synthetic"
mkdir -p "$FIXTURE_DIR"/{solo_claude,l2_gated,l2_forced,bare}
for arm in solo_claude l2_gated l2_forced bare; do
  cat > "$FIXTURE_DIR/$arm/result.json" <<'JSON'
{"elapsed_seconds": 12, "verify_score": 1, "files_changed": 2, "timed_out": false, "disqualifier": false}
JSON
done
cat > "$FIXTURE_DIR/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "l2_gated", "C": "l2_forced", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "l2_gated": 70},
  "c_score": 80
}
JSON

python3 "$SUMMARY" \
  --results-dir "$RUN_DIR" \
  --out "$TMP_DIR/summary.json" \
  --run-id synthetic \
  --git-sha abc123 >/dev/null
python3 - "$TMP_DIR/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
arms = summary["rows"][0]["arms"]
if arms["solo_claude"]["score"] != 60:
    raise SystemExit("solo_claude score must come from scores_by_arm")
if arms["l2_gated"]["score"] != 70:
    raise SystemExit("l2_gated score must come from scores_by_arm")
if arms["l2_forced"]["score"] != 80:
    raise SystemExit("l2_forced score must fall back to lowercase c_score")
if "bare" in arms:
    raise SystemExit("unmapped bare arm must not appear in iter-0033c L1 summary")
PY

MALFORMED_DIR="$TMP_DIR/malformed"
MALFORMED_FIXTURE="$MALFORMED_DIR/F2-synthetic"
mkdir -p "$MALFORMED_FIXTURE"/{solo_claude,l2_gated}
for arm in solo_claude l2_gated; do
  cat > "$MALFORMED_FIXTURE/$arm/result.json" <<'JSON'
{"elapsed_seconds": 12, "verify_score": 1, "files_changed": 2, "timed_out": false, "disqualifier": false}
JSON
done
cat > "$MALFORMED_FIXTURE/judge.json" <<'JSON'
{
  "_blind_mapping": "not-a-dict",
  "scores_by_arm": {"solo_claude": 60, "l2_gated": 70}
}
JSON
python3 "$SUMMARY" \
  --results-dir "$MALFORMED_DIR" \
  --out "$TMP_DIR/malformed-summary.json" \
  --run-id malformed \
  --git-sha abc123 >/dev/null
python3 - "$TMP_DIR/malformed-summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
arms = summary["rows"][0]["arms"]
if arms:
    raise SystemExit("malformed blind mapping must not trust scores_by_arm")
PY

MALFORMED_SCORES_DIR="$TMP_DIR/malformed-scores"
MALFORMED_SCORES_FIXTURE="$MALFORMED_SCORES_DIR/F3-synthetic"
mkdir -p "$MALFORMED_SCORES_FIXTURE"/{solo_claude,l2_gated}
for arm in solo_claude l2_gated; do
  cat > "$MALFORMED_SCORES_FIXTURE/$arm/result.json" <<'JSON'
{"elapsed_seconds": 12, "verify_score": 1, "files_changed": 2, "timed_out": false, "disqualifier": false}
JSON
done
cat > "$MALFORMED_SCORES_FIXTURE/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "l2_gated", "seed": 1},
  "scores_by_arm": ["not", "a", "dict"]
}
JSON
python3 "$SUMMARY" \
  --results-dir "$MALFORMED_SCORES_DIR" \
  --out "$TMP_DIR/malformed-scores-summary.json" \
  --run-id malformed-scores \
  --git-sha abc123 >/dev/null
python3 - "$TMP_DIR/malformed-scores-summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
arms = summary["rows"][0]["arms"]
if arms["solo_claude"]["score"] is not None or arms["l2_gated"]["score"] is not None:
    raise SystemExit("malformed scores_by_arm must not provide arm scores")
PY

OVERRANGE_SCORES_DIR="$TMP_DIR/overrange-scores"
OVERRANGE_SCORES_FIXTURE="$OVERRANGE_SCORES_DIR/F5-synthetic"
mkdir -p "$OVERRANGE_SCORES_FIXTURE"/{solo_claude,l2_gated}
for arm in solo_claude l2_gated; do
  cat > "$OVERRANGE_SCORES_FIXTURE/$arm/result.json" <<'JSON'
{"elapsed_seconds": 12, "verify_score": 1, "files_changed": 2, "timed_out": false, "disqualifier": false}
JSON
done
cat > "$OVERRANGE_SCORES_FIXTURE/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "l2_gated", "seed": 1},
  "scores_by_arm": {"solo_claude": 101, "l2_gated": 70},
  "a_score": 101
}
JSON
python3 "$SUMMARY" \
  --results-dir "$OVERRANGE_SCORES_DIR" \
  --out "$TMP_DIR/overrange-scores-summary.json" \
  --run-id overrange-scores \
  --git-sha abc123 >/dev/null
python3 - "$TMP_DIR/overrange-scores-summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
arms = summary["rows"][0]["arms"]
if arms["solo_claude"]["score"] is not None:
    raise SystemExit("out-of-range scores must not appear in L1 summary")
PY

BOOLEAN_SCORES_DIR="$TMP_DIR/boolean-scores"
BOOLEAN_SCORES_FIXTURE="$BOOLEAN_SCORES_DIR/F6-synthetic"
mkdir -p "$BOOLEAN_SCORES_FIXTURE"/{solo_claude,l2_gated}
for arm in solo_claude l2_gated; do
  cat > "$BOOLEAN_SCORES_FIXTURE/$arm/result.json" <<'JSON'
{"elapsed_seconds": 12, "verify_score": 1, "files_changed": 2, "timed_out": false, "disqualifier": false}
JSON
done
cat > "$BOOLEAN_SCORES_FIXTURE/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "l2_gated", "seed": 1},
  "scores_by_arm": {"solo_claude": true, "l2_gated": 70},
  "a_score": true
}
JSON
python3 "$SUMMARY" \
  --results-dir "$BOOLEAN_SCORES_DIR" \
  --out "$TMP_DIR/boolean-scores-summary.json" \
  --run-id boolean-scores \
  --git-sha abc123 >/dev/null
python3 - "$TMP_DIR/boolean-scores-summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
arms = summary["rows"][0]["arms"]
if arms["solo_claude"]["score"] is not None:
    raise SystemExit("boolean scores must not appear in L1 summary")
PY

BOOLEAN_WALL_DIR="$TMP_DIR/boolean-wall"
BOOLEAN_WALL_FIXTURE="$BOOLEAN_WALL_DIR/F7-synthetic"
mkdir -p "$BOOLEAN_WALL_FIXTURE"/{solo_claude,l2_gated}
cat > "$BOOLEAN_WALL_FIXTURE/solo_claude/result.json" <<'JSON'
{"elapsed_seconds": true, "verify_score": true, "files_changed": 2, "timed_out": false, "disqualifier": false}
JSON
cat > "$BOOLEAN_WALL_FIXTURE/l2_gated/result.json" <<'JSON'
{"elapsed_seconds": 12, "verify_score": 1, "files_changed": 2, "timed_out": false, "disqualifier": false}
JSON
cat > "$BOOLEAN_WALL_FIXTURE/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "l2_gated", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "l2_gated": 70}
}
JSON
python3 "$SUMMARY" \
  --results-dir "$BOOLEAN_WALL_DIR" \
  --out "$TMP_DIR/boolean-wall-summary.json" \
  --run-id boolean-wall \
  --git-sha abc123 >/dev/null
python3 - "$TMP_DIR/boolean-wall-summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
solo = summary["rows"][0]["arms"]["solo_claude"]
if solo["wall_s"] is not None or solo["verify_score"] is not None:
    raise SystemExit("boolean result numeric fields must not appear in L1 summary")
PY

NAN_RESULT_DIR="$TMP_DIR/nan-result"
NAN_RESULT_FIXTURE="$NAN_RESULT_DIR/F8-synthetic"
mkdir -p "$NAN_RESULT_FIXTURE"/{solo_claude,l2_gated}
cat > "$NAN_RESULT_FIXTURE/solo_claude/result.json" <<'JSON'
{"elapsed_seconds": NaN, "verify_score": NaN, "files_changed": 2, "timed_out": false, "disqualifier": false}
JSON
cat > "$NAN_RESULT_FIXTURE/l2_gated/result.json" <<'JSON'
{"elapsed_seconds": 12, "verify_score": 1, "files_changed": 2, "timed_out": false, "disqualifier": false}
JSON
cat > "$NAN_RESULT_FIXTURE/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "l2_gated", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "l2_gated": 70}
}
JSON
python3 "$SUMMARY" \
  --results-dir "$NAN_RESULT_DIR" \
  --out "$TMP_DIR/nan-result-summary.json" \
  --run-id nan-result \
  --git-sha abc123 >/dev/null
python3 - "$TMP_DIR/nan-result-summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
solo = summary["rows"][0]["arms"]["solo_claude"]
if solo["wall_s"] is not None or solo["verify_score"] is not None:
    raise SystemExit("NaN result numeric fields must not appear in L1 summary")
PY

MALFORMED_RESULT_DIR="$TMP_DIR/malformed-result"
MALFORMED_RESULT_FIXTURE="$MALFORMED_RESULT_DIR/F4-synthetic"
mkdir -p "$MALFORMED_RESULT_FIXTURE"/{solo_claude,l2_gated}
printf '["not", "a", "dict"]\n' > "$MALFORMED_RESULT_FIXTURE/solo_claude/result.json"
cat > "$MALFORMED_RESULT_FIXTURE/l2_gated/result.json" <<'JSON'
{"elapsed_seconds": 12, "verify_score": 1, "files_changed": 2, "timed_out": false, "disqualifier": false}
JSON
cat > "$MALFORMED_RESULT_FIXTURE/judge.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "l2_gated", "seed": 1},
  "scores_by_arm": {"solo_claude": 60, "l2_gated": 70}
}
JSON
python3 "$SUMMARY" \
  --results-dir "$MALFORMED_RESULT_DIR" \
  --out "$TMP_DIR/malformed-result-summary.json" \
  --run-id malformed-result \
  --git-sha abc123 >/dev/null
python3 - "$TMP_DIR/malformed-result-summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf8"))
solo = summary["rows"][0]["arms"]["solo_claude"]
if solo["wall_s"] is not None or solo["verify_score"] is not None:
    raise SystemExit("non-dict result.json must not expose result fields")
PY

echo "PASS test-iter-0033c-l1-summary"
