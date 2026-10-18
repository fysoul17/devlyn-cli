"""P1, single-arm registration and the inherited serial lifecycle, offline."""
from copy import deepcopy
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from .conftest import HERE, load, record, append_record, measured


def test_schedule_registration(staged):
    s, _, path = staged
    app = s.runner.Runner(path)
    assert s.runner.SCHEDULE == [('m01', 'BV', 'claude'), ('m02', 'Z0', 'claude'),
                                  ('m03', 'BV', 'claude'), ('m04', 'Z0', 'claude')]
    assert app.slots() == [('smoke-claude', 'SM', 'claude')]
    assert s.runner.smoke_slots(2) == [('smoke2-claude', 'SM', 'claude')]
    assert s.runner.smoke_registry('offline') == Path.home() / '.devlyn/rp-d7-runs/offline'
    for slot in s.runner.SCHEDULE + s.runner.smoke_slots() + s.runner.smoke_slots(2):
        name, _, engine = slot
        assert s.runner.arm_for(name) == 'X'
        assert s.runner.effort_for(name) == 'high'
        assert app.repository(name) == 'fysoul17/rpd7-offline-' + name
        assert s.runner.slot_tasks('measured' if name.startswith('m') else 'smoke', name)['routes'][engine]['owner']['effort'] == 'high'
    assert app.remaining('m04') == ['fysoul17/rpd7-offline-m04']
    assert set(s.read(path)['releases']) == {'X'}
    assert not any('token_gate' in key for key in s.read(path))
    app.select_slot('smoke-claude')
    assert app.frame.prepare.TASKS is app.tasks


@pytest.mark.parametrize('name', ['g01', 'm05', 'smoke-codex', 'smoke2-codex', 'smoke3-claude', 'm1'])
def test_rejects_unregistered_slots_and_repositories(name):
    r = load('runner')
    with pytest.raises(RuntimeError):
        r.arm_for(name)
    with pytest.raises(RuntimeError):
        r.github.url('fysoul17/rpd7-run-' + name)


@pytest.mark.parametrize('repository', ['other/rpd7-run-m01', 'fysoul17/rpd6-run-m01', 'fysoul17/rpd7--m01',
                                       'fysoul17/rpd7-run-m01.git', 'fysoul17/rpd7-run-m01/'])
def test_rejects_wrong_repository(repository):
    with pytest.raises(RuntimeError):
        load('prepare').url(repository)


@pytest.mark.parametrize('attempt', [0, 3, True, '2'])
def test_exactly_one_spare(attempt):
    with pytest.raises(RuntimeError):
        load('runner').smoke_slots(attempt)


def test_p1_exact_derivation_and_replacements(monkeypatch):
    p = load('prepare')
    common = (p.PRIOR / 'common.txt').read_bytes()
    raw = p.prompt_body('X', 'm01')
    assert len(raw) == 353 and raw.endswith(b'\n')
    assert hashlib.sha256(raw).hexdigest() == p.P1_SHA256
    assert p.native_prompt({}, 'X', 'smoke2-claude').encode() == raw + b'\nCALLER CONTRACT\n{}'
    with pytest.raises(RuntimeError, match='common.txt'):
        p.derive(common + b'x')
    for replacement in (b'absent', b'Complete'):
        monkeypatch.setattr(p, 'REPLACEMENTS', ((replacement, b'wrong'),))
        with pytest.raises(RuntimeError):
            p.derive(common)
    with pytest.raises(RuntimeError):
        p.prompt_body('Y')


@pytest.mark.parametrize('fault', ['body', 'argv', 'caller', 'plan_hash', 'baseline_hash', 'full_hash', 'arm', 'release'])
def test_every_prompt_surface_is_bound(tmp_path, fault):
    p = load('prepare')
    out = tmp_path / 'm01'
    (out / 'harness').mkdir(parents=True)
    (out / 'harness/caller.json').write_text('{}')
    prompt = p.native_prompt({}, 'X', 'm01')
    (out / 'prompt.txt').write_text(prompt)
    release = {'version': '4.2.22'}
    plan = dict(arm='X', release=release, prompt_body_sha256=p.P1_SHA256, argv=['claude', prompt])
    baseline = dict(arm='X', release=release, prompt_body_sha256=p.P1_SHA256,
                    prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest())
    p.github.write(out / 'plan.json', plan)
    p.github.write(out / 'baseline.json', baseline)
    p.prompt_binding(out, release)
    if fault == 'body':
        (out / 'prompt.txt').write_text(prompt.replace('Preserve', 'Ignore'))
    elif fault == 'caller':
        (out / 'harness/caller.json').write_text('{"allowed": []}')
    elif fault == 'argv':
        plan['argv'][-1] += 'extra'
    elif fault == 'plan_hash':
        plan['prompt_body_sha256'] = 'bad'
    elif fault == 'baseline_hash':
        baseline['prompt_body_sha256'] = 'bad'
    elif fault == 'full_hash':
        baseline['prompt_sha256'] = 'bad'
    elif fault == 'arm':
        baseline['arm'] = 'Y'
    else:
        plan['release'] = {'version': 'other'}
    p.github.write(out / 'plan.json', plan)
    p.github.write(out / 'baseline.json', baseline)
    with pytest.raises(RuntimeError, match='binding mismatch'):
        p.prompt_binding(out, release)


