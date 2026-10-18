"""Offline lifecycle oracle: synthetic archives/snapshots, no external operations."""
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
ACCOUNT = ['b' * 12, 'c' * 12]


def load(name, path=None):
    spec = importlib.util.spec_from_file_location('rpd5_lifecycle_' + name, path or HERE / (name + '.py'))
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


def archive(pack, root):
    path = root / 'registry.tgz'
    with tarfile.open(path, 'w:gz') as stream:
        for name, raw in [('package.json', b'{"name":"devlyn-cli","version":"4.2.22"}'),
                          *((name, ('# synthetic ' + name + '\n').encode()) for name in pack.FILES)]:
            member = tarfile.TarInfo('package/' + name)
            member.size, member.mode = len(raw), 0o644
            stream.addfile(member, io.BytesIO(raw))
    return path


def snapshot(auth, root, *, account=ACCOUNT, expires=NOW + 9000, token='synthetic-claude'):
    root.mkdir(mode=0o700)
    files = {'codex.json': json.dumps(dict(auth_mode='chatgpt', tokens=dict(account_id='synthetic-account',
        access_token='synthetic-access', refresh_token='synthetic-refresh', id_token='synthetic-id'))).encode(),
        'claude.env': ('CLAUDE_CODE_OAUTH_TOKEN=' + token + '\nCLAUDE_CODE_OAUTH_SCOPES=user:profile\n').encode()}
    manifest = dict(schema_version=1, account=account, expires_at_ms=expires * 1000,
                    files={name: auth.digest(raw) for name, raw in files.items()})
    for name, raw in files.items():
        auth.write_private(root, name, raw)
    auth.write_private(root, 'manifest.json', auth.encoded(manifest))
    return root


@pytest.fixture
def staged(tmp_path, monkeypatch):
    s = load('stage')
    source = archive(s.pack, tmp_path)
    arms = s.pack.build(source, tmp_path / 'release', **s.pack.identity(source))
    host = tmp_path / 'host'
    (host / '.codex').mkdir(parents=True)
    (host / '.codex/models_cache.json').write_text('{"models": []}')
    monkeypatch.setattr(Path, 'home', lambda: host)
    monkeypatch.setattr(s.auth.claude.time, 'time', lambda: NOW)
    monkeypatch.setattr(s.auth.claude, 'profile', lambda _token: ACCOUNT)
    model = snapshot(s.auth, tmp_path / 'claude-auth')
    gh = tmp_path / 'github-auth'
    gh.mkdir(mode=0o700)
    for name in ('hosts.yml', 'config.yml'):
        s.auth.write_private(gh, name, b'synthetic fixture\n')
    args = SimpleNamespace(stage_dir=tmp_path / 'stage', phase='smoke', run_id='offline', arms=arms,
        image='sha256:' + 'a' * 64, auth=model, github_auth=gh, smoke_output=None, smoke_attempt=1)
    return s, args, s.stage(args)


def record(s, app, name, task, config):
    return dict(cell=name, task=task, config=config, arm='X', effort=s.runner.effort_for(name),
        status='ADJUDICATE', dispatched=True, phase=app.runtime['phase'],
        measurement_eligible=app.runtime['phase'] == 'measured',
        release=s.runner.prepare.release_identity(app.runtime, 'X'), prompt_sha256=s.runner.prepare.PROMPT_SHA256['X'],
        account=app.runtime['account'], codex_account=app.runtime['codex_account'],
        auth=app.runtime['auth'], auth_manifest_sha256=app.runtime['auth_manifest_sha256'],
        frozen_runtime_sha256=app.frozen, delivery_assessment='ADJUDICATE',
        smoke_qualification={'status': 'PASS'}, effort_binding='MATCH', merge_refused=False,
        repository_cleanup=dict(repository=app.repository(name), status='DELETED', http_status=404,
                                archive_manifest_sha256='a' * 64))


def append_record(s, app, slot):
    out = Path(app.runtime['output']) / slot[0]
    out.mkdir()
    s.write(out / 'rp-verdict.json', record(s, app, *slot))


