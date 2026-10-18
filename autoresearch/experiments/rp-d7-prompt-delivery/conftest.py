"""Synthetic offline fixtures; no process, socket or experiment dispatch."""
import importlib.util
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace
import urllib.request

import pytest

HERE = Path(__file__).resolve().parent


def load(name, path=None):
    spec = importlib.util.spec_from_file_location('rpd7_test_' + name, path or HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail('external operation forbidden')
    for target, name in ((socket, 'create_connection'), (socket.socket, 'connect'), (urllib.request, 'urlopen'),
                         (subprocess, 'run'), (subprocess, 'Popen'), (subprocess, 'check_output')):
        monkeypatch.setattr(target, name, forbidden)


@pytest.fixture
def staged(tmp_path, monkeypatch):
    s = load('stage')
    fixtures = load('pack_fixtures', HERE.parent / 'rp-d6-claude-delivery/test_pack.py')
    source, _, _, _ = fixtures.fixture(s.pack.legacy, tmp_path, monkeypatch)
    arms = s.pack.build(source, tmp_path / 'release', **s.pack.identity(source))
    historical = load('auth_fixtures', HERE.parent / 'rp-d4-helper-report/test_runtime.py')
    host = tmp_path / 'host'
    host.mkdir()
    monkeypatch.setattr(Path, 'home', lambda: host)
    monkeypatch.setattr(s.auth.claude.time, 'time', lambda: 1_700_000_000)
    model = historical.snapshot(s.auth, tmp_path / 'codex-auth')
    guard = historical.guard_snapshot(s.auth, tmp_path / 'claude-auth', model)
    gh = tmp_path / 'github-auth'
    gh.mkdir(mode=0o700)
    for name in ('hosts.yml', 'config.yml'):
        s.auth.write_private(gh, name, b'synthetic fixture\n')
    frozen = tmp_path / 'registered-models-cache.json'
    frozen.write_text('{"models": []}\n')
    args = SimpleNamespace(stage_dir=tmp_path / 'stage', phase='smoke', run_id='offline', arms=arms,
        image='sha256:' + 'a' * 64, auth=model, claude_auth=guard, github_auth=gh,
        models_cache=frozen, models_cache_sha256=s.digest(frozen), smoke_output=None, smoke_attempt=1)
    return s, args, s.stage(args)


def record(s, app, name, task, config, **changes):
    fixtures = load('runtime_fixtures', HERE.parent / 'rp-d6-claude-delivery/test_runtime.py')
    return fixtures.record(s, app, name, task, config, prompt_binding='MATCH', **changes)


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
