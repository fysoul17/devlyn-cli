#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

FIXTURES_DIR="$TMP/fixtures"
mkdir -p "$FIXTURES_DIR/F99-riskless-high-risk"
fixture="$FIXTURES_DIR/F99-riskless-high-risk"
CHECKER="$ROOT/benchmark/auto-resolve/scripts/solo-headroom-hypothesis.py"
CEILING_CHECKER="$ROOT/benchmark/auto-resolve/scripts/solo-ceiling-avoidance.py"

cat > "$TMP/weak-hypothesis.md" <<'EOF'
## Solo-headroom hypothesis

A capable solo_claude baseline is expected to miss duplicate idempotency ordering.
EOF
if python3 "$CHECKER" "$TMP/weak-hypothesis.md"; then
  echo "weak hypothesis without observable command must fail" >&2
  exit 1
fi
cat > "$TMP/unrelated-backtick-hypothesis.md" <<'EOF'
## Solo-headroom hypothesis

A capable solo_claude baseline is expected to miss duplicate idempotency ordering; implementation token `idempotency-key`.
EOF
if python3 "$CHECKER" "$TMP/unrelated-backtick-hypothesis.md"; then
  echo "hypothesis with unrelated backtick must fail" >&2
  exit 1
fi
cat > "$TMP/actionable-hypothesis.md" <<'EOF'
## Solo-headroom hypothesis

A capable solo_claude baseline is expected to miss duplicate idempotency ordering; `node -e "process.exit(0)"` exposes the miss.
EOF
python3 "$CHECKER" "$TMP/actionable-hypothesis.md"
cat > "$TMP/docs-style-actionable-hypothesis.md" <<'EOF'
## Solo-headroom hypothesis

Solo-headroom hypothesis: the spec must literally contain `solo_claude`, `miss`, and an observable command; `node -e "process.exit(0)"` exposes the miss.
EOF
python3 "$CHECKER" "$TMP/docs-style-actionable-hypothesis.md"
cat > "$TMP/actionable-expected.json" <<'EOF'
{
  "verification_commands": [
    {
      "cmd": "node -e \"process.exit(0)\"",
      "exit_code": 0
    }
  ]
}
EOF
python3 "$CHECKER" --expected-json "$TMP/actionable-expected.json" "$TMP/actionable-hypothesis.md"
python3 "$CHECKER" --expected-json "$TMP/actionable-expected.json" "$TMP/docs-style-actionable-hypothesis.md"
cat > "$TMP/other-expected.json" <<'EOF'
{
  "verification_commands": [
    {
      "cmd": "node -e \"process.exit(1)\"",
      "exit_code": 1
    }
  ]
}
EOF
if python3 "$CHECKER" --expected-json "$TMP/other-expected.json" "$TMP/actionable-hypothesis.md"; then
  echo "hypothesis command must match expected.json verification command" >&2
  exit 1
fi
printf '\xff\n' > "$TMP/non-utf8-hypothesis.md"
set +e
python3 "$CHECKER" "$TMP/non-utf8-hypothesis.md" > "$TMP/non-utf8-hypothesis.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'expected UTF-8 text' "$TMP/non-utf8-hypothesis.out"

cat > "$TMP/weak-solo-ceiling.md" <<'EOF'
## Solo ceiling avoidance

This candidate mentions solo_claude but gives no control comparison.
EOF
if python3 "$CEILING_CHECKER" "$TMP/weak-solo-ceiling.md"; then
  echo "weak solo ceiling avoidance must fail" >&2
  exit 1
fi
cat > "$TMP/actionable-solo-ceiling.md" <<'EOF'
## Solo ceiling avoidance

Unlike solo-saturated S2-S6 controls, this fixture should preserve
solo_claude headroom because it targets a multi-run state dependency.
EOF
python3 "$CEILING_CHECKER" "$TMP/actionable-solo-ceiling.md"
printf '\xff\n' > "$TMP/non-utf8-solo-ceiling.md"
set +e
python3 "$CEILING_CHECKER" "$TMP/non-utf8-solo-ceiling.md" > "$TMP/non-utf8-solo-ceiling.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'expected UTF-8 text' "$TMP/non-utf8-solo-ceiling.out"

