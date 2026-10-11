"""Public-behavior oracle. Exit 0 means a valid per-manifestation verdict."""
import json
from pathlib import Path
import sys
import tempfile
import traceback

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
NAMES = [
    'recursive-ownership-boundaries', 'open-transaction-refresh-isolation',
    'optimistic-conflict-preserves-loser', 'disjoint-rebase-preserves-deletions',
    'overlap-rebase-is-atomic', 'absent-delete-retains-write-intent',
    'failed-save-retry', 'failed-read-rebase-recovery',
    'atomic-backend-conflict-boundary', 'closed-lifecycle-and-durable-store',
]
try:
    from folio import (ConflictError, FileStore, RebaseConflict,
                       StorageError, TransactionClosed, Workspace)
except Exception:
    print(json.dumps({'manifestations': [dict(id=name, passed=False, detail=traceback.format_exc()) for name in NAMES]}))
    raise SystemExit(0)


def expect(kind, operation):
    try:
        operation()
    except kind as error:
        return error
    raise AssertionError(f'expected {kind.__name__}')


def seed(store, documents):
    return store.compare_and_swap(0, documents)


class GateStore:
    """Public backend adapter rejecting the next read/save before commit."""
    def __init__(self, store):
        self.store = store
        self.fail_read = False
        self.fail_save = False
        self.before_save = None

    def read(self):
        if self.fail_read:
            self.fail_read = False
            raise StorageError('read temporarily unavailable')
        return self.store.read()

    def compare_and_swap(self, expected_revision, documents):
        if self.fail_save:
            self.fail_save = False
            raise StorageError('save temporarily unavailable')
        if self.before_save is not None:
            callback, self.before_save = self.before_save, None
            callback()
        return self.store.compare_and_swap(expected_revision, documents)


def ownership(path):
    store = FileStore(path)
    seed(store, {'a': {'parts': [{'tags': ['original']}]}})
    workspace = Workspace(store)
    early = workspace.snapshot()
    early.documents['a']['parts'][0]['tags'].append('caller')
    assert workspace.snapshot().documents['a']['parts'][0]['tags'] == ['original']
    transaction, peer = workspace.begin(), workspace.begin()
    got = transaction.get('a')
    got['parts'][0]['tags'].append('reader')
    assert transaction.get('a')['parts'][0]['tags'] == ['original']
    supplied = {'parts': [{'tags': ['draft']}]}
    transaction.put('a', supplied)
    supplied['parts'][0]['tags'].append('input')
    assert transaction.get('a')['parts'][0]['tags'] == ['draft']
    committed = transaction.commit()
    committed.documents['a']['parts'][0]['tags'].append('returned')
    assert workspace.snapshot().documents['a']['parts'][0]['tags'] == ['draft']
    assert peer.get('a')['parts'][0]['tags'] == ['original']
    assert store.read().documents['a']['parts'][0]['tags'] == ['draft']
    assert early.documents['a']['parts'][0]['tags'] == ['original', 'caller']


def refresh_isolation(path):
    store = FileStore(path)
    seed(store, {'a': {'value': 1}})
    local, remote = Workspace(store), Workspace(FileStore(path))
    draft = local.begin()
    draft.put('local', {'value': 2})
    other = remote.begin()
    other.put('a', {'value': 3})
    other.commit()
    assert local.snapshot().revision == 1
    assert local.refresh().documents == {'a': {'value': 3}}
    assert draft.get('a') == {'value': 1}
    assert draft.get('local') == {'value': 2}
    assert 'local' not in local.snapshot().documents
    draft.rollback()
    assert local.snapshot().documents == {'a': {'value': 3}}


def optimistic(path):
    store = FileStore(path)
    seed(store, {'a': {'value': 1}})
    left, right = Workspace(store), Workspace(FileStore(path))
    first, loser = left.begin(), right.begin()
    first.put('a', {'value': 2})
    loser.put('b', {'value': 3})
    first.commit()
    error = expect(ConflictError, loser.commit)
    assert (error.expected, error.actual) == (1, 2)
    assert right.snapshot().revision == 1 and right.snapshot().documents == {'a': {'value': 1}}
    assert store.read().documents == {'a': {'value': 2}}
    assert loser.get('b') == {'value': 3}
    again = expect(ConflictError, loser.commit)
    assert (again.expected, again.actual) == (1, 2)
    loser.rebase()
    assert loser.commit().documents == {'a': {'value': 2}, 'b': {'value': 3}}
    assert store.read().revision == 3


def disjoint(path):
    store = FileStore(path)
    seed(store, {'keep': {'value': 0}, 'local-delete': {}, 'remote-delete': {}})
    local, remote = Workspace(store), Workspace(FileStore(path))
    draft, other = local.begin(), remote.begin()
    draft.delete('local-delete')
    draft.put('added', {'items': [1]})
    other.delete('remote-delete')
    other.put('keep', {'value': 4})
    other.commit()
    committed = draft.rebase()
    assert committed.revision == 2
    assert committed.documents == {'keep': {'value': 4}, 'local-delete': {}}
    assert local.snapshot().documents == committed.documents
    assert store.read().revision == 2
    assert draft.get('keep') == {'value': 4}
    expect(KeyError, lambda: draft.get('local-delete'))
    expect(KeyError, lambda: draft.get('remote-delete'))
    committed.documents['keep']['value'] = 999
    assert draft.commit().documents == {'keep': {'value': 4}, 'added': {'items': [1]}}