def test_nondelivering_smoke_qualifies(staged):
    s, args, path = staged
    app = s.runner.Runner(path)
    row = append_record(s, app, app.slots()[0])
    assert s.runner.qualify(row)['status'] == 'PASS'
    assert s.runner.qualify(row)['delivered'] is False
    assert app.finish_smoke()['status'] == 'QUALIFIED'
    app.prior_deleted('m01')
    args.phase = 'measured'
    assert s.runner.Runner(s.stage(args)).slots() == s.runner.SCHEDULE


@pytest.mark.parametrize('field,value', [('owner_status', 'EXITED_NONZERO'), ('release_binding', 'UNKNOWN'),
    ('prompt_binding', 'UNKNOWN'), ('prompt_sha256', 'bad'), ('effort_binding', 'STOP'), ('usage', 'PARTIAL'),
    ('status', 'STOP'), ('revocation_required', True), ('repository_cleanup', {})])
def test_smoke_qualification_failures(staged, field, value):
    s, _, path = staged
    app = s.runner.Runner(path)
    row = record(s, app, *app.slots()[0])
    row[field] = value
    assert s.runner.qualify(row)['status'] == 'FAIL'


def test_spare_binds_attempts_and_first_cache(staged, tmp_path):
    s, args, path = staged
    app = s.runner.Runner(path)
    append_record(s, app, app.slots()[0], smoke_qualification={'status': 'FAIL'})
    assert app.finish_smoke()['status'] == 'FAILED'
    args.models_cache.write_text('drift')
    spare = SimpleNamespace(**(vars(args) | dict(stage_dir=tmp_path / 'spare', smoke_attempt=2)))
    target = s.stage(spare)
    assert s.read(target)['models_cache_sha256'] == s.read(path)['models_cache_sha256']
    with pytest.raises(RuntimeError, match='superseded'):
        s.runner.Runner(path)
    second = s.runner.Runner(target)
    append_record(s, second, second.slots()[0], smoke_qualification={'status': 'FAIL'})
    assert second.finish_smoke()['status'] == 'STOP'
    with pytest.raises(RuntimeError):
        s.stage(SimpleNamespace(**(vars(spare) | dict(stage_dir=tmp_path / 'third'))))


def test_renewal_all_slot_boundaries_and_stops(staged):
    s, _, path = measured(staged)
    app = s.runner.Runner(path)
    previous = s.read(path)
    rows = []
    for index, slot in enumerate(s.runner.SCHEDULE, 1):
        rows.append(record(s, app, *slot))
        if index < 4:
            s.renewal_allowed(previous, previous['codex_account'], previous['claude_account'], rows)
            for key, value in [('status', 'STOP'), ('effort_binding', 'STOP'), ('prompt_binding', 'UNKNOWN')]:
                bad = deepcopy(rows)
                bad[-1][key] = value
                with pytest.raises(RuntimeError):
                    s.renewal_allowed(previous, previous['codex_account'], previous['claude_account'], bad)
        else:
            with pytest.raises(RuntimeError):
                s.renewal_allowed(previous, previous['codex_account'], previous['claude_account'], rows)
    for count, account in [(0, previous['claude_account']), (1, 'other-account')]:
        with pytest.raises(RuntimeError):
            s.renewal_allowed(previous, previous['codex_account'], account, rows[:count])


