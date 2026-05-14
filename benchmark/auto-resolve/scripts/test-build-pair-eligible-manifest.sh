#!/usr/bin/env bash
# Regression tests for build-pair-eligible-manifest.py score-source handling.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD="$SCRIPT_DIR/build-pair-eligible-manifest.py"
TMP_DIR="$(mktemp -d /tmp/build-pair-eligible-manifest-test.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

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

cat > "$TMP_DIR/c1.json" <<'JSON'
{
  "rows": [
    {
      "fixture": "F1-cli-example",
      "arms": {
        "solo_claude": {"score": 40, "disqualifier": false},
        "bare": {"score": 50, "disqualifier": false}
      }
    },
    {
      "fixture": "F5-cli-dirty",
      "arms": {
        "solo_claude": {"score": 30, "disqualifier": true},
        "bare": {"score": 50, "disqualifier": false}
      }
    },
    {
      "fixture": "F16-cli-current-proof",
      "arms": {
        "solo_claude": {"score": 40, "disqualifier": false},
        "bare": {"score": 50, "disqualifier": false}
      }
    },
    {
      "fixture": "F17-cli-overrange",
      "arms": {
        "solo_claude": {"score": 101, "disqualifier": false},
        "bare": {"score": 102, "disqualifier": false}
      }
    }
  ]
}
JSON

cat > "$TMP_DIR/c1-all-rejected.json" <<'JSON'
{
  "rows": [
    {
      "fixture": "F1-cli-example",
      "arms": {
        "solo_claude": {"score": 40, "disqualifier": false},
        "bare": {"score": 50, "disqualifier": false}
      }
    }
  ]
}
JSON

cat > "$TMP_DIR/l1.json" <<'JSON'
{
  "rows": [
    {
      "fixture": "F5-cli-dirty",
      "arms": {
        "solo_claude": {"score": 30, "disqualifier": false},
        "bare": {"score": 50, "disqualifier": false}
      }
    }
  ]
}
JSON

write_f9() {
  local path="$1"
  local mapping_a="$2"
  local solo_dq="$3"
  cat > "$path" <<JSON
{
  "a_score": 91,
  "b_score": 76,
  "_blind_mapping": {"A": "$mapping_a", "B": "bare", "seed": 1},
  "scores_by_arm": {"solo_claude": 91, "bare": 76},
  "disqualifiers": {"A": $solo_dq, "B": false},
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": $solo_dq},
    "bare": {"disqualifier": false}
  }
}
JSON
}

write_f9 "$TMP_DIR/f9-pass.json" "solo_claude" false
printf '["not", "a", "dict"]\n' > "$TMP_DIR/c1-malformed-top.json"
expect_fail_contains c1-malformed-top "c1-summary malformed: expected object" \
  python3 "$BUILD" \
    --c1-summary "$TMP_DIR/c1-malformed-top.json" \
    --f9-judge "$TMP_DIR/f9-pass.json" \
    --l1-rerun-summary "$TMP_DIR/l1.json" \
    --output "$TMP_DIR/c1-malformed-top-manifest.json"

cat > "$TMP_DIR/c1-nan-score.json" <<'JSON'
{"rows":[{"fixture":"F1-synthetic","arms":{"solo_claude":{"score":NaN},"bare":{"score":50}}}]}
JSON
expect_fail_contains c1-nan-score "c1-summary malformed: invalid JSON" \
  python3 "$BUILD" \
    --c1-summary "$TMP_DIR/c1-nan-score.json" \
    --f9-judge "$TMP_DIR/f9-pass.json" \
    --l1-rerun-summary "$TMP_DIR/l1.json" \
    --output "$TMP_DIR/c1-nan-score-manifest.json"

cat > "$TMP_DIR/c1-malformed-rows.json" <<'JSON'
{"rows": {"not": "a-list"}}
JSON
expect_fail_contains c1-malformed-rows "c1-summary malformed: rows must be an array" \
  python3 "$BUILD" \
    --c1-summary "$TMP_DIR/c1-malformed-rows.json" \
    --f9-judge "$TMP_DIR/f9-pass.json" \
    --l1-rerun-summary "$TMP_DIR/l1.json" \
    --output "$TMP_DIR/c1-malformed-rows-manifest.json"

printf '["not", "a", "dict"]\n' > "$TMP_DIR/f9-malformed-top.json"
expect_fail_contains f9-malformed-top "f9-judge malformed: expected object" \
  python3 "$BUILD" \
    --c1-summary "$TMP_DIR/c1.json" \
    --f9-judge "$TMP_DIR/f9-malformed-top.json" \
    --l1-rerun-summary "$TMP_DIR/l1.json" \
    --output "$TMP_DIR/f9-malformed-top-manifest.json"

