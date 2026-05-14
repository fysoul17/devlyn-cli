#!/usr/bin/env bash
# lint-fixtures.sh — schema validity + structural check for golden fixtures/.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIXTURES_DIR="${DEVLYN_FIXTURES_DIR:-$REPO_ROOT/benchmark/auto-resolve/fixtures}"
FIXTURE_GLOB="${DEVLYN_FIXTURE_GLOB:-F*}"
RETIRED_FIXTURE_GLOB="${DEVLYN_RETIRED_FIXTURE_GLOB:-F*}"
REJECTED_REGISTRY="${DEVLYN_REJECTED_FIXTURE_REGISTRY:-$REPO_ROOT/benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh}"
SCHEMA="${DEVLYN_EXPECTED_SCHEMA:-$REPO_ROOT/config/skills/_shared/expected.schema.json}"
SPEC_VERIFY_CHECK="$REPO_ROOT/config/skills/_shared/spec-verify-check.py"
SOLO_HEADROOM_CHECK="$REPO_ROOT/benchmark/auto-resolve/scripts/solo-headroom-hypothesis.py"

[ -d "$FIXTURES_DIR" ] || { echo "✗ $FIXTURES_DIR missing"; exit 1; }
[ -f "$SCHEMA" ] || { echo "✗ $SCHEMA missing"; exit 1; }
[ -f "$SPEC_VERIFY_CHECK" ] || { echo "✗ $SPEC_VERIFY_CHECK missing"; exit 1; }
[ -f "$SOLO_HEADROOM_CHECK" ] || { echo "✗ solo-headroom checker missing: $SOLO_HEADROOM_CHECK"; exit 1; }
[ -f "$REJECTED_REGISTRY" ] || { echo "✗ rejected fixture registry missing: $REJECTED_REGISTRY"; exit 1; }

# shellcheck source=/dev/null
source "$REJECTED_REGISTRY"
if ! declare -F rejected_pair_fixture_reason >/dev/null; then
  echo "✗ rejected fixture registry must define rejected_pair_fixture_reason: $REJECTED_REGISTRY"
  exit 1
fi

REQUIRED_FILES=(metadata.json spec.md task.txt expected.json setup.sh NOTES.md)

ERRORS=0
COUNT=0
RETIRED_COUNT=0

for d in "$FIXTURES_DIR"/$FIXTURE_GLOB/; do
  [ -d "$d" ] || continue
  COUNT=$((COUNT + 1))
  fid="$(basename "$d")"

  for f in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$d/$f" ]; then
      echo "✗ $fid: missing $f"
      ERRORS=$((ERRORS + 1))
    fi
  done

  if [ -f "$d/metadata.json" ]; then
    meta_id=$(python3 -c "import json,sys; print(json.load(open('$d/metadata.json'))['id'])" 2>/dev/null || echo "")
    if [ "$meta_id" != "$fid" ]; then
      echo "✗ $fid: metadata.json id='$meta_id' does not match dir name"
      ERRORS=$((ERRORS + 1))
    fi

    python3 - "$d/metadata.json" "$d/spec.md" "$fid" <<'PY' || ERRORS=$((ERRORS + 1))
import json
import re
import sys

metadata_path, spec_path, fid = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    metadata = json.load(open(metadata_path, encoding="utf-8"))
except Exception:
    sys.exit(0)
if metadata.get("category") != "high-risk":
    sys.exit(0)
intent = str(metadata.get("intent") or "")
try:
    spec = open(spec_path, encoding="utf-8").read()
except FileNotFoundError:
    spec = ""
