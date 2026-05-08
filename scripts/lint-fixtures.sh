#!/usr/bin/env bash
# lint-fixtures.sh — schema validity + structural check for golden fixtures/.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIXTURES_DIR="$REPO_ROOT/benchmark/auto-resolve/fixtures"
SCHEMA="$REPO_ROOT/config/skills/_shared/expected.schema.json"

[ -d "$FIXTURES_DIR" ] || { echo "✗ $FIXTURES_DIR missing"; exit 1; }
[ -f "$SCHEMA" ] || { echo "✗ $SCHEMA missing"; exit 1; }

REQUIRED_FILES=(metadata.json spec.md task.txt expected.json setup.sh NOTES.md)

ERRORS=0
COUNT=0

for d in "$FIXTURES_DIR"/F*/; do
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
    if ! python3 -c "import json; json.load(open('$d/expected.json'))" 2>/dev/null; then
      echo "✗ $fid: expected.json is not valid JSON"
      ERRORS=$((ERRORS + 1))
      continue
    fi

    n_cmds=$(python3 -c "import json; print(len(json.load(open('$d/expected.json')).get('verification_commands', [])))")
    if [ "$n_cmds" -lt 1 ]; then
      echo "✗ $fid: expected.json has 0 verification_commands (need ≥1)"
      ERRORS=$((ERRORS + 1))
    fi

    python3 - "$SCHEMA" "$d/expected.json" "$fid" <<'PY' || ERRORS=$((ERRORS + 1))
import json, sys
schema_path, expected_path, fid = sys.argv[1], sys.argv[2], sys.argv[3]
schema = json.load(open(schema_path))
data = json.load(open(expected_path))
try:
    import jsonschema
except ImportError:
    allowed = set(schema["properties"])
    unknown = sorted(set(data) - allowed)
    if unknown:
        print(f"✗ {fid}: expected.json has unknown key(s): {', '.join(unknown)}")
        sys.exit(1)
else:
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        print(f"✗ {fid}: expected.json schema violation: {e.message}")
        sys.exit(1)
PY

    python3 - "$d/spec.md" "$d/expected.json" "$fid" <<'PY' || ERRORS=$((ERRORS + 1))
import json, sys
spec_path, expected_path, fid = sys.argv[1], sys.argv[2], sys.argv[3]
spec = open(spec_path, encoding="utf-8").read()
expected = json.load(open(expected_path, encoding="utf-8"))
errors = []
for idx, command in enumerate(expected.get("verification_commands", [])):
    cmd = str(command.get("cmd", ""))
    if "BENCH_FIXTURE_DIR" not in cmd:
        continue
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

  if [ -f "$d/setup.sh" ] && [ ! -x "$d/setup.sh" ]; then
    echo "✗ $fid: setup.sh not executable (run: chmod +x $d/setup.sh)"
    ERRORS=$((ERRORS + 1))
  fi
done

if [ $COUNT -eq 0 ]; then
  echo "✗ no fixtures found in $FIXTURES_DIR"
  exit 1
fi

if [ $ERRORS -gt 0 ]; then
  echo ""
  echo "✗ lint-fixtures: $ERRORS error(s) across $COUNT fixture(s)"
  exit 1
fi

echo "✓ lint-fixtures: $COUNT fixture(s) passed schema + structural checks"