cat > "$TMP_DIR/c1-malformed-row-fields.json" <<'JSON'
{
  "rows": [
    "not-a-row",
    {
      "fixture": "F1-cli-example",
      "arms": {
        "solo_claude": {"score": true, "disqualifier": false},
        "bare": {"score": 50, "disqualifier": false}
      }
    },
    {
      "fixture": 123,
      "arms": {
        "solo_claude": {"score": 40, "disqualifier": false},
        "bare": {"score": 50, "disqualifier": false}
      }
    },
    {
      "fixture": "F16-cli-current-proof",
      "arms": {
        "solo_claude": {"score": 40, "disqualifier": false},
        "bare": {"score": 50, "disqualifier": false}
      }
    },
    {
      "fixture": "F18-cli-string-disqualifier",
      "arms": {
        "solo_claude": {"score": 40, "disqualifier": "false"},
        "bare": {"score": 50, "disqualifier": false}
      }
    }
  ]
}
JSON
python3 "$BUILD" \
  --c1-summary "$TMP_DIR/c1-malformed-row-fields.json" \
  --f9-judge "$TMP_DIR/f9-pass.json" \
  --l1-rerun-summary "$TMP_DIR/l1.json" \
  --output "$TMP_DIR/c1-malformed-row-fields-manifest.json" >/dev/null
python3 - "$TMP_DIR/c1-malformed-row-fields-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf8"))
promoted = manifest["selection_rule"]["promoted_by_l1_le_l0"]
if "F1" in promoted:
    raise SystemExit("malformed C1 row fields must not promote F1")
if "F16" not in manifest["fixtures_pair_eligible"]:
    raise SystemExit("expected non-rejected F16 row to keep manifest non-empty")
if "F17" in promoted:
    raise SystemExit("overrange C1 row fields must not promote F17")
if "F18" in promoted:
    raise SystemExit("string C1 disqualifier must not promote F18")
PY

expect_fail_contains all-rejected-empty \
  "no pair-eligible fixtures remain after rejected-registry filtering" \
  python3 "$BUILD" \
    --c1-summary "$TMP_DIR/c1-all-rejected.json" \
    --f9-judge "$TMP_DIR/f9-pass.json" \
    --l1-rerun-summary "$TMP_DIR/l1.json" \
    --output "$TMP_DIR/all-rejected-manifest.json"

python3 "$BUILD" \
  --c1-summary "$TMP_DIR/c1.json" \
  --f9-judge "$TMP_DIR/f9-pass.json" \
  --l1-rerun-summary "$TMP_DIR/l1.json" \
  --output "$TMP_DIR/pass-manifest.json" >/dev/null
python3 - "$TMP_DIR/pass-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf8"))
eligible = manifest["fixtures_pair_eligible"]
if "F9" in eligible:
    raise SystemExit("F9 is currently rejected by the shared pair registry")
if "F1" in eligible:
    raise SystemExit("F1 is currently rejected by the shared pair registry")
if "F5" in eligible:
    raise SystemExit("dirty F5 L1<=L0 row must not be promoted")
if "F16" not in eligible:
    raise SystemExit("expected non-rejected F16 L1<=L0 promotion")
rule = manifest["selection_rule"]
if rule["f9_included"] is not True:
    raise SystemExit("expected selection rule to record F9 pre-reg inclusion before rejected-registry filtering")
for fixture in ["F1", "F2", "F3", "F4", "F6", "F7", "F9"]:
    if fixture not in rule["rejected_excluded"]:
        raise SystemExit(f"expected {fixture} to be excluded by rejected registry")
reasons = rule["rejected_excluded_reasons"]
if reasons["F2"] != "bare 83 / solo_claude 95 in 20260512-f2-medium-headroom":
    raise SystemExit("expected rejected_excluded_reasons to preserve the F2 registry reason")
if "20260512-f9-e2e-headroom" not in reasons["F9"]:
    raise SystemExit("expected rejected_excluded_reasons to preserve the F9 registry run id")
PY
python3 - "$TMP_DIR/pass-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf8"))
if "F5" in manifest["fixtures_pair_eligible"]:
    raise SystemExit("l1-rerun-summary must not override pre-registered C1 selection grounds")
PY

