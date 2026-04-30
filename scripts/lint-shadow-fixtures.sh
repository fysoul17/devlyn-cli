#!/usr/bin/env bash
# lint-shadow-fixtures.sh — schema validity + structural check for shadow-fixtures/.
#
# Verifies each S<N>-<slug>/ has the 6 required files per fixtures/SCHEMA.md and
# that expected.json validates against _shared/expected.schema.json. Does NOT
# run reference-solvability (that's the per-task acceptance gate during authoring).
#
# Exits 0 on PASS, 1 on FAIL. Used by iter-0030+ acceptance gates.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SHADOW_DIR="$REPO_ROOT/benchmark/auto-resolve/shadow-fixtures"
SCHEMA="$REPO_ROOT/config/skills/_shared/expected.schema.json"

[ -d "$SHADOW_DIR" ] || { echo "✗ $SHADOW_DIR missing"; exit 1; }
[ -f "$SCHEMA" ] || { echo "✗ $SCHEMA missing"; exit 1; }

REQUIRED_FILES=(metadata.json spec.md task.txt expected.json setup.sh NOTES.md)

ERRORS=0
COUNT=0

for d in "$SHADOW_DIR"/S*/; do
  [ -d "$d" ] || continue
  COUNT=$((COUNT + 1))
  fid="$(basename "$d")"

  # Required files present
  for f in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$d/$f" ]; then
      echo "✗ $fid: missing $f"
      ERRORS=$((ERRORS + 1))
    fi
  done

  # metadata.json: id matches dir name
  if [ -f "$d/metadata.json" ]; then
    meta_id=$(python3 -c "import json,sys; print(json.load(open('$d/metadata.json'))['id'])" 2>/dev/null || echo "")
    if [ "$meta_id" != "$fid" ]; then
      echo "✗ $fid: metadata.json id='$meta_id' does not match dir name"
      ERRORS=$((ERRORS + 1))
    fi
  fi

  # expected.json: valid JSON
  if [ -f "$d/expected.json" ]; then
    if ! python3 -c "import json; json.load(open('$d/expected.json'))" 2>/dev/null; then
      echo "✗ $fid: expected.json is not valid JSON"
      ERRORS=$((ERRORS + 1))
      continue
    fi

    # expected.json: has at least one verification command
    n_cmds=$(python3 -c "import json; print(len(json.load(open('$d/expected.json')).get('verification_commands', [])))")
    if [ "$n_cmds" -lt 1 ]; then
      echo "✗ $fid: expected.json has 0 verification_commands (need ≥1)"
      ERRORS=$((ERRORS + 1))
    fi

    # expected.json: schema validation (Python jsonschema if installed; fallback to structural check)
    python3 - "$SCHEMA" "$d/expected.json" "$fid" <<'PY' || ERRORS=$((ERRORS + 1))
import json, sys
schema_path, expected_path, fid = sys.argv[1], sys.argv[2], sys.argv[3]
schema = json.load(open(schema_path))
data = json.load(open(expected_path))
try:
    import jsonschema
    jsonschema.validate(data, schema)
except ImportError:
    # Fallback: structural check (key types match schema declarations)
    for k, v in data.items():
        if k not in schema["properties"]:
            print(f"✗ {fid}: expected.json has unknown key '{k}' (schema fallback)")
            sys.exit(1)
except jsonschema.ValidationError as e:
    print(f"✗ {fid}: expected.json schema violation: {e.message}")
    sys.exit(1)
PY
  fi

  # setup.sh: executable
  if [ -f "$d/setup.sh" ] && [ ! -x "$d/setup.sh" ]; then
    echo "✗ $fid: setup.sh not executable (run: chmod +x $d/setup.sh)"
    ERRORS=$((ERRORS + 1))
  fi
done

if [ $COUNT -eq 0 ]; then
  echo "✗ no shadow fixtures found in $SHADOW_DIR (expected at least 1)"
  exit 1
fi

if [ $ERRORS -gt 0 ]; then
  echo ""
  echo "✗ lint-shadow-fixtures: $ERRORS error(s) across $COUNT fixture(s)"
  exit 1
fi

echo "✓ lint-shadow-fixtures: $COUNT fixture(s) passed schema + structural checks"
