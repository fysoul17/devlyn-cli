"""Offline runtime integration: synthetic archives/auth, no Docker, network or models."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import subprocess
import tarfile
from types import SimpleNamespace
import urllib.request

import pytest

HERE = Path(__file__).resolve().parent
NOW = 1_700_000_000
CLAUDE_ACCOUNT = ['b' * 12, 'c' * 12]


def load(name):
    spec = importlib.util.spec_from_file_location('rpd4_runtime_test_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail('external operation forbidden')
    for target, name in ((socket, 'create_connection'), (urllib.request, 'urlopen'),
                         (subprocess, 'run'), (subprocess, 'Popen'), (subprocess, 'check_output')):
        monkeypatch.setattr(target, name, forbidden)


def snapshot(auth, root, account='synthetic-account', token='synthetic-token'):
    source = root.parent / (root.name + '-source.json')
    source.write_text(json.dumps(dict(auth_mode='chatgpt', tokens=dict(account_id=account,
        access_token=token, refresh_token='synthetic-refresh', id_token='synthetic-id'))))
    auth.bootstrap(source, root)
    return root


def guard_snapshot(auth, root, codex_root, *, expires=NOW + 9000, account=None):
    root.mkdir(mode=0o700)
    files = {'codex.json': (codex_root / 'codex.json').read_bytes(),
             'claude.env': b'CLAUDE_CODE_OAUTH_TOKEN=synthetic-claude\nCLAUDE_CODE_OAUTH_SCOPES=user:profile\n'}
    manifest = dict(schema_version=1, account=account or CLAUDE_ACCOUNT,
                    expires_at_ms=expires * 1000,
                    files={name: auth.digest(raw) for name, raw in files.items()})
    for name, raw in files.items():
        auth.write_private(root, name, raw)
    auth.write_private(root, 'manifest.json', auth.encoded(manifest))
    return root


def artifact(pack, root, monkeypatch):
    source = root / 'registry.tgz'
    before = {name: ('# synthetic ' + name + '\n').encode() for name in pack.FILES}
    after = {name: raw + b'# candidate\n' for name, raw in before.items()}
    with tarfile.open(source, 'w:gz') as archive:
        for name, raw in [('package.json', b'{"name":"devlyn-cli","version":"4.2.22"}'), *before.items()]:
            member = tarfile.TarInfo('package/' + name)
            member.size, member.mode = len(raw), 0o644
            archive.addfile(member, io.BytesIO(raw))
    commit = 'a' * 40
    def git(*args):
        if args == ('rev-parse', '--verify', commit + '^{commit}'):
            return commit.encode()
        name = args[-1].removeprefix(commit + ':')
        return after[name] if args[0] == 'show' else pack.blob_id(after[name]).encode()
    monkeypatch.setattr(pack, 'git', git)
    return pack.build(source, root / 'release', commit, **pack.identity(source))


@pytest.fixture
def staged(tmp_path, monkeypatch):
    s = load('stage')
    arms = artifact(s.pack, tmp_path, monkeypatch)
    home = tmp_path / 'host'
    (home / '.codex').mkdir(parents=True)
    (home / '.codex/models_cache.json').write_text('{"models": []}')
    monkeypatch.setattr(Path, 'home', lambda: home)
    monkeypatch.setattr(s.auth.claude.time, 'time', lambda: NOW)
    monkeypatch.setattr(s.auth.claude, 'profile', lambda _token: CLAUDE_ACCOUNT)
    model = snapshot(s.auth, tmp_path / 'codex-auth')
    guard_codex = snapshot(s.auth, tmp_path / 'guard-codex-source', token='synthetic-guard-token')
    guard = guard_snapshot(s.auth, tmp_path / 'claude-auth', guard_codex)
    gh = tmp_path / 'github-auth'
    gh.mkdir(mode=0o700)
    for name in ('hosts.yml', 'config.yml'):
        s.auth.write_private(gh, name, b'synthetic fixture\n')
    args = SimpleNamespace(stage_dir=tmp_path / 'stage', phase='smoke', run_id='offline', arms=arms,
        image='sha256:' + 'a' * 64, auth=model, claude_auth=guard,
        github_auth=gh, smoke_output=None, smoke_attempt=1)
    monkeypatch.setattr(s.runner.cell, 'credential', lambda _: pytest.fail('real PAT read forbidden'))
    return s, args, s.stage(args)


def record(s, app, name, task, engine):
    arm = s.runner.arm_for(name)
    active = s.auth.for_engine(app.base_runtime, engine)
    return dict(cell=name, task=task, config=engine, arm=arm, status='ADJUDICATE', dispatched=True,
        phase=app.runtime['phase'], measurement_eligible=app.runtime['phase'] == 'measured',
        release=s.runner.prepare.release_identity(app.runtime, arm), prompt_sha256=s.runner.prepare.PROMPT_SHA256[arm],
        account=active['account'], codex_account=app.runtime['codex_account'],
        auth=active['auth'], auth_manifest_sha256=active['auth_manifest_sha256'], frozen_runtime_sha256=app.frozen,
        delivery_assessment='ADJUDICATE', smoke_qualification={'status': 'PASS'}, merge_refused=False,
        repository_cleanup=dict(repository=app.repository(name), status='DELETED', http_status=404,
                                archive_manifest_sha256='a' * 64))


def append_record(s, app, slot):
    out = Path(app.runtime['output']) / slot[0]
    out.mkdir()
    s.write(out / 'rp-verdict.json', record(s, app, *slot))


def measured(staged):
    s, args, path = staged
    app = s.runner.Runner(path)
    for slot in app.slots():
        append_record(s, app, slot)
    args.phase = 'measured'
    return s, args, s.stage(args)


def test_registered_schedule_names_arms_and_exact_common_prompt(staged):
    s, _, path = staged
    r = s.runner
    assert r.SCHEDULE == [(f'm{i:02}', 'BV' if i <= 4 else 'Z0', 'codex') for i in range(1, 9)] + [
        ('g01', 'BV', 'claude'), ('g02', 'Z0', 'claude')]
    assert [r.arm_for(slot[0]) for slot in r.SCHEDULE] == ['X', 'Y', 'Y', 'X', 'X', 'Y', 'Y', 'X', 'Y', 'Y']
    assert r.smoke_slots() == [('smoke-codex-X', 'SM', 'codex'), ('smoke-codex-Y', 'SM', 'codex')]
    assert r.smoke_slots(2) == [('smoke2-codex-X', 'SM', 'codex'), ('smoke2-codex-Y', 'SM', 'codex')]
    app = r.Runner(path)
    assert app.tasks['routes']['claude']['owner'] == dict(engine='claude', model='claude-opus-5-5', effort='max')
    assert app.tasks['routes']['codex']['owner']['model'] == 'gpt-6-sol'
    assert app.tasks['routes']['codex']['owner']['effort'] == 'high'
    names = [app.repository(slot[0]) for slot in r.SCHEDULE + r.smoke_slots() + r.smoke_slots(2)]
    assert len(set(names)) == 14
    assert all(name.startswith('fysoul17/rpd4-offline-') for name in names)
    assert app.remaining('m03') == [app.repository(slot[0]) for slot in r.SCHEDULE[2:]]
    for name in ('m09', 'g03', 'smoke-claude-Y', 'smoke3-codex-X', 'smoke-codex-P0'):
        with pytest.raises(RuntimeError):
            app.repository(name)
    raw = (r.prepare.PRIOR / 'common.txt').read_bytes()
    for arm in ('X', 'Y'):
        assert r.prepare.prompt_body(arm) == raw
        assert r.prepare.PROMPT_SHA256[arm] == hashlib.sha256(raw).hexdigest()
        caller = {'request': 'synthetic'}
        assert r.prepare.native_prompt(caller, arm).encode() == raw + b'\nCALLER CONTRACT\n' + json.dumps(caller, indent=2).encode()


@pytest.mark.parametrize('attempt', [0, 3, True, '2'])
def test_smoke_has_one_initial_and_one_spare_attempt(attempt):
    with pytest.raises(RuntimeError):
        load('runner').smoke_slots(attempt)


def test_auth_transports_are_separate_and_guard_profile_only(staged, monkeypatch):
    s, args, path = staged
    runtime = s.read(path)
    codex_manifest, _ = s.auth.model_auth(args.auth)
    claude_manifest, _ = s.auth.claude_model_auth(args.claude_auth)
    assert 'expires_at_ms' not in codex_manifest
    assert claude_manifest['expires_at_ms'] == (NOW + 9000) * 1000
    assert (args.auth / 'claude.env').read_bytes() == b''
    assert runtime['account'] == runtime['codex_account'] == hashlib.sha256(b'synthetic-account').hexdigest()[:12]
    assert runtime['claude_account'] == CLAUDE_ACCOUNT
    calls = []
    monkeypatch.setattr(s.auth.claude, 'profile', lambda token: calls.append('profile') or CLAUDE_ACCOUNT)
    assert s.auth.preflight(s.auth.for_engine(runtime, 'codex'))[1] is None
    assert calls == []
    assert s.auth.preflight(s.auth.for_engine(runtime, 'claude'))[1] is None
    assert calls == ['profile']
    assert 'synthetic-token' not in path.read_text()
    assert 'synthetic-claude' not in path.read_text()
    with pytest.raises(ValueError):
        s.auth.for_engine(runtime, 'unknown')


@pytest.mark.parametrize('remaining,allowed', [(6299, False), (6300, True), (6301, True)])
def test_6300_second_floor_applies_only_to_claude(staged, tmp_path, remaining, allowed):
    s, args, path = staged
    runtime = s.read(path)
    guard = guard_snapshot(s.auth, tmp_path / 'expiry-auth', args.auth, expires=NOW + remaining)
    manifest, binding = s.auth.claude_model_auth(guard)
    runtime.update(claude_auth=str(guard), claude_auth_manifest_sha256=binding,
                   claude_account=manifest['account'])
    assert s.auth.preflight(s.auth.for_engine(runtime, 'codex'))[1] is None
    assert (s.auth.preflight(s.auth.for_engine(runtime, 'claude'))[1] is None) == allowed


@pytest.mark.parametrize('engine,fault', [('codex', 'account'), ('codex', 'manifest'), ('codex', 'env'),
                                        ('codex', 'mode'), ('claude', 'account'), ('claude', 'manifest'),
                                        ('claude', 'codex_account'), ('claude', 'profile')])
def test_auth_failures_refuse_before_dispatch(staged, monkeypatch, engine, fault):
    s, args, path = staged
    runtime = s.auth.for_engine(s.read(path), engine)
    if fault == 'account':
        runtime['account'] = '0' * 12 if engine == 'codex' else ['0' * 12, '1' * 12]
    elif fault == 'manifest':
        runtime['auth_manifest_sha256'] = '0' * 64
    elif fault == 'codex_account':
        runtime['codex_account'] = '0' * 12
    elif fault == 'profile':
        monkeypatch.setattr(s.auth.claude, 'profile', lambda _token: ['0' * 12, '1' * 12])
    else:
        target = args.auth / ('claude.env' if fault == 'env' else 'codex.json')
        target.chmod(0o600)
        if fault == 'env':
            target.write_bytes(b'nonempty foreign content')
            target.chmod(0o400)
    venue, blocked = s.auth.preflight(runtime)
    assert venue is None and blocked
    assert 'synthetic-' not in blocked


@pytest.mark.parametrize('arm', ['X', 'Y'])
@pytest.mark.parametrize('fault', ['missing', 'delivery', 'qualification', 'prompt', 'release', 'archive', '404'])
def test_measured_requires_both_qualified_selected_smoke_cells(staged, arm, fault):
    s, args, path = staged
    app = s.runner.Runner(path)
    for slot in app.slots():
        row = record(s, app, *slot)
        if row['arm'] == arm:
            if fault == 'missing':
                continue
            if fault == 'delivery':
                row.update(status='PRODUCT_INCOMPLETE', delivery_assessment='PRODUCT_INCOMPLETE')
            elif fault == 'qualification':
                row.pop('smoke_qualification')
            elif fault == 'prompt':
                row['prompt_sha256'] = '0' * 64
            elif fault == 'release':
                row['release']['sha256'] = '0' * 64
            elif fault == 'archive':
                row['repository_cleanup']['archive_manifest_sha256'] = ''
            else:
                row['repository_cleanup']['http_status'] = 200
        out = Path(app.runtime['output']) / slot[0]
        out.mkdir()
        s.write(out / 'rp-verdict.json', row)
    args.phase = 'measured'
    with pytest.raises((RuntimeError, ValueError, FileNotFoundError)):
        s.stage(args)
    assert not (args.stage_dir / 'runtime-measured.json').exists()


def test_extracted_release_binding_covers_both_replacement_files(staged):
    s, _, path = staged
    runtime = s.read(path)
    s.runner.prepare.verify_release(runtime)
    for name in s.pack.FILES:
        installed = Path(runtime['control']) / 'packages/Y/package' / name
        before = installed.read_bytes()
        installed.write_bytes(before + b'drift')
        with pytest.raises(RuntimeError, match='extracted release'):
            s.runner.prepare.verify_release(runtime)
        installed.write_bytes(before)


def test_guard_and_codex_schedule_pause_after_four_pairs_then_resume(staged, monkeypatch):
    s, _, path = measured(staged)
    app = s.runner.Runner(path)
    calls = []
    def inherited(_self, name, task, route, engine):
        assert route == 'B'
        assert app.check_auth(app.runtime)
        expected = app.base_runtime['claude_auth' if engine == 'claude' else 'auth']
        assert app.runtime['auth'] == expected
        calls.append((name, engine))
        out = Path(app.runtime['output']) / name
        assert not out.exists(), 'slot replayed'
        out.mkdir()
        s.write(out / 'rp-verdict.json', record(s, app, name, task, engine))
        return 0
    monkeypatch.setattr(s.runner.legacy.legacy.Runner, 'run', inherited)
    monkeypatch.setattr(s.runner.smoke, 'merge_refused', lambda _out: False)
    assert app.schedule(1) == 0
    assert len(calls) == 2
    assert app.schedule(4) == 0
    assert len(calls) == 8
    assert s.read(Path(app.runtime['output']) / 'rp-schedule.json')['status'] == 'PAUSED'
    assert app.schedule() == 0
    assert calls == [(name, engine) for name, _, engine in s.runner.SCHEDULE]
    assert s.read(Path(app.runtime['output']) / 'rp-schedule.json')['status'] == 'RECORDED'
    assert app.schedule() == 0
    assert len(calls) == 10
    for limit in (0, 5, True, '1'):
        with pytest.raises(RuntimeError, match='1..4'):
            app.schedule(limit)


@pytest.mark.parametrize('phase', ['smoke', 'measured'])
def test_stop_consumes_remaining_slots_and_never_replays(staged, monkeypatch, phase):
    s, _, path = measured(staged) if phase == 'measured' else staged
    app = s.runner.Runner(path)
    calls = []
    def inherited(_self, name, task, _route, engine):
        calls.append(name)
        out = Path(app.runtime['output']) / name
        out.mkdir()
        s.write(out / 'rp-verdict.json', dict(record(s, app, name, task, engine), status='STOP'))
        return 2
    monkeypatch.setattr(s.runner.legacy.legacy.Runner, 'run', inherited)
    monkeypatch.setattr(s.runner.smoke, 'merge_refused', lambda _out: False)
    assert app.schedule() == 2
    rows = s.read(Path(app.runtime['output']) / 'rp-schedule.json')['slots']
    assert [row['status'] for row in rows] == ['STOP'] + ['NOT_RUN'] * (len(app.slots()) - 1)
    for row in rows:
        app.record_binding(row)
    assert app.schedule() == 2
    assert len(calls) == 1


def test_y_smoke_qualification_failure_stops_pair(staged, monkeypatch):
    s, _, path = staged
    app = s.runner.Runner(path)
    def inherited(_self, name, task, _route, engine):
        out = Path(app.runtime['output']) / name
        out.mkdir()
        s.write(out / 'rp-verdict.json', record(s, app, name, task, engine))
        s.write(out / 'report-checklist.json', {})
        return 0
    def unqualified(_out):
        raise ValueError('synthetic action/sentence mismatch')
    monkeypatch.setattr(s.runner.legacy.legacy.Runner, 'run', inherited)
    monkeypatch.setattr(s.runner.smoke, 'merge_refused', lambda _out: False)
    monkeypatch.setattr(s.runner.smoke, 'qualify', unqualified)
    assert app.schedule() == 2
    rows = s.read(Path(app.runtime['output']) / 'rp-schedule.json')['slots']
    assert [row['status'] for row in rows] == ['ADJUDICATE', 'STOP']
    assert rows[0]['smoke_qualification']['status'] == 'PASS'


@pytest.mark.parametrize('completed_count', range(11))
def test_renewal_is_limited_to_complete_pair_boundaries(staged, completed_count):
    s, _, path = staged
    previous = dict(s.read(path), phase='measured')
    rows = [dict(status='ADJUDICATE') for _ in range(completed_count)]
    if completed_count in (0, 2, 4, 6, 8):
        s.renewal_allowed(previous, previous['codex_account'], rows)
    else:
        with pytest.raises(RuntimeError, match='between measured pairs'):
            s.renewal_allowed(previous, previous['codex_account'], rows)


def test_renewal_preserves_originals_and_requires_both_same_accounts(staged, tmp_path):
    s, args, path = measured(staged)
    app = s.runner.Runner(path)
    for slot in s.runner.SCHEDULE[:2]:
        append_record(s, app, slot)
    replacement = snapshot(s.auth, tmp_path / 'renewed', token='synthetic-renewal')
    guard = guard_snapshot(s.auth, tmp_path / 'renewed-guard', replacement, expires=NOW + 9500)
    original = path.read_bytes()
    renewed = s.renew(path, replacement, guard)
    assert path.read_bytes() == original
    assert s.runner.frozen_runtime(s.read(renewed)) == s.runner.frozen_runtime(s.read(path))
    resumed = s.runner.Runner(renewed)
    resumed.prior_deleted('m03')
    with pytest.raises(RuntimeError, match='within a pair'):
        resumed.prior_deleted('m02')
    foreign = snapshot(s.auth, tmp_path / 'foreign', account='different-synthetic-account')
    with pytest.raises(RuntimeError, match='Codex account'):
        s.renew(path, foreign)
    foreign_guard = guard_snapshot(s.auth, tmp_path / 'foreign-guard', args.auth, account=['d' * 12, 'e' * 12])
    with pytest.raises(RuntimeError, match='identical Claude'):
        s.renew(path, claude_auth_path=foreign_guard)
    wrong_transport = guard_snapshot(s.auth, tmp_path / 'wrong-transport', foreign)
    with pytest.raises(RuntimeError, match='identical Claude'):
        s.renew(path, claude_auth_path=wrong_transport)


@pytest.mark.parametrize('engine', ['codex', 'claude'])
def test_renewal_refuses_snapshots_inside_stage(staged, engine):
    s, _, path = measured(staged)
    unsafe = path.parent / 'new-auth'
    kwargs = {'auth_path' if engine == 'codex' else 'claude_auth_path': unsafe}
    with pytest.raises(RuntimeError, match='model auth.*disjoint'):
        s.renew(path, **kwargs)
    assert not unsafe.exists()


def test_renewal_refuses_stopped_schedule(staged):
    s, _, path = staged
    previous = dict(s.read(path), phase='measured')
    with pytest.raises(RuntimeError, match='stopped schedule'):
        s.renewal_allowed(previous, previous['codex_account'], [dict(status='STOP'), dict(status='NOT_RUN')])


def test_guard_selected_codex_snapshot_is_scanned_before_sealing(staged, monkeypatch, capsys):
    s, args, path = measured(staged)
    app = s.runner.Runner(path)
    for slot in s.runner.SCHEDULE[:8]:
        append_record(s, app, slot)
    token = json.loads((args.claude_auth / 'codex.json').read_bytes())['tokens']['access_token']
    assert token != json.loads((args.auth / 'codex.json').read_bytes())['tokens']['access_token']
    monkeypatch.setattr(s.runner.cell, 'credential', lambda _: (args.github_auth, b'github_pat_synthetic'))
    def inherited(_self, name, _task, _route, _engine):
        out = Path(app.runtime['output']) / name
        out.mkdir()
        (out / 'stdout').write_text(token)
        app.frame.seal_after_teardown(out)
        pytest.fail('leaked evidence reached sealing')
    monkeypatch.setattr(s.runner.legacy.legacy.Runner, 'run', inherited)
    monkeypatch.setitem(app.frame.seal_after_teardown.keywords, 'inherited',
                        lambda _out: pytest.fail('leaked evidence was sealed'))
    with pytest.raises(ValueError) as error:
        app.run('g01', 'BV', 'Y', 'claude')
    assert token not in str(error.value)
    assert capsys.readouterr().out == ''
    assert not (Path(app.runtime['output']) / 'g01/evidence-manifest.json').exists()
    assert app.frame.seal_after_teardown.keywords['runtime'] == app.base_runtime


@pytest.mark.parametrize('phase,arm,engine,observed', [
    ('smoke', 'Y', 'codex', True), ('smoke', 'X', 'codex', False),
    ('measured', 'Y', 'codex', False), ('measured', 'Y', 'claude', False)])
def test_materializer_binds_both_files_and_limits_observer(tmp_path, monkeypatch, phase, arm, engine, observed):
    p = load('prepare')
    out = tmp_path / 'slot'
    (out / 'harness').mkdir(parents=True)
    (out / 'cell/work').mkdir(parents=True)
    release = dict(version='4.2.22', sha256='a' * 64, integrity='synthetic-integrity',
                   source={'registry': 'devlyn-cli@4.2.22'}, manifest_sha256='b' * 64)
    runtime = dict(phase=phase, control=str(tmp_path / 'control'), releases={arm: release})
    installed = {}
    for name in p.pack.FILES:
        raw = ('# synthetic ' + name).encode()
        source = Path(runtime['control']) / 'packages' / arm / 'package' / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(raw)
        relative = '.agents' + name.removeprefix('config')
        target = out / 'cell/work' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        installed[relative] = hashlib.sha256(raw).hexdigest()
    caller = {'request': 'synthetic'}
    (out / 'harness/caller.json').write_text(json.dumps(caller, indent=2))
    prompt = p.native_prompt(caller, arm)
    (out / 'prompt.txt').write_text(prompt)
    identity = dict(arm=arm, release=release)
    p.github.write(out / 'plan.json', dict(identity, engine=engine, task='SM' if phase == 'smoke' else 'BV',
                   env={'PYTHONPATH': 'src:/control/python'}, argv=['synthetic', prompt]))
    p.github.write(out / 'baseline.json', dict(identity, installed_files=installed,
                   prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest()))
    monkeypatch.setattr(p.legacy, 'prepare', lambda *_args, **_kwargs: out)
    assert p.prepare(runtime, 'slot', 'SM', arm, engine) == out
    plan = p.github.read(out / 'plan.json')
    assert ('helper_observer' in plan) is observed
    assert (out / 'harness/sitecustomize.py').exists() is observed
    assert plan['env']['PYTHONPATH'] == ('/harness:' if observed else '') + 'src:/control/python'
    p.binding(out, runtime, arm)
    helper = next(name for name in installed if name.endswith('task-complete.py'))
    (out / 'cell/work' / helper).write_text('changed helper')
    with pytest.raises(RuntimeError, match='installed helper/reporting instruction'):
        p.binding(out, runtime, arm)

