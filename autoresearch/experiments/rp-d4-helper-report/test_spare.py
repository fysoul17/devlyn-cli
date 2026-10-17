"""Offline cross-directory smoke consumption and frozen-input bindings."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rpd4_spare_runtime_tests', HERE / 'test_runtime.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
offline, staged = fixtures.offline, fixtures.staged


def fail_smoke(staged, monkeypatch, *, revoked=False, status='STOP', cleanup_fault=None):
    s, args, path = staged
    app = s.runner.Runner(path)
    def inherited(_self, name, task, _route, engine):
        out = Path(app.runtime['output']) / name
        out.mkdir()
        row = dict(fixtures.record(s, app, name, task, engine), status=status, revocation_required=revoked)
        if cleanup_fault == 'missing':
            row.pop('repository_cleanup')
        elif cleanup_fault:
            row['repository_cleanup'][cleanup_fault] = None
        s.write(out / 'rp-verdict.json', row)
        return 2 if status == 'STOP' else 0
    monkeypatch.setattr(s.runner.legacy.legacy.Runner, 'run', inherited)
    monkeypatch.setattr(s.runner.smoke, 'merge_refused', lambda _out: False)
    assert app.schedule() == 2
    return app


def spare_args(args, root, **changes):
    return SimpleNamespace(**(vars(args) | dict(stage_dir=root / 'spare', smoke_attempt=2) | changes))


def test_spare_requires_recorded_failed_first_attempt(staged, tmp_path):
    s, args, _ = staged
    with pytest.raises(RuntimeError, match='failed first smoke'):
        s.stage(spare_args(args, tmp_path))
    assert not (tmp_path / 'spare').exists()


@pytest.mark.parametrize('fault', ['missing', 'repository', 'status', 'http_status', 'archive_manifest_sha256'])
def test_spare_requires_failed_predecessor_archived_and_deleted(staged, tmp_path, monkeypatch, fault):
    s, args, _ = staged
    fail_smoke(staged, monkeypatch, cleanup_fault=fault)
    with pytest.raises(RuntimeError, match='failed smoke repository has no archived deletion/404 receipt'):
        s.stage(spare_args(args, tmp_path))
    assert not (tmp_path / 'spare').exists()


@pytest.mark.parametrize('status', ['STOP', 'PRODUCT_INCOMPLETE'])
def test_spare_binds_failed_first_across_stage_directories_and_prevents_replay(staged, tmp_path, monkeypatch, status):
    s, args, path = staged
    original = fail_smoke(staged, monkeypatch, status=status)
    spare = spare_args(args, tmp_path)
    target = s.stage(spare)
    app = s.runner.Runner(target)
    app.prior_deleted('smoke2-codex-X')
    state_path, state = s.runner.smoke_registration(s.read(target))
    assert state['previous_sha256'] == s.digest(state_path.parent / 'attempt-1.json')
    assert state['inputs'] == s.runner.smoke_inputs(s.read(path))
    for attempt in (1, 2, 3):
        retry = spare_args(args, tmp_path, stage_dir=tmp_path / f'replay-{attempt}', smoke_attempt=attempt)
        with pytest.raises((RuntimeError, FileExistsError)):
            s.stage(retry)
    with pytest.raises(RuntimeError, match='superseded'):
        original.run('smoke-codex-X', 'SM', 'X', 'codex')


@pytest.mark.parametrize('field', ['arms', 'image', 'codex', 'claude', 'models_cache'])
def test_spare_refuses_frozen_input_drift_in_new_directory(staged, tmp_path, monkeypatch, field):
    s, args, _ = staged
    fail_smoke(staged, monkeypatch)
    spare = spare_args(args, tmp_path)
    if field == 'arms':
        copied = tmp_path / 'copied-release'
        copied.mkdir()
        spare.arms = copied / 'arms.json'
        spare.arms.write_bytes(args.arms.read_bytes() + b'\n')
    elif field == 'image':
        spare.image = 'sha256:' + 'b' * 64
    elif field == 'codex':
        spare.auth = fixtures.snapshot(s.auth, tmp_path / 'foreign-codex', account='foreign-account')
        spare.claude_auth = fixtures.guard_snapshot(s.auth, tmp_path / 'foreign-codex-guard', spare.auth)
    elif field == 'claude':
        spare.claude_auth = fixtures.guard_snapshot(s.auth, tmp_path / 'foreign-claude', args.auth,
                                                   account=['d' * 12, 'e' * 12])
    else:
        (Path.home() / '.codex/models_cache.json').write_text('{"models": ["drift"]}')
    with pytest.raises(RuntimeError, match='spare changed registered'):
        s.stage(spare)
    assert not spare.stage_dir.exists()


def test_spare_failed_stop_persists_across_stage_and_release_directories(staged, tmp_path, monkeypatch):
    s, args, _ = staged
    fail_smoke(staged, monkeypatch)
    spare = spare_args(args, tmp_path)
    target = s.stage(spare)
    fail_smoke((s, spare, target), monkeypatch)
    _, state = s.runner.smoke_registration(s.read(target))
    assert state['status'] == 'STOP'
    copied = tmp_path / 'copied-release'
    copied.mkdir()
    copied_arms = copied / 'arms.json'
    copied_arms.write_bytes(args.arms.read_bytes())
    for attempt in (1, 2, 3):
        retry = spare_args(args, tmp_path, stage_dir=tmp_path / f'replay-{attempt}',
                           arms=copied_arms, smoke_attempt=attempt)
        with pytest.raises((RuntimeError, FileExistsError)):
            s.stage(retry)
    with pytest.raises(RuntimeError, match='consumed'):
        s.runner.Runner(target).run('smoke2-codex-X', 'SM', 'X', 'codex')


def test_credential_revocation_consumes_run_without_spare(staged, tmp_path, monkeypatch):
    s, args, path = staged
    fail_smoke(staged, monkeypatch, revoked=True)
    assert s.runner.smoke_registration(s.read(path))[1]['status'] == 'STOP'
    with pytest.raises(RuntimeError, match='failed first smoke without credential revocation'):
        s.stage(spare_args(args, tmp_path))


def test_spare_checks_original_failure_evidence_has_not_changed(staged, tmp_path, monkeypatch):
    s, args, _ = staged
    app = fail_smoke(staged, monkeypatch)
    verdict = Path(app.runtime['output']) / 'smoke-codex-X/rp-verdict.json'
    verdict.write_bytes(verdict.read_bytes() + b'\n')
    with pytest.raises(RuntimeError, match='smoke evidence changed'):
        s.stage(spare_args(args, tmp_path))


def test_qualified_spare_allows_measurement_only_from_its_stage(staged, tmp_path, monkeypatch):
    s, args, _ = staged
    fail_smoke(staged, monkeypatch)
    spare = spare_args(args, tmp_path)
    target = s.stage(spare)
    app = s.runner.Runner(target)
    for slot in app.slots():
        fixtures.append_record(s, app, slot)
    spare.phase = 'measured'
    measured = s.stage(spare)
    app = s.runner.Runner(measured)
    app.prior_deleted('m01')
    assert s.runner.smoke_registration(s.read(measured))[1]['status'] == 'QUALIFIED'
    args.phase = 'measured'
    with pytest.raises(RuntimeError, match='superseded'):
        s.stage(args)