text = f"{intent}\n{spec}".lower()
risk_pattern = re.compile(
    r"\b("
    r"auth|authz|permissions?|security|tokens?|sessions?|"
    r"payments?|money|billing|invoices?|pricing|tax|ledger|"
    r"persistence|persist\w*|data mutation|delet\w*|migrations?|"
    r"idempoten\w*|replay|duplicates?|api|webhook|raw-body|signatures?|"
    r"allocation|scheduling|inventory|rollback|transaction|"
    r"priority|error-priority|output-shape|output shape|response-shape|response shape"
    r")\b"
)
if not risk_pattern.search(text):
    print(
        f"✗ {fid}: high-risk fixture must include a resolve risk-trigger term "
        "in metadata intent or spec.md"
    )
    sys.exit(1)
PY
  fi

  if [ -f "$d/spec.md" ]; then
    spec_id=$(python3 - "$d/spec.md" <<'PY' 2>/dev/null || true
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r'^id:\s*"?([^"\n]+)"?\s*$', text, re.M)
print(m.group(1) if m else "")
PY
)
    if [ "$spec_id" != "$fid" ]; then
      echo "✗ $fid: spec.md frontmatter id='$spec_id' does not match dir name"
      ERRORS=$((ERRORS + 1))
    fi
  fi

  if [ -f "$d/expected.json" ]; then
    if ! python3 - "$d/expected.json" "$fid" <<'PY'
import json
import sys

expected_path, fid = sys.argv[1], sys.argv[2]
try:
    data = json.load(open(expected_path, encoding="utf-8"))
except json.JSONDecodeError:
    print(f"✗ {fid}: expected.json is not valid JSON")
    sys.exit(1)
if not isinstance(data, dict):
    print(f"✗ {fid}: expected.json must be an object")
    sys.exit(1)
PY
    then
      ERRORS=$((ERRORS + 1))
      continue
    fi

    n_cmds=$(python3 - "$d/expected.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
commands = data.get("verification_commands", [])
print(len(commands) if isinstance(commands, list) else 0)
PY
)
    if [ "$n_cmds" -lt 1 ]; then
      echo "✗ $fid: expected.json has 0 verification_commands (need ≥1)"
      ERRORS=$((ERRORS + 1))
    fi

    schema_ok=1
    if ! python3 - "$SCHEMA" "$d/expected.json" "$fid" <<'PY'
import json, os, sys
schema_path, expected_path, fid = sys.argv[1], sys.argv[2], sys.argv[3]
schema = json.load(open(schema_path))
data = json.load(open(expected_path))

def is_string_list(value):
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value)

def fallback_validate():
    allowed = set(schema["properties"])
    errors = []
    if not isinstance(data, dict):
        return ["expected.json must be an object"]
    unknown = sorted(set(data) - allowed)
    if unknown:
        errors.append(f"expected.json has unknown key(s): {', '.join(unknown)}")
    commands = data.get("verification_commands", [])
    if not isinstance(commands, list):
        errors.append("verification_commands must be an array")
    else:
        for idx, command in enumerate(commands):
            if not isinstance(command, dict):
                errors.append(f"verification_commands[{idx}] must be an object")
                continue
            unknown_command = sorted(set(command) - {"cmd", "exit_code", "stdout_contains", "stdout_not_contains", "contract_refs"})
            if unknown_command:
                errors.append(f"verification_commands[{idx}] has unknown key(s): {', '.join(unknown_command)}")
            if not isinstance(command.get("cmd"), str) or not command.get("cmd"):
                errors.append(f"verification_commands[{idx}].cmd must be a non-empty string")
            exit_code = command.get("exit_code", 0)
            if isinstance(exit_code, bool) or not isinstance(exit_code, int):
                errors.append(f"verification_commands[{idx}].exit_code must be an integer")
            for key in ("stdout_contains", "stdout_not_contains", "contract_refs"):
                if key in command and not is_string_list(command[key]):
                    errors.append(f"verification_commands[{idx}].{key} must be an array of non-empty strings")
    patterns = data.get("forbidden_patterns", [])
    if not isinstance(patterns, list):
        errors.append("forbidden_patterns must be an array")
    else:
        for idx, pattern in enumerate(patterns):
            if not isinstance(pattern, dict):
                errors.append(f"forbidden_patterns[{idx}] must be an object")
                continue
            unknown_pattern = sorted(set(pattern) - {"pattern", "description", "files", "severity"})
            if unknown_pattern:
                errors.append(f"forbidden_patterns[{idx}] has unknown key(s): {', '.join(unknown_pattern)}")
            for key in ("pattern", "description"):
                if not isinstance(pattern.get(key), str) or not pattern.get(key):
                    errors.append(f"forbidden_patterns[{idx}].{key} must be a non-empty string")
            if pattern.get("severity") not in {"disqualifier", "warning"}:
                errors.append(f"forbidden_patterns[{idx}].severity must be disqualifier or warning")
            if "files" in pattern and not is_string_list(pattern["files"]):
                errors.append(f"forbidden_patterns[{idx}].files must be an array of non-empty strings")
    for key in ("required_files", "forbidden_files", "tier_a_waivers", "spec_output_files"):
        if key in data and not is_string_list(data[key]):
            errors.append(f"{key} must be an array of non-empty strings")
    max_deps_added = data.get("max_deps_added", 0)
    if isinstance(max_deps_added, bool) or not isinstance(max_deps_added, int) or max_deps_added < 0:
        errors.append("max_deps_added must be an integer >= 0")
    return errors

