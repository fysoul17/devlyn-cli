"""Offline stage, schedule, prompt, native-binding and spare lifecycle checks."""
from copy import deepcopy
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
NOW = 1_700_000_000


def load(name, path=None):
    spec = importlib.util.spec_from_file_location('rpd6_runtime_' + name, path or HERE / (name + '.py'))
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


@pytest.fixture
def staged(tmp_path, monkeypatch):
    s = load('stage')
    fixtures = load('pack_fixtures', HERE / 'test_pack.py')
    source, _, _, commit = fixtures.fixture(s.pack, tmp_path, monkeypatch)
    arms = s.pack.build(source, tmp_path / 'release', commit, **s.pack.identity(source))
    historical = load('auth_fixtures', HERE.parent / 'rp-d4-helper-report/test_runtime.py')
    host = tmp_path / 'host'
    host.mkdir()
    monkeypatch.setattr(Path, 'home', lambda: host)
    monkeypatch.setattr(s.auth.claude.time, 'time', lambda: NOW)
    model = historical.snapshot(s.auth, tmp_path / 'codex-auth')
    guard = historical.guard_snapshot(s.auth, tmp_path / 'claude-auth', model)
    gh = tmp_path / 'github-auth'
    gh.mkdir(mode=0o700)
    for name in ('hosts.yml', 'config.yml'):
        s.auth.write_private(gh, name, b'synthetic fixture\n')
    frozen = tmp_path / 'registered-models-cache.json'
    frozen.write_text('{"models": []}\n')
    gate = tmp_path / 'rendered-gate.json'
    s.write(gate, dict(passed=True, arms_sha256=s.digest(arms),
        rows={name: dict(claude=[100, 99], o200k=[80, 80]) for name in ('CLAUDE.md', 'AGENTS.md')}))
    args = SimpleNamespace(stage_dir=tmp_path / 'stage', phase='smoke', run_id='offline', arms=arms,
        image='sha256:' + 'a' * 64, auth=model, claude_auth=guard, github_auth=gh,
        models_cache=frozen, models_cache_sha256=s.digest(frozen), token_gate=gate,
        smoke_output=None, smoke_attempt=1)
    return s, args, s.stage(args)


def record(s, app, name, task, config, **changes):
    arm = s.runner.arm_for(name)
    selected = s.auth.for_engine(app.base_runtime, config)
    return dict(cell=name, task=task, config=config, arm=arm, effort=s.runner.effort_for(name),
        status='PRODUCT_INCOMPLETE', dispatched=True, phase=app.runtime['phase'],
        measurement_eligible=app.runtime['phase'] == 'measured',
        release=s.runner.prepare.release_identity(app.runtime, arm), prompt_sha256=s.runner.prepare.prompt_sha256(name),
        account=selected['account'], codex_account=selected['codex_account'], auth=selected['auth'],
        auth_manifest_sha256=selected['auth_manifest_sha256'], frozen_runtime_sha256=app.frozen,
        delivery_assessment='PRODUCT_INCOMPLETE', smoke_qualification={'status': 'PASS'},
        effort_binding='MATCH' if config == 'claude' else 'NOT_APPLICABLE', merge_refused=False,
        owner_status='EXITED_0', release_binding='MATCH', usage='COMPLETE',
        repository_cleanup=dict(repository=app.repository(name), status='DELETED', http_status=404,
                                archive_manifest_sha256='a' * 64)) | changes


def append_record(s, app, slot, **changes):
    out = Path(app.runtime['output']) / slot[0]
    out.mkdir()
    value = record(s, app, *slot, **changes)
    s.write(out / 'rp-verdict.json', value)
    return value


def measured(staged):
    s, args, path = staged
    app = s.runner.Runner(path)
    for slot in app.slots():
        append_record(s, app, slot)
    args.phase = 'measured'
    return s, args, s.stage(args)


def test_schedule_and_actual_stage_projection(staged):
    s, _, path = staged
    app = s.runner.Runner(path)
    assert s.runner.SCHEDULE == [(f'm{i:02}', 'BV' if i <= 4 else 'Z0', 'claude') for i in range(1, 9)] + [
        ('g01', 'BV', 'codex'), ('g02', 'Z0', 'codex'), ('g03', 'BV', 'claude'),
        ('g04', 'BV', 'claude'), ('g05', 'Z0', 'claude'), ('g06', 'BV', 'claude')]
    assert list(s.runner.ARMS.values()) == ['X', 'Y', 'Y', 'X', 'X', 'Y', 'Y', 'X'] + ['Y'] * 6
    assert s.runner.smoke_slots() == [('smoke-claude', 'SM', 'claude'), ('smoke-codex', 'SM', 'codex')]
    assert s.runner.smoke_slots(2) == [('smoke2-claude', 'SM', 'claude'), ('smoke2-codex', 'SM', 'codex')]
    for name, _, engine in s.runner.SCHEDULE + s.runner.smoke_slots(1) + s.runner.smoke_slots(2):
        assert app.repository(name) == (None if name == 'g06' else 'fysoul17/rpd6-offline-' + name)
        assert s.runner.effort_for(name) == ('max' if name == 'g03' else 'high')
        tasks = s.runner.slot_tasks('measured' if name in s.runner.ARMS else 'smoke', name)
        assert tasks['routes'][engine]['owner']['effort'] == s.runner.effort_for(name)
    assert app.remaining('g05') == ['fysoul17/rpd6-offline-g05']
    assert app.remaining('g06') == []
    app.select_slot('smoke-claude')
    assert app.frame.prepare.TASKS is app.tasks
    assert app.tasks['routes']['claude']['owner']['effort'] == 'high'


