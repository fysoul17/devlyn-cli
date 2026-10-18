"""Offline scheduler, route coverage and lifecycle boundary tests."""
import importlib.util
import os
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('rpd8_runner_test_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_schedule_and_routes():
    r = load('runner')
    assert [(task, ''.join(r.ARMS[f'm{i:02}'] for i in (2 * pair - 1, 2 * pair)))
            for pair, task in enumerate(('Z0', 'Z0', 'BV', 'Z0', 'Z0', 'BV', 'Z0', 'Z0'), 1)] == [
        ('Z0', 'XY'), ('Z0', 'YX'), ('BV', 'XY'), ('Z0', 'XY'),
        ('Z0', 'YX'), ('BV', 'YX'), ('Z0', 'XY'), ('Z0', 'YX')]
    assert r.SCHEDULE[16:] == [('g01', 'BV', 'codex'), ('g02', 'Z0', 'codex'),
        ('g03', 'BV', 'claude'), ('g04', 'Z0', 'claude'), ('g05', 'Z0', 'claude'),
        ('g06', 'BV', 'claude'), ('g07', 'BV', 'claude'), ('g08', 'Z0', 'claude')]
    slots = r.SCHEDULE + r.smoke_slots(1) + r.smoke_slots(2)
    assert len(slots) == 28
    for name, _, engine in slots:
        tasks = r.slot_tasks('measured' if name in r.ARMS else 'smoke', name)
        assert tasks['routes']['claude']['owner']['effort'] == r.effort_for(name) == 'high'
        assert tasks['routes']['codex']['owner'] == dict(engine='codex', model='gpt-6-sol', effort='high',
            child_model='gpt-6-sol', child_effort='high')
        if name.startswith(('g', 'smoke')):
            assert r.arm_for(name) == 'Y'
        else:
            assert r.arm_for(name) in ('X', 'Y')
    assert r.legacy.SCHEDULE == r.legacy.ancestor.SCHEDULE == r.SCHEDULE
    assert r.legacy.legacy.prepare is r.prepare


def test_repository_allowlist_and_registry(monkeypatch, tmp_path):
    r = load('runner')
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    app = object.__new__(r.Runner)
    app.runtime = {'run_id': 'offline'}
    app.smoke = r.smoke_slots()
    names = r.SCHEDULE + r.smoke_slots() + r.smoke_slots(2)
    repositories = [app.repository(name) for name, _, _ in names if name != 'g06']
    assert len(repositories) == len(set(repositories)) == 27
    assert app.repository('g06') is None
    assert app.remaining('g06') == []
    assert app.remaining('g05') == [app.repository(slot) for slot in ('g05', 'g07', 'g08')]
    for repository in repositories:
        assert r.github.url(repository) == 'https://github.com/' + repository + '.git'
    for repository in ('fysoul17/rpd8-offline-g06', 'fysoul17/rpd8-offline-m17',
                       'fysoul17/rpd7-offline-m01', 'other/rpd8-offline-m01'):
        with pytest.raises(r.github.EvidenceError):
            r.github.url(repository)
    assert r.smoke_registry('offline') == tmp_path / '.devlyn/rp-d8-runs/offline'


def test_route_watch_alive_dead_missing_and_log(tmp_path, monkeypatch):
    r = load('runner')
    assert r.route_watch()['alive'] is None
    pid = tmp_path / 'watch.pid'
    log = tmp_path / 'watch.log'
    pid.write_text(str(os.getpid()) + '\n')
    log.write_text('start\n' + 'long ' * 10000 + '\nlast route\n')
    result = r.route_watch(pid)
    assert result['alive'] is True and result['last_line'] == 'last route'
    def dead(*_args):
        raise ProcessLookupError
    monkeypatch.setattr(r.os, 'kill', dead)
    assert r.route_watch(pid)['alive'] is False
    pid.write_text('-1')
    assert r.route_watch(pid)['alive'] is None
    pid.unlink()
    log.unlink()
    result = r.route_watch(pid)
    assert result['alive'] is None and result['last_line'] is None and 'unavailable' in result['reason']


def test_smoke_qualification_checks_prompt_without_requiring_delivery():
    r = load('runner')
    record = dict(dispatched=True, owner_status='EXITED_0', release_binding='MATCH', config='claude',
        effort_binding='MATCH', usage='COMPLETE', status='PRODUCT_INCOMPLETE',
        delivery_assessment='PRODUCT_INCOMPLETE', prompt_binding='MATCH', prompt_sha256=r.prepare.P1_SHA256,
        repository_cleanup=dict(status='DELETED', http_status=404, archive_manifest_sha256='a' * 64))
    assert r.qualify(record)['status'] == 'PASS'
    assert r.qualify(record)['delivered'] is False
    for change in ({'effort_binding': 'MISMATCH'}, {'prompt_binding': 'UNKNOWN'}, {'usage': 'PARTIAL'},
                   {'owner_status': 'EXITED_1'}, {'revocation_required': True}):
        assert r.qualify(record | change)['status'] == 'FAIL'


def fake_scheduler(r, tmp_path):
    app = object.__new__(r.Runner)
    app.runtime = dict(phase='measured', output=str(tmp_path))
    app.frozen = 'frozen'
    app.completed_prefix = lambda: []
    app.slots = lambda: r.SCHEDULE
    return app


@pytest.mark.parametrize('pair', [1, 4, 5, 8])
def test_pause_at_each_pair_boundary(tmp_path, monkeypatch, pair):
    r = load('runner')
    app = fake_scheduler(r, tmp_path)
    monkeypatch.setattr(r.prepare, 'release_identity', lambda _runtime, arm: arm)
    calls = []
    def run(name, task, arm, config):
        calls.append(name)
        (tmp_path / name).mkdir()
        r.write(tmp_path / name / 'rp-verdict.json', dict(cell=name, status='PRODUCT_INCOMPLETE', dispatched=True))
        return 0
    app.run = run
    assert app.schedule(pair) == 0
    assert calls == [name for name, _, _ in r.SCHEDULE[:2 * pair]]
    assert r.read(tmp_path / 'rp-schedule.json')['status'] == 'PAUSED'


def test_stop_never_dispatches_successors(tmp_path, monkeypatch):
    r = load('runner')
    app = fake_scheduler(r, tmp_path)
    monkeypatch.setattr(r.prepare, 'release_identity', lambda _runtime, arm: arm)
    calls = []
    def stop(name, task, arm, config):
        calls.append(name)
        (tmp_path / name).mkdir()
        r.write(tmp_path / name / 'rp-verdict.json', dict(cell=name, status='STOP', dispatched=True))
        return 2
    app.run = stop
    assert app.schedule() == 2
    assert calls == ['m01']
    result = r.read(tmp_path / 'rp-schedule.json')
    assert len(result['slots']) == 24 and result['dispatched'] == 1
    assert all(row['status'] == 'NOT_RUN' for row in result['slots'][1:])


def test_guard_pause_boundary(tmp_path, monkeypatch):
    r = load('runner')
    app = fake_scheduler(r, tmp_path)
    monkeypatch.setattr(r.prepare, 'release_identity', lambda _runtime, arm: arm)
    calls = []
    def run(name, task, arm, config):
        calls.append(name)
        (tmp_path / name).mkdir()
        r.write(tmp_path / name / 'rp-verdict.json', dict(cell=name, status='PASS', dispatched=True))
        return 0
    app.run = run
    app.schedule(through_guard=6)
    assert calls[-1] == 'g06' and len(calls) == 22


def test_stamp_precedes_smoke_registry_digest(tmp_path, monkeypatch):
    r = load('runner')
    app = object.__new__(r.Runner)
    app.runtime = {'output': str(tmp_path)}
    app.active_name = 'smoke-claude'
    app.route_observation = {'alive': True, 'last_line': 'route'}
    path = tmp_path / app.active_name / 'rp-verdict.json'
    path.parent.mkdir()
    r.write(path, {})
    def finish(_app):
        record = r.read(path)
        assert record['route_watch'] == app.route_observation
        return {'sha256': r.digest(path)}
    monkeypatch.setattr(r.legacy.Runner, 'finish_smoke', finish)
    assert app.finish_smoke()['sha256'] == r.digest(path)


@pytest.mark.parametrize('fault', [None, 'STOP', 'effort', 'archive', 'account', 'runtime'])
def test_g07_requires_g06_local_custody_without_http_receipt(tmp_path, monkeypatch, fault):
    r = load('runner')
    app = object.__new__(r.Runner)
    app.runtime = app.base_runtime = dict(output=str(tmp_path), codex_account='codex', claude_account='claude')
    app.frozen = 'frozen'
    app.record_binding = lambda _record: None
    monkeypatch.setattr(r, 'smoke_registration', lambda _runtime: (None, {'status': 'QUALIFIED'}))
    manifest = tmp_path / 'archives/g06/manifest.json'
    manifest.parent.mkdir(parents=True)
    r.write(manifest, {'repository': None, 'files': {}})
    record = dict(status='PRODUCT_INCOMPLETE', effort_binding='MATCH', codex_account='codex',
        account='claude', frozen_runtime_sha256='frozen', repository_cleanup=dict(repository=None,
        status='NOT_APPLICABLE', archive_manifest_sha256=r.digest(manifest)))
    if fault == 'STOP':
        record['status'] = 'STOP'
    elif fault == 'effort':
        record['effort_binding'] = 'MISMATCH'
    elif fault == 'archive':
        record['repository_cleanup']['archive_manifest_sha256'] = '0' * 64
    elif fault == 'account':
        record['account'] = 'other'
    elif fault == 'runtime':
        record['frozen_runtime_sha256'] = 'other'
    (tmp_path / 'g06').mkdir()
    r.write(tmp_path / 'g06/rp-verdict.json', record)
    if fault is None:
        app.prior_deleted('g07')
    else:
        with pytest.raises(RuntimeError):
            app.prior_deleted('g07')


def test_watcher_observed_before_slot_and_stamped_after(tmp_path, monkeypatch):
    r = load('runner')
    app = object.__new__(r.Runner)
    app.runtime = dict(phase='measured', output=str(tmp_path))
    app.route_watch_pid_file = app.route_watch_log = None
    events = []
    observation = dict(alive=None, last_line=None, reason='not configured')
    def observe(*_args):
        events.append('watch')
        return observation
    def inherited(_app, name, *_args):
        events.append('slot')
        assert app.route_observation is observation
        (tmp_path / name).mkdir()
        r.write(tmp_path / name / 'rp-verdict.json', {'status': 'STOP'})
        return 2
    monkeypatch.setattr(r, 'route_watch', observe)
    monkeypatch.setattr(r.legacy.Runner, 'run', inherited)
    assert app.run('m01', 'Z0', 'X', 'claude') == 2
    assert events == ['watch', 'slot']
    assert r.read(tmp_path / 'm01/rp-verdict.json')['route_watch'] == observation