force_fallback = os.environ.get("DEVLYN_LINT_FIXTURES_NO_JSONSCHEMA") == "1"
try:
    if force_fallback:
        raise ImportError
    import jsonschema
except ImportError:
    fallback_errors = fallback_validate()
    if fallback_errors:
        for error in fallback_errors:
            print(f"✗ {fid}: expected.json schema violation: {error}")
        sys.exit(1)
else:
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        print(f"✗ {fid}: expected.json schema violation: {e.message}")
        sys.exit(1)
PY
    then
      ERRORS=$((ERRORS + 1))
      schema_ok=0
    fi

    if [ "$schema_ok" -eq 1 ]; then
      if ! python3 "$SPEC_VERIFY_CHECK" --check "$d/spec.md"; then
        echo "✗ $fid: spec-verify-check --check failed"
        ERRORS=$((ERRORS + 1))
      fi
      if ! python3 "$SPEC_VERIFY_CHECK" --check-expected "$d/expected.json"; then
        echo "✗ $fid: spec-verify-check --check-expected failed"
        ERRORS=$((ERRORS + 1))
      fi

      python3 - "$d/spec.md" "$d/expected.json" "$fid" <<'PY' || ERRORS=$((ERRORS + 1))
import json, pathlib, re, sys
spec_path, expected_path, fid = sys.argv[1], sys.argv[2], sys.argv[3]
spec = open(spec_path, encoding="utf-8").read()
expected = json.load(open(expected_path, encoding="utf-8"))
fixture_dir = pathlib.Path(expected_path).parent
fixture_root = fixture_dir.resolve()
errors = []
for idx, command in enumerate(expected.get("verification_commands", [])):
    cmd = str(command.get("cmd", ""))
    if "BENCH_FIXTURE_DIR" not in cmd:
        continue
    fixture_refs = re.findall(r"(?:\$\{BENCH_FIXTURE_DIR\}|\$BENCH_FIXTURE_DIR)/([^\"'\s]+)", cmd)
    if not fixture_refs:
        errors.append(
            f"verification_commands[{idx}] hidden oracle must reference an explicit $BENCH_FIXTURE_DIR/... file"
        )
    stdout_contains = command.get("stdout_contains", [])
    if '"ok":true' not in stdout_contains:
        errors.append(
            f"verification_commands[{idx}] hidden oracle must assert stdout_contains includes '\"ok\":true'"
        )
    for fixture_ref in fixture_refs:
        target = (fixture_dir / fixture_ref).resolve(strict=False)
        try:
            target.relative_to(fixture_root)
        except ValueError:
            errors.append(
                f"verification_commands[{idx}] BENCH_FIXTURE_DIR file escapes fixture dir: {fixture_ref!r}"
            )
            continue
        if not target.is_file():
            errors.append(
                f"verification_commands[{idx}] BENCH_FIXTURE_DIR file not found: {fixture_ref!r}"
            )
    refs = command.get("contract_refs", [])
    if not refs:
        errors.append(f"verification_commands[{idx}] hidden oracle missing contract_refs")
        continue
    for ref in refs:
        if ref not in spec:
            errors.append(
                f"verification_commands[{idx}] contract_ref not found in spec.md: {ref!r}"
            )