def measured(staged):
    s, args, path = staged
    app = s.runner.Runner(path)
    append_record(s, app, app.slots()[0])
    args.phase = 'measured'
    return s, args, s.stage(args)


def analysis(*, status='MATCH', effort='MATCH', stages=None):
    return dict(status=status, effort_binding=effort, stages=stages or [dict(stage='Other', turns=1)])


def fake_inherited(s, app, monkeypatch):
    calls = []
    def inherited(name, task, config):
        calls.append(name)
        assert app.tasks == s.runner.slot_tasks(app.runtime['phase'], name)
        out = Path(app.runtime['output']) / name
        out.mkdir()
        s.write(out / 'rp-verdict.json', record(s, app, name, task, config))
        s.write(out.parent / ('verdict-' + name + '.json'),
                dict(owner_seconds=12.5, evidence_manifest_sha256='a' * 64))
        (out / 'retained.jsonl').write_text('synthetic sealed evidence\n')
        return 0
    monkeypatch.setattr(app, 'inherited_run', inherited)
    monkeypatch.setattr(s.runner.smoke, 'merge_refused', lambda _out: False)
    original = s.runner.load
    monkeypatch.setattr(s.runner, 'load', lambda name, path: SimpleNamespace(analyze=lambda *_a, **_k: analysis())
                        if name == 'attribute_rpd5_runner' else original(name, path))
    return calls


def test_schedule_prompt_names_and_per_slot_effort_projection(staged):
    s, _, path = staged
    app = s.runner.Runner(path)
    assert s.runner.SCHEDULE == [('c01', 'BV', 'claude'), ('c02', 'BV', 'claude'),
                                 ('c03', 'Z0', 'claude'), ('c04', 'Z0', 'claude')]
    assert [s.runner.effort_for(n) for n, _, _ in s.runner.SCHEDULE] == ['max', 'high', 'high', 'max']
    assert s.runner.smoke_slots() == [('smoke-claude', 'SM', 'claude')]
    assert s.runner.smoke_slots(2) == [('smoke2-claude', 'SM', 'claude')]
    for name, _, _ in s.runner.SCHEDULE + s.runner.smoke_slots() + s.runner.smoke_slots(2):
        assert app.repository(name) == 'fysoul17/rpd5-offline-' + name
    app.select_slot('smoke-claude')
    assert app.tasks['routes']['claude']['owner']['effort'] == 'high'
    assert app.frame.prepare.TASKS is app.tasks
    raw = (s.runner.PRIOR / 'common.txt').read_bytes()
    assert s.runner.prepare.prompt_body('X') == raw
    assert s.runner.prepare.PROMPT_SHA256 == {'X': hashlib.sha256(raw).hexdigest()}
    assert (s.runner.PRIOR / 'Dockerfile').read_text().find("^2\\.1\\.296") >= 0


@pytest.mark.parametrize('attempt', [0, 3, True, '2'])
def test_only_one_spare(attempt):
    with pytest.raises(RuntimeError):
        load('runner').smoke_slots(attempt)


def test_registry_artifact_only_and_both_registered_digests(tmp_path):
    pack = load('pack')
    source = archive(pack, tmp_path)
    expected = pack.identity(source)
    for field in ('sha256', 'integrity'):
        with pytest.raises(ValueError, match='SHA-256/integrity'):
            pack.build(source, tmp_path / ('bad-' + field), **(expected | {field: 'invalid'}))
    arms = pack.build(source, tmp_path / 'release', **expected)
    assert set(pack.verify_arms(arms)) == {'X'}
    assert (arms.parent / 'X.tgz').read_bytes() == source.read_bytes()
    (arms.parent / 'X.tgz').write_bytes(b'drift')
    with pytest.raises(ValueError, match='SHA-256/integrity'):
        pack.verify_arms(arms)


