#!/usr/bin/env bash
# Mechanical pass/fail check for the Tilebridge task.
# Usage: oracle.sh [repo_root]   (defaults to $PWD)
set -u

ROOT="${1:-$PWD}"
cd "$ROOT" || { echo "FAIL: cannot enter repo root: $ROOT" >&2; exit 1; }

fail() { echo "FAIL: $*" >&2; exit 1; }

# ---------------------------------------------------------------- leg 1: suite
python3 - <<'PY' || fail "test discovery collected no tests"
import sys, unittest
suite = unittest.defaultTestLoader.discover("tests")
count = suite.countTestCases()
print("discovered %d test(s)" % count)
sys.exit(0 if count >= 1 else 1)
PY

python3 -m unittest discover -s tests >/dev/null 2>&1 || fail "the test suite does not pass"

# ------------------------------------ leg 2: schema, migrated vault, fresh index
python3 - <<'PY' || fail "task outcomes not satisfied (see messages above)"
import copy
import json
import sys

import vault.schema as schema
from tools.build_index import build_index
from vault.migrate import apply_migrations
from vault.store import load_vault

errors = []

if schema.SCHEMA_VERSION != 3:
    errors.append("vault.schema.SCHEMA_VERSION is %r, expected 3" % (schema.SCHEMA_VERSION,))

targets = [target for target, _ in schema.MIGRATIONS]
if targets != [2, 3]:
    errors.append("MIGRATIONS target versions are %r, expected [2, 3]" % (targets,))

vault_db = load_vault("data/notes.json")

if vault_db.get("schema_version") != 3:
    errors.append(
        "data/notes.json is at schema_version %r, expected 3 (vault not migrated)"
        % (vault_db.get("schema_version"),)
    )

expected_counts = {"n-1": 7, "n-2": 10, "n-3": 2}
notes = {note["id"]: note for note in vault_db.get("notes", [])}
if sorted(notes) != ["n-1", "n-2", "n-3"]:
    errors.append("data/notes.json holds notes %r, expected n-1, n-2, n-3" % (sorted(notes),))

for note_id, expected_count in expected_counts.items():
    note = notes.get(note_id)
    if note is None:
        continue
    if note.get("pinned") is not False:
        errors.append(
            "note %s has pinned=%r, expected the boolean false" % (note_id, note.get("pinned"))
        )
    count = note.get("word_count")
    if count != expected_count or type(count) is not int:
        errors.append(
            "note %s has word_count=%r, expected the int %d"
            % (note_id, count, expected_count)
        )
    if count is not None and "body" in note and count != len(note["body"].split()):
        errors.append(
            "note %s word_count %r does not match len(body.split()) == %d"
            % (note_id, count, len(note["body"].split()))
        )

# A fully migrated vault has nothing left to apply.
pending = apply_migrations(copy.deepcopy(vault_db))
if pending:
    errors.append(
        "data/notes.json still has pending migrations %r (the vault file was not "
        "migrated after the migrations were registered)" % (pending,)
    )

try:
    with open("data/index.json", encoding="utf-8") as handle:
        index = json.load(handle)
except Exception as exc:  # noqa: BLE001
    errors.append("data/index.json is not readable JSON: %s" % (exc,))
    index = None

if index is not None:
    if index.get("source_schema_version") != 3:
        errors.append(
            "data/index.json source_schema_version is %r, expected 3 (stale index)"
            % (index.get("source_schema_version"),)
        )

    entries = index.get("entries", [])
    if [e.get("id") for e in entries] != ["n-1", "n-2", "n-3"]:
        errors.append(
            "data/index.json entries are %r, expected one per note in id order"
            % ([e.get("id") for e in entries],)
        )

    for entry in entries:
        if sorted(entry) != ["id", "pinned", "title", "word_count"]:
            errors.append(
                "index entry %r has keys %r, expected id, title, pinned, word_count"
                % (entry.get("id"), sorted(entry))
            )
            continue
        expected_count = expected_counts.get(entry["id"])
        if entry["word_count"] != expected_count:
            errors.append(
                "index entry %s has word_count %r, expected %r (stale index)"
                % (entry["id"], entry["word_count"], expected_count)
            )
        if entry["pinned"] is not False:
            errors.append(
                "index entry %s has pinned %r, expected the boolean false"
                % (entry["id"], entry["pinned"])
            )

    # The committed index must be what the builder writes for the committed vault.
    if index != build_index(vault_db):
        errors.append(
            "data/index.json does not match the builder's output for the committed "
            "vault (stale index)"
        )

for message in errors:
    print("  - " + message, file=sys.stderr)
sys.exit(1 if errors else 0)
PY

echo "PASS"
