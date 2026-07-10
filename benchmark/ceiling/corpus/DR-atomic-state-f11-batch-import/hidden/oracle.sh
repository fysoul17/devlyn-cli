#!/usr/bin/env bash
set -euo pipefail

ORACLE_DIR="$(cd "$(dirname "$0")" && pwd)"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/f11-oracle.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

failed=0
invalid=0
check_index=0

run_check() {
  local label="$1"
  local required_text="$2"
  local forbidden_text="$3"
  shift 3

  check_index=$((check_index + 1))
  local stdout_file="$TMP_ROOT/check-${check_index}.stdout"
  local stderr_file="$TMP_ROOT/check-${check_index}.stderr"
  local exit_code

  set +e
  "$@" >"$stdout_file" 2>"$stderr_file"
  exit_code=$?
  set -e

  cat "$stdout_file"
  cat "$stderr_file" >&2

  if [ "$exit_code" -eq 1 ]; then
    echo "oracle check failed: $label" >&2
    failed=1
  elif [ "$exit_code" -ne 0 ]; then
    echo "oracle check runtime invalid: $label (exit $exit_code)" >&2
    [ "$invalid" -ne 0 ] || invalid="$exit_code"
  fi

  if [ -n "$required_text" ] \
    && ! grep -Fq -- "$required_text" "$stdout_file" "$stderr_file"; then
    echo "oracle check missing required output: $label" >&2
    failed=1
  fi
  if [ -n "$forbidden_text" ] \
    && grep -Fq -- "$forbidden_text" "$stdout_file" "$stderr_file"; then
    echo "oracle check emitted forbidden output: $label" >&2
    failed=1
  fi
}

check_forbidden_source() {
  local label="$1"
  local pattern="$2"
  shift 2

  local file flattened="$TMP_ROOT/forbidden-source.txt"
  : >"$flattened"
  for file in "$@"; do
    if [ ! -f "$file" ]; then
      echo "oracle required source missing: $file" >&2
      failed=1
      continue
    fi
    tr '\n' ' ' <"$file" >>"$flattened"
    printf '\n' >>"$flattened"
  done
  if grep -Eq -- "$pattern" "$flattened"; then
    echo "oracle forbidden source pattern: $label" >&2
    failed=1
  fi
}

run_check "server tests" "" "not ok " node --test tests/server.test.js
run_check "failed request leaves store unchanged" '"ok":true' "" \
  node "$ORACLE_DIR/failed-unchanged.js"
run_check "fully valid request succeeds" '"ok":true' "" \
  node "$ORACLE_DIR/success.js"
run_check "invalid body leaves store unchanged" '"ok":true' "" \
  node "$ORACLE_DIR/invalid-body.js"

check_forbidden_source \
  "silent catch returning fallback" \
  "catch[[:space:]]*\\([^)]*\\)[[:space:]]*\\{[^}]*return[[:space:]]+(null|undefined|''|\\{\\})" \
  server/index.js
check_forbidden_source \
  "empty catch block" \
  "catch[[:space:]]*\\([^)]*\\)[[:space:]]*\\{[[:space:]]*\\}" \
  server/index.js

changed_files="$TMP_ROOT/changed-files.txt"
{
  git diff --name-only HEAD --
  git ls-files --others --exclude-standard
} | LC_ALL=C sort -u >"$changed_files"
while IFS= read -r file; do
  [ -n "$file" ] || continue
  case "$file" in
    server/index.js|tests/server.test.js) ;;
    *)
      echo "oracle out-of-scope changed file: $file" >&2
      failed=1
      ;;
  esac
done <"$changed_files"

if [ "$invalid" -ne 0 ]; then
  exit "$invalid"
fi
if [ "$failed" -ne 0 ]; then
  exit 1
fi