@pytest.mark.parametrize('remaining,allowed', [(6299, False), (6300, True), (6301, True)])
def test_inherited_claude_floor_and_no_separate_codex_snapshot(staged, tmp_path, remaining, allowed):
    s, _, path = staged
    auth_path = snapshot(s.auth, tmp_path / 'renew-auth', expires=NOW + remaining)
    manifest, binding = s.auth.model_auth(auth_path)
    runtime = s.read(path) | dict(auth=str(auth_path), auth_manifest_sha256=binding, account=manifest['account'])
    assert (s.auth.preflight(runtime)[1] is None) == allowed
    assert runtime['auth_engine'] == 'claude'
    assert not (path.parent / 'codex-auth').exists()


@pytest.mark.parametrize('remaining,allowed', [(6299, False), (6300, True)])
def test_stage_check_enforces_claude_lifetime(staged, monkeypatch, remaining, allowed):
    s, _, path = staged
    monkeypatch.setattr(s.auth.claude.time, 'time', lambda: NOW + 9000 - remaining)
    validated = []
    monkeypatch.setattr(s.runner.Runner, 'validate', lambda _self, name: validated.append(name))
    if allowed:
        s.check(path)
    else:
        with pytest.raises(s.auth.claude.AuthError, match='below-6300-seconds'):
            s.check(path)
    assert validated == (['smoke-claude'] if allowed else [])


def test_slots_resume_and_local_evidence_survives_repository_deletion(staged, monkeypatch):
    s, _, path = measured(staged)
    app = s.runner.Runner(path)
    calls = fake_inherited(s, app, monkeypatch)
    assert app.schedule(1) == 0
    assert calls == ['c01']
    assert s.read(Path(app.runtime['output']) / 'rp-schedule.json')['status'] == 'PAUSED'
    assert app.schedule() == 0
    assert calls == ['c01', 'c02', 'c03', 'c04']
    for name in calls:
        out = Path(app.runtime['output']) / name
        row = s.read(out / 'rp-verdict.json')
        assert row['repository_cleanup']['http_status'] == 404
        assert row['owner_seconds'] == 12.5
        assert (out / 'retained.jsonl').read_text() == 'synthetic sealed evidence\n'
    assert app.schedule() == 0
    assert len(calls) == 4


@pytest.mark.parametrize('fault', ['effort', 'accounting'])
def test_effort_mismatch_or_unknown_accounting_stops_before_next_slot(staged, monkeypatch, fault):
    s, _, path = measured(staged)
    app = s.runner.Runner(path)
    calls = fake_inherited(s, app, monkeypatch)
    monkeypatch.setattr(s.runner, 'load', lambda *_a: SimpleNamespace(analyze=lambda *_a, **_k:
        analysis(status='UNKNOWN', effort='STOP' if fault == 'effort' else 'MATCH')))
    assert app.schedule() == 2
    assert calls == ['c01']
    rows = s.read(Path(app.runtime['output']) / 'rp-schedule.json')['slots']
    assert [row['status'] for row in rows] == ['STOP', 'NOT_RUN', 'NOT_RUN', 'NOT_RUN']
    assert rows[0]['usage'] == 'UNKNOWN'
    assert app.schedule() == 2
    assert len(calls) == 1


@pytest.mark.parametrize('fault', ['delivery', 'effort', 'accounting', 'stages', 'merge_refused'])
def test_smoke_requires_all_qualification_gates(fault):
    r = load('runner')
    row = dict(status='ADJUDICATE', delivery_assessment='ADJUDICATE', merge_refused=False)
    report = analysis()
    assert r.qualify(row, report)['status'] == 'PASS'
    if fault == 'delivery':
        row['delivery_assessment'] = 'PRODUCT_INCOMPLETE'
    elif fault == 'merge_refused':
        row['merge_refused'] = True
    elif fault == 'stages':
        report['stages'] = []
    else:
        report['effort_binding' if fault == 'effort' else 'status'] = 'UNKNOWN'
    assert r.qualify(row, report)['status'] == 'FAIL'


