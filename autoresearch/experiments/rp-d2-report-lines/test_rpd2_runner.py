"""Offline two-arm staging, installer binding and serial lifecycle contracts."""
import hashlib
import json
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


def snapshot(s, path, account, salt='', seconds=10000, codex_account='offline-codex-account'):
    path.mkdir(mode=0o700)
    files = {'claude.env': b'CLAUDE_CODE_OAUTH_TOKEN=offline\nCLAUDE_CODE_OAUTH_SCOPES=user:profile\n',
             'codex.json': s.auth.encoded(dict(tokens=dict(account_id=codex_account, access_token='offline' + salt)))}
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
        codex_account=app.runtime['codex_account'],
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


@pytest.mark.parametrize('boundary', ['stage', 'renew', 'validate', 'launch'])
def test_codex_only_account_switch_refused(staged, tmp_path, monkeypatch, boundary):
    s, args, path = staged
    manifest = s.read(args.auth / 'manifest.json')
    monkeypatch.setattr(time, 'time', lambda: manifest['expires_at_ms'] / 1000 - 10000)
    foreign = snapshot(s, tmp_path / 'foreign-codex', manifest['account'], codex_account='other-codex-account')
    replacement, _ = s.model_auth(foreign)
    assert replacement == dict(manifest, files=dict(manifest['files'], **{
        'codex.json': replacement['files']['codex.json']}))
    if boundary == 'stage':
        smoke_receipts(s, path)
        args.phase, args.auth = 'measured', foreign
        with pytest.raises(RuntimeError, match='codex_account'):
            s.stage(args)
    elif boundary == 'renew':
        s, _, path = measured(staged)
        before = path.read_bytes()
        with pytest.raises(RuntimeError, match='Codex account'):
            s.renew(path, foreign)
        assert path.read_bytes() == before
        assert not list(path.parent.glob('runtime-measured-auth-*.json'))
    else:
        app = s.runner.Runner(path)
        # A valid replacement manifest must not authorize a different Codex account.
        app.runtime.update(auth=str(foreign), auth_manifest_sha256=s.digest(foreign / 'manifest.json'))
        with pytest.raises(RuntimeError, match='Codex account'):
            if boundary == 'validate':
                app.validate('smoke-codex-X')
            else:
                app.frame.cell_run.run(Path(app.runtime['output']) / 'smoke-codex-X', app.runtime)


def test_staged_codex_identity_is_nonsecret(staged):
    s, _, path = staged
    assert s.read(path)['codex_account'] == hashlib.sha256(b'offline-codex-account').hexdigest()[:12]
    assert 'offline-codex-account' not in path.read_text()
    assert 'access_token' not in path.read_text()


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
def test_installer_plan_and_inherited_policy_bind_each_arm(staged, monkeypatch, arm, engine):
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
    plan = s.read(out / 'plan.json')
    (out / 'run').mkdir()
    event = (dict(type='thread.started', thread_id='offline-owner') if engine == 'codex' else
             dict(type='system', subtype='init', session_id='offline-owner'))
    (out / 'run/stdout').write_text(json.dumps(event) + '\n')
    for generation in ('0255', '0238'):
        entry = next(cls.__dict__['run'] for cls in type(app).__mro__ if 'run' in cls.__dict__ and
                     Path(cls.__dict__['run'].__code__.co_filename).parent.name == generation)
        policy = entry.__globals__['policy']
        assert Path(policy.check.__globals__['base_policy'].__file__).parent.name == '0242'
        result = policy.check(out, plan, app.tasks, app.frame.cell_run.evidence)
        assert result['status'] == 'MATCH'
        assert not result['gaps'] and not result['violations'] and not result['protocol_violations']
        with pytest.raises((ValueError, RuntimeError), match='unregistered rp-d2 arm'):
            policy.check(out, dict(plan, arm='UNKNOWN'), app.tasks, app.frame.cell_run.evidence)
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
    assert updated['codex_account'] == app.runtime['codex_account']
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