def test_prompt_bytes_and_hash_bound_suffixes(staged):
    s, _, _ = staged
    p = s.runner.prepare
    raw = (s.runner.PRIOR / 'common.txt').read_bytes()
    for name, _, _ in s.runner.SCHEDULE + s.runner.smoke_slots():
        expected = raw + b'\n' + p.SUFFIXES[name] + b'\n' if name in p.SUFFIXES else raw
        assert p.prompt_body(s.runner.arm_for(name), name) == expected
        assert p.prompt_sha256(name) == hashlib.sha256(expected).hexdigest()
        assert p.native_prompt({}, s.runner.arm_for(name), name).encode() == expected + b'\nCALLER CONTRACT\n{}'
    assert p.prompt_sha256('g04') != p.prompt_sha256('g05') != p.prompt_sha256('m01')


@pytest.mark.parametrize('attempt', [0, 3, True, '2'])
def test_exactly_one_spare(attempt):
    with pytest.raises(RuntimeError):
        load('runner').smoke_slots(attempt)


def test_first_stage_and_measured_use_registered_copy_without_host_cache(staged):
    s, args, path = staged
    runtime = s.read(path)
    assert not (Path.home() / '.codex/models_cache.json').exists()
    assert Path(runtime['models_cache']).read_bytes() == args.models_cache.read_bytes()
    args.models_cache.write_text('upstream registration source later changes\n')
    s, _, measured_path = measured(staged)
    actual = s.read(measured_path)
    assert actual['models_cache'] == runtime['models_cache']
    assert actual['models_cache_sha256'] == runtime['models_cache_sha256']


def test_spare_uses_first_frozen_stage_even_if_host_and_argument_change(staged, tmp_path):
    s, args, path = staged
    first = s.runner.Runner(path)
    append_record(s, first, first.slots()[0], smoke_qualification={'status': 'FAIL'})
    assert first.finish_smoke()['status'] == 'FAILED'
    (Path.home() / '.codex').mkdir()
    (Path.home() / '.codex/models_cache.json').write_text('host drift must be irrelevant')
    args.models_cache.write_text('input source drift must be irrelevant')
    spare = SimpleNamespace(**(vars(args) | dict(stage_dir=tmp_path / 'spare', smoke_attempt=2)))
    target = s.stage(spare)
    actual, expected = s.read(target), s.read(path)
    assert actual['models_cache_sha256'] == expected['models_cache_sha256']
    assert Path(actual['models_cache']).read_bytes() == Path(expected['models_cache']).read_bytes()
    app = s.runner.Runner(target)
    append_record(s, app, app.slots()[0], smoke_qualification={'status': 'FAIL'})
    assert app.finish_smoke()['status'] == 'STOP'
    retry = SimpleNamespace(**(vars(spare) | dict(stage_dir=tmp_path / 'retry')))
    with pytest.raises(RuntimeError, match='superseded'):
        s.stage(retry)


def test_spare_rejects_mutated_registered_stage_cache(staged, tmp_path):
    s, args, path = staged
    app = s.runner.Runner(path)
    append_record(s, app, app.slots()[0], smoke_qualification={'status': 'FAIL'})
    app.finish_smoke()
    Path(s.read(path)['models_cache']).write_text('changed frozen copy')
    spare = SimpleNamespace(**(vars(args) | dict(stage_dir=tmp_path / 'spare', smoke_attempt=2)))
    with pytest.raises(RuntimeError, match='registered models cache'):
        s.stage(spare)
    assert not spare.stage_dir.exists()


def test_initial_registration_refuses_host_models_cache_before_read(staged, monkeypatch):
    s, args, _ = staged
    args.models_cache = Path.home() / '.codex/models_cache.json'
    original = s.digest
    def no_host(path):
        assert Path(path) != args.models_cache
        return original(path)
    monkeypatch.setattr(s, 'digest', no_host)
    with pytest.raises(RuntimeError, match='host models cache'):
        s.cache_input(args)


