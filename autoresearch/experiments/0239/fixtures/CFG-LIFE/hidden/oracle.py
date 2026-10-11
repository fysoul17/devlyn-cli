import json
import sys
import tempfile
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
results = []
def check(name, fn):
    try:
        fn()
    except Exception as exc:
        results.append({'id': name, 'passed': False, 'detail': traceback.format_exc()})
    else:
        results.append({'id': name, 'passed': True})

import os
from beacon import Loader, ConfigManager, ConfigError

def write(root, name, values=None, includes=None):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {}
    if includes is not None:
        document['include'] = includes
    if values is not None:
        document['values'] = values
    path.write_text(json.dumps(document), encoding='utf-8')
    return path.resolve()

def same_json(actual, expected):
    # JSON has one number kind, but booleans must not compare equal to 0/1.
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(
            same_json(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            same_json(left, right) for left, right in zip(actual, expected))
    if type(expected) in (int, float):
        return type(actual) in (int, float) and actual == expected
    return type(actual) is type(expected) and actual == expected

def loader_merge_value_kinds():
    # Exercise merge semantics only through documents and the exported Loader.
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        write(root, 'base.json', {
            'service': {'workers': 2, 'limits': {'soft': 3, 'hard': 8}},
            'tags': ['base'], 'keep': 1})
        app = write(root, 'app.json', {
            'service': {'limits': {'soft': 5}}, 'tags': ['prod'], 'keep': None},
            ['base.json'])
        assert same_json(Loader().load(app).values, {
            'service': {'workers': 2, 'limits': {'soft': 5, 'hard': 8}},
            'tags': ['prod'], 'keep': None})
        earlier = [
            {'left_only': {'keep': [1]}, 'overlap': {'before': 1}},
            ['earlier'], None, 'earlier', 13, False]
        later = [
            {'right_only': [2], 'overlap': {'after': 2}},
            ['later'], None, 'later', 29, True]
        for left in earlier:
            for right in later:
                write(root, 'base.json', {'value': left})
                app = write(root, 'app.json', {'value': right}, ['base.json'])
                expected = right
                if isinstance(left, dict) and isinstance(right, dict):
                    expected = {'left_only': {'keep': [1]},
                                'overlap': {'before': 1, 'after': 2},
                                'right_only': [2]}
                actual = Loader().load(app).values
                assert same_json(actual, {'value': expected}), (left, right, actual)
check('loader-merge-value-kinds', loader_merge_value_kinds)

def relative_diamond():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        base = write(root, 'base.json', {'service': {'timeout': 5, 'workers': 1}, 'color': 'base'})
        west = write(root, 'regions/west.json', {'service': {'timeout': 9}, 'color': 'west'}, ['../base.json'])
        service = write(root, 'services/api.json', {'service': {'workers': 4}}, ['../base.json'])
        app = write(root, 'apps/root.json', {'service': {'host': 'localhost'}}, ['../regions/west.json', '../services/api.json'])
        resolved = Loader().load(app)
        assert resolved.values == {'service': {'timeout': 5, 'workers': 4, 'host': 'localhost'}, 'color': 'base'}
        assert resolved.dependencies == tuple(sorted([base, west, service, app], key=str))
check('relative-diamond-layer-order', relative_diamond)

def transitive_same_stat():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        leaf = write(root, 'leaf.json', {'port': 7011})
        write(root, 'middle.json', {}, ['leaf.json'])
        app = write(root, 'app.json', {}, ['middle.json'])
        manager = ConfigManager(app)
        first = manager.reload()
        metadata = leaf.stat()
        text = leaf.read_text(encoding='utf-8')
        leaf.write_text(text.replace('7011', '7022'), encoding='utf-8')
        os.utime(leaf, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
        assert leaf.stat().st_size == metadata.st_size
        second = manager.reload()
        assert second.values == {'port': 7022} and second.generation == 2
        assert first.values == {'port': 7011} and first.generation == 1
check('transitive-change-same-size-and-mtime', transitive_same_stat)

def snapshot_isolation():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        app = write(root, 'app.json', {'service': {'tags': ['one']}})
        manager = ConfigManager(app)
        published = manager.reload()
        published.values['service']['tags'].append('caller change')
        assert manager.current.values == {'service': {'tags': ['one']}}
        read = manager.current
        read.values['service']['tags'].append('second change')
        assert manager.current.values == {'service': {'tags': ['one']}}
        assert manager.reload().generation == 1
        loader = Loader()
        resolved = loader.load(app)
        resolved.values['service']['tags'].append('loader caller')
        assert loader.load(app).values == {'service': {'tags': ['one']}}
check('nested-caller-isolation', snapshot_isolation)

def generation_and_dependencies():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        a = write(root, 'a.json', {'port': 7011})
        b = write(root, 'b.json', {'port': 7011})
        app = write(root, 'app.json', {}, ['a.json'])
        manager = ConfigManager(app)
        assert manager.reload().generation == 1
        assert manager.reload().generation == 1
        write(root, 'app.json', {}, ['b.json'])
        switched = manager.reload()
        assert switched.generation == 1
        assert switched.dependencies == tuple(sorted([app, b], key=str))
        b.write_text('{ "values" : { "port" : 7011 } }', encoding='utf-8')
        assert manager.reload().generation == 1
        write(root, 'b.json', {'port': 7033})
        assert manager.reload().generation == 2
        assert a not in manager.current.dependencies
check('semantic-generation-current-dependencies', generation_and_dependencies)

def failed_reload_recovery():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        leaf = write(root, 'leaf.json', {'mode': 'stable'})
        app = write(root, 'app.json', {'local': 1}, ['leaf.json'])
        manager = ConfigManager(app)
        before = manager.reload()
        write(root, 'app.json', {'local': 2}, ['leaf.json', 'missing.json'])
        try:
            manager.reload()
        except ConfigError as exc:
            assert exc.path == root / 'missing.json'
            assert exc.chain == (app, root / 'missing.json')
        else:
            raise AssertionError('failed graph published')
        assert manager.current == before
        new = write(root, 'missing.json', {'mode': 'recovered'})
        recovered = manager.reload()
        assert recovered.values == {'mode': 'recovered', 'local': 2}
        assert recovered.generation == 2
        assert recovered.dependencies == tuple(sorted([app, leaf, new], key=str))
check('failed-reload-preserves-and-recovers', failed_reload_recovery)

def failed_initial_no_cached_branch():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        write(root, 'first.json', {'mode': 'old'})
        app = write(root, 'app.json', {}, ['first.json', 'absent.json'])
        manager = ConfigManager(app)
        try:
            manager.reload()
        except ConfigError:
            pass
        else:
            raise AssertionError('missing dependency accepted')
        assert manager.current is None
        write(root, 'first.json', {'mode': 'new'})
        write(root, 'absent.json', {'ready': True})
        snapshot = manager.reload()
        assert snapshot.generation == 1 and snapshot.values == {'mode': 'new', 'ready': True}
check('failed-first-load-no-cache-poisoning', failed_initial_no_cached_branch)

def removed_dependency():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        leaf = write(root, 'leaf.json', {'mode': 'stable'})
        app = write(root, 'app.json', {}, ['leaf.json'])
        manager = ConfigManager(app)
        before = manager.reload()
        leaf.unlink()
        try:
            manager.reload()
        except ConfigError as exc:
            assert exc.path == leaf and exc.chain == (app, leaf)
        else:
            raise AssertionError('deleted dependency served from cache')
        assert manager.current == before
        write(root, 'leaf.json', {'mode': 'new'})
        assert manager.reload().values == {'mode': 'new'}
check('deleted-dependency-repair', removed_dependency)

def cycle_after_success():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        app = write(root, 'app.json', {}, ['branch.json'])
        branch = write(root, 'branch.json', {'ok': True})
        manager = ConfigManager(app)
        before = manager.reload()
        write(root, 'branch.json', {}, ['./sub/../app.json'])
        (root / 'sub').mkdir()
        try:
            manager.reload()
        except ConfigError as exc:
            assert exc.path == app and exc.chain == (app, branch, app)
        else:
            raise AssertionError('cycle introduced after success accepted')
        assert manager.current == before
        write(root, 'branch.json', {'ok': False})
        assert manager.reload().values == {'ok': False}
check('canonical-cycle-after-success', cycle_after_success)

def repeated_include_freshness():
    # This observes public values/dependencies, not syscall or document-read counts.
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        leaf = write(root, 'leaf.json', {'nested': {'a': 1}})
        app = write(root, 'app.json', {}, ['leaf.json', './leaf.json'])
        loader = Loader()
        first = loader.load(app)
        assert first.values == {'nested': {'a': 1}}
        assert first.dependencies == tuple(sorted([app, leaf], key=str))
        write(root, 'leaf.json', {'nested': {'a': 2}})
        second = loader.load(app)
        assert second.values == {'nested': {'a': 2}}
        assert second.dependencies == first.dependencies
        assert first.values == {'nested': {'a': 1}}
check('repeated-include-public-freshness', repeated_include_freshness)

def sibling_dependency_accuracy():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        left = write(root, 'left.json', {'left': 1})
        right = write(root, 'right.json', {'right': 2})
        app = write(root, 'app.json', {}, ['left.json', 'right.json'])
        loader = Loader()
        assert loader.load(app).dependencies == tuple(sorted([app, left, right], key=str))
        right_alone = loader.load(right)
        assert right_alone.dependencies == (right,)
        assert right_alone.values == {'right': 2}
check('independent-root-dependency-accuracy', sibling_dependency_accuracy)

def schema_diagnostic_chain():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        app = write(root, 'app.json', {}, ['middle.json'])
        middle = write(root, 'middle.json', {}, ['leaf.json'])
        leaf = root / 'leaf.json'
        for raw in ['{"include": [1]}', '{"values": []}', '{"extra": true}', '{bad', 'null']:
            leaf.write_text(raw, encoding='utf-8')
            try:
                Loader().load(app)
            except ConfigError as exc:
                assert exc.path == leaf and exc.chain == (app, middle, leaf)
            else:
                raise AssertionError('invalid document accepted')
check('schema-errors-retain-include-chain', schema_diagnostic_chain)

print(json.dumps({'manifestations': results}, sort_keys=True))