write_fixture() {
  local intent="$1"
  cat > "$fixture/metadata.json" <<EOF
{
  "id": "F99-riskless-high-risk",
  "category": "high-risk",
  "difficulty": "high",
  "timeout_seconds": 900,
  "required_tools": ["node"],
  "browser": false,
  "deps_change_expected": false,
  "intent": "$intent"
}
EOF
  cat > "$fixture/spec.md" <<EOF
---
id: F99-riskless-high-risk
---

# Riskless Fixture

## Context

$intent

## Requirements

- Add the requested behavior.
EOF
  printf '%s\n' "$intent" > "$fixture/task.txt"
  cat > "$fixture/expected.json" <<'EOF'
{
  "verification_commands": [
    {
      "cmd": "node -e \"process.exit(0)\"",
      "exit_code": 0
    }
  ],
  "forbidden_patterns": [],
  "required_files": [],
  "forbidden_files": [],
  "tier_a_waivers": [],
  "spec_output_files": [],
  "max_deps_added": 0
}
EOF
  cat > "$fixture/setup.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
EOF
  chmod +x "$fixture/setup.sh"
  cat > "$fixture/NOTES.md" <<'EOF'
# Notes

Synthetic lint fixture for high-risk trigger validation.
EOF
}

write_fixture "Add a generic CLI helper with clear output."
set +e
DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/fail.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'high-risk fixture must include a resolve risk-trigger term' "$TMP/fail.out"

write_fixture "Add idempotency handling for duplicate requests."
DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/pass.out" 2>&1
grep -Fq '✓ lint-fixtures: 1 active fixture(s) passed schema + structural checks; 0 retired fixture(s) preserved' "$TMP/pass.out"

cat >> "$fixture/NOTES.md" <<'EOF'

## Measurement status

Pair evidence passed in `test-pair-run`: bare `33`, solo_claude `66`, pair `99`,
margin `+33`, wall `1.50x`, arm `l2_risk_probes`, verdict `pair_evidence_passed`.
EOF
set +e
DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/pair-evidence-hypothesis-fail.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'pair_evidence_passed fixture spec.md must document an actionable solo-headroom hypothesis with solo_claude miss and observable command from expected.json' \
  "$TMP/pair-evidence-hypothesis-fail.out"

cat >> "$fixture/spec.md" <<'EOF'

## Solo-headroom hypothesis

A capable solo_claude baseline is expected to miss duplicate idempotency ordering;
observable command `node -e "process.exit(0)"` exposes the miss.
EOF
DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/pair-evidence-hypothesis-pass.out" 2>&1
grep -Fq '✓ lint-fixtures: 1 active fixture(s) passed schema + structural checks; 0 retired fixture(s) preserved' \
  "$TMP/pair-evidence-hypothesis-pass.out"
write_fixture "Add idempotency handling for duplicate requests."

python3 - "$fixture/spec.md" <<'PY'
import pathlib
path = pathlib.Path(__import__("sys").argv[1])
text = path.read_text(encoding="utf-8")
path.write_text(text.replace("---\nid:", "---\ncomplexity: hihg\nid:", 1), encoding="utf-8")
PY
set +e
DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/spec-verify-check-fail.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'spec-verify-check --check failed' "$TMP/spec-verify-check-fail.out"
grep -Fq 'frontmatter complexity must be one of' "$TMP/spec-verify-check-fail.out"
write_fixture "Add idempotency handling for duplicate requests."

cat > "$TMP/malformed-rejected.sh" <<'EOF'
#!/usr/bin/env bash
not_the_registry_function() {
  return 1
}
EOF
set +e
DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" \
DEVLYN_REJECTED_FIXTURE_REGISTRY="$TMP/malformed-rejected.sh" \
  bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/malformed-rejected.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'rejected fixture registry must define rejected_pair_fixture_reason' \
  "$TMP/malformed-rejected.out"

SHADOW_DIR="$TMP/shadow-fixtures"
shadow_fixture="$SHADOW_DIR/S99-riskless-high-risk"
mkdir -p "$shadow_fixture"
cp -R "$fixture/." "$shadow_fixture/"
python3 - "$shadow_fixture" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
for name in ("metadata.json", "spec.md"):
    path = root / name
    path.write_text(path.read_text().replace("F99-riskless-high-risk", "S99-riskless-high-risk"))
