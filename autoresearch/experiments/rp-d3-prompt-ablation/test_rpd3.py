"""Synthetic fixtures only; all model, Docker, GitHub and host-auth boundaries blocked."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import socket
import subprocess
from types import SimpleNamespace
import urllib.request

import pytest

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('rpd3_test_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail('external operation forbidden')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    real_run = subprocess.run
    def local_git(argv, **kwargs):
        assert argv[0] == 'git', 'external process forbidden: ' + str(argv[0])
        assert not any(value in argv for value in ('push', 'fetch', 'clone', 'ls-remote'))
        return real_run(argv, **kwargs)
    monkeypatch.setattr(subprocess, 'run', local_git)


def artifact(p, root, monkeypatch):
    import tarfile
    source = root / 'registry.tgz'
    blob = b'# synthetic frozen reporting instruction\n'
    with tarfile.open(source, 'w:gz') as archive:
        for name, data in [('package/package.json', b'{"name":"devlyn-cli","version":"4.2.18"}'),
                           ('package/' + p.FILE, blob), ('package/bin/devlyn.js', b'// synthetic\n')]:
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), 0o644
            archive.addfile(info, io.BytesIO(data))
    release = dict(version='4.2.18', **p.identity(source))
    monkeypatch.setattr(p, 'RELEASE_SHA256', release['sha256'])
    monkeypatch.setattr(p, 'registered', lambda: release)
    monkeypatch.setattr(p, 'REPORT_BLOB', hashlib.sha1(b'blob ' + str(len(blob)).encode() + b'\0' + blob).hexdigest())
    return source, blob, release


def snapshot(auth, root, account='synthetic-account', token='synthetic-token'):
    source = root.parent / (root.name + '-source.json')
    source.write_text(json.dumps(dict(auth_mode='chatgpt', tokens=dict(account_id=account,
        access_token=token, refresh_token='synthetic-refresh', id_token='synthetic-id'))))
    auth.bootstrap(source, root)
    return root


@pytest.fixture
def staged(tmp_path, monkeypatch):
    s = load('stage')
    source, _, _ = artifact(s.pack, tmp_path, monkeypatch)
    arms = s.pack.build(source, tmp_path / 'release')
    home = tmp_path / 'host'
    (home / '.codex').mkdir(parents=True)
    (home / '.codex/models_cache.json').write_text('{"models": []}')
    monkeypatch.setattr(Path, 'home', lambda: home)
    model = snapshot(s.auth, tmp_path / 'auth')
    gh = tmp_path / 'github-auth'
    gh.mkdir(mode=0o700)
    for name in ('hosts.yml', 'config.yml'):
        s.auth.write_private(gh, name, b'synthetic fixture\n')
    args = SimpleNamespace(stage_dir=tmp_path / 'stage', phase='smoke', run_id='offline', arms=arms,
        image='sha256:' + 'a' * 64, auth=model, github_auth=gh, smoke_output=None, smoke_attempt=1)
    monkeypatch.setattr(s.runner.cell, 'credential', lambda _: pytest.fail('real PAT read forbidden'))
    return s, args, s.stage(args)


def record(s, app, name, task, engine):
    arm = s.runner.arm_for(name)
    return dict(cell=name, task=task, config=engine, arm=arm, status='ADJUDICATE', dispatched=True,
        phase=app.runtime['phase'], measurement_eligible=app.runtime['phase'] == 'measured',
        release=s.runner.prepare.release_identity(app.runtime, arm), prompt_sha256=s.runner.prepare.PROMPT_SHA256[arm],
        codex_account=app.runtime['codex_account'], auth=app.runtime['auth'],
        auth_manifest_sha256=app.runtime['auth_manifest_sha256'], frozen_runtime_sha256=app.frozen,
        delivery_assessment='ADJUDICATE', repository_cleanup=dict(repository=app.repository(name),
        status='DELETED', http_status=404, archive_manifest_sha256='a' * 64))


def measured(staged):
    s, args, path = staged
    app = s.runner.Runner(path)
    for slot in app.slots():
        out = Path(app.runtime['output']) / slot[0]
        out.mkdir()
        s.write(out / 'rp-verdict.json', record(s, app, *slot))
    args.phase = 'measured'
    return s, args, s.stage(args)


def test_schedule_smoke_and_repository_census(staged):
    s, _, path = staged
    r = s.runner
    assert r.SCHEDULE == [(f'm{i:02}', 'BV' if i <= 4 else 'Z0', 'codex') for i in range(1, 9)]
    assert [r.arm_for(row[0]) for row in r.SCHEDULE] == ['P0', 'P1', 'P1', 'P0', 'P0', 'P1', 'P1', 'P0']
    assert r.smoke_slots() == [('smoke-codex-P0', 'SM', 'codex'), ('smoke-codex-P1', 'SM', 'codex')]
    assert r.smoke_slots(2) == [('smoke2-codex-P0', 'SM', 'codex'), ('smoke2-codex-P1', 'SM', 'codex')]
    app = r.Runner(path)
    assert len({app.repository(row[0]) for row in r.SCHEDULE + r.smoke_slots() + r.smoke_slots(2)}) == 12
    assert app.remaining('m03') == [app.repository(row[0]) for row in r.SCHEDULE[2:]]
    for name in ('m09', 'smoke-claude-P0', 'smoke3-codex-P0', 'smoke-codex-X'):
        with pytest.raises(RuntimeError):
            app.repository(name)
    for attempt in (0, 3, True, '2'):
        with pytest.raises(RuntimeError):
            r.smoke_slots(attempt)


def test_prompt_exact_bytes_and_caller_contract():
    p = load('prepare')
    raw = (p.PRIOR / 'common.txt').read_bytes()
    for arm in ('P0', 'P1'):
        body = p.prompt_body(arm)
        assert body == (raw if arm == 'P0' else raw[:-len(p.SUFFIX) - 1] + b'\n')
        assert hashlib.sha256(body).hexdigest() == p.PROMPT_SHA256[arm]
        caller = {'request': 'synthetic \u00e9', 'allowed': ['src']}
        assert p.native_prompt(caller, arm).encode() == body + b'\nCALLER CONTRACT\n' + json.dumps(caller, indent=2).encode()


@pytest.mark.parametrize('fault', ['suffix', 'prefix', 'newline', 'hash'])
def test_prompt_derivation_fails_closed(tmp_path, monkeypatch, fault):
    p = load('prepare')
    raw = (p.PRIOR / 'common.txt').read_bytes()
    if fault == 'suffix':
        raw = raw.replace(p.SUFFIX, b' Changed ending.')
    elif fault == 'prefix':
        raw = b'drift' + raw
    elif fault == 'newline':
        raw = raw.rstrip(b'\n')
    else:
        monkeypatch.setitem(p.PROMPT_SHA256, 'P1', '0' * 64)
    (tmp_path / 'common.txt').write_bytes(raw)
    monkeypatch.setattr(p, 'PRIOR', tmp_path)
    with pytest.raises(RuntimeError):
        p.prompt_body('P0')


def test_single_tarball_and_blob_check(staged):
    s, args, path = staged
    runtime = s.read(path)
    assert set(runtime['releases']) == {'B'}
    assert len(list((args.stage_dir / 'arms').glob('*.tgz'))) == 1
    s.runner.prepare.verify_release(runtime)
    installed = Path(runtime['control']) / 'packages/B/package' / s.pack.FILE
    installed.write_bytes(installed.read_bytes() + b'drift')
    with pytest.raises(RuntimeError, match='extracted release'):
        s.runner.prepare.verify_release(runtime)


@pytest.mark.parametrize('fault', ['sha256', 'integrity', 'blob'])
def test_pack_rejects_invalid_identity_before_writing(tmp_path, monkeypatch, fault):
    p = load('pack')
    source, _, release = artifact(p, tmp_path, monkeypatch)
    if fault == 'blob':
        monkeypatch.setattr(p, 'REPORT_BLOB', '0' * 40)
    else:
        release[fault] = 'wrong'
    with pytest.raises(ValueError):
        p.build(source, tmp_path / 'dest')
    assert not (tmp_path / 'dest').exists()


def test_registered_hash_and_blob_are_pinned():
    p = load('pack')
    assert p.registered()['sha256'] == p.RELEASE_SHA256 == '7b22cce865d99e1400f9c0b0bff41c1b9ae3645b132cbb868ec01cadc973393e'
    assert p.legacy.git('rev-parse', '7516ebc9:' + p.FILE).decode().strip() == p.REPORT_BLOB
    p.check_blob(p.legacy.git('show', '7516ebc9:' + p.FILE))


@pytest.mark.parametrize('attempt', [1, 2])
def test_codex_only_smoke_and_measured_check(staged, tmp_path, monkeypatch, attempt):
    s, args, path = staged
    if attempt == 2:
        args.stage_dir, args.smoke_attempt = tmp_path / 'stage2', 2
        path = s.stage(args)
    monkeypatch.setattr(subprocess, 'check_output', lambda *_a, **_k: args.image + '\n')
    s.check(path)
    before = path.read_bytes()
    assert s.runner.Runner(path).preflight()[1] is None
    s, args, measured_path = measured((s, args, path))
    s.check(measured_path)
    runtime = s.read(measured_path)
    assert path.read_bytes() == before
    assert runtime['boot_catalogs'] == {}
    assert runtime['account'] == runtime['codex_account'] == hashlib.sha256(b'synthetic-account').hexdigest()[:12]
    assert (args.auth / 'claude.env').read_bytes() == b''
    assert 'expires_at_ms' not in s.model_auth(args.auth)[0]
    assert 'access_token' not in measured_path.read_text()
    assert len(s.runner.Runner(measured_path).slots()) == 8


@pytest.mark.parametrize('fault', ['account', 'manifest', 'codex', 'env', 'mode'])
def test_auth_refusals_are_codex_only(staged, fault):
    s, args, path = staged
    runtime = s.read(path)
    if fault in ('account', 'manifest'):
        runtime['codex_account' if fault == 'account' else 'auth_manifest_sha256'] = '0' * 64
    else:
        target = args.auth / ('claude.env' if fault == 'env' else 'codex.json')
        target.chmod(0o600)
        if fault != 'mode':
            target.write_bytes(b'nonempty foreign contents')
            target.chmod(0o400)
    assert s.auth.preflight(runtime)[1] is not None


@pytest.mark.parametrize('attempt', [1, 2])
@pytest.mark.parametrize('arm', ['P0', 'P1'])
@pytest.mark.parametrize('fault', ['missing', 'delivery', 'prompt', 'release', 'archive', 'deleted', '404'])
def test_measured_stage_requires_both_selected_smoke_cells(staged, tmp_path, attempt, arm, fault):
    s, args, path = staged
    if attempt == 2:
        args.stage_dir, args.smoke_attempt = tmp_path / 'stage2', 2
        path = s.stage(args)
    app = s.runner.Runner(path)
    for smoke_attempt in (1, 2):
        for slot in s.runner.smoke_slots(smoke_attempt):
            row = record(s, app, *slot)
            if smoke_attempt == attempt and row['arm'] == arm:
                if fault == 'missing':
                    continue
                if fault == 'delivery':
                    row.update(status='PRODUCT_INCOMPLETE', delivery_assessment='PRODUCT_INCOMPLETE')
                elif fault == 'prompt':
                    row['prompt_sha256'] = '0' * 64
                elif fault == 'release':
                    row['release']['sha256'] = '0' * 64
                else:
                    key, value = {'archive': ('archive_manifest_sha256', ''),
                                  'deleted': ('status', 'PENDING'), '404': ('http_status', 200)}[fault]
                    row['repository_cleanup'][key] = value
            out = Path(app.runtime['output']) / slot[0]
            out.mkdir()
            s.write(out / 'rp-verdict.json', row)
    args.phase = 'measured'
    with pytest.raises((RuntimeError, FileNotFoundError)):
        s.stage(args)
    assert not (args.stage_dir / 'runtime-measured.json').exists()


def materialize(staged, monkeypatch, arm):
    s, args, path = staged
    app = s.runner.Runner(path)
    calls = []
    real_run = subprocess.run
    def install(argv, **kwargs):
        if argv[:3] == ['docker', 'image', 'inspect']:
            return subprocess.CompletedProcess(argv, 0, args.image + '\n', '')
        if argv[:2] == ['docker', 'run']:
            calls.append(argv)
            mount = next(value for value in argv if value.endswith(',dst=/work'))
            work = Path(mount.removeprefix('type=bind,src=').removesuffix(',dst=/work'))
            target = work / '.agents/skills/_shared/task-completion.md'
            target.parent.mkdir(parents=True)
            shutil.copyfile(Path(app.runtime['control']) / 'packages/B/package' / s.pack.FILE, target)
            return subprocess.CompletedProcess(argv, 0, b'', b'')
        return real_run(argv, **kwargs)
    monkeypatch.setattr(subprocess, 'run', install)
    monkeypatch.setattr(s.runner.github, 'seed', lambda *_: None)
    app.active_arm = arm
    out = app.prepare('smoke-codex-' + arm, 'SM', 'B', 'codex')
    return s, app, out, calls


@pytest.mark.parametrize('arm', ['P0', 'P1'])
def test_installer_prompt_seal_and_codex_policy(staged, monkeypatch, arm):
    s, app, out, calls = materialize(staged, monkeypatch, arm)
    assert len(calls) == 1
    assert f'type=bind,src={app.runtime["control"]}/packages/B,dst=/install,readonly' in calls[0]
    app.unchanged(out)
    s.runner.prepare.binding(out, app.runtime, arm)
    plan = s.read(out / 'plan.json')
    assert plan['arm'] == arm and plan['prompt_body_sha256'] == s.runner.prepare.PROMPT_SHA256[arm]
    (out / 'run').mkdir()
    (out / 'run/stdout').write_text(json.dumps(dict(type='thread.started', thread_id='synthetic')) + '\n')
    policy = s.runner.legacy.legacy.legacy.policy.check(out, plan, app.tasks, app.frame.cell_run.evidence)
    assert policy['status'] == 'MATCH'
    assert not policy['protocol_violations']


@pytest.mark.parametrize('fault', ['arm', 'body_hash', 'release', 'prompt', 'argv', 'installed'])
def test_launch_binding_rejects_mutations(staged, monkeypatch, fault):
    s, app, out, _ = materialize(staged, monkeypatch, 'P1')
    plan = s.read(out / 'plan.json')
    if fault == 'arm':
        plan['arm'] = 'P0'
    elif fault == 'body_hash':
        plan['prompt_body_sha256'] = '0' * 64
    elif fault == 'release':
        plan['release']['sha256'] = '0' * 64
    elif fault == 'argv':
        plan['argv'][-1] += 'drift'
    elif fault == 'prompt':
        (out / 'prompt.txt').write_text('drift')
    else:
        (out / 'cell/work/.agents/skills/_shared/task-completion.md').write_text('drift')
    s.write(out / 'plan.json', plan)
    with pytest.raises((RuntimeError, ValueError), match='binding|blob'):
        app.frame.cell_run.run(out, app.runtime)


@pytest.mark.parametrize('fault', ['prompt_sha256', 'release'])
def test_verdict_binding_refuses_resume(staged, fault):
    s, _, path = measured(staged)
    app = s.runner.Runner(path)
    row = record(s, app, *s.runner.SCHEDULE[0])
    if fault == 'release':
        row['release']['sha256'] = '0' * 64
    else:
        row[fault] = '0' * 64
    out = Path(app.runtime['output']) / 'm01'
    out.mkdir()
    s.write(out / 'rp-verdict.json', row)
    with pytest.raises(RuntimeError, match='binding'):
        app.completed_prefix()


def test_renewal_only_between_pairs_same_codex_account(staged, tmp_path):
    s, _, path = measured(staged)
    app = s.runner.Runner(path)
    replacement = snapshot(s.auth, tmp_path / 'renewed', token='synthetic-renewal')
    for slot in s.runner.SCHEDULE[:2]:
        out = Path(app.runtime['output']) / slot[0]
        out.mkdir()
        s.write(out / 'rp-verdict.json', record(s, app, *slot))
        if slot[0] == 'm01':
            with pytest.raises(RuntimeError, match='between measured pairs'):
                s.renew(path, replacement)
    original = path.read_bytes()
    renewed = s.renew(path, replacement)
    assert path.read_bytes() == original
    assert s.runner.frozen_runtime(s.read(renewed)) == s.runner.frozen_runtime(s.read(path))
    resumed = s.runner.Runner(renewed)
    resumed.prior_deleted('m03')
    with pytest.raises(RuntimeError, match='within a pair'):
        resumed.prior_deleted('m02')
    foreign = snapshot(s.auth, tmp_path / 'foreign', account='different-synthetic-account')
    with pytest.raises(RuntimeError, match='Codex account'):
        s.renew(path, foreign)


@pytest.fixture
def evidence(tmp_path):
    s = load('summarize')
    output = tmp_path / 'output'
    output.mkdir()
    reviews = {name: tmp_path / name for name in s.REVIEWERS}
    for path in reviews.values():
        path.mkdir()
    rows = []
    for slot, task, engine in s.runner.SCHEDULE:
        arm = s.runner.arm_for(slot)
        out = output / slot
        out.mkdir()
        rows.append(dict(cell=slot, task=task, config=engine, arm=arm,
            prompt_sha256=s.runner.prepare.PROMPT_SHA256[arm], release=dict(sha256=s.runner.prepare.pack.RELEASE_SHA256),
            phase='measured', measurement_eligible=True, dispatched=True, status='ADJUDICATE',
            delivery_assessment='ADJUDICATE', usage='COMPLETE', owner_seconds=100, input_tokens=1000, output_tokens=10))
        checklist = dict(report='Checks passed. Merged. Cleanup pending. Checkout reconciled.',
            facts=dict(verification='PASSED', merge='MERGED', cleanup='CLEANUP_PENDING', reconciliation='RECONCILED'),
            evidence={category: {'evidence': 'sha'} for category in s.github.CATEGORIES})
        s.write(out / 'report-checklist.json', checklist)
        for name, path in reviews.items():
            s.write(path / (slot + '.json'), dict(reviewer=s.REVIEWERS[name],
                checklist_sha256=s.github.review_report(checklist)['checklist_sha256'],
                claims={key: dict(quote=checklist['report'], claim=value, finding='SUPPORTED', evidence=['evidence'])
                        for key, value in checklist['facts'].items()}))
    flush(s, output, rows)
    return s, output, reviews, rows


def flush(s, output, rows):
    for row in rows:
        s.write(output / row['cell'] / 'rp-verdict.json', row)
    s.write(output / 'rp-schedule.json', dict(phase='measured', slots=rows, dispatched=sum(row['dispatched'] for row in rows)))


def findings(s, reviews, rows, arm, category, supported_count):
    selected = [row for row in rows if row['arm'] == arm]
    for row in selected[supported_count:]:
        for directory in reviews.values():
            path = directory / (row['cell'] + '.json')
            review = s.read(path)
            review['claims'][category].update(finding='MISSING', quote='', evidence=[])
            s.write(path, review)


@pytest.mark.parametrize('p0,p1,cleanup,reconciliation,expected,follow', [
    (0, 3, 4, 4, 'PROMPT-SENSITIVE', 'registered benchmark-prompt'),
    (1, 4, 4, 4, 'PROMPT-SENSITIVE', 'Claude check'),
    (0, 0, 0, 0, 'NO RESCUE', 'product reporting candidate'),
    (1, 1, 1, 1, 'NO RESCUE', 'product reporting candidate'),
    (0, 2, 4, 4, 'MIXED', 'category that still fails'),
    (0, 0, 0, 4, 'MIXED', 'rp-d2 Y cleanup paragraph'),
    (2, 4, 4, 4, 'MIXED', 'no attribution'),
    (2, 2, 3, 4, 'MIXED', 'no attribution'),
    (2, 1, 1, 3, 'MIXED', 'no attribution'),
    (0, 2, 2, 2, 'MIXED', None),
])
def test_decisions_and_followups(evidence, p0, p1, cleanup, reconciliation, expected, follow):
    s, out, reviews, rows = evidence
    findings(s, reviews, rows, 'P0', 'verification', p0)
    findings(s, reviews, rows, 'P1', 'verification', p1)
    findings(s, reviews, rows, 'P1', 'cleanup', cleanup)
    findings(s, reviews, rows, 'P1', 'reconciliation', reconciliation)
    result = s.summarize(out, reviews)
    assert result['decision']['decision'] == expected
    assert result['arms']['P0']['successes'] == p0
    assert result['arms']['P1']['successes'] == p1
    assert result['arms']['P1']['cleanup_supported'] == cleanup
    assert result['arms']['P1']['reconciliation_supported'] == reconciliation
    if follow == 'no attribution':
        assert result['decision']['follow_up'] == []
        assert result['decision']['reason'] == 'no attribution'
    elif follow:
        assert follow in ' '.join(result['decision']['follow_up'])
    else:
        assert not result['decision']['follow_up']


@pytest.mark.parametrize('fault', ['stop', 'not_run', 'delivery', 'pending', 'fail_and_pending', 'stale_review'])
def test_inconclusive_overrides_every_outcome(evidence, fault):
    s, out, reviews, rows = evidence
    findings(s, reviews, rows, 'P0', 'verification', 0)
    if fault == 'stop':
        rows[0]['status'] = 'STOP'
    elif fault == 'not_run':
        rows[0].update(status='NOT_RUN', dispatched=False)
    elif fault == 'delivery':
        rows[0].update(status='PRODUCT_INCOMPLETE', delivery_assessment='PRODUCT_INCOMPLETE')
    elif fault == 'stale_review':
        path = reviews['astra'] / 'm02.json'
        review = s.read(path)
        review['checklist_sha256'] = '0' * 64
        s.write(path, review)
    else:
        (reviews['astra'] / ('m01.json' if fault == 'fail_and_pending' else 'm02.json')).unlink()
    flush(s, out, rows)
    result = s.summarize(out, reviews)
    assert result['decision']['decision'] == 'INCONCLUSIVE'
    if fault == 'fail_and_pending':
        assert result['slots'][0]['status'] == 'FAILED'


def test_summary_cli_template_pairs_costs(evidence, capsys):
    s, out, reviews, _ = evidence
    assert s.main([str(out), 'm01', '--review-template']) == 0
    template = json.loads(capsys.readouterr().out)
    assert set(template['claims']) == set(s.github.CATEGORIES)
    assert s.REVIEWERS == {'astra': 'astra-ultra', 'grok': 'grok-4.7'}
    assert s.main([str(out), '--review', 'astra=' + str(reviews['astra']), '--review', 'grok=' + str(reviews['grok'])]) == 0
    assert 'MIXED' in capsys.readouterr().out
    summary = s.read(out / 'summary.json')
    assert len(summary['pairs']) == 4
    for arm in ('P0', 'P1'):
        assert summary['arms'][arm]['delivery_pass'] == 4
        assert summary['arms'][arm]['totals'] == dict(owner_seconds=400, input_tokens=4000, output_tokens=40)


def test_cost_missing_is_descriptive_not_decision_gate(evidence):
    s, out, reviews, rows = evidence
    findings(s, reviews, rows, 'P0', 'cleanup', 0)
    rows[0].update(usage='UNKNOWN', input_tokens=None, output_tokens=None)
    rows[1].pop('owner_seconds')
    flush(s, out, rows)
    summary = s.summarize(out, reviews)
    assert summary['arms']['P0']['totals']['input_tokens'] is None
    assert summary['arms']['P1']['totals']['owner_seconds'] is None
    assert summary['decision']['decision'] == 'PROMPT-SENSITIVE'


@pytest.mark.parametrize('fault', ['arm', 'prompt_sha256', 'release'])
def test_summary_rejects_identity_drift(evidence, fault):
    s, out, reviews, rows = evidence
    if fault == 'release':
        rows[0]['release']['sha256'] = '0' * 64
    else:
        rows[0][fault] = 'wrong'
    flush(s, out, rows)
    with pytest.raises(RuntimeError, match='binding mismatch'):
        s.summarize(out, reviews)


@pytest.mark.parametrize('phase,failure', [('measured', None), ('measured', 'precheck'),
                                         ('measured', 'accounting'), ('measured', 'scan'), ('smoke', None)])
def test_serial_lifecycle_pause_stop_binding_and_no_replay(staged, monkeypatch, phase, failure):
    s, _, path = measured(staged) if phase == 'measured' else staged
    r = s.runner
    app = r.Runner(path)
    events = []
    def precheck(_remaining):
        events.append('precheck')
        if failure == 'precheck':
            raise r.github.EvidenceError('synthetic nonempty repository')
    def inherited(_self, name, _task, route, engine):
        assert route == 'B' and engine == 'codex'
        events.append('launch')
        out = Path(app.runtime['output']) / name
        (out / 'run').mkdir(parents=True)
        s.write(out / 'run/started.json', {})
        s.write(out.parent / f'verdict-{name}.json', dict(status='STOP' if failure == 'accounting' else 'CHECKS_PASS',
            reason='whole-run usage UNKNOWN', usage='UNKNOWN' if failure == 'accounting' else 'COMPLETE',
            input_tokens=7, output_tokens=3, teardown='CLEAN', evidence_manifest_sha256='seal', snapshot={}))
    def archive(_repository, root):
        events.append('archive')
        root.mkdir(parents=True)
        return dict(manifest_sha256='sealed archive')
    def done(*_args):
        events.append('grade')
        return dict(status='ADJUDICATE', checklist={})
    def delete(repository, *_args):
        events.append('delete')
        return dict(repository=repository, status='DELETED', http_status=404, archive_manifest_sha256='sealed archive')
    def scan(_out, _runtime, *, roots):
        events.append('scan')
        assert roots
        if failure == 'scan':
            raise ValueError('synthetic scanner failure')
    monkeypatch.setattr(r.github, 'precheck', precheck)
    monkeypatch.setattr(r.legacy.legacy.legacy.Runner, 'run', inherited)
    monkeypatch.setattr(r.github, 'archive', archive)
    monkeypatch.setattr(r.github, 'done_check', done)
    monkeypatch.setattr(r.github, 'delete_archived', delete)
    monkeypatch.setattr(r.cell, 'scan', scan)
    if failure is None and phase == 'measured':
        assert app.schedule(1) == 0
        assert len(app.completed_prefix()) == 2
        assert s.read(Path(app.runtime['output']) / 'rp-schedule.json')['status'] == 'PAUSED'
        with pytest.raises(RuntimeError, match='1..4'):
            app.schedule(5)
    assert app.schedule() == (2 if failure else 0)
    rows = s.read(Path(app.runtime['output']) / 'rp-schedule.json')['slots']
    assert len(rows) == (8 if phase == 'measured' else 2)
    for row in rows:
        app.record_binding(row)
    if failure:
        assert [row['status'] for row in rows] == ['UNKNOWN' if failure == 'scan' else 'STOP'] + ['NOT_RUN'] * 7
        before = list(events)
        assert app.schedule() == 2
        assert events == before
        if failure == 'accounting':
            assert 'grade' not in events and 'delete' in events
    else:
        assert events == ['precheck', 'launch', 'archive', 'grade', 'delete', 'scan'] * len(rows)
        for name, task, engine in app.slots():
            with pytest.raises(ValueError, match='never replay'):
                app.run(name, task, r.arm_for(name), engine)


def test_frozen_launcher_accepts_empty_env_without_any_claude_credential(staged, monkeypatch):
    s, _, path = staged
    r = s.runner
    app = r.Runner(path)
    out = Path(app.runtime['output']) / 'synthetic-launch'
    for name in ('home/.claude', 'home/.codex', 'cell', 'tmp', 'harness'):
        (out / name).mkdir(parents=True)
    s.write(out / 'plan.json', dict(home=str(out / 'home'), cell=str(out / 'cell'),
        control=app.runtime['control'], harness=str(out / 'harness'), tmp=str(out / 'tmp'),
        image=app.runtime['image'], argv=['codex', 'exec', 'synthetic'], env={}, wall_seconds=5400, engine='codex'))
    calls = []
    def docker(*argv):
        calls.append(argv)
        if argv[0] == 'inspect':
            return '{"Running":false,"Pid":0}'
        return 'synthetic-container'
    class Process:
        def __init__(self, argv, **kwargs):
            assert argv[:3] == ['docker', 'start', '-a']
        def wait(self, timeout):
            assert timeout == 5400
            return 0
    monkeypatch.setattr(subprocess, 'Popen', Process)
    native = SimpleNamespace(docker=docker, preserve_tmp=lambda *_args: None,
        identity=lambda *_args: {'status': 'MATCH'}, lines=lambda _path: [],
        base=SimpleNamespace(final_message=lambda *_args: 'synthetic final'))
    result = r.cell.legacy.run(out, app.runtime, native=native, check_auth=s.auth.preflight)
    assert result['owner_status'] == 'EXITED_0' and result['teardown'] == 'CLEAN'
    create = next(argv for argv in calls if argv[0] == 'create')
    env = Path(create[create.index('--env-file') + 1])
    assert env.read_bytes() == b''
    assert not list(env.parent.glob('claude.json'))
    assert 'synthetic-token' not in json.dumps(result)


def test_paused_pair_summary_is_inconclusive_without_creating_missing_slots(evidence):
    s, out, reviews, rows = evidence
    for row in rows[2:]:
        shutil.rmtree(out / row['cell'])
    flush(s, out, rows[:2])
    schedule = s.read(out / 'rp-schedule.json')
    s.write(out / 'rp-schedule.json', dict(schedule, status='PAUSED'))
    summary = s.summarize(out, reviews)
    assert summary['decision']['decision'] == 'INCONCLUSIVE'
    assert len(summary['slots']) == 8
    assert all(row['runner_status'] == 'NOT_RUN' for row in summary['slots'][2:])
    assert not (out / 'm03').exists()
    (out / 'm03').mkdir()
    with pytest.raises(RuntimeError, match='unrecorded attempt'):
        s.summarize(out, reviews)


@pytest.mark.parametrize('change', [
    {'auth_mode': 'apikey'}, {'auth_mode': 'chatgptAuthTokens'}, {'auth_mode': None},
    {'auth_mode': 'unknown'}, {'OPENAI_API_KEY': 'synthetic-key'}, {'OPENAI_API_KEY': ''},
    {'personal_access_token': 'synthetic-pat'}, {'agent_identity': 'synthetic-agent'},
    {'bedrock_api_key': 'synthetic-bedrock'}, {'unexpected': 'synthetic-secret'},
])
def test_auth_rejects_competing_modes_and_keys(tmp_path, change):
    auth = load('auth')
    root = snapshot(auth, tmp_path / 'auth')
    value = json.loads((root / 'codex.json').read_bytes()) | change
    source = tmp_path / 'invalid.json'
    source.write_text(json.dumps(value))
    with pytest.raises(auth.legacy.AuthError) as error:
        auth.bootstrap(source, tmp_path / 'refused')
    assert 'synthetic-' not in str(error.value)
    assert not (tmp_path / 'refused').exists()


@pytest.mark.parametrize('fault', ['missing_mode', 'token_key', 'tokens_list', 'blank_account',
                                       'blank_access', 'refresh_type', 'id_type', 'duplicate'])
def test_auth_rejects_malformed_oauth(tmp_path, fault):
    auth = load('auth')
    root = snapshot(auth, tmp_path / 'auth')
    value = json.loads((root / 'codex.json').read_bytes())
    if fault == 'missing_mode':
        del value['auth_mode']
    elif fault == 'token_key':
        value['tokens']['OPENAI_API_KEY'] = 'synthetic-key'
    elif fault == 'tokens_list':
        value['tokens'] = []
    elif fault == 'blank_account':
        value['tokens']['account_id'] = ' '
    elif fault == 'blank_access':
        value['tokens']['access_token'] = ''
    elif fault == 'refresh_type':
        value['tokens']['refresh_token'] = {}
    elif fault == 'id_type':
        value['tokens']['id_token'] = 1
    raw = json.dumps(value)
    if fault == 'duplicate':
        raw = raw.replace('"auth_mode":', '"auth_mode": "apikey", "auth_mode":')
    with pytest.raises(auth.legacy.AuthError):
        auth.account(raw)


@pytest.mark.parametrize('boundary', ['output', 'smoke_output', 'scratch', 'stage'])
@pytest.mark.parametrize('relation', ['inside', 'equal', 'ancestor'])
@pytest.mark.parametrize('operation', ['stage', 'renew'])
def test_model_auth_disjoint_roots(staged, tmp_path, boundary, relation, operation):
    s, args, path = measured(staged) if operation == 'renew' else staged
    runtime = s.read(path)
    root = path.parent if boundary == 'stage' else Path(runtime[boundary])
    candidate = root / 'model-auth' if relation == 'inside' else root if relation == 'equal' else root.parent
    original = path.read_bytes()
    if operation == 'stage':
        args.auth = candidate
        args.phase = 'measured'
        action = lambda: s.stage(args)
    else:
        action = lambda: s.renew(path, candidate)
    with pytest.raises(RuntimeError, match='model auth.*disjoint'):
        action()
    assert path.read_bytes() == original
    assert not list(path.parent.glob('runtime-measured-auth-*.json'))


@pytest.mark.parametrize('secret', ['access_token', 'refresh_token', 'id_token', 'raw', 'pat'])
@pytest.mark.parametrize('location', ['stdout', 'filename', 'symlink', 'git'])
def test_secret_scan_precedes_sealing(staged, tmp_path, monkeypatch, capsys, secret, location):
    s, args, path = staged
    r = s.runner
    app = r.Runner(path)
    out = Path(app.runtime['output']) / 'synthetic-scan'
    out.mkdir()
    raw = (args.auth / 'codex.json').read_bytes()
    token = (b'github_pat_synthetic' if secret == 'pat' else raw if secret == 'raw'
             else json.loads(raw)['tokens'][secret].encode())
    monkeypatch.setattr(r.cell, 'credential', lambda _: (args.github_auth, b'github_pat_synthetic'))
    if location == 'stdout':
        (out / 'stdout').write_bytes(b'x' * (1024 * 1024 - 3) + token)
    elif location == 'filename':
        # JSON is a legal synthetic filename here and also tests full snapshot matching.
        (out / token.decode()).write_text('unrelated')
    elif location == 'symlink':
        (out / 'link').symlink_to(token.decode())
    else:
        subprocess.run(['git', 'init', '--bare', str(out / 'repo.git')], check=True, capture_output=True)
        subprocess.run(['git', '--git-dir', str(out / 'repo.git'), 'hash-object', '-w', '--stdin'],
                       input=token, check=True, capture_output=True)
    seal = app.frame.seal_after_teardown
    monkeypatch.setitem(seal.keywords, 'inherited', lambda _: pytest.fail('leaked evidence was sealed'))
    with pytest.raises(ValueError) as error:
        seal(out)
    assert token.decode() not in str(error.value)
    assert not capsys.readouterr().out
    assert not (out / 'evidence-manifest.json').exists()


@pytest.mark.parametrize('location', ['preseal', 'archive', 'verdict'])
def test_codex_leak_stops_slot_and_remaining_schedule(staged, monkeypatch, location, capsys):
    s, args, path = measured(staged)
    r = s.runner
    app = r.Runner(path)
    events = []
    token = 'synthetic-refresh'
    monkeypatch.setattr(r.cell, 'credential', lambda _: (args.github_auth, b'github_pat_synthetic'))
    monkeypatch.setattr(r.github, 'precheck', lambda *_: None)
    monkeypatch.setitem(app.frame.seal_after_teardown.keywords, 'inherited',
                        lambda _: pytest.fail('leaked evidence was sealed'))
    def inherited(_self, name, *_args):
        out = Path(app.runtime['output']) / name
        (out / 'run').mkdir(parents=True)
        s.write(out / 'run/started.json', {})
        if location == 'preseal':
            (out / 'run/stdout').write_text(token)
            app.frame.seal_after_teardown(out)
        s.write(out.parent / f'verdict-{name}.json', dict(status='CHECKS_PASS', usage='COMPLETE',
            input_tokens=7, output_tokens=3, teardown='CLEAN', evidence_manifest_sha256='seal', snapshot={},
            diagnostic=token if location == 'verdict' else 'clean'))
    def archive(_repository, root):
        root.mkdir(parents=True)
        (root / 'metadata.json').write_text(token if location == 'archive' else 'clean')
        return dict(manifest_sha256='seal')
    def grade(*_):
        events.append('grade')
        return dict(status='ADJUDICATE', checklist={})
    monkeypatch.setattr(r.legacy.legacy.legacy.Runner, 'run', inherited)
    monkeypatch.setattr(r.github, 'archive', archive)
    monkeypatch.setattr(r.github, 'done_check', grade)
    monkeypatch.setattr(r.github, 'delete_archived', lambda *_: dict(status='DELETED'))
    assert app.schedule() == 2
    rows = s.read(Path(app.runtime['output']) / 'rp-schedule.json')['slots']
    assert [row['status'] for row in rows] == ['STOP'] + ['NOT_RUN'] * 7
    assert rows[0]['delivery_assessment'] == 'NOT_ASSESSED'
    assert rows[0]['input_tokens'] is None
    assert 'Codex credential scan' in rows[0]['reason']
    assert token not in json.dumps(rows)
    if location == 'preseal':
        assert events == []
    assert not capsys.readouterr().out
    assert app.schedule() == 2


def test_clean_secret_scan_allows_seal(staged, monkeypatch):
    s, args, path = staged
    app = s.runner.Runner(path)
    monkeypatch.setattr(s.runner.cell, 'credential', lambda _: (args.github_auth, b'github_pat_synthetic'))
    out = Path(app.runtime['output']) / 'clean'
    out.mkdir()
    (out / 'stdout').write_text('nonsecret evidence')
    monkeypatch.setitem(app.frame.seal_after_teardown.keywords, 'inherited', lambda _: ('seal', []))
    assert app.frame.seal_after_teardown(out) == ('seal', [])
    assert not (out / 'codex-scan.json').exists()


def test_oauth_null_api_key_and_metadata_are_not_credentials(tmp_path):
    auth = load('auth')
    root = snapshot(auth, tmp_path / 'auth')
    value = json.loads((root / 'codex.json').read_bytes())
    value.update(OPENAI_API_KEY=None, last_refresh='2026-10-16T00:00:00Z')
    assert auth.account(json.dumps(value)) == hashlib.sha256(b'synthetic-account').hexdigest()[:12]


def test_renew_rejects_valid_snapshot_inside_evidence(staged):
    s, _, path = measured(staged)
    app = s.runner.Runner(path)
    for slot in s.runner.SCHEDULE[:2]:
        out = Path(app.runtime['output']) / slot[0]
        out.mkdir()
        s.write(out / 'rp-verdict.json', record(s, app, *slot))
    root = Path(app.runtime['output']) / 'm01/home'
    root.mkdir()
    replacement = snapshot(s.auth, root / 'model-auth', token='synthetic-renewal')
    with pytest.raises(RuntimeError, match='model auth.*disjoint'):
        s.renew(path, replacement)
    assert not list(path.parent.glob('runtime-measured-auth-*.json'))


@pytest.mark.parametrize('operation', ['stage', 'renew'])
def test_auth_disjoint_resolves_symlink_and_case(staged, tmp_path, operation):
    s, args, path = measured(staged) if operation == 'renew' else staged
    alias = tmp_path / 'alias'
    alias.symlink_to(path.parent, target_is_directory=True)
    for candidate in (alias / 'private-auth', path.parent.with_name(path.parent.name.upper()) / 'private-auth'):
        if operation == 'stage':
            args.auth, args.phase = candidate, 'measured'
            action = lambda: s.stage(args)
        else:
            action = lambda: s.renew(path, candidate)
        with pytest.raises(RuntimeError, match='model auth.*disjoint'):
            action()


def test_raw_snapshot_scan_catches_json_escaped_secrets(staged, monkeypatch):
    s, args, path = staged
    raw = (args.auth / 'codex.json').read_text()
    for key in ('access_token', 'refresh_token', 'id_token'):
        token = json.loads(raw)['tokens'][key]
        raw = raw.replace(token, ''.join(f'\\u{ord(char):04x}' for char in token))
    source = args.auth.parent / 'escaped-source.json'
    source.write_text(raw)
    replacement = args.auth.parent / 'escaped-auth'
    s.auth.bootstrap(source, replacement)
    app = s.runner.Runner(path)
    runtime = dict(app.runtime, auth=str(replacement))
    out = Path(runtime['output']) / 'raw-leak'
    out.mkdir()
    (out / 'stdout').write_text(raw)
    assert all(token.encode() not in raw.encode() for key, token in s.auth.oauth(raw).items()
               if key != 'account_id')
    monkeypatch.setattr(s.runner.cell, 'credential', lambda _: (args.github_auth, b'github_pat_synthetic'))
    with pytest.raises(ValueError, match='Codex credential scan'):
        s.runner.cell.scan(out, runtime)
    assert s.read(out / 'codex-scan.json')['status'] == 'STOP'