def test_merge_refused_is_incomplete_even_when_delivery_claimed(staged, monkeypatch):
    s, _, path = measured(staged)
    app = s.runner.Runner(path)
    fake_inherited(s, app, monkeypatch)
    monkeypatch.setattr(s.runner.smoke, 'merge_refused', lambda _out: True)
    assert app.schedule(1) == 0
    row = s.read(Path(app.runtime['output']) / 'c01/rp-verdict.json')
    assert row['status'] == row['delivery_assessment'] == 'PRODUCT_INCOMPLETE'


@pytest.mark.parametrize('completed_count', range(5))
def test_renewal_between_every_slot_not_only_pairs(staged, completed_count):
    s, _, path = staged
    runtime = s.read(path) | dict(phase='measured')
    rows = [dict(status='ADJUDICATE', effort_binding='MATCH')] * completed_count
    if completed_count < 4:
        s.renewal_allowed(runtime, ACCOUNT, rows)
    else:
        with pytest.raises(RuntimeError, match='unfinished'):
            s.renewal_allowed(runtime, ACCOUNT, rows)


def test_renewal_preserves_runtime_same_claude_account_and_next_slot(staged, tmp_path):
    s, _, path = measured(staged)
    app = s.runner.Runner(path)
    append_record(s, app, s.runner.SCHEDULE[0])
    replacement = snapshot(s.auth, tmp_path / 'fresh-auth', token='synthetic-renewal')
    original = path.read_bytes()
    renewed = s.renew(path, replacement)
    assert path.read_bytes() == original
    assert s.runner.frozen_runtime(s.read(path)) == s.runner.frozen_runtime(s.read(renewed))
    s.runner.Runner(renewed).prior_deleted('c02')
    foreign = snapshot(s.auth, tmp_path / 'foreign-auth', account=['d' * 12, 'e' * 12])
    with pytest.raises(RuntimeError, match='identical Claude'):
        s.renew(path, foreign)


@pytest.mark.parametrize('fault', ['effort', 'qualification', 'archive', '404'])
def test_measured_requires_qualified_smoke_and_archive(staged, fault):
    s, args, path = staged
    app = s.runner.Runner(path)
    slot = app.slots()[0]
    append_record(s, app, slot)
    target = Path(app.runtime['output']) / slot[0] / 'rp-verdict.json'
    row = s.read(target)
    if fault == 'effort':
        row['effort_binding'] = 'STOP'
    elif fault == 'qualification':
        row['smoke_qualification']['status'] = 'FAIL'
    elif fault == 'archive':
        row['repository_cleanup']['archive_manifest_sha256'] = ''
    else:
        row['repository_cleanup']['http_status'] = 200
    s.write(target, row)
    args.phase = 'measured'
    with pytest.raises(RuntimeError):
        s.stage(args)
    assert not (args.stage_dir / 'runtime-measured.json').exists()


def test_effort_mismatch_in_first_smoke_stops_and_refuses_spare(staged, monkeypatch):
    s, args, path = staged
    app = s.runner.Runner(path)
    calls = fake_inherited(s, app, monkeypatch)
    monkeypatch.setattr(s.runner, 'load', lambda *_a: SimpleNamespace(analyze=lambda *_a, **_k:
        analysis(status='UNKNOWN', effort='STOP')))
    assert app.schedule() == 2
    registry = s.runner.smoke_registry(args.run_id)
    assert s.read(registry / 'attempt-1.json')['status'] == 'STOP'
    assert app.finish_smoke()['status'] == 'STOP'
    assert app.schedule() == 2
    assert calls == ['smoke-claude']
    args.stage_dir = args.stage_dir.parent / 'spare-stage'
    args.smoke_attempt = 2
    with pytest.raises(RuntimeError, match='spare requires a failed first smoke'):
        s.stage(args)
    assert not (registry / 'attempt-2.json').exists()
    assert not args.stage_dir.exists()


