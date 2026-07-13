# Tilebridge — note vault

A small note vault with a versioned on-disk format.

## Layout

- `data/notes.json` — the vault. Carries a `schema_version`.
- `vault/schema.py` — `SCHEMA_VERSION` (what the code expects) and `MIGRATIONS`.
- `vault/migrate.py` — applies pending migrations to a vault file, in place.
- `vault/store.py` — load/save the vault.
- `tools/build_index.py` — regenerates `data/index.json` from the vault.
- `data/index.json` — **generated**. Only as fresh as the vault it was built from.

## Common commands

```
python3 -m vault.migrate data/notes.json   # bring the vault up to the current schema
python3 -m tools.build_index               # rebuild the generated index
python3 -m unittest discover -s tests      # run the suite
```
