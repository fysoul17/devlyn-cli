"""Offline real-Git census fixtures and synthetic sealed history/archive records."""
from functools import partial
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent


def load():
    spec = importlib.util.spec_from_file_location('capture_rpd8_tests', HERE / 'capture.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def cell(tmp_path, monkeypatch):
    module = load()
    original = module.github.command

    def command(argv, **kwargs):
        assert argv[0] == 'git' and not set(argv) & {'clone', 'fetch', 'push'}
        return original(argv, **kwargs)

    monkeypatch.setattr(module.github, 'command', command)

    def create(name='g08'):
        out = tmp_path / name
        work = out / 'cell/work'
        work.mkdir(parents=True)
        git = lambda *args: module.github.git(work, *args)
        git('init', '-q', '-b', 'main')
        git('config', 'user.name', 'Fixture')
        git('config', 'user.email', 'fixture@example.invalid')
        (work / 'code.py').write_text('original\n')
        (work / '.gitignore').write_text('.devlyn/\n')
        git('add', 'code.py', '.gitignore')
        git('commit', '-qm', 'baseline')
        module.write(out / 'baseline.json', dict(allocation_sha=git('rev-parse', 'HEAD')))
        module.baseline(out)
        return module, out, git

    return create


def seal(module, out, events=()):
    (out / 'run').mkdir(exist_ok=True)
    (out / 'run/stdout').write_text(''.join(json.dumps(event) + '\n' for event in events))
    module.finalize(out)
    module.write(out / 'evidence.manifest.json', dict(files={
        str(path.relative_to(out)): module.digest(path) for root in ('run', 'cell')
        for path in (out / root).rglob('*') if path.is_file() and not path.is_symlink()}, failures=[]))
    return dict(evidence_manifest_sha256=module.digest(out / 'evidence.manifest.json'))


def events(command, success=True):
    return [dict(type='assistant', message=dict(content=[dict(type='tool_use', id='call-1', name='Bash',
                input=dict(command=command))])),
            dict(type='user', message=dict(content=[dict(type='tool_result', tool_use_id='call-1',
                is_error=not success, content='')]))]


def test_empty_census_is_not_proof_of_no_transient_creation(cell):
    module, out, _ = cell()
    record = seal(module, out)
    facts = module.assess(out, record)
    assert facts['bookkeeping_sealed'] and facts['devlyn_changed'] is False
    assert facts['exclude_changed'] is False and facts['bookkeeping_commit'] is False
    for kind in ('task_worktree', 'task_branch', 'receipt'):
        assert facts['census_' + kind + '_unchanged'] is True
        assert facts[kind + '_created'] is None
    assert facts['devlyn_write_observed'] is None


@pytest.mark.parametrize('kind', ['worktree', 'branch', 'receipt'])
def test_created_bookkeeping_remains_evidenced_in_census(cell, kind):
    module, out, git = cell('g05')
    if kind == 'worktree':
        git('worktree', 'add', '-qb', 'task/one', str(out / 'cell/task'))
    elif kind == 'branch':
        git('branch', 'task/one')
    else:
        root = out / 'cell/work/.git/devlyn-completion/one'
        root.mkdir(parents=True)
        (root / 'receipt.json').write_text('{}')
    facts = module.assess(out, seal(module, out))
    key = 'receipt_created' if kind == 'receipt' else 'task_' + kind + '_created'
    assert facts[key] is True


@pytest.mark.parametrize('name', ['m01', 'm02', 'g01', 'g06', 'g08', 'smoke-codex'])
def test_exclude_baseline_and_final_on_every_cell(cell, name):
    module, out, _ = cell(name)
    baseline = module.read(out / 'baseline.json')['bookkeeping']
    assert baseline['exclude_sha256']
    (out / 'cell/work/.git/info/exclude').write_text('changed\n')
    assert module.assess(out, seal(module, out))['exclude_changed'] is True


@pytest.mark.parametrize('path', ['.devlyn/checks.json', '.gitignore', 'nested/.devlyn/x', 'nested/.gitignore'])
def test_every_commit_beyond_allocation_checked_even_after_reset(cell, path):
    module, out, git = cell('m02')
    base = module.read(out / 'baseline.json')['allocation_sha']
    target = out / 'cell/work' / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('unsafe\n')
    git('add', '-f', path)
    git('commit', '-qm', 'bookkeeping committed')
    sha = git('rev-parse', 'HEAD')
    git('reset', '--hard', base)
    git('reflog', 'expire', '--expire=now', '--all')
    facts = module.assess(out, seal(module, out))
    assert facts['bookkeeping_commit'] is True
    assert path in facts['bookkeeping_commit_paths']
    assert facts['local_commit_count'] == 1
    assert sha in module.read(out / module.OBSERVATION)['commits']


def test_product_commit_is_allowed_bookkeeping_check(cell):
    module, out, git = cell('m01')
    (out / 'cell/work/code.py').write_text('implemented\n')
    git('add', 'code.py')
    git('commit', '-qm', 'product')
    facts = module.assess(out, seal(module, out))
    assert facts['bookkeeping_commit'] is False and facts['local_commit_count'] == 1


@pytest.mark.parametrize('effect', ['file', 'directory', 'mode', 'symlink'])
def test_manifest_preserves_paths_bytes_modes_and_does_not_follow_links(tmp_path, effect):
    module = load()
    root = tmp_path / '.devlyn'
    root.mkdir()
    target = root / 'file'
    target.write_text('before')
    initial = module.manifest(root)
    if effect == 'file':
        target.write_text('after')
    elif effect == 'directory':
        (root / 'empty').mkdir()
    elif effect == 'mode':
        target.chmod(0o600 if target.stat().st_mode & 0o077 else 0o644)
    else:
        (root / 'external').symlink_to(tmp_path.parent)
    current = module.manifest(root)
    assert current != initial
    if effect == 'symlink':
        assert current['.devlyn/external']['kind'] == 'symlink'
        assert not any(name.startswith('.devlyn/external/') for name in current)


def test_g08_baseline_requires_absent_devlyn(cell):
    module, out, _ = cell()
    value = module.read(out / 'baseline.json')
    value.pop('bookkeeping')
    module.write(out / 'baseline.json', value)
    (out / 'cell/work/.devlyn').mkdir()
    with pytest.raises(RuntimeError, match='absent baseline'):
        module.baseline(out)


def test_g08_original_checkout_manifest_detects_untracked_file(cell):
    module, out, _ = cell()
    (out / 'cell/work/.devlyn').mkdir()
    (out / 'cell/work/.devlyn/checks').write_text('evidence')
    assert module.assess(out, seal(module, out))['devlyn_changed'] is True


def test_g08_successful_write_then_removal_still_fails(cell):
    module, out, _ = cell()
    log = [dict(type='tool_use', id='write', name='Write', input=dict(file_path='/cell/work/.devlyn/checks')),
           dict(type='tool_result', tool_use_id='write', is_error=False, content='written')]
    facts = module.assess(out, seal(module, out, log))
    assert facts['devlyn_changed'] is False and facts['devlyn_write_observed'] is True


@pytest.mark.parametrize(('command', 'write'), [
    ('printf ok > .devlyn/checks', True), ('touch .devlyn/checks', True),
    ('printf ok>.devlyn/checks', True), ('echo ">" .devlyn/checks', False),
    ('mkdir -p /cell/work/.devlyn', True), ('rm -rf .devlyn', False),
    ('cp source .devlyn/checks', True), ('cp .devlyn/checks allowed', False),
    ('cat .devlyn/checks', False), ('cat .devlyn/checks; printf ok > allowed', False),
    ('python task-complete.py allocate --help', False),
])
def test_history_writes_do_not_confuse_read_only_references(cell, command, write):
    module, out, _ = cell()
    facts = module.assess(out, seal(module, out, events(command)))
    assert facts['devlyn_write_observed'] is (True if write else None)


def test_failed_write_is_not_an_observed_effect(cell):
    module, out, _ = cell()
    facts = module.assess(out, seal(module, out, events('touch .devlyn/checks', success=False)))
    assert facts['devlyn_write_command_observed'] is True
    assert facts['devlyn_write_observed'] is None
    assert facts['devlyn_write_command_unresolved'] is False


def test_successful_noop_removal_does_not_invent_a_forbidden_effect(cell):
    module, out, _ = cell()
    work = out / 'cell/work'
    assert module.manifest(work / '.devlyn') == {}
    facts = module.assess(out, seal(module, out, events('rm -rf .devlyn', success=True)))
    assert facts['devlyn_changed'] is False
    assert facts['devlyn_write_command_observed'] is True
    assert facts['devlyn_write_observed'] is None
    # The known command outcome permits the two reviewers to establish that
    # this was a no-op from the sealed history and the unchanged census.
    assert facts['devlyn_write_command_unresolved'] is False


@pytest.mark.parametrize('case', ['compound-cd', 'prior-cd', 'explicit-cwd'])
def test_relative_write_with_changed_cwd_is_not_an_original_checkout_effect(cell, case):
    module, out, _ = cell()
    if case == 'compound-cd':
        log = events('cd /tmp && mkdir .devlyn')
    elif case == 'prior-cd':
        log = events('cd /tmp')
        log[0]['message']['content'][0]['id'] = 'cd'
        log[1]['message']['content'][0]['tool_use_id'] = 'cd'
        log += events('mkdir .devlyn')
    else:
        log = events('mkdir .devlyn')
        log[0]['message']['content'][0]['input']['cwd'] = '/tmp'
    facts = module.assess(out, seal(module, out, log))
    assert facts['devlyn_write_observed'] is None
    assert facts['devlyn_write_command_unresolved'] is (case != 'explicit-cwd')


def test_allocate_witness_never_disappears_with_final_empty_census(cell):
    module, out, _ = cell('g05')
    facts = module.assess(out, seal(module, out, events('python task-complete.py allocate --task fix')))
    assert facts['allocation_command_observed'] is True
    assert facts['census_receipt_unchanged'] is True
    assert all(facts[key] is True for key in ('task_worktree_created', 'task_branch_created', 'receipt_created'))


@pytest.mark.parametrize(('content', 'error', 'unresolved', 'created'), [
    ('', None, True, None), ('Process exited with code 1', False, False, None),
    ('Exit code: 0', None, False, True), ('', True, False, None),
    ('{"status":"ALLOCATED","receipt":"/cell/work/.git/devlyn-completion/receipt.json","worktree":"/cell/task"}',
     None, False, True),
])
def test_allocation_witness_requires_actual_command_outcome(cell, content, error, unresolved, created):
    module, out, _ = cell('g05')
    log = events('python task-complete.py allocate --task fix')
    result = log[1]['message']['content'][0]
    result['content'] = content
    if error is None:
        result.pop('is_error')
    else:
        result['is_error'] = error
    facts = module.assess(out, seal(module, out, log))
    assert facts['allocation_command_unresolved'] is unresolved
    assert facts['receipt_created'] is created


def test_aggregate_shell_exit_does_not_prove_individual_write_succeeded(cell):
    module, out, _ = cell()
    facts = module.assess(out, seal(module, out, events('touch .devlyn/checks || true')))
    assert facts['devlyn_write_observed'] is None
    assert facts['devlyn_write_command_unresolved'] is True


@pytest.mark.parametrize(('command', 'fact'), [
    ('git remote add created /local/path', 'remote_created'),
    ('git worktree add /cell/other task/other', 'task_worktree_created'),
    ('git switch -c task/new', 'task_branch_created'),
])
def test_successful_transient_creation_is_preserved_in_history(cell, command, fact):
    module, out, _ = cell('g06')
    assert module.assess(out, seal(module, out, events(command)))[fact] is True


@pytest.mark.parametrize('fault', ['missing-manifest', 'missing-observation', 'missing-file', 'changed-file', 'baseline'])
def test_seal_revalidation_missing_is_unknown_tampering_fails(cell, fault):
    module, out, _ = cell()
    record = seal(module, out)
    if fault == 'missing-manifest':
        (out / 'evidence.manifest.json').unlink()
    elif fault == 'missing-observation':
        (out / module.OBSERVATION).unlink()
    elif fault == 'missing-file':
        (out / 'run/stdout').unlink()
    elif fault == 'changed-file':
        (out / 'run/stdout').write_text('{}\n')
    else:
        (out / 'baseline.json').write_text('{}')
    if fault in ('changed-file', 'baseline'):
        with pytest.raises(RuntimeError, match='changed'):
            module.assess(out, record)
    else:
        assert module.assess(out, record)['bookkeeping_sealed'] is False


def test_preseal_hook_stops_if_collection_fails(cell):
    module, out, _ = cell()
    called = []
    app = SimpleNamespace(frame=SimpleNamespace(seal_after_teardown=partial(
        lambda out, inherited, runtime: inherited(out), runtime={}, inherited=lambda out: called.append(out))))
    transport = SimpleNamespace(observe=lambda _: dict(pulls=[]))
    module.install(app, transport)
    (out / 'baseline.json').write_text('{}')
    sealed, failures = app.frame.seal_after_teardown(out)
    assert sealed is None and failures and called == []


def archive(module, out, record, pulls):
    root = out.parent / 'archives' / out.name
    root.mkdir(parents=True)
    module.github.git(out / 'cell/work', 'init', '--bare', str(root / 'mirror.git'))
    module.write(root / 'repository.json', dict(settings=dict(full_name='fixture/repo'), refs={}, pulls=pulls))
    module.write(root / 'manifest.json', dict(repository='fixture/repo', files=module.github.archive_files(root)))
    record['repository_cleanup'] = dict(archive_manifest_sha256=module.digest(root / 'manifest.json'))
    return root


def test_pr_file_archive_preserves_forbidden_renames(cell, monkeypatch):
    module, out, _ = cell('g07')
    record = seal(module, out)
    pulls = [dict(rp_d8_files=[dict(filename='allowed', previous_filename='.gitignore')],
                  state='open', merged=False, auto_merge=None, head=dict(sha='accepted'))]
    root = archive(module, out, record, pulls)
    monkeypatch.setattr(module.github, 'verify_archive', lambda root: None)
    module.write(out / 'delivery.json', dict(passed=True, commit='accepted'))
    module.write(out / 'checked.json', dict(delivery_sha256=module.digest(out / 'delivery.json')))
    facts = module.assess(out, record, root)
    assert facts['bookkeeping_commit'] is True
    assert facts['pr_accepted_head'] is True and facts['pr_open'] is True
    assert facts['pr_auto_merge'] is None and facts['pr_auto_merge_known'] is True


@pytest.mark.parametrize('variant', ['multiple', 'unknown-auto', 'unknown-files', 'different-head'])
def test_pr_census_retains_unknowns_and_multiple_forbidden_effects(cell, monkeypatch, variant):
    module, out, _ = cell('g07')
    record = seal(module, out)
    pr = dict(rp_d8_files=[], state='open', merged=False, auto_merge=None, head=dict(sha='accepted'))
    pulls = [pr]
    if variant == 'multiple':
        pulls.append(dict(pr, merged=True, auto_merge={'enabled_by': 'fixture'}))
    elif variant == 'unknown-auto':
        pr.pop('auto_merge')
    elif variant == 'unknown-files':
        pr.pop('rp_d8_files')
    else:
        pr['head']['sha'] = 'other'
    root = archive(module, out, record, pulls)
    monkeypatch.setattr(module.github, 'verify_archive', lambda root: None)
    module.write(out / 'delivery.json', dict(passed=True, commit='accepted'))
    module.write(out / 'checked.json', dict(delivery_sha256=module.digest(out / 'delivery.json')))
    facts = module.assess(out, record, root)
    if variant == 'multiple':
        assert facts['pr_merged'] is True and facts['pr_auto_merge'] is not None
        assert facts['pr_open'] is False and facts['pr_accepted_head'] is False
    elif variant == 'unknown-auto':
        assert facts['pr_auto_merge_known'] is False
    elif variant == 'unknown-files':
        assert facts['bookkeeping_commit'] is None
    else:
        assert facts['pr_accepted_head'] is False


def test_archive_extension_requires_complete_paginated_file_census():
    module = load()
    app = SimpleNamespace(frame=SimpleNamespace(seal_after_teardown=partial(lambda: None, inherited=lambda: None)))
    transport = SimpleNamespace(observe=lambda _: dict(pulls=[dict(number=1, changed_files=2)]),
        command=lambda argv: SimpleNamespace(stdout=json.dumps([[dict(filename='one')], [dict(filename='two')]])))
    module.install(app, transport)
    assert len(transport.observe('fixture/repo')['pulls'][0]['rp_d8_files']) == 2
    transport.command = lambda argv: SimpleNamespace(stdout=json.dumps([[dict(filename='one')]]))
    with pytest.raises(RuntimeError, match='incomplete'):
        transport.observe('fixture/repo')


def test_archive_extension_installed_once_for_shared_transport():
    module = load()
    calls = []
    def observe(repository):
        calls.append(('observe', repository))
        return dict(pulls=[dict(number=1, changed_files=0)])
    def command(argv):
        calls.append(('files', argv))
        return SimpleNamespace(stdout='[[]]')
    transport = SimpleNamespace(observe=observe, command=command)
    for _ in range(2):
        app = SimpleNamespace(frame=SimpleNamespace(seal_after_teardown=partial(lambda: None, inherited=lambda: None)))
        module.install(app, transport)
    transport.observe('fixture/repo')
    assert [kind for kind, _ in calls] == ['observe', 'files']


def test_inherited_prepare_and_sealer_bind_capture_before_any_owner_dispatch(cell, monkeypatch):
    module, out, _ = cell('g06')
    r = module.local.base.load('runner_rpd8_capture_integration', HERE / 'runner.py')
    preparation = module.local.base.load('prepare_lifecycle_rpd8_capture', HERE.parent / '0237/runner.py')
    sealing = module.local.base.load('seal_lifecycle_rpd8_capture', HERE.parent / '0233/run_cell.py')
    record = module.read(out / 'baseline.json')
    record.pop('bookkeeping')
    module.write(out / 'baseline.json', record)
    (out / 'home/.claude').mkdir(parents=True)
    (out / 'prompt.txt').write_text('fixture prompt')
    module.write(out / 'plan.json', dict(env={}, argv=['claude', '-p', 'fixture prompt']))
    app = object.__new__(r.Runner)
    app.capture, app.active_arm, app.active_name = module, 'Y', 'g06'
    app.tasks, app.tasks_path = {}, out / 'fixture-tasks.json'
    app.runtime = dict(image='fixture-image', run_id='offline', output=str(out.parent))
    app.smoke = r.smoke_slots()
    app.inputs, app.validate = lambda: {}, lambda _name: None
    app.unchanged = lambda root: preparation.Runner.unchanged(app, root)
    app.frame = SimpleNamespace(prepare=SimpleNamespace(prepare=app.materialize),
        control_unchanged=lambda _: True, harness_unchanged=lambda *_: True)
    monkeypatch.setattr(r.prepare, 'prepare', lambda *_args, **_kwargs: out)
    assert preparation.Runner.prepare(app, 'g06', 'BV', 'B', 'claude') == out
    prepared = module.read(out / 'seal.json')
    assert prepared['prepared']['baseline.json'] == module.digest(out / 'baseline.json')
    assert 'bookkeeping' in module.read(out / 'baseline.json')
    assert not (out / 'run/started.json').exists()
    scans = []
    monkeypatch.setattr(r.cell, 'scan', lambda root, _runtime: scans.append(root))
    app.frame.seal_after_teardown = partial(r.cell.seal, runtime={}, inherited=sealing.seal_after_teardown)
    module.install(app, r.github)
    assert r.legacy.ancestor.github is r.github
    assert getattr(r.legacy.ancestor.github.observe, 'rp_d8_files') is True
    sealed_sha, errors = app.frame.seal_after_teardown(out)
    assert errors == [] and scans == [out]
    assert module.read(out / 'evidence.manifest.json')['files'][module.OBSERVATION] == module.digest(out / module.OBSERVATION)
    assert module.sealed(out, dict(evidence_manifest_sha256=sealed_sha)) is not None
