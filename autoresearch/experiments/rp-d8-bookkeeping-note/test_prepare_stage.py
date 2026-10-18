"""Offline P1, installed bindings, registration and renewal coverage."""
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace
import urllib.request

import pytest

HERE = Path(__file__).resolve().parent


def load(name, path=None):
    spec = importlib.util.spec_from_file_location('rpd8_prepare_test_' + name, path or HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail('external operation forbidden')
    for target, name in ((socket, 'create_connection'), (socket.socket, 'connect'), (urllib.request, 'urlopen'),
                         (subprocess, 'run'), (subprocess, 'Popen')):
        monkeypatch.setattr(target, name, forbidden)


def test_p1_every_arm_slot_exact_suffix_and_hash():
    p = load('prepare')
    expected = {
        'g03': b'Do not push or open a pull request.', 'g04': b'Commit.', 'g05': b'Do not commit.',
        'g07': b'Open a pull request.', 'g08': b'Do not create or change any file outside the allowed paths.',
    }
    assert p.SUFFIXES == expected
    assert len(p.SLOTS) == 28
    original = p.prompt_body('X')
    assert len(original) == 353 and hashlib.sha256(original).hexdigest() == p.P1_SHA256
    for arm in ('X', 'Y'):
        for name in p.SLOTS:
            body = original + b'\n' + expected[name] + b'\n' if name in expected else original
            assert p.prompt_body(arm, name) == body
            assert p.prompt_sha256(name) == hashlib.sha256(body).hexdigest()
    for arm, slot in [('Z', 'm01'), ('X', 'm17'), ('Y', 'g09')]:
        with pytest.raises((ValueError, RuntimeError)):
            p.prompt_body(arm, slot)


@pytest.mark.parametrize('slot', ['m01', 'm16', 'g03', 'g04', 'g05', 'g06', 'g07', 'g08', 'smoke2-codex'])
@pytest.mark.parametrize('arm', ['X', 'Y'])
def test_full_caller_contract_prompt_binding(tmp_path, slot, arm):
    p = load('prepare')
    out = tmp_path / slot
    (out / 'harness').mkdir(parents=True)
    caller = {'request': 'fix fixture', 'allowed': ['src/example.py']}
    caller_raw = json.dumps(caller, indent=2).encode()
    (out / 'harness/caller.json').write_bytes(caller_raw)
    raw = p.native_prompt(caller, arm, slot).encode()
    (out / 'prompt.txt').write_bytes(raw)
    release = {'registered': arm}
    common = dict(arm=arm, release=release, prompt_body_sha256=p.prompt_sha256(slot))
    p.github.write(out / 'baseline.json', dict(common, prompt_sha256=hashlib.sha256(raw).hexdigest()))
    p.github.write(out / 'plan.json', dict(common, argv=['native', raw.decode()]))
    p.prompt_binding(out, release, arm)
    (out / 'harness/caller.json').write_bytes(caller_raw + b'\n')
    with pytest.raises((ValueError, RuntimeError), match='prompt binding mismatch'):
        p.prompt_binding(out, release, arm)


def test_installed_candidate_and_root_instructions_bound(tmp_path):
    p = load('prepare')
    gate = load('rendered_gate')
    out, control = tmp_path / 'm02', tmp_path / 'control'
    package = control / 'packages/Y/package'
    work = out / 'cell/work'
    installed = {}
    for source in (p.pack.FILE, 'config/skills/_shared/runtime-principles.md'):
        raw = ('# ' + source + '\n').encode()
        target = package / source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        name = '.agents' + source.removeprefix('config')
        target = work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        installed[name] = {}
    for name in ('CLAUDE.md', 'AGENTS.md'):
        (package / name).write_bytes(b'# instructions\n')
        (work / name).write_bytes(b'@AGENTS.md\n' if name == 'CLAUDE.md' else gate.managed_block(b'# instructions\n'))
    p.github.write(out / 'baseline.json', {'installed_files': installed})
    p.installed_binding(out, {'control': str(control)}, 'Y')
    task = work / ('.agents' + p.pack.FILE.removeprefix('config'))
    task.write_bytes(b'wrong candidate')
    with pytest.raises((ValueError, RuntimeError), match='task-completion.md differs'):
        p.installed_binding(out, {'control': str(control)}, 'Y')


@pytest.fixture(scope='module')
def stage_module():
    return load('stage')


@pytest.fixture
def staged(tmp_path, monkeypatch, stage_module):
    s = stage_module
    fixtures = load('fixtures', HERE / 'test_pack_gate.py')
    arms, paths = fixtures.gate_fixture(s.gate, tmp_path, monkeypatch)
    monkeypatch.setattr(s.pack, 'REGISTERED', s.gate.pack.REGISTERED)
    monkeypatch.setattr(s.pack, 'CANDIDATE_BLOB', s.gate.pack.CANDIDATE_BLOB)
    historical = load('auth_fixtures', HERE.parent / 'rp-d4-helper-report/test_runtime.py')
    host = tmp_path / 'host'
    host.mkdir()
    monkeypatch.setattr(Path, 'home', lambda: host)
    monkeypatch.setattr(s.auth.claude.time, 'time', lambda: 1_700_000_000)
    model = historical.snapshot(s.auth, tmp_path / 'codex-auth')
    guard = historical.guard_snapshot(s.auth, tmp_path / 'claude-auth', model)
    gh = tmp_path / 'github-auth'
    gh.mkdir(mode=0o700)
    for name, raw in [('hosts.yml', b'github.com:\n    oauth_token: github_pat_synthetic\n'),
                      ('config.yml', b'version: 1\n')]:
        s.auth.write_private(gh, name, raw)
    frozen = tmp_path / 'registered-models-cache.json'
    frozen.write_text('{"models": []}\n')
    token_gate = tmp_path / 'token-gate.json'
    s.write(token_gate, s.gate.evaluate(arms, paths, len, SimpleNamespace(encode=list)))
    args = SimpleNamespace(stage_dir=tmp_path / 'stage', phase='smoke', run_id='offline', arms=arms,
        image='sha256:' + 'a' * 64, auth=model, claude_auth=guard, github_auth=gh,
        models_cache=frozen, models_cache_sha256=s.digest(frozen), token_gate=token_gate,
        smoke_output=None, smoke_attempt=1)
    return s, args


def test_stage_registered_gate_and_models_copy(staged):
    s, args = staged
    path = s.stage(args)
    runtime = s.read(path)
    assert runtime['token_gate_sha256'] == s.digest(args.token_gate)
    assert Path(runtime['token_gate']).read_bytes() == args.token_gate.read_bytes()
    assert runtime['models_cache_sha256'] == s.digest(args.models_cache)
    assert Path(runtime['models_cache']).read_bytes() == args.models_cache.read_bytes()
    assert s.read(s.runner.smoke_registry(args.run_id) / 'attempt-1.json')['inputs']['prompt_body_sha256'] == s.runner.prepare.P1_SHA256
    tasks = list((args.stage_dir / 'tasks').glob('*.json'))
    assert len(tasks) == 26  # 24 schedule cells plus the active smoke pair.
    s.runner.prepare.verify_release(runtime)


@pytest.mark.parametrize('fault', ['missing', 'changed-arms', 'increased-count', 'root-difference'])
def test_stage_rejects_gate_before_registration(staged, fault):
    s, args = staged
    gate = s.read(args.token_gate)
    if fault == 'missing':
        args.token_gate = None
    elif fault == 'changed-arms':
        gate['arms_sha256'] = '0' * 64
    elif fault == 'increased-count':
        gate['rows']['task-completion.md']['claude'] = [10, 11]
    else:
        gate['rows']['CLAUDE.md']['identical'] = False
    if args.token_gate:
        s.write(args.token_gate, gate)
    with pytest.raises((ValueError, RuntimeError)):
        s.stage(args)
    assert not args.stage_dir.exists()
    assert not s.runner.smoke_registry(args.run_id).exists()


@pytest.mark.parametrize('count', range(25))
def test_renewal_only_completed_pairs_and_between_guards(count, stage_module):
    s = stage_module
    previous = dict(phase='measured', codex_account='codex', claude_account='claude')
    completed = [dict(status='PRODUCT_INCOMPLETE', config='claude', effort_binding='MATCH', prompt_binding='MATCH')
                 for _ in range(count)]
    if 0 < count < 24 and (count >= 16 or count % 2 == 0):
        s.renewal_allowed(previous, 'codex', 'claude', completed)
    else:
        with pytest.raises((ValueError, RuntimeError), match='boundary'):
            s.renewal_allowed(previous, 'codex', 'claude', completed)


@pytest.mark.parametrize('changes', [{'status': 'STOP'}, {'status': 'NOT_RUN'}, {'effort_binding': 'MISMATCH'},
                                     {'prompt_binding': 'UNKNOWN'}])
def test_renewal_never_resumes_stop(changes, stage_module):
    s = stage_module
    row = dict(status='PASS', config='claude', effort_binding='MATCH', prompt_binding='MATCH')
    with pytest.raises((ValueError, RuntimeError), match='stopped schedule'):
        s.renewal_allowed(dict(phase='measured', codex_account='codex', claude_account='claude'),
                          'codex', 'claude', [row, row | changes])


def smoke_records(s, path, *, failure=False):
    app = s.runner.Runner(path)
    fixture = load('runtime_records', HERE.parent / 'rp-d6-claude-delivery/test_runtime.py')
    for index, slot in enumerate(app.slots()):
        name, task, config = slot
        out = Path(app.runtime['output']) / name
        out.mkdir()
        value = fixture.record(s, app, name, task, config, prompt_binding='MATCH')
        if failure and index == 0:
            value['owner_status'] = 'EXITED_1'
        value['smoke_qualification'] = s.runner.qualify(value)
        s.write(out / 'rp-verdict.json', value)
    return app


def test_qualified_smoke_freezes_verdicts_and_measured_inputs(staged):
    s, args = staged
    smoke_path = s.stage(args)
    app = smoke_records(s, smoke_path)
    result = app.finish_smoke()
    assert result['status'] == 'QUALIFIED'
    args.phase = 'measured'
    measured = s.read(s.stage(args))
    smoke = s.read(smoke_path)
    for key in ('models_cache_sha256', 'token_gate_sha256', 'arms_file', 'releases', 'smoke_attempt'):
        assert measured[key] == smoke[key]
    app = s.runner.Runner(args.stage_dir / 'runtime-measured.json')
    assert len(app.slots()) == 24
    state = s.read(s.runner.smoke_registry(args.run_id) / 'attempt-1.json')
    verdict = Path(next(iter(state['verdicts'])))
    changed = s.read(verdict)
    changed['route_watch'] = {'alive': False}
    s.write(verdict, changed)
    with pytest.raises((ValueError, RuntimeError), match='changed'):
        s.runner.smoke_registration(smoke)


def test_failed_smoke_single_spare_reuses_gate_and_cache(staged):
    s, args = staged
    first_path = s.stage(args)
    app = smoke_records(s, first_path, failure=True)
    assert app.finish_smoke()['status'] == 'FAILED'
    original = s.read(first_path)
    args.stage_dir = args.stage_dir.parent / 'spare'
    args.smoke_attempt = 2
    args.models_cache = args.token_gate = None
    spare_path = s.stage(args)
    spare = s.read(spare_path)
    assert spare['models_cache_sha256'] == original['models_cache_sha256']
    assert spare['token_gate_sha256'] == original['token_gate_sha256']
    state = s.read(s.runner.smoke_registry(args.run_id) / 'attempt-2.json')
    assert state['previous_sha256'] == s.digest(s.runner.smoke_registry(args.run_id) / 'attempt-1.json')
    spare_app = smoke_records(s, spare_path, failure=True)
    assert spare_app.finish_smoke()['status'] == 'STOP'
    with pytest.raises((ValueError, RuntimeError)):
        s.runner.smoke_slots(3)


def test_renewal_changed_account_is_rejected(stage_module):
    s = stage_module
    completed = [dict(status='PASS', config='claude', effort_binding='MATCH', prompt_binding='MATCH')] * 2
    with pytest.raises((ValueError, RuntimeError), match='identical'):
        s.renewal_allowed(dict(phase='measured', codex_account='codex', claude_account='claude'),
                          'different', 'claude', completed)