@pytest.mark.parametrize('fault', ['owner', 'binding', 'effort', 'usage', 'archive', 'deleted', 'stop'])
def test_smoke_instrumentation_failures_do_not_qualify(staged, fault):
    s, _, path = staged
    app = s.runner.Runner(path)
    row = record(s, app, *app.slots()[0])
    if fault == 'owner':
        row['owner_status'] = 'EXITED_NONZERO'
    elif fault == 'binding':
        row['release_binding'] = 'UNKNOWN'
    elif fault == 'effort':
        row['effort_binding'] = 'STOP'
    elif fault == 'usage':
        row['usage'] = 'PARTIAL'
    elif fault == 'archive':
        row['repository_cleanup'].pop('archive_manifest_sha256')
    elif fault == 'deleted':
        row['repository_cleanup']['http_status'] = 200
    else:
        row['status'] = 'STOP'
    assert s.runner.qualify(row)['status'] == 'FAIL'


def test_nondelivering_smoke_pair_qualifies_and_allows_measurement(staged):
    s, args, path = staged
    app = s.runner.Runner(path)
    for slot in app.slots():
        row = append_record(s, app, slot)
        assert s.runner.qualify(row) == dict(status='PASS', checks={key: True for key in
            ('owner', 'binding', 'effort', 'usage', 'archive', 'deleted', 'lifecycle')}, delivered=False)
    assert app.finish_smoke()['status'] == 'QUALIFIED'
    app.prior_deleted('m01')
    args.phase = 'measured'
    measured_path = s.stage(args)
    assert s.runner.Runner(measured_path).slots() == s.runner.SCHEDULE


@pytest.mark.parametrize('fault', ['larger', 'negative', 'nan', 'missing', 'pack', 'false'])
def test_rendered_gate_rejected_before_registration(staged, tmp_path, fault):
    s, args, _ = staged
    gate = s.read(args.token_gate)
    if fault == 'larger':
        gate['rows']['CLAUDE.md']['claude'] = [10, 11]
    elif fault == 'negative':
        gate['rows']['AGENTS.md']['o200k'] = [-1, -2]
    elif fault == 'nan':
        gate['rows']['AGENTS.md']['o200k'] = [float('nan'), 0]
    elif fault == 'missing':
        gate['rows'].pop('AGENTS.md')
    elif fault == 'pack':
        gate['arms_sha256'] = '0' * 64
    else:
        gate['passed'] = False
    candidate = tmp_path / 'bad-gate.json'
    s.write(candidate, gate)
    args = SimpleNamespace(**(vars(args) | dict(stage_dir=tmp_path / 'bad-stage', run_id='bad', token_gate=candidate)))
    with pytest.raises(RuntimeError, match='rendered token gate'):
        s.stage(args)
    assert not args.stage_dir.exists()
    assert not s.runner.smoke_registry('bad').exists()


@pytest.mark.parametrize('remaining,allowed', [(6299, False), (6300, True)])
def test_inherited_claude_snapshot_lifetime_floor(staged, monkeypatch, remaining, allowed):
    s, _, path = staged
    runtime = s.auth.for_engine(s.read(path), 'claude')
    manifest, _ = s.auth.claude_model_auth(runtime['auth'])
    monkeypatch.setattr(s.auth.claude.time, 'time', lambda: manifest['expires_at_ms'] / 1000 - remaining)
    monkeypatch.setattr(s.auth.claude, 'profile', lambda _token: runtime['account'])
    assert (s.auth.preflight(runtime)[1] is None) == allowed


def test_sealed_claude_effort_checks_every_request_and_manifest(tmp_path):
    a = load('attribute', HERE.parent / 'rp-d5-claude-stages/attribute.py')
    out = tmp_path / 'evidence'
    root = out / a.audit.BODY
    root.mkdir(parents=True)
    requests = [root / (str(i) + '.request.json') for i in range(2)]
    for path in requests:
        path.write_text(json.dumps({'output_config': {'effort': 'high'}}))
    def seal():
        manifest = out / 'evidence.manifest.json'
        manifest.write_text(json.dumps(dict(files={str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                                                   for p in requests})))
        return hashlib.sha256(manifest.read_bytes()).hexdigest()
    binding = seal()
    assert a.effort_binding(out, binding, 'high') == 'MATCH'
    assert a.effort_binding(out, binding, 'max') == 'STOP'
    requests[1].write_text(json.dumps({'output_config': {'effort': 'max'}}))
    assert a.effort_binding(out, seal(), 'high') == 'STOP'
    assert a.effort_binding(out, binding, 'max') == 'STOP'


