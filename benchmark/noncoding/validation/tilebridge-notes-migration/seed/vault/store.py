"""Reading and writing the vault file."""

import json

DEFAULT_PATH = "data/notes.json"


def load_vault(path=DEFAULT_PATH):
    """Return the vault stored at `path`, exactly as it is on disk."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_vault(db, path=DEFAULT_PATH):
    """Write `db` back to `path` in the vault's canonical formatting."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(db, handle, indent=2, sort_keys=True)
        handle.write("\n")


def notes_by_id(db):
    """Return {note id: note} for every note in the vault."""
    return {note["id"]: note for note in db["notes"]}


def titles(db):
    """Return the note titles, ordered by note id."""
    return [note["title"] for note in sorted(db["notes"], key=lambda n: n["id"])]