PY
DEVLYN_FIXTURES_DIR="$SHADOW_DIR" DEVLYN_FIXTURE_GLOB="S*" \
  bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/shadow-pass.out" 2>&1
grep -Fq '✓ lint-fixtures: 1 active fixture(s) passed schema + structural checks; 0 retired fixture(s) preserved' "$TMP/shadow-pass.out"

cat > "$TMP/empty-rejected.sh" <<'EOF'
#!/usr/bin/env bash
rejected_pair_fixture_reason() {
  return 1
}
EOF
set +e
DEVLYN_SHADOW_FIXTURES_DIR="$SHADOW_DIR" \
DEVLYN_REJECTED_FIXTURE_REGISTRY="$TMP/empty-rejected.sh" \
  bash "$ROOT/scripts/lint-shadow-fixtures.sh" > "$TMP/shadow-missing-hypothesis.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'unmeasured high-risk shadow fixture spec.md must document a solo-headroom hypothesis with solo_claude miss and observable command from expected.json before provider spend' \
  "$TMP/shadow-missing-hypothesis.out"

cat >> "$shadow_fixture/spec.md" <<'EOF'

## Solo-headroom hypothesis

A capable solo_claude baseline is expected to miss duplicate idempotency ordering.
EOF
set +e
DEVLYN_SHADOW_FIXTURES_DIR="$SHADOW_DIR" \
DEVLYN_REJECTED_FIXTURE_REGISTRY="$TMP/empty-rejected.sh" \
  bash "$ROOT/scripts/lint-shadow-fixtures.sh" > "$TMP/shadow-weak-hypothesis.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'solo-headroom hypothesis must include' "$TMP/shadow-weak-hypothesis.out"

cat >> "$shadow_fixture/spec.md" <<'EOF'

Observable command: `node -e "process.exit(0)"` exposes the miss.
EOF
set +e
DEVLYN_SHADOW_FIXTURES_DIR="$SHADOW_DIR" \
DEVLYN_REJECTED_FIXTURE_REGISTRY="$TMP/empty-rejected.sh" \
  bash "$ROOT/scripts/lint-shadow-fixtures.sh" > "$TMP/shadow-missing-solo-ceiling-avoidance.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'unmeasured high-risk shadow fixture NOTES.md must include ## Solo ceiling avoidance' \
  "$TMP/shadow-missing-solo-ceiling-avoidance.out"

cat >> "$shadow_fixture/NOTES.md" <<'EOF'

## Solo ceiling avoidance

This candidate mentions solo_claude but gives no control comparison.
EOF
set +e
DEVLYN_SHADOW_FIXTURES_DIR="$SHADOW_DIR" \
DEVLYN_REJECTED_FIXTURE_REGISTRY="$TMP/empty-rejected.sh" \
  bash "$ROOT/scripts/lint-shadow-fixtures.sh" > "$TMP/shadow-weak-solo-ceiling-avoidance.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'unmeasured high-risk shadow fixture NOTES.md must include ## Solo ceiling avoidance' \
  "$TMP/shadow-weak-solo-ceiling-avoidance.out"

cat >> "$shadow_fixture/NOTES.md" <<'EOF'

This candidate is expected to preserve solo_claude headroom because it differs
from solo-saturated S2-S6 controls by exercising a synthetic hidden invariant.
EOF
DEVLYN_SHADOW_FIXTURES_DIR="$SHADOW_DIR" \
DEVLYN_REJECTED_FIXTURE_REGISTRY="$TMP/empty-rejected.sh" \
  bash "$ROOT/scripts/lint-shadow-fixtures.sh" > "$TMP/shadow-hypothesis-pass.out" 2>&1
grep -Fq '✓ lint-fixtures: 1 active fixture(s) passed schema + structural checks; 0 retired fixture(s) preserved' \
  "$TMP/shadow-hypothesis-pass.out"

cat >> "$shadow_fixture/NOTES.md" <<'EOF'

## Calibration status