@pytest.mark.parametrize('payload', [b'{"merge_refused": "conflict"}', br'{\"merge_refused\": \"conflict\"}'])
def test_structure_free_refusal_scan_is_reused(tmp_path, payload):
    r = load('runner')
    out = tmp_path / 'evidence'
    (out / 'run').mkdir(parents=True)
    (out / 'run/stdout').write_bytes(payload)
    r.write(out / 'evidence.manifest.json', dict(failures=[], files={'run/stdout': r.digest(out / 'run/stdout')}))
    assert r.smoke.merge_refused(out)


def fake_inherited(s, app, monkeypatch, *, failed_effort=None):
    calls = []
    def inherited(name, task, config):
        calls.append(name)
        assert app.tasks == s.runner.slot_tasks(app.runtime['phase'], name)
        out = Path(app.runtime['output']) / name
        out.mkdir()
        row = record(s, app, name, task, config)
        for filename in ('plan.json', 'baseline.json'):
            s.write(out / filename, dict(arm=row['arm'], release=row['release'], prompt_body_sha256=row['prompt_sha256']))
        s.write(out / 'rp-verdict.json', row)
        s.write(out.parent / ('verdict-' + name + '.json'),
                dict(owner_seconds=12.5, owner_status='EXITED_0', evidence_manifest_sha256='a' * 64))
        return 0
    monkeypatch.setattr(app, 'inherited_run', inherited)
    monkeypatch.setattr(app.grading, 'assess', lambda *_args, **_kwargs: dict(delivery_pass=False))
    monkeypatch.setattr(s.runner.smoke, 'merge_refused', lambda _out: False)
    original = s.runner.load
    monkeypatch.setattr(s.runner, 'load', lambda name, path: SimpleNamespace(
        effort_binding=lambda out, *_args: 'STOP' if out.name == failed_effort else 'MATCH')
        if name == 'attribute_rpd5_rpd6' else original(name, path))
    return calls


def test_actual_runner_qualifies_nondelivery_and_resumes_four_pairs_then_guards(staged, monkeypatch):
    s, args, path = staged
    app = s.runner.Runner(path)
    calls = fake_inherited(s, app, monkeypatch)
    assert app.schedule() == 0
    assert calls == ['smoke-claude', 'smoke-codex']
    assert app.finish_smoke()['status'] == 'QUALIFIED'
    args.phase = 'measured'
    measured_path = s.stage(args)
    measured_app = s.runner.Runner(measured_path)
    calls = fake_inherited(s, measured_app, monkeypatch)
    assert measured_app.schedule(2) == 0
    assert calls == ['m01', 'm02', 'm03', 'm04']
    assert s.read(Path(measured_app.runtime['output']) / 'rp-schedule.json')['status'] == 'PAUSED'
    assert measured_app.schedule() == 0
    assert calls == [name for name, _, _ in s.runner.SCHEDULE]
    assert measured_app.schedule() == 0
    assert len(calls) == 14
    for name in calls:
        out = Path(measured_app.runtime['output']) / name
        row = s.read(out / 'rp-verdict.json')
        assert row['owner_seconds'] == 12.5
        assert row['grading_sha256'] == s.digest(out / 'grading.json')


def test_effort_mismatch_stops_measured_schedule_without_replacement(staged, monkeypatch):
    s, _, path = measured(staged)
    app = s.runner.Runner(path)
    calls = fake_inherited(s, app, monkeypatch, failed_effort='m02')
    assert app.schedule() == 2
    assert calls == ['m01', 'm02']
    rows = s.read(Path(app.runtime['output']) / 'rp-schedule.json')['slots']
    assert rows[1]['effort_binding'] == 'STOP'
    assert [row['status'] for row in rows[2:]] == ['NOT_RUN'] * 12
    assert [row['cell'] for row in rows] == [name for name, _, _ in s.runner.SCHEDULE]


def test_first_smoke_effort_miss_consumes_spare_instead_of_changing_threshold(staged, tmp_path, monkeypatch):
    s, args, path = staged
    app = s.runner.Runner(path)
    calls = fake_inherited(s, app, monkeypatch, failed_effort='smoke-claude')
    assert app.schedule() == 2
    assert calls == ['smoke-claude']
    assert app.finish_smoke()['status'] == 'FAILED'
    spare = SimpleNamespace(**(vars(args) | dict(stage_dir=tmp_path / 'spare', smoke_attempt=2)))
    target = s.stage(spare)
    assert s.runner.Runner(target).slots() == s.runner.smoke_slots(2)


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
    assert (out / 'prompt.txt').read_bytes().startswith((s.runner.PRIOR / 'common.txt').read_bytes())
    (out / 'home/.codex/models_cache.json').write_text('different model cache')
    with pytest.raises(RuntimeError, match='cell models cache'):
        s.runner.prepare.binding(out, app.runtime, 'X')
