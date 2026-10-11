"""Public malformed-constant boundary and repair, with no private injection."""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
from folio import FileStore, StorageError, Workspace

results = []
with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
    path = Path(temporary) / 'workspace.json'
    store = FileStore(path)
    store.compare_and_swap(0, {'good': {'value': 7}})
    good = path.read_bytes()
    for constant in ('NaN', 'Infinity', '-Infinity'):
        workspace = Workspace(store)
        bad = ('{"revision": 1, "documents": {"bad": {"value": ' + constant + '}}}').encode()
        path.write_bytes(bad)
        row = {'constant': constant}
        for label, call in [('read', store.read), ('refresh', workspace.refresh)]:
            try:
                call()
            except StorageError:
                row[label] = 'StorageError'
            else:
                row[label] = 'accepted'
        row['bad_bytes_preserved'] = path.read_bytes() == bad
        row['prior_view_preserved'] = workspace.snapshot().documents == {'good': {'value': 7}}
        path.write_bytes(good)
        row['recovered_view'] = workspace.refresh().documents == {'good': {'value': 7}}
        results.append(row)
    recovered = workspace.begin().commit()
    commit = {'revision': recovered.revision, 'documents': recovered.documents}
print(json.dumps({'constants': results, 'recovered_no_edit_commit': commit}))
