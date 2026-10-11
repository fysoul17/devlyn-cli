# Public contract

Documents are JSON-compatible dictionaries; a workspace is a mapping from string
names to documents. Callers supply these types. Names need not be filesystem
paths. `Snapshot(revision, documents)` is a public data object. `ConflictError`
exposes `expected` and `actual`; `RebaseConflict` exposes sorted tuple `names`.
`StorageError` and `TransactionClosed` are public exceptions.

C1 — Ownership. Every returned Snapshot and every transaction `get(name)` result
is a detached recursive copy. Mutating it never changes a transaction, workspace,
backend, or another returned value. `put(name, document)` captures a recursive
copy when called, including nested lists/dictionaries. Earlier snapshots retain
their values after later operations. Missing `get` raises `KeyError`.

C2 — Views. `Workspace(store)` reads the backend once. `snapshot()` reports that
handle's last known committed state. `begin()` starts an independent transaction
from that state, including its revision. Transactions read their own writes and
deletes. A transaction's staged edits stay private until it commits. `refresh()`
reads the backend and replaces that handle's committed view; it does not modify
any open transaction. A failed refresh preserves the previous committed view.

C3 — Atomic optimistic commit. `commit()` submits the whole staged document set
against the transaction's base revision. A successful commit publishes precisely
that set, increments the store revision once, updates the owning handle, returns
a detached Snapshot, and closes the transaction. Any intervening committed
revision, including a commit through another handle, raises `ConflictError` with
the base and current revisions without changing backend, handle, or transaction.
The losing transaction remains open, preserving its staged edits for rebase or
rollback. A no-edit commit is still a commit and increments the revision.

C4 — Rebase. `rebase()` reads the latest backend and reapplies this transaction's
explicitly touched names over it. A name is touched by any `put` or `delete`,
including deleting an absent name. If the latest presence/value of any touched
name differs from its presence/value at the transaction's base, raise
`RebaseConflict` listing all such names. Compare presence as well as value.
Unrelated changes are merged; untouched deletions stay deleted. Successful
rebase updates the transaction's base and the owning handle's committed view,
keeps staged edits uncommitted, and returns the latest committed Snapshot.
A conflict or storage failure changes none of those states and leaves the
transaction open. A successful rebase alone never writes to the backend.

C5 — Persistence and retry. A backend implements `read() -> Snapshot` and
`compare_and_swap(expected_revision, documents) -> Snapshot`. Reads return a
self-consistent committed version. Compare-and-swap either commits the complete
new version atomically or raises `ConflictError`/`StorageError` without committing
anything. Returned/input objects are caller-owned and not retained by the
backend. Implementations may raise `StorageError` before any operation completes;
the workspace must propagate it, keep its last good committed view, and keep a
failed transaction's base and staged edits intact. Retrying the same transaction
after recovery is supported. The workspace calls the backend's atomic operation;
an earlier read is not a substitute for its revision check. `FileStore(path)`
implements this protocol: missing file means revision 0 and empty documents,
separate FileStore objects see the same file, committed data survives reopening,
and unreadable/malformed files raise StorageError without replacing their bytes.

C6 — Lifecycle. `delete(name)` removes that name if present. `rollback()` discards
the transaction and closes it without updating the handle or backend. After a
successful commit or rollback, `get`, `put`, `delete`, `commit`, `rebase`, and
`rollback` all raise `TransactionClosed`. Other open transactions remain usable.