@pytest.fixture
def accounting_lifecycle(staged, monkeypatch):
    def setup(*, phase='measured', engine='claude', defect=None, product_failure=None):
        s, _, path = measured(staged) if phase == 'measured' else staged
        r = s.runner
        app = r.Runner(path)
        target = next(name for name, _, config in app.slots() if config == engine)
        events, originals = [], {}

        def event(label):
            events.append(label)
            if defect == label:
                raise r.github.EvidenceError('synthetic ' + label + ' failure')

        def inherited(_self, name, task, route, config):
            assert route == 'B'
            event('owner:' + name)
            out = Path(app.runtime['output']) / name
            (out / 'run').mkdir(parents=True)
            s.write(out / 'run/started.json', {})
            (out / 'run/stdout').write_text('synthetic sealed owner evidence\n')
            s.write(out / 'evidence.manifest.json', dict(failures=[], files={
                'run/started.json': r.digest(out / 'run/started.json'),
                'run/stdout': r.digest(out / 'run/stdout')}))
            verdict = dict(cell=name, task=task, arm=route, config=config, status='CHECKS_PASS',
                usage='COMPLETE', input_tokens=7, output_tokens=3, owner_seconds=12.5,
                owner_status='EXITED_0', identity=dict(status='MATCH', owner='MATCH'),
                peer_policy=dict(status='MATCH', gaps=[], violations=[], protocol_violations=[]),
                teardown='CLEAN', evidence_manifest_sha256=r.digest(out / 'evidence.manifest.json'), snapshot={})
            if name == target:
                verdict.update(status='STOP', reason='ValueError: whole-run usage UNKNOWN',
                    usage='UNKNOWN', input_tokens=None, output_tokens=None,
                    usage_gaps=['error or retry outside scope' if config == 'claude' else
                                'rollout offline-owner has no usable counters'])
                verdict.pop('snapshot')
                if defect == 'identity':
                    verdict['identity']['status'] = 'UNKNOWN'
                elif defect == 'peer':
                    verdict['peer_policy']['gaps'] = ['unbound invocation']
                elif defect == 'teardown':
                    verdict['teardown'] = 'UNKNOWN'
                elif defect == 'seal':
                    verdict['evidence_manifest_sha256'] = 'wrong'
                elif defect == 'evidence':
                    (out / 'run/stdout').write_text('damaged evidence\n')
                elif defect == 'collection':
                    manifest = s.read(out / 'evidence.manifest.json')
                    manifest['failures'] = ['unreadable file']
                    s.write(out / 'evidence.manifest.json', manifest)
                    verdict['evidence_manifest_sha256'] = r.digest(out / 'evidence.manifest.json')
                elif defect == 'accounting-instrumentation':
                    verdict['usage_gaps'].append('native scope inventory failed: ValueError')
                elif defect == 'other-stop':
                    verdict['reason'] = 'ValueError: authentication failed'
                elif defect == 'pat':
                    s.write(out / 'pat-scan.json', dict(revocation_required=True))
                if product_failure == 'owner':
                    verdict['owner_status'] = 'EXITED_1'
                elif product_failure == 'protocol':
                    verdict['peer_policy']['protocol_violations'] = ['protocol failure']
            file = out.parent / f'verdict-{name}.json'
            s.write(file, verdict)
            originals[name] = file.read_bytes()
            return 2 if verdict['status'] == 'STOP' else 0

        def boot(out, config):
            event('boot')
            expected = app.boot_expectation('B', config)
            return {key: sorted(value) for key, value in expected.items()} if expected is not None else {}

        def quota(_):
            event('quota')
            return dict(execution=[dict(fault='auth')] if defect == 'auth' else [])

        def locate(_):
            event('locate')
            return dict(kind='accepted')

        def checks(out, runtime):
            event('checks')
            checked = dict(product_check_pass=product_failure != 'checks', adjudication_needed=False)
            s.write(out / 'checks.json', checked)
            return checked

        def delivery(*_):
            event('delivery')
            return dict(passed=product_failure != 'delivery')

        def archive(repository, root):
            event('archive')
            root.mkdir(parents=True)
            return dict(manifest_sha256='verified archive')

        def done(out, root, selection, locate, packet):
            event('done')
            if out.name == target:
                assert (out / 'checked.json').exists()
                assert selection == dict(kind='accepted')
            return dict(status='PRODUCT_INCOMPLETE' if product_failure == 'preservation' else 'ADJUDICATE',
                        checklist=dict(report='synthetic report', facts=dict(merge='MERGED')))

        def delete(repository, root, manifest):
            event('delete')
            event('404')
            return dict(repository=repository, status='DELETED', http_status=404,
                        archive_manifest_sha256=manifest)

        def scan(out, runtime, *, roots):
            events.append('scan')
            assert out in roots and out.parent / f'verdict-{out.name}.json' in roots
            if defect == 'scan':
                raise ValueError('synthetic PAT scan failure')

        monkeypatch.setattr(r.legacy.legacy.Runner, 'run', inherited)
        monkeypatch.setattr(r.github, 'precheck', lambda _: event('precheck'))
        monkeypatch.setattr(app, 'boot_catalogs', boot)
        monkeypatch.setattr(app.frame.quota, 'classify', quota)
        monkeypatch.setattr(app, 'unchanged', lambda _: event('bindings'))
        monkeypatch.setattr(app.frame.locate, 'locate', locate)
        monkeypatch.setattr(app.frame.check, 'check', checks)
        monkeypatch.setattr(r.legacy.legacy.delivery, 'check', delivery)
        monkeypatch.setattr(r.github, 'archive', archive)
        monkeypatch.setattr(r.github, 'done_check', done)
        monkeypatch.setattr(r.github, 'delete_archived', delete)
        monkeypatch.setattr(r.cell, 'scan', scan)
        return s, app, target, events, originals
    return setup


