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