@pytest.mark.parametrize('dispatched', [False, True])
def test_unanalyzed_first_smoke_allows_spare(staged, monkeypatch, dispatched):
    s, args, path = staged
    app = s.runner.Runner(path)
    fake_inherited(s, app, monkeypatch)
    inherited = app.inherited_run
    analyzed = []
    def failed_inherited(name, task, config):
        inherited(name, task, config)
        target = Path(app.runtime['output']) / name / 'rp-verdict.json'
        row = s.read(target)
        row.update(dispatched=dispatched, status='STOP', delivery_assessment='NOT_ASSESSED')
        if not dispatched:
            row.pop('repository_cleanup')
        s.write(target, row)
        return 2
    def failed_analysis(*_args, **_kwargs):
        analyzed.append(True)
        raise ValueError('synthetic analysis failure')
    monkeypatch.setattr(app, 'inherited_run', failed_inherited)
    monkeypatch.setattr(s.runner, 'load', lambda *_a: SimpleNamespace(analyze=failed_analysis))
    assert app.schedule() == 2
    assert analyzed == ([True] if dispatched else [])
    row = s.read(Path(app.runtime['output']) / 'smoke-claude/rp-verdict.json')
    assert row['status'] == 'STOP'
    registry = s.runner.smoke_registry(args.run_id)
    assert s.read(registry / 'attempt-1.json')['status'] == 'FAILED'
    args.stage_dir = args.stage_dir.parent / 'spare-stage'
    args.smoke_attempt = 2
    assert s.stage(args).is_file()
    assert s.read(registry / 'attempt-2.json')['status'] == 'STAGED'


def test_delivery_failure_allows_spare_and_stops_failed_spare(staged, monkeypatch):
    s, args, path = staged
    app = s.runner.Runner(path)
    fake_inherited(s, app, monkeypatch)
    monkeypatch.setattr(s.runner.smoke, 'merge_refused', lambda _out: True)
    assert app.schedule() == 2
    first = s.read(s.runner.smoke_registry(args.run_id) / 'attempt-1.json')
    assert first['status'] == 'FAILED'
    args.stage_dir = args.stage_dir.parent / 'spare-stage'
    args.smoke_attempt = 2
    spare_path = s.stage(args)
    spare = s.runner.Runner(spare_path)
    fake_inherited(s, spare, monkeypatch)
    monkeypatch.setattr(s.runner.smoke, 'merge_refused', lambda _out: True)
    assert spare.schedule() == 2
    assert s.read(s.runner.smoke_registry(args.run_id) / 'attempt-2.json')['status'] == 'STOP'
    assert Path(first['runtime']).is_file()
    assert (path.parent / 'smoke-output/smoke-claude/retained.jsonl').is_file()


@pytest.mark.parametrize('slot', ['smoke-claude', 'c01', 'c02', 'c03', 'c04'])
def test_inherited_task_guard_passes_only_exact_effort_projection(staged, monkeypatch, slot):
    s, args, path = measured(staged) if slot.startswith('c') else staged
    app = s.runner.Runner(path)
    seen = []
    monkeypatch.setattr(app, 'prior_deleted', lambda _name: None)
    monkeypatch.setattr(s.runner.github, 'precheck', lambda *_a: None)
    monkeypatch.setattr(s.runner.cell, 'scan', lambda *_a, **_k: None)
    def lower(_self, name, task, arm, config):
        seen.append((name, app.tasks['routes']['claude']['owner']['effort'], arm, config))
        out = Path(app.runtime['output']) / name
        (out / 'run').mkdir(parents=True)
        s.write(out / 'run/started.json', {})
        s.write(out.parent / ('verdict-' + name + '.json'), dict(status='STOP', reason='fixture stop',
            usage='UNKNOWN', input_tokens=None, output_tokens=None))
    monkeypatch.setattr(s.runner.ancestor.legacy.Runner, 'run', lower)
    app.select_slot(slot)
    task = 'SM' if slot.startswith('smoke') else next(task for name, task, _ in s.runner.SCHEDULE if name == slot)
    assert app.inherited_run(slot, task, 'claude') == 2
    assert seen == [(slot, s.runner.effort_for(slot), 'B', 'claude')]
    # The rp-d1 task guard still rejects any unrelated task change before dispatch.
    app.tasks['tasks'][0]['request'] += ' tampered'
    with pytest.raises(ValueError, match='frozen rp-d1 tasks'):
        app.inherited_run(slot, task, 'claude')
    assert len(seen) == 1


