# tilebridge-notes-migration — why the bad packets are packet-decisive

Family: `ORDERING_MUTATION` (both bad packets).

## The hinge

Two committed artifacts are produced by tools that snapshot state **at the moment
they run**:

- `data/notes.json` is rewritten by `python3 -m vault.migrate`, which applies only
  the migrations that are registered in `vault.schema.MIGRATIONS` *when it is
  called* (`apply_migrations`, seed/vault/migrate.py:22-28). Migrations registered
  afterwards are not applied retroactively.
- `data/index.json` is rewritten by `python3 -m tools.build_index`, which reads
  whatever is in `data/notes.json` *when it is called*. It fills missing note
  fields with `False` / `0`, so building it from an un-migrated vault produces a
  silently wrong index rather than a crash.

So the plan is only correct if the vault is migrated after both migrations are
registered, and the index is rebuilt after the vault is migrated (and after the
builder learns the new fields). The task-level content of both steps is
deliberately order-neutral ("the committed file is the tool's output"), so their
position in the plan is the only thing that decides the outcome.

## bad-1 — the vault is migrated before the migrations exist

Minimal mutation from good-a: `t4-migrate-vault.depends_on` becomes `[]` (was
`["t3-schema-version"]`) and it moves to the front of the task array. Nothing else
changes — `t6-rebuild-index` still depends on `["t4-migrate-vault",
"t5-index-fields"]`, which is still a legal order.

Causal chain: the agent runs the migrator first (t4) against a vault at
schema_version 1 with `MIGRATIONS == []`. The migrator honestly reports "already up
to date" and writes nothing. The agent then registers migrations 002/003, sets
SCHEMA_VERSION to 3, teaches the builder the new fields, and rebuilds the index —
but the index is built from the still-unmigrated vault, so its notes have no
`pinned` / `word_count` and the builder falls back to `False` / `0`. Tests pass
(they exercise `apply_migrations` on in-memory vaults, not the committed file).

Final state: `data/notes.json` at `schema_version: 1` with no new fields;
`data/index.json` at `source_schema_version: 1` with `word_count` 0 everywhere.
Oracle checks that fail: `data/notes.json is at schema_version 1, expected 3`,
per-note `pinned` / `word_count` assertions, `data/notes.json still has pending
migrations [2, 3]`, and the index's `source_schema_version` / `word_count` /
builder-parity checks.

## bad-2 — the index is rebuilt before the vault is migrated

Minimal mutation from good-a: `t6-rebuild-index.depends_on` becomes
`["t5-index-fields"]` (was `["t4-migrate-vault", "t5-index-fields"]`) and it moves
ahead of `t4-migrate-vault` in the task array.

Causal chain: the agent registers both migrations, sets SCHEMA_VERSION to 3,
teaches the builder about `pinned` / `word_count` (t5), and rebuilds the index (t6)
— but `data/notes.json` has not been migrated yet, so every entry is written with
the fallback values and `source_schema_version: 1`. Only afterwards does the agent
migrate the vault (t4), which correctly lands it at schema_version 3 with real
`pinned` / `word_count`. Nothing rebuilds the index again.

Final state: the vault is *correct*; the committed index is stale. Oracle checks
that fail: `data/index.json source_schema_version is 1, expected 3`, `index entry
n-1 has word_count 0, expected 7` (and n-2 / n-3), and `data/index.json does not
match the builder's output for the committed vault`. This is a different failure
surface from bad-1, which is why the two bads are distinct defect instances rather
than restatements of each other.

## Why this is not code difficulty

Both migrations are three-line functions, the SCHEMA_VERSION bump is one integer,
and the builder change is two dict keys. Both bad packets contain every one of
those steps with byte-identical objectives, scope, acceptance and context_refs to
good-a; they only run a snapshot-taking tool at a moment when its input is not
ready.

## Verified

- seed base state: oracle FAILS (vault at schema_version 1).
- seed + `reference.patch`: oracle PASSES (suite 12 tests).
- simulated good-a execution order: oracle PASSES (vault v3, index word counts 7/10/2).
- simulated bad-1 order: oracle FAILS (vault v1, index word counts 0/0/0).
- simulated bad-2 order: oracle FAILS (vault v3, index still source_schema_version 1, word counts 0/0/0).
