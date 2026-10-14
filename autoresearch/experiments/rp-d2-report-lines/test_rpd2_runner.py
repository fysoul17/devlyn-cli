"""Offline two-arm staging, installer binding and serial lifecycle contracts."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import time
from types import SimpleNamespace

import pytest

from test_rpd2_pack import fixture, load


@pytest.fixture
def staged(tmp_path, monkeypatch):
    s = load('stage')
    source, _, _, commit = fixture(s.pack, tmp_path, monkeypatch)
    arms = s.pack.build(source, tmp_path / 'arms', commit)
    home = tmp_path / 'host'
    (home / '.codex').mkdir(parents=True)
    (home / '.codex/models_cache.json').write_text('{"models": []}')
    monkeypatch.setattr(Path, 'home', lambda: home)
    account = ['a' * 12, 'b' * 12]
    model = snapshot(s, tmp_path / 'auth', account)
    github_auth = tmp_path / 'github-auth'
    github_auth.mkdir(mode=0o700)
    for name in ('hosts.yml', 'config.yml'):
        s.auth.write_private(github_auth, name, b'not a credential\n')
    args = SimpleNamespace(stage_dir=tmp_path / 'stage', phase='smoke', run_id='offline', arms=arms,
        image='sha256:' + 'a' * 64, auth=model, github_auth=github_auth, smoke_output=None, smoke_attempt=1)
    real_run = subprocess.run
    def offline(argv, **kwargs):
        assert argv[0] == 'git', 'external process forbidden: ' + str(argv[0])
        assert not any(value in argv for value in ('push', 'fetch', 'clone', 'ls-remote'))
        return real_run(argv, **kwargs)
    monkeypatch.setattr(subprocess, 'run', offline)
    monkeypatch.setattr(s.runner.cell, 'credential', lambda _: pytest.fail('real PAT read forbidden'))
    path = s.stage(args)
    return s, args, path


def snapshot(s, path, account, salt='', seconds=10000):
    path.mkdir(mode=0o700)
    files = {'claude.env': b'CLAUDE_CODE_OAUTH_TOKEN=offline\nCLAUDE_CODE_OAUTH_SCOPES=user:profile\n',
             'codex.json': ('{"synthetic":' + repr(salt).replace("'", '"') + '}').encode()}
    manifest = dict(schema_version=1, account=account, expires_at_ms=(time.time() + seconds) * 1000,
                    files={name: hashlib.sha256(data).hexdigest() for name, data in files.items()})
    for name, data in (files | {'manifest.json': s.auth.encoded(manifest)}).items():
        s.auth.write_private(path, name, data)
    return path


def record(s, app, name, task, engine):
    arm = s.runner.arm_for(name)
    return dict(cell=name, task=task, config=engine, arm=arm, status='ADJUDICATE', dispatched=True,
        phase=app.runtime['phase'], measurement_eligible=app.runtime['phase'] == 'measured',
        release=s.runner.prepare.release_identity(app.runtime, arm), account=app.runtime['account'],
        auth=app.runtime['auth'], auth_manifest_sha256=app.runtime['auth_manifest_sha256'],
        frozen_runtime_sha256=app.frozen, repository_cleanup=dict(repository=app.repository(name),
            status='DELETED', http_status=404, archive_manifest_sha256='a' * 64))


def smoke_receipts(s, path):
    app = s.runner.Runner(path)
    output = Path(app.runtime['output'])
    for name, task, engine in app.slots():
        (output / name).mkdir()
        s.write(output / name / 'rp-verdict.json', record(s, app, name, task, engine))
        if engine == 'claude':
            s.write(output / f'verdict-{name}.json', dict(boot_catalogs=dict(
                skills=['devlyn-ideate', s.runner.arm_for(name)], plugins=[], mcp_servers=[])))


def measured(staged):
    s, args, smoke = staged
    smoke_receipts(s, smoke)
    args.phase = 'measured'
    return s, args, s.stage(args)


def test_schedule_order_arms_smoke_names_and_repositories(staged):
    s, _, path = staged
    r = s.runner
    assert r.PAIRS == [('BV', 'claude'), ('BV', 'codex'), ('Z0', 'codex'), ('Z0', 'claude'),
                       ('Z0', 'claude'), ('Z0', 'codex'), ('BV', 'codex'), ('BV', 'claude')]
    assert [name for name, _, _ in r.SCHEDULE] == [f'm{i:02}' for i in range(1, 17)]
    for index in range(8):
        pair = r.SCHEDULE[index * 2:index * 2 + 2]
        assert [(task, engine) for _, task, engine in pair] == [r.PAIRS[index]] * 2
        assert [r.arm_for(name) for name, _, _ in pair] == (['X', 'Y'] if index % 2 == 0 else ['Y', 'X'])
    assert r.smoke_slots() == [('smoke-claude-X', 'SM', 'claude'), ('smoke-claude-Y', 'SM', 'claude'),
                              ('smoke-codex-X', 'SM', 'codex'), ('smoke-codex-Y', 'SM', 'codex')]
    app = r.Runner(path)
    names = [row[0] for row in r.smoke_slots() + r.smoke_slots(2) + r.SCHEDULE]
    assert len({app.repository(name) for name in names}) == 24
    assert app.remaining('smoke-claude-X') == [app.repository(row[0]) for row in r.smoke_slots() + r.SCHEDULE]
    assert app.remaining('m03') == [app.repository(row[0]) for row in r.SCHEDULE[2:]]
    for invalid in ('fysoul17/rpd1-offline-o01', 'other/rpd2-offline-m01', 'fysoul17/rpd2-offline-m17',
                    'fysoul17/rpd2-offline-smoke3-claude-X', 'fysoul17/rpd2-offline-smoke-codex-B'):
        with pytest.raises(RuntimeError, match='repository'):
            r.github.url(invalid)
    for attempt in (0, 3, True, '2'):
        with pytest.raises(ValueError, match='smoke_attempt'):
            r.smoke_slots(attempt)


def test_stage_check_both_arms_and_per_arm_boot_catalogs(staged, monkeypatch):
    s, args, smoke = staged
    monkeypatch.setattr(subprocess, 'check_output', lambda argv, **_: args.image + '\n')
    s.check(smoke)
    before = {p: p.read_bytes() for p in args.stage_dir.rglob('*') if p.is_file()}
    s, args, path = measured(staged)
    s.check(path)
    runtime = s.read(path)
    assert runtime['boot_catalogs']['claude']['X']['skills'][-1] == 'X'
    assert runtime['boot_catalogs']['claude']['Y']['skills'][-1] == 'Y'
    assert set(runtime['releases']) == {'X', 'Y'}
    assert not (args.stage_dir / 'control/packages/B').exists()
    for file, raw in before.items():
        assert file.read_bytes() == raw
    runtime['boot_catalogs']['claude']['Y'] = runtime['boot_catalogs']['claude']['X']
    s.write(path, runtime)
    with pytest.raises(RuntimeError, match='catalogs differ'):
        s.check(path)


def test_stage_refuses_account_change_since_smoke(staged, tmp_path):
    s, args, smoke = staged
    smoke_receipts(s, smoke)
    args.phase = 'measured'
    args.auth = snapshot(s, tmp_path / 'foreign-auth', ['c' * 12, 'b' * 12])
    with pytest.raises(RuntimeError, match='account'):
        s.stage(args)


def test_release_tree_tampering_or_swapped_arms_fails(staged):
    s, _, path = staged
    runtime = s.read(path)
    runtime['releases']['X'], runtime['releases']['Y'] = runtime['releases']['Y'], runtime['releases']['X']
    with pytest.raises(RuntimeError, match='release mismatch'):
        s.runner.prepare.verify_release(runtime)
    runtime = s.read(path)
    package = Path(runtime['control']) / 'packages/Y/package' / s.pack.FILE
    package.write_bytes(package.read_bytes() + b'drift')
    with pytest.raises(RuntimeError, match='extracted release'):
        s.runner.prepare.verify_release(runtime)


def test_launch_refuses_model_cache_changed_between_arms(staged):
    s, _, path = staged
    app = s.runner.Runner(path)
    Path(app.runtime['models_cache']).write_text('{"models": ["different"]}')
    with pytest.raises(RuntimeError, match='models cache changed'):
        app.validate('smoke-claude-X')


def test_spare_smoke_stages_fresh_and_supplies_its_own_catalogs(staged, tmp_path, monkeypatch):
    s, args, first = staged
    original = first.read_bytes()
    args.stage_dir, args.smoke_attempt = tmp_path / 'stage2', 2
    second = s.stage(args)
    app = s.runner.Runner(second)
    assert all(name.startswith('smoke2-') for name, _, _ in app.slots())
    assert len(app.slots()) == 4
    smoke_receipts(s, second)
    args.phase = 'measured'
    path = s.stage(args)
    monkeypatch.setattr(subprocess, 'check_output', lambda *_a, **_k: args.image + '\n')
    s.check(path)
    assert s.read(path)['smoke_attempt'] == 2
    assert first.read_bytes() == original


@pytest.mark.parametrize('arm,engine', [('X', 'claude'), ('Y', 'claude'), ('X', 'codex'), ('Y', 'codex')])
def test_unchanged_installer_mount_and_plan_bind_each_arm(staged, monkeypatch, arm, engine):
    s, _, path = staged
    app = s.runner.Runner(path)
    name = f'smoke-{engine}-{arm}'
    calls = []
    real_run = subprocess.run
    def docker(argv, **kwargs):
        if argv[:3] == ['docker', 'image', 'inspect']:
            return subprocess.CompletedProcess(argv, 0, app.runtime['image'] + '\n', '')
        if argv[:2] == ['docker', 'run']:
            calls.append(argv)
            mount = next(value for value in argv if value.endswith(',dst=/work'))
            work = Path(mount.removeprefix('type=bind,src=').removesuffix(',dst=/work'))
            target = work / ('.claude' if engine == 'claude' else '.agents') / 'skills/_shared/task-completion.md'
            target.parent.mkdir(parents=True)
            shutil.copyfile(Path(app.runtime['control']) / 'packages' / arm / 'package' / s.pack.FILE, target)
            return subprocess.CompletedProcess(argv, 0, b'', b'')
        return real_run(argv, **kwargs)
    monkeypatch.setattr(subprocess, 'run', docker)
    monkeypatch.setattr(s.runner.github, 'seed', lambda *_: None)
    app.active_arm = arm
    out = app.prepare(name, 'SM', 'B', engine)
    assert len(calls) == 1
    assert f'type=bind,src={app.runtime["control"]}/packages/{arm},dst=/install,readonly' in calls[0]
    assert calls[0][-2:] == (['-y', '--claude'] if engine == 'claude' else ['/install/package/bin/devlyn.js', '-y'])
    for file in ('plan.json', 'baseline.json'):
        row = s.read(out / file)
        assert row['arm'] == arm
        assert row['release']['sha256'] == app.runtime['releases'][arm]['sha256']
    app.unchanged(out)
    s.runner.prepare.binding(out, app.runtime, arm)
    baseline = s.read(out / 'baseline.json')
    installed = next(name for name in baseline['installed_files'] if name.endswith('task-completion.md'))
    other = 'Y' if arm == 'X' else 'X'
    shutil.copyfile(Path(app.runtime['control']) / 'packages' / other / 'package' / s.pack.FILE,
                    out / 'cell/work' / installed)
    with pytest.raises(RuntimeError, match='differs from attempt arm'):
        app.frame.cell_run.run(out, app.runtime)
    plan = s.read(out / 'plan.json')
    s.write(out / 'plan.json', dict(plan, arm=other))
    with pytest.raises(RuntimeError, match='binding mismatch'):
        s.runner.prepare.binding(out, app.runtime, arm)


def test_wrong_scheduled_arm_refused_before_lifecycle(staged, monkeypatch):
    s, _, path = staged
    app = s.runner.Runner(path)
    monkeypatch.setattr(s.runner.legacy.Runner, 'run', lambda *_: pytest.fail('must not dispatch'))
    with pytest.raises(RuntimeError, match='slot/task/engine/arm'):
        app.run('smoke-claude-X', 'SM', 'Y', 'claude')


def test_all_four_smoke_deletion_receipts_required(staged):
    s, _, path = measured(staged)
    app = s.runner.Runner(path)
    app.prior_deleted('m01')
    for name, _, _ in s.runner.smoke_slots():
        file = Path(app.runtime['smoke_output']) / name / 'rp-verdict.json'
        original = s.read(file)
        for changed in (dict(original, status='PRODUCT_INCOMPLETE'), dict(original, account=['c' * 12, 'b' * 12]),
                        dict(original, repository_cleanup=dict(original['repository_cleanup'], http_status=403))):
            s.write(file, changed)
            with pytest.raises(RuntimeError):
                app.prior_deleted('m01')
        s.write(file, original)


def test_renewal_same_accounts_only_between_complete_pairs(staged, tmp_path):
    s, _, path = measured(staged)
    app = s.runner.Runner(path)
    first, second = s.runner.SCHEDULE[:2]
    out = Path(app.runtime['output'])
    replacement = snapshot(s, tmp_path / 'new-auth', app.runtime['account'], salt='renewed')
    for slot in (first, second):
        (out / slot[0]).mkdir()
        s.write(out / slot[0] / 'rp-verdict.json', record(s, app, *slot))
        if slot == first:
            with pytest.raises(RuntimeError, match='between measured pairs'):
                s.renew(path, replacement)
    before = path.read_bytes()
    renewed = s.renew(path, replacement)
    assert path.read_bytes() == before
    updated = s.read(renewed)
    assert s.runner.frozen_runtime(updated) == s.runner.frozen_runtime(s.read(path))
    assert updated['auth'] == str(replacement)
    resumed = s.runner.Runner(renewed)
    resumed.prior_deleted('m03')
    with pytest.raises(RuntimeError, match='within a pair'):
        resumed.prior_deleted('m02')
    foreign = snapshot(s, tmp_path / 'foreign', ['a' * 12, 'c' * 12])
    with pytest.raises(RuntimeError, match='identical account pair'):
        s.renew(path, foreign)
    changed = s.read(out / 'm02/rp-verdict.json')
    s.write(out / 'm02/rp-verdict.json', dict(changed, status='STOP'))
    with pytest.raises(RuntimeError, match='stopped schedule'):
        s.renew(path, replacement)


def test_launch_retains_6300_second_floor(staged, monkeypatch):
    s, _, path = staged
    app = s.runner.Runner(path)
    auth = app.preflight.__func__.__globals__['auth']
    manifest = s.read(Path(app.runtime['auth']) / 'manifest.json')
    monkeypatch.setattr(auth, 'profile', lambda _: app.runtime['account'])
    monkeypatch.setattr(auth.time, 'time', lambda: manifest['expires_at_ms'] / 1000 - 6299)
    assert app.preflight()[1] == 'frozen-auth-lifetime-below-6300-seconds'
    monkeypatch.setattr(auth.time, 'time', lambda: manifest['expires_at_ms'] / 1000 - 6300)
    assert app.preflight()[1] is None
    # 0251 rechecks this same callback after preparation, before Docker create.
    with pytest.raises(ValueError, match='fixed authentication refused before launch'):
        out = Path(app.runtime['output']) / 'dummy'
        out.mkdir()
        s.write(out / 'plan.json', {})
        s.runner.cell.legacy.run(out, app.runtime, native=None,
            check_auth=lambda _: (None, 'frozen-auth-lifetime-below-6300-seconds'))


@pytest.mark.parametrize('failure', ['precheck', 'accounting', 'scan', None])
def test_inherited_lifecycle_stop_scans_and_cleanup_order(staged, monkeypatch, failure):
    s, _, path = measured(staged)
    r = s.runner
    app = r.Runner(path)
    events = []
    def precheck(remaining):
        assert remaining == app.remaining(remaining[0].rsplit('-', 1)[-1])
        events.append('precheck')
        if failure == 'precheck':
            raise r.github.EvidenceError('last repository is not empty')
    def inherited(_self, name, task, route, engine):
        assert route == 'B'
        events.append('launch')
        out = Path(app.runtime['output']) / name
        (out / 'run').mkdir(parents=True)
        s.write(out / 'run/started.json', {})
        s.write(out.parent / f'verdict-{name}.json', dict(status='STOP' if failure == 'accounting' else 'CHECKS_PASS',
            reason='whole-run usage UNKNOWN', usage='UNKNOWN' if failure == 'accounting' else 'COMPLETE',
            input_tokens=7, output_tokens=3, teardown='CLEAN', evidence_manifest_sha256='seal', snapshot={}))
    def archive(repository, root):
        events.append('archive')
        root.mkdir(parents=True)
        return dict(manifest_sha256='sealed archive')
    def done(*_):
        events.append('grade')
        return dict(status='ADJUDICATE', checklist={})
    def delete(repository, *_):
        events.append('verified-delete-404')
        return dict(repository=repository, status='DELETED', http_status=404, archive_manifest_sha256='sealed archive')
    def scan(out, runtime, *, roots):
        events.append('final-scan')
        assert not (out / 'rp-verdict.json').exists()
        if failure != 'precheck':
            assert out.parent / 'archives' / out.name in roots
            assert out.parent / f'verdict-{out.name}.json' in roots
        if failure == 'scan':
            raise ValueError('synthetic scanner failure')
    monkeypatch.setattr(r.github, 'precheck', precheck)
    monkeypatch.setattr(r.legacy.legacy.Runner, 'run', inherited)
    monkeypatch.setattr(r.github, 'archive', archive)
    monkeypatch.setattr(r.github, 'done_check', done)
    monkeypatch.setattr(r.github, 'delete_archived', delete)
    monkeypatch.setattr(r.cell, 'scan', scan)
    if failure is None:
        assert app.schedule() == 0
        assert events == ['precheck', 'launch', 'archive', 'grade', 'verified-delete-404', 'final-scan'] * 16
        for name, task, engine in r.SCHEDULE:
            with pytest.raises(ValueError, match='never replay'):
                app.run(name, task, r.arm_for(name), engine)
    else:
        assert app.schedule() == 2
        rows = s.read(Path(app.runtime['output']) / 'rp-schedule.json')['slots']
        assert [row['status'] for row in rows] == ['UNKNOWN' if failure == 'scan' else 'STOP'] + ['NOT_RUN'] * 15
        assert [row['arm'] for row in rows] == [r.arm_for(row[0]) for row in r.SCHEDULE]
        assert events[-1] == 'final-scan'
        if failure == 'accounting':
            assert 'grade' not in events
            assert 'verified-delete-404' in events


def test_pair_pause_resume_and_stop_never_replay(staged, monkeypatch):
    s, _, path = measured(staged)
    app = s.runner.Runner(path)
    calls = []
    def run(name, task, arm, config):
        calls.append(name)
        out = Path(app.runtime['output']) / name
        out.mkdir()
        s.write(out / 'rp-verdict.json', record(s, app, name, task, config))
        return 0
    monkeypatch.setattr(app, 'run', run)
    assert app.schedule(1) == 0
    assert calls == ['m01', 'm02']
    assert s.read(Path(app.runtime['output']) / 'rp-schedule.json')['status'] == 'PAUSED'
    assert app.schedule(2) == 0
    assert calls == ['m01', 'm02', 'm03', 'm04']
