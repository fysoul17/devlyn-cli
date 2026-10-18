"""Synthetic archive, installed-token and prompt registration checks; no network."""
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


def load(name, path=None):
    spec = importlib.util.spec_from_file_location('rpd8_pack_test_' + name, path or HERE / (name + '.py'))
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


def archive_fixture(pack, root, monkeypatch, changed=None, candidate_files=None):
    source = root / 'registry.tgz'
    before, after = b'# original task completion\n', b'# candidate\n'
    entries = {'package.json': b'{"name":"devlyn-cli","version":"4.2.22"}',
        pack.FILE: before, 'bin/devlyn.js': b'// unchanged\n',
        'config/skills/_shared/runtime-principles.md': b'principles\n',
        'CLAUDE.md': b'# Shared project instructions\n', 'AGENTS.md': b'# Shared project instructions\n'}
    with tarfile.open(source, 'w:gz') as archive:
        for name, raw in entries.items():
            member = tarfile.TarInfo('package/' + name)
            member.size, member.mode = len(raw), 0o644
            archive.addfile(member, io.BytesIO(raw))
    commit = pack.CANDIDATE_COMMIT
    files = ['bin', 'config', 'CLAUDE.md', 'AGENTS.md', '!**/*.pyc']

    def git(*args):
        if args == ('rev-parse', '--verify', commit + '^{commit}'):
            return (commit + '\n').encode()
        if args == ('show', pack.DESIGN_COMMIT + ':package.json'):
            return json.dumps(dict(files=files)).encode()
        if args == ('show', commit + ':package.json'):
            return json.dumps(dict(files=files if candidate_files is None else candidate_files)).encode()
        if args[:1] == ('diff-tree',):
            assert args[-3:] == (pack.DESIGN_COMMIT, commit, '--')
            return ('\0'.join(pack.FILES if changed is None else changed) + '\0').encode()
        if args == ('show', commit + ':' + pack.FILE):
            return after
        assert args == ('rev-parse', '--verify', commit + ':' + pack.FILE)
        return (pack.blob_id(after) + '\n').encode()
    monkeypatch.setattr(pack.legacy, 'git', git)
    return source, entries, after


def packed(pack, root, monkeypatch, **kwargs):
    source, entries, after = archive_fixture(pack, root, monkeypatch, **kwargs)
    arms = pack.build(source, root / 'arms', pack.CANDIDATE_COMMIT, **pack.identity(source))
    return arms, source, entries, after


def gate_fixture(gate, root, monkeypatch):
    arms, _, entries, after = packed(gate.pack, root, monkeypatch)
    paths = {name: [] for name in gate.NAMES}
    for arm in ('X', 'Y'):
        folder = root / arm
        folder.mkdir()
        for name in gate.NAMES:
            raw = (entries[gate.pack.FILE] if arm == 'X' else after) if name == 'task-completion.md' else (
                b'@AGENTS.md\n' if name == 'CLAUDE.md' else gate.managed_block(entries[name]))
            path = folder / name
            path.write_bytes(raw)
            paths[name].append(path)
    return arms, paths


def test_frozen_pack_exact_one_path_and_identity(tmp_path, monkeypatch):
    p = load('pack')
    arms, source, _, after = packed(p, tmp_path, monkeypatch)
    registration = p.verify_arms(arms)
    assert p.FILES == ('config/skills/_shared/task-completion.md',)
    assert (arms.parent / 'X.tgz').read_bytes() == source.read_bytes()
    assert p.content(arms.parent / 'Y.tgz') == after
    assert registration['Y']['source']['candidate_commit'] == p.CANDIDATE_COMMIT
    assert registration['Y']['source']['candidate_blobs'] == {p.FILE: p.blob_id(after)}
    manifests = [p.archive_manifest(arms.parent / (arm + '.tgz')) for arm in ('X', 'Y')]
    assert {name for name in manifests[0] if manifests[0][name] != manifests[1][name]} == set(p.FILES)
    prior = load('prior', HERE.parent / 'rp-d6-claude-delivery/pack.py')
    assert len(prior.FILES) == 3


@pytest.mark.parametrize('extra', ['bin/devlyn.js', 'config/other.md', 'CLAUDE.md', 'package.json', 'README.md', 'LICENSE'])
def test_any_other_shipped_difference_fails(tmp_path, monkeypatch, extra):
    p = load('pack')
    source, _, _ = archive_fixture(p, tmp_path, monkeypatch, changed=[p.FILE, extra])
    with pytest.raises(ValueError, match='exactly task-completion.md'):
        p.build(source, tmp_path / 'arms', p.CANDIDATE_COMMIT, **p.identity(source))
    assert not (tmp_path / 'arms').exists()


def test_unshipped_mirror_allowed(tmp_path, monkeypatch):
    p = load('pack')
    assert packed(p, tmp_path, monkeypatch, changed=[p.FILE, '.agents/skills/_shared/task-completion.md'])[0].is_file()