- `test-shadow-headroom`: bare `33`, solo_claude `99`, headroom gate FAIL.
EOF
set +e
DEVLYN_SHADOW_FIXTURES_DIR="$SHADOW_DIR" \
DEVLYN_REJECTED_FIXTURE_REGISTRY="$TMP/empty-rejected.sh" \
  bash "$ROOT/scripts/lint-shadow-fixtures.sh" > "$TMP/shadow-calibration-rejected-missing.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'NOTES.md records pair-candidate rejection but pair-rejected-fixtures.sh has no rejected reason' \
  "$TMP/shadow-calibration-rejected-missing.out"

cat > "$TMP/rejected.sh" <<'EOF'
#!/usr/bin/env bash
rejected_pair_fixture_reason() {
  case "$1" in
    F99-*|F99) echo "bare 33 / solo_claude 98 in test-active-headroom" ;;
    S99-*|S99) echo "bare 33 / solo_claude 99 in test-shadow-headroom" ;;
    *) return 1 ;;
  esac
}
EOF
DEVLYN_SHADOW_FIXTURES_DIR="$SHADOW_DIR" \
DEVLYN_REJECTED_FIXTURE_REGISTRY="$TMP/rejected.sh" \
  bash "$ROOT/scripts/lint-shadow-fixtures.sh" > "$TMP/shadow-calibration-rejected-pass.out" 2>&1
grep -Fq '✓ lint-fixtures: 1 active fixture(s) passed schema + structural checks; 0 retired fixture(s) preserved' \
  "$TMP/shadow-calibration-rejected-pass.out"

cat >> "$fixture/NOTES.md" <<'EOF'

## Pair-candidate status

Rejected as pair-lift evidence by `test-active-headroom`: bare scored 33, but
solo_claude scored 98.
EOF
set +e
DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" \
DEVLYN_REJECTED_FIXTURE_REGISTRY="$TMP/empty-rejected.sh" \
  bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/active-calibration-rejected-missing.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'NOTES.md records pair-candidate rejection but pair-rejected-fixtures.sh has no rejected reason' \
  "$TMP/active-calibration-rejected-missing.out"

DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" \
DEVLYN_REJECTED_FIXTURE_REGISTRY="$TMP/rejected.sh" \
  bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/active-calibration-rejected-pass.out" 2>&1
grep -Fq '✓ lint-fixtures: 1 active fixture(s) passed schema + structural checks; 0 retired fixture(s) preserved' \
  "$TMP/active-calibration-rejected-pass.out"

cat > "$fixture/expected.json" <<'EOF'
{
  "verification_commands": [],
  "forbidden_patterns": [],
  "required_files": [],
  "forbidden_files": [],
  "tier_a_waivers": [],
  "spec_output_files": [],
  "max_deps_added": 0
}
EOF
set +e
DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/spec-verify-check-expected-fail.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'spec-verify-check --check-expected failed' "$TMP/spec-verify-check-expected-fail.out"
grep -Fq 'unless sibling spec.md declares all Requirements are pure-design' "$TMP/spec-verify-check-expected-fail.out"

write_fixture "Add idempotency handling for duplicate requests."

mkdir -p "$fixture/verifiers"
printf 'console.log(JSON.stringify({ ok: true }))\n' > "$fixture/verifiers/hidden-oracle.js"

cat > "$fixture/expected.json" <<'EOF'
{
  "verification_commands": [
    {
      "cmd": "node \"$BENCH_FIXTURE_DIR/verifiers/hidden-oracle.js\"",
      "exit_code": 0
    }
  ],
  "forbidden_patterns": [],
  "required_files": [],
  "forbidden_files": [],
  "tier_a_waivers": [],
  "spec_output_files": [],
  "max_deps_added": 0
}
EOF
set +e
DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/missing-contract-refs.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'hidden oracle missing contract_refs' "$TMP/missing-contract-refs.out"

cat > "$fixture/expected.json" <<'EOF'
{
  "verification_commands": [
    {
      "cmd": "node \"$BENCH_FIXTURE_DIR/verifiers/hidden-oracle.js\"",
      "exit_code": 0,
      "contract_refs": ["Add the requested behavior."]
    }
  ],
  "forbidden_patterns": [],
  "required_files": [],
  "forbidden_files": [],
  "tier_a_waivers": [],
  "spec_output_files": [],
  "max_deps_added": 0
}
EOF
set +e
DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/missing-hidden-oracle-sentinel.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq "hidden oracle must assert stdout_contains includes '\"ok\":true'" "$TMP/missing-hidden-oracle-sentinel.out"