def fake_inherited(s, app, monkeypatch, fail_effort=None, mutate_prompt=None):
    calls = []
    def inherited(name, task, config):
        calls.append(name)
        out = Path(app.runtime['output']) / name
        (out / 'harness').mkdir(parents=True)
        row = record(s, app, name, task, config)
        prompt = s.runner.prepare.native_prompt({}, 'X', name)
        (out / 'harness/caller.json').write_text('{}')
        (out / 'prompt.txt').write_text(prompt + ('mutation' if name == mutate_prompt else ''))
        for filename in ('plan.json', 'baseline.json'):
            s.write(out / filename, dict(arm='X', release=row['release'], prompt_body_sha256=row['prompt_sha256'],
                prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(), argv=['claude', prompt]))
        s.write(out / 'rp-verdict.json', row)
        s.write(out.parent / ('verdict-' + name + '.json'),
                dict(owner_seconds=12.5, owner_status='EXITED_0', evidence_manifest_sha256='a' * 64))
        return 0
    monkeypatch.setattr(app, 'inherited_run', inherited)
    # Keep the real prompt-binding wrapper; replace only the mechanical assessor.
    monkeypatch.setattr(app.grading.legacy, 'assess', lambda *_args, **_kwargs: dict(
        delivery_pass=False, publication={}, false_completion={'value': False}, severe_regression={}))
    monkeypatch.setattr(app.grading, 'history_evidence', lambda *_args: {})
    monkeypatch.setattr(s.runner.smoke, 'merge_refused', lambda _out: False)
    original = s.runner.legacy.load
    monkeypatch.setattr(s.runner.legacy, 'load', lambda name, path: SimpleNamespace(
        effort_binding=lambda out, *_args: 'STOP' if out.name == fail_effort else 'MATCH')
        if name == 'attribute_rpd5_rpd6' else original(name, path))
    return calls


def test_actual_runner_smoke_and_four_slot_pauses(staged, monkeypatch):
    s, args, path = staged
    app = s.runner.Runner(path)
    calls = fake_inherited(s, app, monkeypatch)
    assert app.schedule() == 0 and calls == ['smoke-claude']
    assert app.finish_smoke()['status'] == 'QUALIFIED'
    args.phase = 'measured'
    app = s.runner.Runner(s.stage(args))
    calls = fake_inherited(s, app, monkeypatch)
    for boundary in range(1, 5):
        assert app.schedule(boundary) == 0
        assert calls == [name for name, _, _ in s.runner.SCHEDULE[:boundary]]
    assert app.schedule() == 0 and len(calls) == 4
    assert set(s.read(Path(app.runtime['output']) / 'rp-schedule.json')['releases']) == {'X'}


@pytest.mark.parametrize('fault', ['effort', 'prompt'])
def test_slot_mismatch_stops_without_replacement(staged, monkeypatch, fault):
    s, _, path = measured(staged)
    app = s.runner.Runner(path)
    calls = fake_inherited(s, app, monkeypatch, **{'fail_effort' if fault == 'effort' else 'mutate_prompt': 'm02'})
    assert app.schedule() == 2
    assert calls == ['m01', 'm02']
    rows = s.read(Path(app.runtime['output']) / 'rp-schedule.json')['slots']
    assert [row['status'] for row in rows[1:]] == ['STOP', 'NOT_RUN', 'NOT_RUN']


def test_single_arm_release_tamper(staged):
    s, _, path = staged
    runtime = s.read(path)
    s.runner.prepare.verify_release(runtime)
    bad = deepcopy(runtime)
    bad['releases']['Y'] = bad['releases']['X']
    with pytest.raises(RuntimeError):
        s.runner.prepare.verify_release(bad)
    (Path(runtime['control']) / 'packages/X/package/CLAUDE.md').write_text('tampered')
    with pytest.raises(RuntimeError, match='extracted release'):
        s.runner.prepare.verify_release(runtime)


def test_real_renewal_after_odd_slot_and_mid_slot_rejection(staged):
    s, _, path = measured(staged)
    app = s.runner.Runner(path)
    append_record(s, app, s.runner.SCHEDULE[0])
    renewed = s.renew(path, claude_auth_path=Path(app.base_runtime['claude_auth']))
    next_app = s.runner.Runner(renewed)
    assert next_app.frozen == app.frozen
    next_app.prior_deleted('m02')
    (Path(next_app.runtime['output']) / 'm02').mkdir()
    with pytest.raises((RuntimeError, ValueError)):
        s.renew(renewed, claude_auth_path=Path(next_app.base_runtime['claude_auth']))


def test_frozen_cache_cannot_drift_or_use_host(staged, tmp_path):
    s, args, path = staged
    app = s.runner.Runner(path)
    append_record(s, app, app.slots()[0], smoke_qualification={'status': 'FAIL'})
    app.finish_smoke()
    Path(s.read(path)['models_cache']).write_text('mutated')
    spare = SimpleNamespace(**(vars(args) | dict(stage_dir=tmp_path / 'spare', smoke_attempt=2)))
    with pytest.raises(RuntimeError, match='registered models cache'):
        s.stage(spare)
    args.models_cache = Path.home() / '.codex/models_cache.json'
    with pytest.raises(RuntimeError, match='host models cache'):
        s.cache_input(args)


