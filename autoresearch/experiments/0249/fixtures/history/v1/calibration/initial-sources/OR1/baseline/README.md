# Folio workspace

Folio is the document editing layer used by a small publishing service. Editors
open independent workspaces over a shared JSON file, stage changes, and save or
rebase after another editor saves. All APIs are synchronous; calls are serialized
in one process. Thread/process locking is outside this package's contract.

Repair the workspace so the existing ownership, conflict, and recovery contract
in `docs/contract.md` holds. Keep the public API. Product files are `folio/*.py`;
checks may be added or changed under `checks/`. `docs/`, `README.md`, and the
consumer in `examples/editor.py` describe the supported behavior.

Run `python3 -B checks/run_checks.py`. No third-party dependencies.