cat > "$fixture/expected.json" <<'EOF'
{
  "verification_commands": [
    {
      "cmd": "node \"$BENCH_FIXTURE_DIR/verifiers/hidden-oracle.js\"",
      "exit_code": 0,
      "contract_refs": ["This visible contract is not in the spec."]
    }
  ],
  "forbidden_patterns": [],
  "required_files": [],
  "forbidden_files": [],
  "tier_a_waivers": [],
  "spec_output_files": [],
  "max_deps_added": 0
}
EOF
set +e
DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/bad-contract-ref.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'contract_ref not found in spec.md' "$TMP/bad-contract-ref.out"

printf 'console.log("outside")\n' > "$FIXTURES_DIR/outside-hidden-oracle.js"
cat > "$fixture/expected.json" <<'EOF'
{
  "verification_commands": [
    {
      "cmd": "node \"$BENCH_FIXTURE_DIR/../outside-hidden-oracle.js\"",
      "exit_code": 0,
      "contract_refs": ["Add the requested behavior."]
    }
  ],
  "forbidden_patterns": [],
  "required_files": [],
  "forbidden_files": [],
  "tier_a_waivers": [],
  "spec_output_files": [],
  "max_deps_added": 0
}
EOF
set +e
DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/escaping-hidden-oracle-file.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'BENCH_FIXTURE_DIR file escapes fixture dir' "$TMP/escaping-hidden-oracle-file.out"

cat > "$fixture/expected.json" <<'EOF'
{
  "verification_commands": [
    {
      "cmd": "cd \"$BENCH_FIXTURE_DIR\" && node verifiers/hidden-oracle.js",
      "exit_code": 0,
      "contract_refs": ["Add the requested behavior."]
    }
  ],
  "forbidden_patterns": [],
  "required_files": [],
  "forbidden_files": [],
  "tier_a_waivers": [],
  "spec_output_files": [],
  "max_deps_added": 0
}
EOF
set +e
DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/implicit-hidden-oracle-file.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'hidden oracle must reference an explicit $BENCH_FIXTURE_DIR/... file' "$TMP/implicit-hidden-oracle-file.out"

cat > "$fixture/expected.json" <<'EOF'
{
  "verification_commands": [
    {
      "cmd": "node \"$BENCH_FIXTURE_DIR/verifiers/missing-hidden-oracle.js\"",
      "exit_code": 0,
      "contract_refs": ["Add the requested behavior."]
    }
  ],
  "forbidden_patterns": [],
  "required_files": [],
  "forbidden_files": [],
  "tier_a_waivers": [],
  "spec_output_files": [],
  "max_deps_added": 0
}
EOF
set +e
DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/missing-hidden-oracle-file.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'BENCH_FIXTURE_DIR file not found' "$TMP/missing-hidden-oracle-file.out"

cat > "$fixture/expected.json" <<'EOF'
{
  "verification_commands": "node -e \"process.exit(0)\"",
  "forbidden_patterns": [],
  "required_files": [],
  "forbidden_files": [],
  "tier_a_waivers": [],
  "spec_output_files": [],
  "max_deps_added": 0
}
EOF
set +e
DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" DEVLYN_LINT_FIXTURES_NO_JSONSCHEMA=1 \
  bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/fallback-fail.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'verification_commands must be an array' "$TMP/fallback-fail.out"
if grep -Fq 'Traceback' "$TMP/fallback-fail.out"; then
  echo "fallback schema failure must not continue into traceback-prone checks" >&2
  cat "$TMP/fallback-fail.out" >&2
  exit 1
fi

cat > "$fixture/expected.json" <<'EOF'
[]
EOF
set +e
DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" bash "$ROOT/scripts/lint-fixtures.sh" > "$TMP/non-object-fail.out" 2>&1
status=$?
set -e
[ "$status" -ne 0 ]
grep -Fq 'expected.json must be an object' "$TMP/non-object-fail.out"
if grep -Fq 'Traceback' "$TMP/non-object-fail.out"; then
  echo "non-object expected.json failure must not emit Traceback" >&2
  cat "$TMP/non-object-fail.out" >&2
  exit 1
fi

echo "PASS test-lint-fixtures"
