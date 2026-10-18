"""Offline pack checks with synthetic archives and local Git object responses."""
from copy import deepcopy
import importlib.util
import io
from pathlib import Path
import socket
import subprocess
import tarfile
import urllib.request

import pytest

HERE = Path(__file__).resolve().parent


def load(path=HERE / 'pack.py'):
    spec = importlib.util.spec_from_file_location('rpd6_test_pack', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail('external operation forbidden')
    for target, name in ((socket, 'create_connection'), (urllib.request, 'urlopen'),
                         (subprocess, 'run'), (subprocess, 'Popen')):
        monkeypatch.setattr(target, name, forbidden)


def fixture(pack, root, monkeypatch, version='4.2.22'):
    source = root / 'registry.tgz'
    before = {name: ('# original ' + name + '\n').encode() for name in pack.FILES}
    after = {name: raw + b'# candidate\n' for name, raw in before.items()}
    entries = {'package.json': ('{"name":"devlyn-cli","version":"' + version + '"}').encode(),
               **before, 'bin/devlyn.js': b'// fixture\n',
               'bin/instruction-templates.json': b'{"old": "template"}\n',
               '.agents/skills/_shared/runtime-principles.md': b'unchanged optional mirror\n'}
    with tarfile.open(source, 'w:gz', format=tarfile.PAX_FORMAT) as archive:
        for name, raw in entries.items():
            info = tarfile.TarInfo('package/' + name)
            info.size, info.mode, info.mtime = len(raw), 0o755 if name.endswith('.js') else 0o644, 42
            info.uid, info.gid, info.uname, info.gname = 501, 20, 'fixture', 'staff'
            archive.addfile(info, io.BytesIO(raw))
        link = tarfile.TarInfo('package/link')
        link.type, link.linkname = tarfile.SYMTYPE, 'bin/devlyn.js'
        archive.addfile(link)
    commit = 'a' * 40

    def git(*args):
        if args == ('rev-parse', '--verify', commit + '^{commit}'):
            return (commit + '\n').encode()
        name = args[-1].removeprefix(commit + ':')
        assert name in pack.FILES
        if args[0] == 'show':
            return after[name]
        assert args[:2] == ('rev-parse', '--verify')
        return (pack.blob_id(after[name]) + '\n').encode()
    monkeypatch.setattr(pack.legacy, 'git', git)
    return source, before, after, commit


def build(pack, source, dest, commit):
    return pack.build(source, dest, commit, **pack.identity(source))


def test_exact_three_candidate_paths_and_registry_identity(tmp_path, monkeypatch):
    p = load()
    assert p.FILES == ('CLAUDE.md', 'AGENTS.md', 'config/skills/_shared/runtime-principles.md')
    source, _, after, commit = fixture(p, tmp_path, monkeypatch)
    first = build(p, source, tmp_path / 'first', commit)
    second = build(p, source, tmp_path / 'second', commit)
    assert first.read_bytes() == second.read_bytes()
    assert (first.parent / 'X.tgz').read_bytes() == source.read_bytes()
    assert (first.parent / 'Y.tgz').read_bytes() == (second.parent / 'Y.tgz').read_bytes()
    arms = p.verify_arms(first)
    assert arms['Y']['source']['candidate_commit'] == commit
    assert arms['Y']['source']['candidate_blobs'] == {name: p.blob_id(raw) for name, raw in after.items()}
    manifests = {arm: p.archive_manifest(first.parent / (arm + '.tgz')) for arm in ('X', 'Y')}
    assert {name for name in manifests['X'] if manifests['X'][name] != manifests['Y'][name]} == set(p.FILES)
    for name, raw in after.items():
        assert p.content(first.parent / 'Y.tgz', name) == raw
    assert p.content(first.parent / 'Y.tgz') == after['CLAUDE.md']
    for arm in ('X', 'Y'):
        archive_path = first.parent / (arm + '.tgz')
        with tarfile.open(archive_path) as archive:
            archive.extractall(tmp_path / arm, filter='data')
        assert p.tree_manifest(tmp_path / arm / 'package') == manifests[arm]
    prior = load(HERE.parent / 'rp-d4-helper-report/pack.py')
    assert prior.FILES == ('config/skills/_shared/task-complete.py', 'config/skills/_shared/task-completion.md')


@pytest.mark.parametrize('fault', ['sha256', 'integrity', 'version', 'commit', 'unchanged', 'git-blob'])
def test_invalid_inputs_rejected_before_output(tmp_path, monkeypatch, fault):
    p = load()
    source, before, after, commit = fixture(p, tmp_path, monkeypatch,
                                          version='4.2.18' if fault == 'version' else '4.2.22')
    registration = p.identity(source)
    if fault in ('sha256', 'integrity'):
        registration[fault] = 'wrong'
    elif fault == 'commit':
        commit = '--help'
    elif fault == 'unchanged':
        after[p.FILES[0]] = before[p.FILES[0]]
    elif fault == 'git-blob':
        original = p.legacy.git
        monkeypatch.setattr(p.legacy, 'git', lambda *args: b'0' * 40 if args ==
                            ('rev-parse', '--verify', commit + ':' + p.FILES[0]) else original(*args))
    with pytest.raises(ValueError):
        p.build(source, tmp_path / 'dest', commit, **registration)
    assert not (tmp_path / 'dest').exists()


@pytest.mark.parametrize('fault', ['labels', 'hash', 'manifest', 'candidate-blob', 'provenance'])
def test_verify_rejects_broken_bindings(tmp_path, monkeypatch, fault):
    p = load()
    source, _, _, commit = fixture(p, tmp_path, monkeypatch)
    path = build(p, source, tmp_path / 'arms', commit)
    arms = p.read(path)
    if fault == 'labels':
        arms['X'], arms['Y'] = arms['Y'], arms['X']
    elif fault == 'hash':
        (path.parent / 'Y.tgz').write_bytes((path.parent / 'Y.tgz').read_bytes() + b'drift')
    elif fault == 'manifest':
        arms['Y']['manifest_sha256'] = '0' * 64
    elif fault == 'candidate-blob':
        arms['Y']['source']['candidate_blobs'][p.FILES[0]] = '0' * 40
    else:
        arms['Y']['source']['registry'] = 'devlyn-cli@4.2.18'
    p.write(path, arms)
    with pytest.raises(ValueError):
        p.verify_arms(path)


@pytest.mark.parametrize('fault', ['extra-content', 'candidate-mode', 'candidate-mtime', 'order'])
def test_pair_rejects_extra_changes(tmp_path, monkeypatch, fault):
    p = load()
    source, _, _, commit = fixture(p, tmp_path, monkeypatch)
    path = build(p, source, tmp_path / 'arms', commit)
    target = tmp_path / 'changed.tgz'
    with tarfile.open(path.parent / 'Y.tgz') as archive, tarfile.open(target, 'w:gz') as output:
        members = archive.getmembers()
        if fault == 'order':
            members.reverse()
        for original in members:
            member = deepcopy(original)
            data = archive.extractfile(original).read() if original.isfile() else None
            if fault == 'extra-content' and member.name == 'package/bin/instruction-templates.json':
                data = b'{}\n'
                member.size = len(data)
            elif member.name == 'package/' + p.FILES[0]:
                if fault == 'candidate-mode':
                    member.mode = 0o755
                elif fault == 'candidate-mtime':
                    member.mtime += 1
            output.addfile(member, io.BytesIO(data) if data is not None else None)
    with pytest.raises(ValueError):
        p.verify_pair({'X': source, 'Y': target}, p.read(path)['Y']['source']['candidate_blobs'])
