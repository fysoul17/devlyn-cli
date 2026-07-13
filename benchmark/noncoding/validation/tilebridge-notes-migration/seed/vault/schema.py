"""The shape of a Tilebridge vault, and the migrations that evolve it.

SCHEMA_VERSION is the version the code expects to work with. MIGRATIONS lists, in
ascending order, every step that takes a vault from the version below it to the
version it targets:

    MIGRATIONS = [
        (2, migrate_002_something),   # 1 -> 2
        (3, migrate_003_something),   # 2 -> 3
    ]

A migration takes the whole vault dict and edits it in place. It must never set
schema_version itself — the migrator does that once the step has run.
"""

SCHEMA_VERSION = 1

MIGRATIONS = []
