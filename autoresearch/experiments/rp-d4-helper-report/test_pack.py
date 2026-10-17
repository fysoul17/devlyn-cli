"""Synthetic archives and mocked local Git objects; no credentials or external operations."""
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


def load():
    spec = importlib.util.spec_from_file_location('rpd4_test_pack', HERE / 'pack.py')
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
    entries = [('package/package.json', ('{"name":"devlyn-cli","version":"' + version + '"}').encode()),
               *(('package/' + name, raw) for name, raw in before.items()),
               ('package/bin/devlyn.js', b'// fixture\n'),
               ('package/long-' + 'z' * 110, b'\x00\xffbytes\n')]
    with tarfile.open(source, 'w:gz', format=tarfile.PAX_FORMAT) as archive:
        for name, raw in entries:
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(raw), 0o755 if '/bin/' in name else 0o644, 1720000123
            info.uid, info.gid, info.uname, info.gname = 501, 20, 'fixture', 'staff'
            archive.addfile(info, io.BytesIO(raw))
        directory = tarfile.TarInfo('package/empty')
        directory.type, directory.mode, directory.mtime = tarfile.DIRTYPE, 0o755, 42
        archive.addfile(directory)
        link = tarfile.TarInfo('package/link')
        link.type, link.linkname, link.mtime = tarfile.SYMTYPE, 'bin/devlyn.js', 55
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
    monkeypatch.setattr(pack, 'git', git)
    return source, before, after, commit


def build(pack, source, dest, commit):
    return pack.build(source, dest, commit, **pack.identity(source))


def test_pack_copies_registry_and_changes_exact_candidate_blobs_deterministically(tmp_path, monkeypatch):
    p = load()
    source, _, after, commit = fixture(p, tmp_path, monkeypatch)
    first = build(p, source, tmp_path / 'first', commit)
    second = build(p, source, tmp_path / 'second', commit)
    assert first.read_bytes() == second.read_bytes()
    assert (first.parent / 'X.tgz').read_bytes() == source.read_bytes()
    assert (first.parent / 'Y.tgz').read_bytes() == (second.parent / 'Y.tgz').read_bytes()
    assert (first.parent / 'Y.tgz').read_bytes()[4:8] == b'\0' * 4
    arms = p.verify_arms(first)
    assert arms['Y']['source']['candidate_commit'] == commit
    assert arms['Y']['source']['candidate_blobs'] == {name: p.blob_id(raw) for name, raw in after.items()}
    for name, raw in after.items():
        assert p.content(first.parent / 'Y.tgz', name) == raw
    for arm in ('X', 'Y'):
        archive_path = first.parent / (arm + '.tgz')
        with tarfile.open(archive_path) as archive:
            archive.extractall(tmp_path / arm, filter='data')
        manifest = p.tree_manifest(tmp_path / arm / 'package')
        assert manifest == p.archive_manifest(archive_path)
        assert p.manifest_digest(manifest) == arms[arm]['manifest_sha256']


@pytest.mark.parametrize('fault', ['sha256', 'integrity', 'version', 'commit', 'unchanged', 'git-blob'])
def test_invalid_inputs_are_rejected_before_writing(tmp_path, monkeypatch, fault):
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
        original = p.git
        monkeypatch.setattr(p, 'git', lambda *args: b'0' * 40 if args ==
                            ('rev-parse', '--verify', commit + ':' + p.FILES[0]) else original(*args))
    with pytest.raises(ValueError):
        p.build(source, tmp_path / 'dest', commit, **registration)
    assert not (tmp_path / 'dest').exists()


@pytest.mark.parametrize('fault', ['labels', 'hash', 'manifest', 'candidate-blob', 'provenance'])
def test_verify_arms_rejects_broken_bindings(tmp_path, monkeypatch, fault):
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


@pytest.mark.parametrize('field', ['mode', 'mtime', 'name', 'bytes', 'order', 'candidate-mode', 'candidate-mtime'])
def test_pair_rejects_extra_content_metadata_and_order_changes(tmp_path, monkeypatch, field):
    p = load()
    source, _, _, commit = fixture(p, tmp_path, monkeypatch)
    path = build(p, source, tmp_path / 'arms', commit)
    target = tmp_path / 'changed.tgz'
    candidate = field.startswith('candidate-')
    member_name = 'package/' + p.FILES[0] if candidate else 'package/bin/devlyn.js'
    property_name = field.removeprefix('candidate-')
    with tarfile.open(path.parent / 'Y.tgz') as archive, tarfile.open(target, 'w:gz') as output:
        members = archive.getmembers()
        if field == 'order':
            members.reverse()
        for original in members:
            member = deepcopy(original)
            data = archive.extractfile(original).read() if original.isfile() else None
            if member.name == member_name:
                if property_name in ('mode', 'mtime'):
                    setattr(member, property_name, getattr(member, property_name) + 1)
                elif field == 'name':
                    member.name += '-extra'
                elif field == 'bytes':
                    data = b'changed bytes'
                    member.size = len(data)
            output.addfile(member, io.BytesIO(data) if data is not None else None)
    with pytest.raises(ValueError):
        p.verify_pair({'X': source, 'Y': target}, p.read(path)['Y']['source']['candidate_blobs'])


@pytest.mark.parametrize('name', ['package/../outside', '/absolute', 'package/./alias'])
def test_unsafe_or_aliased_archive_paths_are_rejected(tmp_path, name):
    p = load()
    source = tmp_path / 'bad.tgz'
    with tarfile.open(source, 'w:gz') as archive:
        member = tarfile.TarInfo(name)
        member.size = 1
        archive.addfile(member, io.BytesIO(b'x'))
    with pytest.raises(ValueError):
        p.archive_manifest(source)
