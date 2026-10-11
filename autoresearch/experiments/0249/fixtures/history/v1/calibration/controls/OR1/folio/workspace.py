from copy import deepcopy
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
        self.documents[name] = document
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