@pytest.mark.parametrize('token', ['synthetic-claude', 'synthetic-access'])
def test_inherited_model_scans_run_before_sealing(staged, monkeypatch, token):
    s, args, path = staged
    app = s.runner.Runner(path)
    out = Path(app.runtime['output']) / 'scan-fixture'
    out.mkdir()
    (out / 'stdout').write_text(token)
    monkeypatch.setattr(s.runner.cell, 'credential', lambda _: (args.github_auth, b'github_pat_synthetic'))
    monkeypatch.setitem(app.frame.seal_after_teardown.keywords, 'inherited',
                        lambda _: pytest.fail('credential-bearing evidence reached sealing'))
    with pytest.raises(ValueError) as error:
        app.frame.seal_after_teardown(out)
    assert token not in str(error.value)
    marker = 'claude-scan.json' if token == 'synthetic-claude' else 'codex-scan.json'
    assert s.read(out / marker) == dict(status='STOP', revocation_required=True)


@pytest.mark.parametrize('encoded', [b'{"merge_refused": "conflict"}', br'{\"merge_refused\": \"conflict\"}'])
def test_inherited_merge_refused_scans_sealed_native_bytes(tmp_path, encoded):
    r = load('runner')
    out = tmp_path / 'refusal'
    (out / 'run').mkdir(parents=True)
    (out / 'run/stdout').write_bytes(encoded + b'\n')
    r.write(out / 'evidence.manifest.json', dict(failures=[], files={'run/stdout': r.digest(out / 'run/stdout')}))
    assert r.smoke.merge_refused(out) is True
    (out / 'run/stdout').unlink()
    with pytest.raises(ValueError, match='unsafe helper evidence file'):
        r.smoke.merge_refused(out)


