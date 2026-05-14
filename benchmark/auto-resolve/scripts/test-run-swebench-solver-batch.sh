#!/usr/bin/env bash
# Regression tests for run-swebench-solver-batch.sh argument guards.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNNER="$SCRIPT_DIR/run-swebench-solver-batch.sh"
TMP_DIR="$(mktemp -d /tmp/run-swebench-solver-batch-test.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT
FAKEBIN="$TMP_DIR/fakebin"
mkdir -p "$FAKEBIN"
cat > "$FAKEBIN/claude" <<'EOF'
#!/usr/bin/env bash
echo "fake claude should not be reached" >&2
exit 1
EOF
chmod +x "$FAKEBIN/claude"

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
  if ! grep -Fq -- "$needle" "$out"; then
    echo "missing expected text for $label: $needle" >&2
    cat "$out" >&2
    exit 1
  fi
}

bash "$RUNNER" --help > "$TMP_DIR/help.out" 2>&1
grep -Fq 'usage:' "$TMP_DIR/help.out"
grep -Fq -- '--instances-jsonl <path>' "$TMP_DIR/help.out"
grep -Fq -- '--predictions-out <path>' "$TMP_DIR/help.out"
grep -Fq -- '--timeout-seconds N' "$TMP_DIR/help.out"
grep -Fq 'require_value()' "$RUNNER"

expect_fail_contains missing-instances-jsonl-value \
  '--instances-jsonl requires a value' \
  bash "$RUNNER" --instances-jsonl

expect_fail_contains missing-predictions-out-value \
  '--predictions-out requires a value' \
  bash "$RUNNER" --instances-jsonl "$TMP_DIR/instances.jsonl" --predictions-out

expect_fail_contains missing-model-name-value \
  '--model-name requires a value' \
  bash "$RUNNER" --instances-jsonl "$TMP_DIR/instances.jsonl" --predictions-out "$TMP_DIR/predictions.jsonl" --model-name

expect_fail_contains missing-repos-root-value \
  '--repos-root requires a value' \
  bash "$RUNNER" --instances-jsonl "$TMP_DIR/instances.jsonl" --predictions-out "$TMP_DIR/predictions.jsonl" --repos-root

expect_fail_contains missing-worktrees-root-value \
  '--worktrees-root requires a value' \
  bash "$RUNNER" --instances-jsonl "$TMP_DIR/instances.jsonl" --predictions-out "$TMP_DIR/predictions.jsonl" --worktrees-root

expect_fail_contains missing-timeout-value \
  '--timeout-seconds requires a value' \
  bash "$RUNNER" --instances-jsonl "$TMP_DIR/instances.jsonl" --predictions-out "$TMP_DIR/predictions.jsonl" --timeout-seconds

expect_fail_contains missing-limit-value \
  '--limit requires a value' \
  bash "$RUNNER" --instances-jsonl "$TMP_DIR/instances.jsonl" --predictions-out "$TMP_DIR/predictions.jsonl" --limit

expect_fail_contains missing-instance-id-value \
  '--instance-id requires a value' \
  bash "$RUNNER" --instances-jsonl "$TMP_DIR/instances.jsonl" --predictions-out "$TMP_DIR/predictions.jsonl" --instance-id

touch "$TMP_DIR/instances.jsonl"
expect_fail_contains invalid-timeout \
  '--timeout-seconds must be an integer' \
  bash "$RUNNER" --instances-jsonl "$TMP_DIR/instances.jsonl" --predictions-out "$TMP_DIR/predictions.jsonl" --timeout-seconds nope

expect_fail_contains zero-timeout \
  '--timeout-seconds must be > 0' \
  bash "$RUNNER" --instances-jsonl "$TMP_DIR/instances.jsonl" --predictions-out "$TMP_DIR/predictions.jsonl" --timeout-seconds 0

expect_fail_contains invalid-limit \
  '--limit must be an integer' \
  bash "$RUNNER" --instances-jsonl "$TMP_DIR/instances.jsonl" --predictions-out "$TMP_DIR/predictions.jsonl" --limit nope

expect_fail_contains zero-limit \
  '--limit must be > 0' \
  bash "$RUNNER" --instances-jsonl "$TMP_DIR/instances.jsonl" --predictions-out "$TMP_DIR/predictions.jsonl" --limit 0

expect_fail_contains missing-claude \
  'claude command not found' \
  env PATH="/usr/bin:/bin" bash "$RUNNER" --instances-jsonl "$TMP_DIR/instances.jsonl" --predictions-out "$TMP_DIR/predictions.jsonl"

printf '[]\n' > "$TMP_DIR/non-object-instances.jsonl"
expect_fail_contains non-object-instance-row \
  'expected JSON object' \
  env PATH="$FAKEBIN:/usr/bin:/bin" bash "$RUNNER" --instances-jsonl "$TMP_DIR/non-object-instances.jsonl" --predictions-out "$TMP_DIR/predictions.jsonl"

printf '{"instance_id": NaN}\n' > "$TMP_DIR/nan-instances.jsonl"
expect_fail_contains nan-instance-row \
  'invalid JSON numeric constant: NaN' \
  env PATH="$FAKEBIN:/usr/bin:/bin" bash "$RUNNER" --instances-jsonl "$TMP_DIR/nan-instances.jsonl" --predictions-out "$TMP_DIR/predictions.jsonl"

printf '{"repo":"local/repo"}\n' > "$TMP_DIR/missing-id-instances.jsonl"
expect_fail_contains missing-instance-id-row \
  'missing instance_id' \
  env PATH="$FAKEBIN:/usr/bin:/bin" bash "$RUNNER" --instances-jsonl "$TMP_DIR/missing-id-instances.jsonl" --predictions-out "$TMP_DIR/predictions.jsonl"

echo "PASS test-run-swebench-solver-batch"
