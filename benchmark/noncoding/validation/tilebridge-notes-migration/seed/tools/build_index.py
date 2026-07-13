"""Build the generated lookup index from the vault.

    python3 -m tools.build_index

Reads data/notes.json and rewrites data/index.json. The index is a generated file:
it is only ever as fresh as the vault it was built from, so it has to be rebuilt
whenever the vault changes.
"""

import json
import os
import sys

from vault.store import load_vault

OUTPUT_PATH = os.path.join("data", "index.json")


def build_index(db):
    """Return the index document for the vault `db`."""
    entries = []
    for note in sorted(db["notes"], key=lambda n: n["id"]):
        entries.append({"id": note["id"], "title": note["title"]})
    return {"source_schema_version": db["schema_version"], "entries": entries}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    index = build_index(load_vault(*argv[:1]))
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(index, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(
        "wrote %s (%d entries, source_schema_version %d)"
        % (OUTPUT_PATH, len(index["entries"]), index["source_schema_version"])
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