def test_real_materializer_accounting_and_archive_keep_high_slot_evidence(staged, monkeypatch):
    """Exercise the path adapters; only Git, installer and native execution are synthetic."""
    import shutil
    s, args, path = measured(staged)
    app = s.runner.Runner(path)
    append_record(s, app, s.runner.SCHEDULE[0])
    name, task, config = s.runner.SCHEDULE[1]
    repository_url = s.runner.github.url(app.repository(name))
    prepare = s.runner.prepare.legacy.legacy.legacy
    observed = []

    def git(work, *args, **_kwargs):
        if args == ('rev-parse', 'HEAD'):
            return 'b' * 40 if (work / '.agents').exists() else 'a' * 40
        if args == ('remote',):
            return 'origin'
        if args[:2] == ('config', '--local') and 'remote.origin.url' in args or args[:2] == ('remote', 'get-url'):
            return repository_url
        return ''

    def source(task, _runtime, work, _base):
        shutil.copytree(Path(app.runtime['source_root']) / task['source_dir'], work)
        (work / '.git').mkdir()
        (work / '.git/config').write_text('[core]\n')

    def install(runtime, work, _home, engine, arm):
        assert engine == 'claude' and arm == 'X'
        for filename in s.pack.FILES:
            target = work / ('.agents' + filename.removeprefix('config'))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(runtime['control']) / 'packages/X/package' / filename, target)

    def tree(work, _commit):
        return {str(p.relative_to(work)): s.digest(p) for p in work.rglob('*') if p.is_file() and '.git' not in p.parts}

    class Objects:
        stdout = io.BytesIO()
        def __enter__(self):
            self.stdout = io.BytesIO()
            return self
        def __exit__(self, *_):
            self.stdout.close()
        def wait(self):
            return 0

    monkeypatch.setattr(s.runner.github, 'git', git)
    monkeypatch.setattr(s.runner.github, 'precheck', lambda *_: None)
    monkeypatch.setattr(s.runner.github, 'seed', lambda *_: None)
    monkeypatch.setattr(app.frame.prepare, 'source', source)
    monkeypatch.setattr(app.frame.prepare, 'install', install)
    monkeypatch.setattr(app.frame.prepare, 'committed_tree', tree)
    monkeypatch.setattr(app, 'validate', lambda slot: app.select_slot(slot))
    monkeypatch.setattr(s.runner.cell, 'credential', lambda _: (args.github_auth, b'github_pat_synthetic'))
    monkeypatch.setattr(subprocess, 'Popen', lambda *_a, **_k: Objects())

    def seal(out):
        files = {str(p.relative_to(out)): s.digest(p) for p in out.rglob('*') if p.is_file()}
        s.write(out / 'evidence.manifest.json', dict(failures=[], files=files))
        observed.append('seal')
        return s.digest(out / 'evidence.manifest.json'), []

    monkeypatch.setitem(app.frame.seal_after_teardown.keywords, 'inherited', seal)

    def audit(_out, **kwargs):
        observed.append(('audit-effort', kwargs['effort']))
        return dict(status='UNKNOWN', gaps=['synthetic audit boundary'], input_tokens=None, output_tokens=None)
    monkeypatch.setattr(s.runner.ancestor.legacy.accounting, 'audit', audit)

    def lower(_self, name, task, arm, config):
        out = app.prepare(name, task, arm, config)
        plan = s.read(out / 'plan.json')
        assert plan['effort'] == plan['env']['CLAUDE_CODE_EFFORT_LEVEL'] == 'high'
        assert plan['argv'][plan['argv'].index('--effort') + 1] == 'high'
        assert s.read(out / 'home/.claude/settings.json')['effortLevel'] == 'high'
        assert s.read(out / 'baseline.json')['tasks_sha256'] == s.digest(app.tasks_path)
        (out / 'run').mkdir()
        s.write(out / 'run/started.json', {})
        (out / 'run/stdout').write_text('{"synthetic": "retained"}\n')
        sealed, errors = app.frame.seal_after_teardown(out)
        assert errors == []
        app.account(out, sealed)
        s.write(out.parent / ('verdict-' + name + '.json'), dict(status='CHECKS_PASS', usage='COMPLETE',
            input_tokens=7, output_tokens=3, teardown='CLEAN', evidence_manifest_sha256=sealed,
            owner_seconds=12.5, snapshot={}))

    def archive(_repository, root):
        observed.append('archive')
        root.mkdir(parents=True)
        (root / 'metadata.json').write_text('{}')
        return dict(manifest_sha256='a' * 64)

    def deleted(repository, _root, binding):
        observed.append('delete')
        return dict(repository=repository, status='DELETED', http_status=404, archive_manifest_sha256=binding)

    monkeypatch.setattr(s.runner.ancestor.legacy.Runner, 'run', lower)
    monkeypatch.setattr(s.runner.github, 'archive', archive)
    monkeypatch.setattr(s.runner.github, 'done_check', lambda *_: dict(status='ADJUDICATE', checklist={}))
    monkeypatch.setattr(s.runner.github, 'delete_archived', deleted)
    original = s.runner.load
    monkeypatch.setattr(s.runner, 'load', lambda name, path: SimpleNamespace(analyze=lambda *_a, **_k: analysis())
                        if name == 'attribute_rpd5_runner' else original(name, path))
    assert app.run(name, task, 'X', config) == 0
    out = Path(app.runtime['output']) / name
    row = s.read(out / 'rp-verdict.json')
    assert row['status'] == 'ADJUDICATE'
    assert row['repository_cleanup']['http_status'] == 404
    assert observed == ['seal', ('audit-effort', 'high'), 'archive', 'delete']
    assert s.read(out / 'evidence.manifest.json')['files']['run/stdout'] == s.digest(out / 'run/stdout')
    assert (out / 'run/stdout').read_text() == '{"synthetic": "retained"}\n'
