"""Real local Git fixtures; every network, seed and container boundary is blocked."""
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import shutil
from types import SimpleNamespace
import urllib.request

import pytest

HERE = Path(__file__).resolve().parent


def load():
    spec = importlib.util.spec_from_file_location('rpd6_local_tests', HERE / 'local_only.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def local_cell(tmp_path, monkeypatch):
    module = load()
    commands = []
    original = subprocess.run
    def command(argv, **kwargs):
        commands.append(list(argv))
        assert argv[0] == 'git' and not any(arg in ('push', 'fetch', 'clone') for arg in argv)
        return original(argv, **kwargs)
    def forbidden(*_args, **_kwargs):
        pytest.fail('external boundary crossed')
    monkeypatch.setattr(subprocess, 'run', command)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    for method in ('seed', 'precheck', 'api', 'archive', 'delete_archived'):
        monkeypatch.setattr(module.github, method, forbidden)
    git = module.base.bootstrap_git
    def tree(work):
        names = module.github.git(work, 'ls-files').splitlines()
        return {name: hashlib.sha256((work / name).read_bytes()).hexdigest() + ':100644' for name in names}
    def source(_task, _runtime, work, _base):
        work.mkdir()
        git(work, 'init', '-q', '-b', 'main')
        git(work, 'config', 'user.name', 'Fixture')
        git(work, 'config', 'user.email', 'fixture@example.invalid')
        (work / 'code.py').write_text('original\n')
        (work / '.user-state').mkdir()
        (work / '.user-state/draft.txt').write_text('preserve\n')
        (work / '.git/info/exclude').write_text('.user-state/\n')
        git(work, 'add', 'code.py')
        git(work, 'commit', '-qm', 'fixture')
    def install(_runtime, work, _home, config, arm):
        assert (config, arm) == ('claude', 'Y')
        (work / 'CLAUDE.md').write_text('candidate instructions\n')
        git(work, 'add', 'CLAUDE.md')
        git(work, 'commit', '-qm', 'install')
    inherited = SimpleNamespace(source=source, install=install,
        committed_tree=lambda work, _sha: tree(work),
        packet=SimpleNamespace(tree=tree, allowed=lambda name, allowed: name in allowed),
        native_prompt=lambda caller: 'common\nCALLER CONTRACT\n' + json.dumps(caller, indent=2))
    cache = tmp_path / 'frozen-models.json'
    cache.write_text('{}')
    tasks = dict(tasks=[dict(id='BV', request='fixture', obligations=[], allowed=['code.py'], public_checks=[])],
        routes=dict(claude=dict(owner=dict(engine='claude', model='claude-opus-5-5', effort='high'))),
        watchdog_seconds=dict(owner=5400))
    tasks_path = tmp_path / 'tasks.json'
    tasks_path.write_text(json.dumps(tasks))
    runtime = dict(output=str(tmp_path / 'output'), models_cache=str(cache),
                   control=str(tmp_path / 'control'), auth=str(tmp_path / 'private'), image='synthetic-image')
    out = module.prepare(runtime, 'g06', 'BV', 'Y', 'claude', inherited=inherited,
                         tasks=tasks, tasks_path=tasks_path)
    return module, out, runtime, commands


def test_g06_never_configures_remote_or_tracking_ref(local_cell):
    module, out, _, commands = local_cell
    assert module.storage(out) == dict(remotes=[], remote_refs=[])
    for argv in commands:
        assert not ('remote' in argv and any(action in argv for action in ('add', 'set-url')))
        assert not any('refs/remotes/' in arg for arg in argv)
    baseline = module.read(out / 'baseline.json')
    assert baseline['transport'] == dict(repository=None, local=dict(remotes=[], remote_refs=[]))
    assert module.harness_unchanged(out, baseline)
    assert module.read(out / 'plan.json')['effort'] == 'high'
    assert (out / 'home/.codex/models_cache.json').read_bytes() == b'{}'


def test_remote_creation_is_observed_product_failure_not_hidden(local_cell):
    module, out, _, _ = local_cell
    # A local path suffices to demonstrate unauthorized remote creation, without network.
    module.github.git(out / 'cell/work', 'remote', 'add', 'unexpected', '/synthetic/remote')
    assert module.storage(out)['remotes'] == ['unexpected']
    assert module.harness_unchanged(out, module.read(out / 'baseline.json'))


@pytest.mark.parametrize('fault', ['caller', 'roles', 'include', 'foreign-storage'])
def test_no_origin_retains_harness_and_storage_invariants(local_cell, fault):
    module, out, _, _ = local_cell
    baseline = module.read(out / 'baseline.json')
    if fault in ('caller', 'roles'):
        (out / 'harness' / (fault + '.json')).write_text('{}')
        assert not module.harness_unchanged(out, baseline)
    else:
        if fault == 'include':
            module.github.git(out / 'cell/work', 'config', 'include.path', '/synthetic/config')
        else:
            (out / 'cell/work/.git/commondir').write_text('/synthetic/storage')
        with pytest.raises(RuntimeError):
            module.harness_unchanged(out, baseline)


def test_local_archive_binds_commit_and_seal_without_github(local_cell):
    module, out, _, _ = local_cell
    work = out / 'cell/work'
    (work / 'code.py').write_text('implemented\n')
    module.base.bootstrap_git(work, 'add', 'code.py')
    module.base.bootstrap_git(work, 'commit', '-qm', 'task')
    sha = module.github.git(work, 'rev-parse', 'HEAD')
    root = out.parent / 'archives/g06'
    result = module.archive(out, root, dict(snapshot=dict(kind='accepted', sha=sha), evidence_manifest_sha256='seal'))
    assert result['manifest_sha256'] == module.digest(root / 'manifest.json')
    observation = module.read(root / 'local-only.json')
    assert observation['local_commit_count'] == 1 and observation['remotes'] == []
    assert observation['repository'] is None and observation['evidence_manifest_sha256'] == 'seal'
    assert not (root / 'repository.json').exists()


def test_local_run_preserves_cost_and_scans_archive(local_cell):
    module, fixture_out, runtime, _ = local_cell
    # Give run() an unused slot root; a stub native lifecycle supplies sealed fixture evidence.
    runtime['output'] = str(fixture_out.parent.parent / 'run-output')
    app = SimpleNamespace(runtime=runtime, prior_deleted=lambda name: None)
    observed = []
    def lower(name, _task, arm, _config):
        assert arm == 'B'
        out = Path(runtime['output']) / name
        import shutil
        shutil.copytree(fixture_out, out)
        (out / 'run').mkdir()
        module.write(out / 'run/started.json', {})
        module.write(out.parent / ('verdict-' + name + '.json'), dict(status='PRODUCT_INCOMPLETE',
            usage='COMPLETE', input_tokens=11, output_tokens=7, teardown='CLEAN', evidence_manifest_sha256='seal', snapshot={}))
    def scan(_out, _runtime, *, roots):
        observed.extend(roots)
    assert module.run(app, 'g06', 'BV', 'claude', lower, scan) == 0
    row = module.read(Path(runtime['output']) / 'g06/rp-verdict.json')
    assert row['usage'] == 'COMPLETE' and row['input_tokens'] == 11
    assert row['repository_cleanup']['status'] == 'NOT_APPLICABLE'
    assert Path(runtime['output']) / 'archives/g06' in observed


@pytest.mark.parametrize('fault', ['none', 'read-mode', 'anchor-content', 'index-flag', 'retained', 'sentinel'])
def test_local_preservation_checks_raw_anchor_and_retained_trees(local_cell, fault):
    module, out, _, _ = local_cell
    anchor = out / 'cell/work'
    snapshot = out / 'snapshot'
    snapshot.mkdir()
    for name in ('code.py', 'CLAUDE.md'):
        shutil.copyfile(anchor / name, snapshot / name)
    if fault == 'read-mode':
        (snapshot / 'CLAUDE.md').chmod(0o600)
    elif fault == 'anchor-content':
        (anchor / 'CLAUDE.md').write_text('damaged outside scope')
    elif fault == 'index-flag':
        module.github.git(anchor, 'update-index', '--assume-unchanged', 'CLAUDE.md')
        (anchor / 'CLAUDE.md').write_text('hidden damage')
    elif fault == 'retained':
        retained = out / 'cell/retained'
        shutil.copytree(snapshot, retained)
        (retained / 'CLAUDE.md').write_text('retained damage')
        registration = anchor / '.git/worktrees/retained'
        registration.mkdir(parents=True)
        (registration / 'gitdir').write_text('/cell/retained/.git')
    elif fault == 'sentinel':
        (anchor / '.user-state/draft.txt').unlink()
    result = module.preservation(out)
    assert result['scope_violations'] == (['CLAUDE.md'] if fault in
                                         ('anchor-content', 'index-flag', 'retained') else [])
    assert result['user_data_harm'] is (fault == 'sentinel')