def overlap(path):
    store = FileStore(path)
    seed(store, {'a': {'n': 0}, 'z': {'n': 0}, 'other': {}})
    local, remote = Workspace(store), Workspace(FileStore(path))
    draft, competing = local.begin(), remote.begin()
    draft.put('a', {'n': 1})
    draft.delete('z')
    competing.put('z', {'n': 2})
    competing.put('a', {'n': 2})
    competing.commit()
    error = expect(RebaseConflict, draft.rebase)
    assert error.names == ('a', 'z')
    assert local.snapshot().revision == 1
    assert draft.get('a') == {'n': 1}
    expect(KeyError, lambda: draft.get('z'))
    assert expect(RebaseConflict, draft.rebase).names == ('a', 'z')
    assert store.read().revision == 2
    draft.rollback()
    assert local.refresh().revision == 2


def absent_delete(path):
    store = FileStore(path)
    local, remote = Workspace(store), Workspace(FileStore(path))
    draft = local.begin()
    draft.delete('later')
    other = remote.begin()
    other.put('later', {})
    other.commit()
    assert expect(RebaseConflict, draft.rebase).names == ('later',)
    assert local.snapshot().revision == 0
    expect(KeyError, lambda: draft.get('later'))
    draft.rollback()


def failed_save(path):
    disk = FileStore(path)
    seed(disk, {'old': {'n': 1}})
    gate = GateStore(disk)
    workspace = Workspace(gate)
    draft = workspace.begin()
    draft.delete('old')
    draft.put('new', {'parts': [1, 2]})
    gate.fail_save = True
    error = expect(StorageError, draft.commit)
    assert str(error) == 'save temporarily unavailable'
    assert workspace.snapshot().revision == 1 and workspace.snapshot().documents == {'old': {'n': 1}}
    assert disk.read().documents == {'old': {'n': 1}}
    assert draft.get('new') == {'parts': [1, 2]}
    assert draft.commit().revision == 2
    assert Workspace(FileStore(path)).snapshot().documents == {'new': {'parts': [1, 2]}}


def failed_read(path):
    disk = FileStore(path)
    seed(disk, {'base': {'n': 1}})
    gate = GateStore(disk)
    workspace = Workspace(gate)
    draft = workspace.begin()
    draft.put('mine', {'n': 2})
    remote = Workspace(FileStore(path)).begin()
    remote.put('base', {'n': 3})
    remote.commit()
    gate.fail_read = True
    expect(StorageError, workspace.refresh)
    assert workspace.snapshot().revision == 1
    gate.fail_read = True
    expect(StorageError, draft.rebase)
    assert workspace.snapshot().revision == 1
    assert draft.get('base') == {'n': 1} and draft.get('mine') == {'n': 2}
    assert draft.rebase().revision == 2
    assert draft.commit().documents == {'base': {'n': 3}, 'mine': {'n': 2}}


def atomic_boundary(path):
    disk = FileStore(path)
    gate = GateStore(disk)
    workspace = Workspace(gate)
    draft = workspace.begin()
    draft.put('mine', {'n': 1})
    gate.before_save = lambda: disk.compare_and_swap(0, {'remote': {'n': 2}})
    error = expect(ConflictError, draft.commit)
    assert (error.expected, error.actual) == (0, 1)
    assert workspace.snapshot().documents == {} and workspace.snapshot().revision == 0
    assert disk.read().documents == {'remote': {'n': 2}}
    assert draft.get('mine') == {'n': 1}
    draft.rebase()
    assert draft.commit().documents == {'remote': {'n': 2}, 'mine': {'n': 1}}


def lifecycle(path):
    workspace = Workspace(FileStore(path))
    peer = workspace.begin()
    for method in ('commit', 'rollback'):
        transaction = workspace.begin()
        getattr(transaction, method)()
        for operation in (lambda: transaction.get('a'), lambda: transaction.put('a', {}),
                          lambda: transaction.delete('a'), transaction.commit,
                          transaction.rebase, transaction.rollback):
            expect(TransactionClosed, operation)
    peer.put('still-open', {})
    peer.rollback()
    assert Workspace(FileStore(path)).snapshot().revision == 1
    before = path.read_bytes()
    path.write_text('{broken')
    expect(StorageError, workspace.refresh)
    assert path.read_text() == '{broken'
    assert workspace.snapshot().revision == 1
    path.write_bytes(before)
    assert workspace.refresh().revision == 1
    path.write_bytes(b'\xff')
    expect(StorageError, workspace.refresh)
    assert path.read_bytes() == b'\xff'
    assert workspace.snapshot().revision == 1

FUNCTIONS = [ownership, refresh_isolation, optimistic, disjoint, overlap,
             absent_delete, failed_save, failed_read, atomic_boundary, lifecycle]
results = []
for name, function in zip(NAMES, FUNCTIONS):
    try:
        with tempfile.TemporaryDirectory() as root:
            function(Path(root) / 'documents.json')
    except Exception:
        results.append(dict(id=name, passed=False, detail=traceback.format_exc()))
    else:
        results.append(dict(id=name, passed=True))
print(json.dumps({'manifestations': results}))
