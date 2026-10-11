"""Deterministically construct the two original 0249 ownership/recovery fixtures."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent

def write(task, relative, text):
    path = ROOT / task / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + '\n')

COMMON_CHECKS = '''
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern="test_*.py"))
print(json.dumps({"public_passed": result.wasSuccessful(), "tests": result.testsRun}))
raise SystemExit(0 if result.wasSuccessful() else 1)
'''

write('OR1', 'visible/README.md', '''
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
''')
write('OR1', 'visible/docs/contract.md', '''
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
''')
write('OR1', 'visible/folio/__init__.py', '''
from .storage import ConflictError, FileStore, Snapshot, StorageError
from .workspace import RebaseConflict, TransactionClosed, Workspace
__all__ = ["ConflictError", "FileStore", "Snapshot", "StorageError", "RebaseConflict", "TransactionClosed", "Workspace"]
''')
write('OR1', 'visible/folio/storage.py', '''
from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile

@dataclass
class Snapshot:
    revision: int
    documents: dict

class StorageError(Exception):
    pass

class ConflictError(Exception):
    def __init__(self, expected, actual):
        self.expected, self.actual = expected, actual
        super().__init__(f"expected revision {expected}, found {actual}")

class FileStore:
    """Atomic replacement for serialized callers in one process."""
    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        try:
            text = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return Snapshot(0, {})
        except (OSError, UnicodeError) as exc:
            raise StorageError(str(exc)) from exc
        try:
            value = json.loads(text)
            if (not isinstance(value, dict) or set(value) != {"revision", "documents"}
                    or type(value["revision"]) is not int or value["revision"] < 0
                    or not isinstance(value["documents"], dict)
                    or not all(isinstance(doc, dict) for doc in value["documents"].values())):
                raise ValueError("invalid workspace format")
            return Snapshot(value["revision"], value["documents"])
        except (ValueError, TypeError) as exc:
            raise StorageError(f"invalid workspace: {exc}") from exc

    def compare_and_swap(self, expected_revision, documents):
        current = self.read()
        if current.revision != expected_revision:
            raise ConflictError(expected_revision, current.revision)
        result = Snapshot(current.revision + 1, deepcopy(documents))
        temporary = None
        try:
            payload = json.dumps({"revision": result.revision, "documents": result.documents}, allow_nan=False)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            temporary = None
        except (OSError, TypeError, ValueError) as exc:
            raise StorageError(str(exc)) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return result
''')
OR1_BASE = '''
from copy import copy
from .storage import Snapshot

class TransactionClosed(Exception):
    pass

class RebaseConflict(Exception):
    def __init__(self, names):
        self.names = tuple(sorted(names))
        super().__init__(f"changed documents: {', '.join(self.names)}")

class Workspace:
    def __init__(self, store):
        self.store = store
        self._committed = store.read()

    def snapshot(self):
        return Snapshot(self._committed.revision, copy(self._committed.documents))

    def refresh(self):
        self._committed = self.store.read()
        return self.snapshot()

    def begin(self):
        return Transaction(self)

class Transaction:
    def __init__(self, workspace):
        self.workspace = workspace
        self.base = workspace.snapshot()
        self.documents = copy(self.base.documents)
        self.touched = set()
        self.closed = False

    def _active(self):
        if self.closed:
            raise TransactionClosed("transaction is closed")

    def get(self, name):
        self._active()
        return copy(self.documents[name])

    def put(self, name, document):
        self._active()
        self.documents[name] = copy(document)
        self.touched.add(name)

    def delete(self, name):
        self._active()
        self.documents.pop(name, None)
        self.touched.add(name)

    def commit(self):
        self._active()
        self.closed = True
        self.workspace._committed = Snapshot(self.base.revision + 1, self.documents)
        result = self.workspace.store.compare_and_swap(self.base.revision, self.documents)
        self.workspace._committed = result
        return self.workspace.snapshot()

    def rebase(self):
        self._active()
        latest = self.workspace.refresh()
        changed = [name for name in self.touched if self.base.documents.get(name) != latest.documents.get(name)]
        self.base = latest
        if changed:
            raise RebaseConflict(changed)
        self.documents = {**latest.documents, **self.documents}
        return latest

    def rollback(self):
        self._active()
        self.closed = True
'''
OR1_GOLD = '''
from copy import deepcopy

class TransactionClosed(Exception):
    pass

class RebaseConflict(Exception):
    def __init__(self, names):
        self.names = tuple(sorted(names))
        super().__init__(f"changed documents: {', '.join(self.names)}")

class Workspace:
    def __init__(self, store):
        self.store = store
        self._committed = deepcopy(store.read())

    def snapshot(self):
        return deepcopy(self._committed)

    def refresh(self):
        latest = self.store.read()
        self._committed = deepcopy(latest)
        return self.snapshot()

    def begin(self):
        return Transaction(self)

class Transaction:
    def __init__(self, workspace):
        self.workspace = workspace
        self.base = workspace.snapshot()
        self.documents = deepcopy(self.base.documents)
        self.touched = set()
        self.closed = False

    def _active(self):
        if self.closed:
            raise TransactionClosed("transaction is closed")

    def get(self, name):
        self._active()
        return deepcopy(self.documents[name])

    def put(self, name, document):
        self._active()
        self.documents[name] = deepcopy(document)
        self.touched.add(name)

    def delete(self, name):
        self._active()
        self.documents.pop(name, None)
        self.touched.add(name)

    def commit(self):
        self._active()
        result = self.workspace.store.compare_and_swap(self.base.revision, deepcopy(self.documents))
        self.workspace._committed = deepcopy(result)
        self.closed = True
        return self.workspace.snapshot()

    def rebase(self):
        self._active()
        latest = self.workspace.store.read()
        changed = [name for name in self.touched
                   if ((name in self.base.documents) != (name in latest.documents)
                       or self.base.documents.get(name) != latest.documents.get(name))]
        if changed:
            raise RebaseConflict(changed)
        merged = deepcopy(latest.documents)
        for name in self.touched:
            if name in self.documents:
                merged[name] = deepcopy(self.documents[name])
            else:
                merged.pop(name, None)
        self.base = deepcopy(latest)
        self.documents = merged
        self.workspace._committed = deepcopy(latest)
        return self.workspace.snapshot()

    def rollback(self):
        self._active()
        self.closed = True
'''
write('OR1', 'visible/folio/workspace.py', OR1_BASE)
write('OR1', 'visible/examples/editor.py', '''
"""Two editors saving different articles; run from the project root."""
from folio import ConflictError, FileStore, Workspace

def edit_pair(path):
    west, east = Workspace(FileStore(path)), Workspace(FileStore(path))
    headline, footer = west.begin(), east.begin()
    headline.put("headline", {"text": "Today's edition", "tags": ["news"]})
    footer.put("footer", {"text": "Contact the desk"})
    headline.commit()
    try:
        footer.commit()
    except ConflictError:
        footer.rebase()
        footer.commit()
    return Workspace(FileStore(path)).snapshot()
''')
write('OR1', 'visible/checks/run_checks.py', COMMON_CHECKS)
write('OR1', 'visible/checks/test_smoke.py', '''
from pathlib import Path
import tempfile
import unittest
from folio import FileStore, StorageError, TransactionClosed, Workspace

class Smoke(unittest.TestCase):
    def test_save_reopen_and_delete(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "articles.json"
            workspace = Workspace(FileStore(path))
            transaction = workspace.begin()
            transaction.put("welcome", {"text": "Hello"})
            self.assertEqual(transaction.get("welcome"), {"text": "Hello"})
            self.assertEqual(transaction.commit().revision, 1)
            reopened = Workspace(FileStore(path))
            self.assertEqual(reopened.snapshot().documents, {"welcome": {"text": "Hello"}})
            delete = reopened.begin()
            delete.delete("welcome")
            self.assertEqual(delete.commit().documents, {})

    def test_rollback_closes_and_malformed_is_visible(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "articles.json"
            workspace = Workspace(FileStore(path))
            transaction = workspace.begin()
            transaction.put("draft", {"text": "discard"})
            transaction.rollback()
            self.assertEqual(workspace.snapshot().documents, {})
            with self.assertRaises(TransactionClosed):
                transaction.commit()
            path.write_text("broken")
            with self.assertRaises(StorageError):
                workspace.refresh()
''')

write('OR2', 'visible/README.md', '''
# Relay keyed loader

Relay shares asynchronous catalog loads between request handlers. It caches
successful documents, allows an administrator to invalidate a key while old
requests finish, and shuts down outstanding work at service exit.

Fix Relay so request cancellation, invalidation, and backend failures obey the
existing public contract in `docs/contract.md`. Keep the API. Product files are
`relay/*.py`; checks may be added or changed under `checks/`. The example in
`examples/catalog.py` is an ordinary consumer. Run `python3 -B checks/run_checks.py`.
Python 3.11+ standard library only; one asyncio event loop per loader instance.
''')
write('OR2', 'visible/docs/contract.md', '''
# Public contract

Construct `KeyedLoader(fetch)` with an async callable `fetch(key)` accepting a
string and returning a JSON-compatible dictionary. `await get(key)` loads one
value. `invalidate(key)` is synchronous. `snapshot()` returns a dictionary of
completed cached values only. `await close()` ends this loader's lifetime.
`ClosedError` is public. Calls use one asyncio loop; threads are out of scope.

C1 — Sharing. Concurrent get calls for the same key and current generation share
one fetch operation. Different keys progress independently. After success,
further get calls use the cached value until invalidation. `snapshot()` never
reports unfinished or failed loads. Generation means the period between
invalidations of that key; callers do not need to provide a generation number.

C2 — Ownership. Each get result and snapshot is a recursive detached copy,
independent of the cache, the object returned by fetch, all other callers, and
later results. Mutating any of those caller/backend-owned objects after
completion cannot alter the cached value or other returned objects.

C3 — Invalidation. invalidate removes the key's cached value immediately and
starts a new generation even when a fetch is in progress. Existing callers keep
waiting for their original operation and receive its success/failure. A get
started after invalidate uses a fresh operation; it must not join the retired
operation. Retired operations may finish in any order but cannot publish a cached
value for, remove, cancel, or otherwise disturb the current generation. Repeated
invalidations, including of unknown keys, are valid. Other keys are unaffected.

C4 — Caller cancellation. Cancelling one get caller raises CancelledError to
that caller only. It never cancels the shared fetch or other callers. This also
applies when the cancelled caller was the sole waiter: the fetch still finishes
and may populate the cache if its generation is current. A later caller may
join that ongoing operation. An abandoned fetch failure must be consumed so it
does not become an event-loop 'Task exception was never retrieved' report.

C5 — Failure and recovery. Fetch exceptions propagate with their original type
and message to all waiting callers. Neither exceptions nor backend cancellation
are cached. The next get in that same generation starts a fresh operation and
can recover. An old-generation failure or cancellation cannot remove a newer
in-flight operation or completed cached value. Previously cached other keys
remain available after a failure.

C6 — Shutdown. close marks the instance closed, empties its cache, cancels and
awaits all unfinished fetches it owns, including operations retired by
invalidation or abandoned by callers. Waiting callers observe cancellation when
their fetch is cancelled. close is idempotent; on return no owned fetch remains
running. get and invalidate on a closed loader raise ClosedError; snapshot is
empty. No completion may repopulate it after close. Fetch functions cooperate
with cancellation, possibly after asynchronous cleanup; close waits for that
cleanup. Closing an instance does not affect a different loader instance.
''')
write('OR2', 'visible/relay/__init__.py', '''
from .loader import ClosedError, KeyedLoader
__all__ = ["ClosedError", "KeyedLoader"]
''')
OR2_BASE = '''
import asyncio
from copy import copy

class ClosedError(Exception):
    pass

class KeyedLoader:
    def __init__(self, fetch):
        self.fetch = fetch
        self._cache = {}
        self._pending = {}
        self._closed = False

    async def _load(self, key):
        result = await self.fetch(key)
        self._cache[key] = result
        self._pending.pop(key, None)
        return result

    async def get(self, key):
        if self._closed:
            raise ClosedError("loader is closed")
        if key in self._cache:
            return copy(self._cache[key])
        if key not in self._pending:
            self._pending[key] = asyncio.create_task(self._load(key))
        return copy(await self._pending[key])

    def invalidate(self, key):
        if self._closed:
            raise ClosedError("loader is closed")
        self._cache.pop(key, None)
        self._pending.pop(key, None)

    def snapshot(self):
        return copy(self._cache)

    async def close(self):
        self._closed = True
        pending = list(self._pending.values())
        self._cache.clear()
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        self._pending.clear()
'''
OR2_GOLD = '''
import asyncio
from copy import deepcopy

class ClosedError(Exception):
    pass

class KeyedLoader:
    def __init__(self, fetch):
        self.fetch = fetch
        self._cache = {}
        self._pending = {}
        self._owned = set()
        self._closed = False

    def _settled(self, task):
        self._owned.discard(task)
        if not task.cancelled():
            task.exception()

    async def _load(self, key):
        task = asyncio.current_task()
        try:
            result = deepcopy(await self.fetch(key))
            if not self._closed and self._pending.get(key) is task:
                self._cache[key] = deepcopy(result)
            return result
        finally:
            if self._pending.get(key) is task:
                self._pending.pop(key)

    async def get(self, key):
        if self._closed:
            raise ClosedError("loader is closed")
        if key in self._cache:
            return deepcopy(self._cache[key])
        if key not in self._pending:
            task = asyncio.create_task(self._load(key))
            self._pending[key] = task
            self._owned.add(task)
            task.add_done_callback(self._settled)
        return deepcopy(await asyncio.shield(self._pending[key]))

    def invalidate(self, key):
        if self._closed:
            raise ClosedError("loader is closed")
        self._cache.pop(key, None)
        self._pending.pop(key, None)

    def snapshot(self):
        return deepcopy(self._cache)

    async def close(self):
        already_closed = self._closed
        self._closed = True
        self._cache.clear()
        pending = list(self._owned)
        if not already_closed:
            for task in pending:
                task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        self._pending.clear()
'''
write('OR2', 'visible/relay/loader.py', OR2_BASE)
write('OR2', 'visible/examples/catalog.py', '''
"""Request handlers share a loader; admin updates invalidate one SKU."""
from relay import KeyedLoader

class Catalog:
    def __init__(self, database):
        self.documents = KeyedLoader(database.fetch_product)

    async def product_card(self, sku):
        document = await self.documents.get(sku)
        document.setdefault("display", {})["expanded"] = True
        return document

    def product_updated(self, sku):
        self.documents.invalidate(sku)

    async def shutdown(self):
        await self.documents.close()
''')
write('OR2', 'visible/checks/run_checks.py', COMMON_CHECKS)
write('OR2', 'visible/checks/test_smoke.py', '''
import unittest
from relay import ClosedError, KeyedLoader

class Smoke(unittest.IsolatedAsyncioTestCase):
    async def test_cache_and_completed_invalidation(self):
        calls = []
        async def fetch(key):
            calls.append(key)
            return {"name": key, "version": len(calls)}
        loader = KeyedLoader(fetch)
        self.assertEqual(await loader.get("sku"), {"name": "sku", "version": 1})
        self.assertEqual(await loader.get("sku"), {"name": "sku", "version": 1})
        self.assertEqual(calls, ["sku"])
        loader.invalidate("sku")
        self.assertEqual(await loader.get("sku"), {"name": "sku", "version": 2})
        await loader.close()
        self.assertEqual(loader.snapshot(), {})
        with self.assertRaises(ClosedError):
            await loader.get("sku")

    async def test_other_keys(self):
        async def fetch(key):
            return {"name": key}
        loader = KeyedLoader(fetch)
        self.assertEqual(await loader.get("left"), {"name": "left"})
        self.assertEqual(await loader.get("right"), {"name": "right"})
        self.assertEqual(set(loader.snapshot()), {"left", "right"})
        await loader.close()
''')

for task, module, gold in [('OR1', 'folio/workspace.py', OR1_GOLD), ('OR2', 'relay/loader.py', OR2_GOLD)]:
    shutil.copytree(ROOT / task / 'visible', ROOT / task / 'gold', dirs_exist_ok=True)
    write(task, 'gold/' + module, gold)
    write(task, 'GOLD.md', 'gold/ is a complete replacement for visible/. All files other than ' + module + ' are byte-identical to visible/.')