@pytest.mark.parametrize('fault', ['sha256', 'integrity', 'files', 'candidate'])
def test_pack_frozen_inputs_fail_closed(tmp_path, monkeypatch, fault):
    p = load('pack')
    source, _, _ = archive_fixture(p, tmp_path, monkeypatch, candidate_files=['bin'] if fault == 'files' else None)
    hashes = p.identity(source)
    if fault in hashes:
        hashes[fault] = 'wrong'
    if fault == 'candidate':
        original = p.legacy.git
        monkeypatch.setattr(p.legacy, 'git', lambda *args: b'a' * 40 if args[0] == 'rev-parse' else original(*args))
    with pytest.raises(ValueError):
        p.build(source, tmp_path / 'arms', p.CANDIDATE_COMMIT, **hashes)


def test_gate_on_verified_installed_files_and_bound_record(tmp_path, monkeypatch):
    gate = load('rendered_gate')
    arms, paths = gate_fixture(gate, tmp_path, monkeypatch)
    result = gate.evaluate(arms, paths, len, SimpleNamespace(encode=list))
    assert gate.validate(result, arms) == result
    assert result['passed'] is True
    assert result['rows']['CLAUDE.md']['identical'] is True
    assert result['rows']['task-completion.md']['claude'] == [27, 12]


@pytest.mark.parametrize('fault', ['claude', 'o200k', 'root-bytes', 'arms', 'nan', 'bool', 'missing'])
def test_gate_registration_refuses_every_failure(tmp_path, monkeypatch, fault):
    gate = load('rendered_gate')
    arms, paths = gate_fixture(gate, tmp_path, monkeypatch)
    result = gate.evaluate(arms, paths, len, SimpleNamespace(encode=list))
    if fault in ('claude', 'o200k'):
        result['rows']['task-completion.md'][fault] = [10, 11]
    elif fault == 'root-bytes':
        result['rows']['AGENTS.md']['sha256'][1] = '0' * 64
    elif fault == 'arms':
        result['arms_sha256'] = '0' * 64
    elif fault == 'missing':
        del result['rows']['CLAUDE.md']
    else:
        result['rows']['task-completion.md']['claude'] = [float('nan') if fault == 'nan' else True, 0]
    with pytest.raises(ValueError):
        gate.validate(result, arms)


def test_gate_increased_counts_fail_and_root_byte_mismatch_fails(tmp_path, monkeypatch):
    gate = load('rendered_gate')
    arms, paths = gate_fixture(gate, tmp_path, monkeypatch)
    result = gate.evaluate(arms, paths, lambda body: 100 - len(body), SimpleNamespace(encode=list))
    assert result['passed'] is False
    paths['CLAUDE.md'][1].write_bytes(gate.managed_block(b'# Shared project instructions\n'))
    result = gate.evaluate(arms, paths, len, SimpleNamespace(encode=list))
    assert result['passed'] is False
    paths['task-completion.md'][1].write_bytes(b'tampered\n')
    with pytest.raises(ValueError, match='differs from verified arm'):
        gate.evaluate(arms, paths, len, SimpleNamespace(encode=list))


def test_gate_cli_records_pass_and_fails_without_printing_oauth(tmp_path, monkeypatch, capsys):
    gate = load('rendered_gate')
    arms, paths = gate_fixture(gate, tmp_path, monkeypatch)
    counter = SimpleNamespace(tiktoken=SimpleNamespace(get_encoding=lambda _: SimpleNamespace(encode=list)),
                              claude_tokens=lambda body, token: len(body))
    # Substitute only the inherited network counter import; the complete CLI runs offline.
    original_spec = gate.importlib.util.spec_from_file_location
    def spec(name, path):
        if name == 'gate_rpd6_rpd8':
            return SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module: module.__dict__.update(counter.__dict__)))
        return original_spec(name, path)
    original_module = gate.importlib.util.module_from_spec
    monkeypatch.setattr(gate.importlib.util, 'spec_from_file_location', spec)
    monkeypatch.setattr(gate.importlib.util, 'module_from_spec',
                        lambda value: SimpleNamespace() if isinstance(value, SimpleNamespace) else original_module(value))
    monkeypatch.setattr(gate.subprocess, 'run', lambda *a, **kw: SimpleNamespace(
        stdout=json.dumps({'claudeAiOauth': {'accessToken': 'synthetic-secret'}})))
    import sys
    monkeypatch.setattr(sys, 'argv', ['rendered_gate.py', *[str(path) for name in gate.NAMES for path in paths[name]],
                                    '--arms', str(arms), '--output', str(tmp_path / 'gate.json')])
    assert gate.main() == 0
    assert 'synthetic-secret' not in capsys.readouterr().out
    assert json.loads((tmp_path / 'gate.json').read_text())['passed'] is True