@pytest.mark.parametrize('remaining,allowed', [(6299, False), (6300, True)])
def test_claude_floor_retained(staged, monkeypatch, remaining, allowed):
    s, _, path = staged
    runtime = s.auth.for_engine(s.read(path), 'claude')
    manifest, _ = s.auth.claude_model_auth(runtime['auth'])
    monkeypatch.setattr(s.auth.claude.time, 'time', lambda: manifest['expires_at_ms'] / 1000 - remaining)
    monkeypatch.setattr(s.auth.claude, 'profile', lambda _token: runtime['account'])
    assert (s.auth.preflight(runtime)[1] is None) == allowed


def test_inherited_all_request_effort_and_structure_free_refusal(tmp_path):
    tests = load('runtime_inherited', HERE.parent / 'rp-d6-claude-delivery/test_runtime.py')
    tests.test_sealed_claude_effort_checks_every_request_and_manifest(tmp_path)
    for index, payload in enumerate((b'{"merge_refused": "conflict"}', br'{\"merge_refused\": \"conflict\"}')):
        tests.test_structure_free_refusal_scan_is_reused(tmp_path / str(index), payload)


def test_materializer_reuses_installer_and_binds_real_prompt_cache_and_instruction_bytes(staged, monkeypatch):
    import shutil
    s, _, path = measured(staged)
    app = s.runner.Runner(path)
    name, task, engine = s.runner.SCHEDULE[0]
    app.active_arm, app.active_name = 'X', name
    app.select_slot(name)
    repository_url = s.runner.github.url(app.repository(name))
    seen = []
    def git(work, *args, **_kwargs):
        seen.append(args)
        if args == ('rev-parse', 'HEAD'):
            return ('b' if (work / 'AGENTS.md').exists() else 'a') * 40
        if args == ('remote',):
            return 'origin'
        if args[:2] == ('config', '--local') and 'remote.origin.url' in args or args[:2] == ('remote', 'get-url'):
            return repository_url
        return ''
    def source(task, _runtime, work, _base):
        shutil.copytree(Path(app.runtime['source_root']) / task['source_dir'], work)
        (work / '.git').mkdir()
        (work / '.git/config').write_text('[core]\n')
    def install(runtime, work, _home, config, arm):
        assert (config, arm) == ('claude', 'X')
        package = Path(runtime['control']) / 'packages' / arm / 'package'
        for filename in ('CLAUDE.md', 'AGENTS.md'):
            raw = (package / filename).read_bytes().replace(b'\r\n', b'\n').removesuffix(b'\n') + b'\n'
            body = b'Project-specific instructions outside this managed block take precedence over these defaults.\n\n' + raw
            (work / filename).write_bytes(b'<!-- devlyn:instructions:begin sha256=' + hashlib.sha256(body).hexdigest().encode()
                + b' -->\n' + body + b'<!-- devlyn:instructions:end -->\n')
        target = work / '.agents/skills/_shared/runtime-principles.md'
        target.parent.mkdir(parents=True)
        shutil.copyfile(package / 'config/skills/_shared/runtime-principles.md', target)
    def tree(work, _sha):
        return {str(p.relative_to(work)): dict(mode=p.stat().st_mode & 0o777, sha256=s.digest(p))
                for p in work.rglob('*') if p.is_file() and '.git' not in p.parts}
    monkeypatch.setattr(s.runner.github, 'git', git)
    monkeypatch.setattr(s.runner.github, 'seed', lambda *_args: None)
    monkeypatch.setattr(app.frame.prepare, 'source', source)
    monkeypatch.setattr(app.frame.prepare, 'install', install)
    monkeypatch.setattr(app.frame.prepare, 'committed_tree', tree)
    monkeypatch.setattr(app.frame.prepare, 'native_prompt', app.native_prompt)
    out = app.materialize(app.runtime, name, task, 'B', engine)
    s.runner.prepare.binding(out, app.runtime, 'X')
    assert ('remote', 'add', 'origin', repository_url) in seen
    baseline = s.read(out / 'baseline.json')
    assert baseline['tasks_sha256'] == s.digest(app.tasks_path)
    assert s.read(out / 'plan.json')['effort'] == 'high'
    assert (out / 'prompt.txt').read_bytes().startswith(s.runner.prepare.prompt_body('X', name))
    (out / 'home/.codex/models_cache.json').write_text('different model cache')
    with pytest.raises(RuntimeError, match='cell models cache'):
        s.runner.prepare.binding(out, app.runtime, 'X')