write_f9 "$TMP_DIR/f9-wrong-mapping.json" "variant" false
python3 "$BUILD" \
  --c1-summary "$TMP_DIR/c1.json" \
  --f9-judge "$TMP_DIR/f9-wrong-mapping.json" \
  --l1-rerun-summary "$TMP_DIR/l1.json" \
  --output "$TMP_DIR/wrong-mapping-manifest.json" >/dev/null
python3 - "$TMP_DIR/wrong-mapping-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf8"))
if "F9" in manifest["fixtures_pair_eligible"]:
    raise SystemExit("F9 must not be included when solo_claude is absent from _blind_mapping")
if manifest["selection_rule"]["f9_included"] is not False:
    raise SystemExit("expected f9_included false for wrong mapping")
PY

write_f9 "$TMP_DIR/f9-dq.json" "solo_claude" true
python3 "$BUILD" \
  --c1-summary "$TMP_DIR/c1.json" \
  --f9-judge "$TMP_DIR/f9-dq.json" \
  --l1-rerun-summary "$TMP_DIR/l1.json" \
  --output "$TMP_DIR/dq-manifest.json" >/dev/null
python3 - "$TMP_DIR/dq-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf8"))
if "F9" in manifest["fixtures_pair_eligible"]:
    raise SystemExit("F9 must not be included when solo_claude is disqualified")
PY

cat > "$TMP_DIR/f9-malformed-mapping.json" <<'JSON'
{
  "a_score": 91,
  "b_score": 76,
  "_blind_mapping": "not-a-dict",
  "scores_by_arm": {"solo_claude": 91, "bare": 76},
  "disqualifiers": {"A": false, "B": false},
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false}
  }
}
JSON
python3 "$BUILD" \
  --c1-summary "$TMP_DIR/c1.json" \
  --f9-judge "$TMP_DIR/f9-malformed-mapping.json" \
  --l1-rerun-summary "$TMP_DIR/l1.json" \
  --output "$TMP_DIR/malformed-mapping-manifest.json" >/dev/null
python3 - "$TMP_DIR/malformed-mapping-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf8"))
if "F9" in manifest["fixtures_pair_eligible"]:
    raise SystemExit("F9 must not be included when _blind_mapping is malformed")
if manifest["selection_rule"]["f9_included"] is not False:
    raise SystemExit("expected f9_included false for malformed mapping")
PY

cat > "$TMP_DIR/f9-malformed-scores.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "seed": 1},
  "scores_by_arm": ["not", "a", "dict"],
  "disqualifiers": {"A": false, "B": false},
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false}
  }
}
JSON
python3 "$BUILD" \
  --c1-summary "$TMP_DIR/c1.json" \
  --f9-judge "$TMP_DIR/f9-malformed-scores.json" \
  --l1-rerun-summary "$TMP_DIR/l1.json" \
  --output "$TMP_DIR/malformed-scores-manifest.json" >/dev/null
python3 - "$TMP_DIR/malformed-scores-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf8"))
if "F9" in manifest["fixtures_pair_eligible"]:
    raise SystemExit("F9 must not be included when scores_by_arm is malformed and no legacy scores exist")
if manifest["selection_rule"]["f9_included"] is not False:
    raise SystemExit("expected f9_included false for malformed scores")
PY

cat > "$TMP_DIR/f9-overrange-scores.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "seed": 1},
  "scores_by_arm": {"solo_claude": 101, "bare": 76},
  "a_score": 101,
  "b_score": 76,
  "disqualifiers": {"A": false, "B": false},
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false}
  }
}
JSON
python3 "$BUILD" \
  --c1-summary "$TMP_DIR/c1.json" \
  --f9-judge "$TMP_DIR/f9-overrange-scores.json" \
  --l1-rerun-summary "$TMP_DIR/l1.json" \
  --output "$TMP_DIR/overrange-scores-manifest.json" >/dev/null
python3 - "$TMP_DIR/overrange-scores-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf8"))
if manifest["selection_rule"]["f9_included"] is not False:
    raise SystemExit("F9 must not be included when mapped scores are out of range")
PY

cat > "$TMP_DIR/f9-boolean-scores.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "seed": 1},
  "scores_by_arm": {"solo_claude": true, "bare": 0},
  "a_score": true,
  "b_score": 0,
  "disqualifiers": {"A": false, "B": false},
  "disqualifiers_by_arm": {
    "solo_claude": {"disqualifier": false},
    "bare": {"disqualifier": false}
  }
}
JSON
python3 "$BUILD" \
  --c1-summary "$TMP_DIR/c1.json" \
  --f9-judge "$TMP_DIR/f9-boolean-scores.json" \
  --l1-rerun-summary "$TMP_DIR/l1.json" \
  --output "$TMP_DIR/boolean-scores-manifest.json" >/dev/null