@pytest.mark.parametrize('engine', ['claude', 'codex'])
@pytest.mark.parametrize('product_failure', [None, 'checks', 'delivery', 'preservation', 'owner', 'protocol'])
def test_measured_accounting_unknown_grades_and_continues_once(accounting_lifecycle, engine, product_failure):
    s, app, target, events, originals = accounting_lifecycle(engine=engine, product_failure=product_failure)
    assert app.schedule() == 0
    output = Path(app.runtime['output'])
    schedule = s.read(output / 'rp-schedule.json')
    row = next(row for row in schedule['slots'] if row['cell'] == target)
    assert row['status'] == ('PRODUCT_INCOMPLETE' if product_failure else 'ADJUDICATE')
    assert row['delivery_assessment'] != 'NOT_ASSESSED'
    assert row['usage'] == 'UNKNOWN' and row['input_tokens'] is row['output_tokens'] is None
    inherited = s.read(output / f'verdict-{target}.json')
    assert inherited['owner_seconds'] == 12.5
    assert inherited['usage'] == 'UNKNOWN' and inherited['input_tokens'] is inherited['output_tokens'] is None
    assert (output / target / 'accounting-stop.json').read_bytes() == originals[target]
    assert inherited['accounting_stop_sha256'] == s.runner.digest(output / target / 'accounting-stop.json')
    assert (output / target / 'report-checklist.json').exists()
    assert schedule['status'] == 'RECORDED' and schedule['dispatched'] == 16
    assert [value for value in events if value.startswith('owner:')] == [
        'owner:' + name for name, _, _ in app.slots()]
    start = events.index('owner:' + target)
    assert events[start:start + 12] == ['owner:' + target, 'boot', 'quota', 'bindings', 'locate',
        'checks', 'delivery', 'archive', 'done', 'delete', '404', 'scan']
    before = list(events)
    assert app.schedule() == 0 and events == before
    task, config = next((task, config) for name, task, config in app.slots() if name == target)
    with pytest.raises(ValueError, match='never replay'):
        app.run(target, task, s.runner.arm_for(target), config)


@pytest.mark.parametrize('defect', ['identity', 'peer', 'teardown', 'seal', 'evidence', 'collection',
    'accounting-instrumentation', 'other-stop', 'pat', 'boot', 'auth', 'bindings', 'locate', 'checks',
    'delivery', 'archive', 'done', 'delete', '404', 'scan'])
def test_accounting_unknown_with_other_defect_stops(accounting_lifecycle, defect):
    s, app, target, events, _ = accounting_lifecycle(defect=defect)
    assert app.schedule() == 2
    rows = s.read(Path(app.runtime['output']) / 'rp-schedule.json')['slots']
    assert rows[0]['cell'] == target
    assert rows[0]['status'] == ('UNKNOWN' if defect in ('pat', 'scan') else 'STOP')
    assert rows[0]['delivery_assessment'] == 'NOT_ASSESSED'
    assert [row['status'] for row in rows[1:]] == ['NOT_RUN'] * 15
    assert [value for value in events if value.startswith('owner:')] == ['owner:' + target]
    assert events[-1] == 'scan'


@pytest.mark.parametrize('engine', ['claude', 'codex'])
def test_smoke_accounting_unknown_still_stops(accounting_lifecycle, engine):
    s, app, target, events, _ = accounting_lifecycle(phase='smoke', engine=engine)
    assert app.schedule() == 2
    output = Path(app.runtime['output'])
    rows = s.read(output / 'rp-schedule.json')['slots']
    index = next(i for i, row in enumerate(rows) if row['cell'] == target)
    assert rows[index]['status'] == 'STOP' and rows[index]['delivery_assessment'] == 'NOT_ASSESSED'
    assert all(row['status'] == 'NOT_RUN' for row in rows[index + 1:])
    assert not (output / target / 'accounting-stop.json').exists()
    assert events[events.index('owner:' + target):] == ['owner:' + target, 'archive', 'delete', '404', 'scan']
