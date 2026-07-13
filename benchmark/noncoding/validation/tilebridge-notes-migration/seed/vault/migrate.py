"""Apply pending vault migrations to a vault file.

    python3 -m vault.migrate data/notes.json

Applies every migration registered in vault.schema.MIGRATIONS whose target version
is above the file's current schema_version, in ascending order, then writes the
vault back. Running it against an already-migrated file does nothing.
"""

import sys

from vault.schema import MIGRATIONS
from vault.store import DEFAULT_PATH, load_vault, save_vault


def apply_migrations(db):
    """Run every pending migration against `db` in place.

    Returns the list of target versions that were applied (empty if the vault was
    already up to date).
    """
    applied = []
    for target_version, migration in MIGRATIONS:
        if db["schema_version"] < target_version:
            migration(db)
            db["schema_version"] = target_version
            applied.append(target_version)
    return applied


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    path = argv[0] if argv else DEFAULT_PATH

    db = load_vault(path)
    applied = apply_migrations(db)
    if applied:
        save_vault(db, path)
        print(
            "%s: applied migration(s) %s, now at schema_version %d"
            % (path, ", ".join(str(v) for v in applied), db["schema_version"])
        )
    else:
        print(
            "%s: already up to date (schema_version %d)"
            % (path, db["schema_version"])
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