if errors:
    for err in errors:
        print(f"✗ {fid}: {err}")
    sys.exit(1)
PY
    fi
  fi

  if [ -f "$d/setup.sh" ] && [ ! -x "$d/setup.sh" ]; then
    echo "✗ $fid: setup.sh not executable (run: chmod +x $d/setup.sh)"
    ERRORS=$((ERRORS + 1))
  fi

  if [ -f "$d/NOTES.md" ] \
     && { { grep -Fq 'headroom gate' "$d/NOTES.md" && grep -Eq '`?FAIL`?' "$d/NOTES.md"; } \
       || { grep -Fq 'pair-lift evidence' "$d/NOTES.md" && grep -Eiq 'reject|rejected' "$d/NOTES.md"; }; } \
     && ! rejected_pair_fixture_reason "$fid" >/dev/null 2>&1; then
    echo "✗ $fid: NOTES.md records pair-candidate rejection but pair-rejected-fixtures.sh has no rejected reason"
    ERRORS=$((ERRORS + 1))
  fi

  if [ -f "$d/NOTES.md" ] \
     && grep -Fq 'pair_evidence_passed' "$d/NOTES.md" \
     && ! python3 "$SOLO_HEADROOM_CHECK" --expected-json "$d/expected.json" "$d/spec.md"; then
    echo "✗ $fid: pair_evidence_passed fixture spec.md must document an actionable solo-headroom hypothesis with solo_claude miss and observable command from expected.json"
    ERRORS=$((ERRORS + 1))
  fi
done

for d in "$FIXTURES_DIR"/retired/$RETIRED_FIXTURE_GLOB/; do
  [ -d "$d" ] || continue
  RETIRED_COUNT=$((RETIRED_COUNT + 1))
  fid="$(basename "$d")"

  if [ ! -f "$d/RETIRED.md" ]; then
    echo "✗ retired/$fid: missing RETIRED.md"
    ERRORS=$((ERRORS + 1))
  fi

  for f in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$d/$f" ]; then
      echo "✗ retired/$fid: missing preserved $f"
      ERRORS=$((ERRORS + 1))
    fi
  done

  if [ -f "$d/metadata.json" ]; then
    meta_id=$(python3 -c "import json,sys; print(json.load(open('$d/metadata.json'))['id'])" 2>/dev/null || echo "")
    if [ "$meta_id" != "$fid" ]; then
      echo "✗ retired/$fid: metadata.json id='$meta_id' does not match dir name"
      ERRORS=$((ERRORS + 1))
    fi
  fi

  if [ -f "$d/setup.sh" ] && [ ! -x "$d/setup.sh" ]; then
    echo "✗ retired/$fid: setup.sh not executable (run: chmod +x $d/setup.sh)"
    ERRORS=$((ERRORS + 1))
  fi
done

if [ $COUNT -eq 0 ]; then
  echo "✗ no fixtures found in $FIXTURES_DIR"
  exit 1
fi

if [ $ERRORS -gt 0 ]; then
  echo ""
  echo "✗ lint-fixtures: $ERRORS error(s) across $COUNT active fixture(s) and $RETIRED_COUNT retired fixture(s)"
  exit 1
fi

echo "✓ lint-fixtures: $COUNT active fixture(s) passed schema + structural checks; $RETIRED_COUNT retired fixture(s) preserved"