python3 - "$TMP_DIR/boolean-scores-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf8"))
if manifest["selection_rule"]["f9_included"] is not False:
    raise SystemExit("F9 must not be included when mapped scores are booleans")
PY

cat > "$TMP_DIR/f9-malformed-dq.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "seed": 1},
  "scores_by_arm": {"solo_claude": 91, "bare": 76},
  "disqualifiers": ["not", "a", "dict"],
  "disqualifiers_by_arm": ["not", "a", "dict"]
}
JSON
python3 "$BUILD" \
  --c1-summary "$TMP_DIR/c1.json" \
  --f9-judge "$TMP_DIR/f9-malformed-dq.json" \
  --l1-rerun-summary "$TMP_DIR/l1.json" \
  --output "$TMP_DIR/malformed-dq-manifest.json" >/dev/null
python3 - "$TMP_DIR/malformed-dq-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf8"))
if "F9" in manifest["fixtures_pair_eligible"]:
    raise SystemExit("F9 must not be included when disqualifier maps are malformed")
if manifest["selection_rule"]["f9_included"] is not False:
    raise SystemExit("malformed disqualifier maps must fail closed before registry filtering")
PY

cat > "$TMP_DIR/f9-malformed-dq-entry.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "seed": 1},
  "scores_by_arm": {"solo_claude": 91, "bare": 76},
  "disqualifiers": {"A": false, "B": false},
  "disqualifiers_by_arm": {"solo_claude": true}
}
JSON
python3 "$BUILD" \
  --c1-summary "$TMP_DIR/c1.json" \
  --f9-judge "$TMP_DIR/f9-malformed-dq-entry.json" \
  --l1-rerun-summary "$TMP_DIR/l1.json" \
  --output "$TMP_DIR/malformed-dq-entry-manifest.json" >/dev/null
python3 - "$TMP_DIR/malformed-dq-entry-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf8"))
if "F9" in manifest["fixtures_pair_eligible"]:
    raise SystemExit("truthy malformed disqualifier entry must exclude F9")
PY

cat > "$TMP_DIR/f9-string-dq-entry.json" <<'JSON'
{
  "_blind_mapping": {"A": "solo_claude", "B": "bare", "seed": 1},
  "scores_by_arm": {"solo_claude": 91, "bare": 76},
  "disqualifiers": {"A": false, "B": false},
  "disqualifiers_by_arm": {"solo_claude": {"disqualifier": "false"}}
}
JSON
python3 "$BUILD" \
  --c1-summary "$TMP_DIR/c1.json" \
  --f9-judge "$TMP_DIR/f9-string-dq-entry.json" \
  --l1-rerun-summary "$TMP_DIR/l1.json" \
  --output "$TMP_DIR/string-dq-entry-manifest.json" >/dev/null
python3 - "$TMP_DIR/string-dq-entry-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf8"))
if manifest["selection_rule"]["f9_included"] is not False:
    raise SystemExit("string disqualifier entry must fail closed")
PY

python3 - "$BUILD" <<'PY'
import importlib.util
import pathlib
import sys
import tempfile

spec = importlib.util.spec_from_file_location("build_pair_eligible_manifest", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
reasons = module.load_rejected_fixture_reasons(module.REJECTED_REGISTRY)
assert reasons["F31"] == "solo_claude scored 98 with bare disqualifiers in 20260512-f31-seat-rebalance-headroom"
assert reasons["F32"] == "bare 33 / solo_claude 98 in 20260512-f32-subscription-renewal-headroom"
assert reasons["S3"] == "bare 33 / solo_claude 99 with solo timeout in 20260513-s3-ticket-headroom"
with tempfile.TemporaryDirectory() as tmp:
    registry = pathlib.Path(tmp) / "pair-rejected-fixtures.sh"
    registry.write_text(
        'rejected_pair_fixture_reason() {\n'
        '  case "$1" in\n'
        '    S3-*|S3)\n'
        '      echo "shadow solo ceiling"\n'
        '      ;;\n'
        '    *) return 1 ;;\n'
        '  esac\n'
        '}\n',
        encoding="utf8",
    )
    assert module.load_rejected_fixture_reasons(registry) == {"S3": "shadow solo ceiling"}
PY

echo "PASS test-build-pair-eligible-manifest"
