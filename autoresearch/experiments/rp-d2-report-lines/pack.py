"""Offline registry descendant: pack.py <registry.tgz> <new-directory> --candidate <commit>."""
import argparse
import base64
from copy import deepcopy
import difflib
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / 'rp-d1-delivery-cost'
FILE = 'config/skills/_shared/task-completion.md'
MEMBER = 'package/' + FILE
OLD = (b'Report verification, delivery and checkout reconciliation separately. A delivery\n'
       b'error does not rewrite an accepted product result; unperformed verification\n'
       b'must never be reported as accepted.\n')
NEW = (b'Report verification, delivery, cleanup and checkout reconciliation separately. A\n'
       b'delivery error never changes an accepted product result; never report unperformed\n'
       b'verification as accepted.\n')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def identity(path):
    raw = Path(path).read_bytes()
    return dict(sha256=digest(raw), integrity='sha512-' + base64.b64encode(hashlib.sha512(raw).digest()).decode())


def manifest_digest(manifest):
    return digest(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode())


def archive_manifest(path):
    result, names = {}, set()
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive:
            name = Path(member.name)
            require(not name.is_absolute() and '..' not in name.parts and name.parts[0] == 'package',
                    'unsafe release archive path')
            require(member.name not in names, 'duplicate release archive member')
            names.add(member.name)
            require(member.isfile() or member.isdir() or member.issym(), 'unsupported release archive entry')
            if member.isdir():
                continue
            relative = str(name.relative_to('package'))
            require(relative != '.', 'release member must be inside package')
            result[relative] = (dict(type='link', target=member.linkname) if member.issym() else
                                dict(type='file', mode=member.mode, sha256=digest(archive.extractfile(member).read())))
    for name in result:
        require(not any(str(parent) in result for parent in Path(name).parents),
                'release entry has a non-directory ancestor')
    return result


def tree_manifest(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            value = dict(type='link', target=str(path.readlink()))
        elif path.is_file():
            value = dict(type='file', mode=path.stat().st_mode & 0o7777, sha256=digest(path.read_bytes()))
        else:
            require(path.is_dir(), 'unsupported extracted release entry')
            continue
        result[str(path.relative_to(root))] = value
    return result


def content(path):
    with tarfile.open(path, 'r:gz') as archive:
        member = archive.getmember(MEMBER)
        require(member.isfile(), 'reporting instruction must be a regular file')
        return archive.extractfile(member).read()


def paragraph_diff(before, after):
    require(before.count(OLD) == 1, 'control paragraph must occur exactly once')
    expected = before.replace(OLD, NEW, 1)
    diff = lambda raw: ''.join(difflib.unified_diff(before.decode().splitlines(True),
                              raw.decode().splitlines(True), fromfile='X/' + FILE, tofile='Y/' + FILE))
    require(after == expected and diff(after) == diff(expected), 'candidate differs from the registered three-line change')
    return diff(after)


def verify_pair(paths):
    manifests = {arm: archive_manifest(path) for arm, path in paths.items()}
    x, y = manifests['X'], manifests['Y']
    require(x.keys() == y.keys() and [name for name in x if x[name] != y[name]] == [FILE],
            'arm manifests must differ in exactly the reporting instruction')
    paragraph_diff(content(paths['X']), content(paths['Y']))
    with tarfile.open(paths['X'], 'r:gz') as control, tarfile.open(paths['Y'], 'r:gz') as candidate:
        left, right = control.getmembers(), candidate.getmembers()
        require(len(left) == len(right), 'archive member count changed')
        for a, b in zip(left, right):
            a_info, b_info = a.get_info(), b.get_info()
            # The tar header checksum is derived from the size, not member metadata.
            a_info.pop('chksum')
            b_info.pop('chksum')
            a_pax, b_pax = dict(a.pax_headers), dict(b.pax_headers)
            if a.name == MEMBER:
                a_info.pop('size')
                b_info.pop('size')
                a_pax.pop('size', None)
                b_pax.pop('size', None)
            require(a_info == b_info and a_pax == b_pax, 'archive member metadata/order changed')
    return manifests


def repack(source, target, replacement):
    with tarfile.open(source, 'r:gz') as archive, target.open('xb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT) as output:
                for original in archive:
                    member = deepcopy(original)
                    data = archive.extractfile(original).read() if original.isfile() else None
                    if member.name == MEMBER:
                        data = replacement
                        member.size = len(data)
                        if 'size' in member.pax_headers:
                            member.pax_headers['size'] = str(len(data))
                    output.addfile(member, io.BytesIO(data) if data is not None else None)


def git(*args):
    # Local objects only, including in a partial clone; never lazy-fetch a missing blob.
    import os
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_NO_REPLACE_OBJECTS='1', GIT_CONFIG_NOSYSTEM='1',
               GIT_CONFIG_GLOBAL='/dev/null', GIT_OPTIONAL_LOCKS='0')
    return subprocess.check_output(['git', '-C', str(HERE.parents[2]), *args], env=env)


def build(source, dest, candidate):
    release = read(PRIOR / 'registration.json')['release']
    require(identity(source) == {key: release[key] for key in ('sha256', 'integrity')},
            'registry tarball SHA-256/integrity mismatch')
    require(re.fullmatch('[a-fA-F0-9]{8,40}', candidate), 'candidate must be a commit hash')
    commit = git('rev-parse', '--verify', candidate + '^{commit}').decode().strip()
    before, after = git('show', '7516ebc9:' + FILE), git('show', commit + ':' + FILE)
    require(content(source) == before, 'registry reporting instruction differs from 7516ebc9')
    paragraph_diff(before, after)
    archive_manifest(source)
    dest.mkdir(parents=True, exist_ok=False)
    paths = {arm: dest / (arm + '.tgz') for arm in ('X', 'Y')}
    shutil.copyfile(source, paths['X'])
    repack(source, paths['Y'], after)
    manifests = verify_pair(paths)
    arms = {arm: dict(version=release['version'], tarball=path.name, **identity(path),
                     source=dict(registry='devlyn-cli@' + release['version'],
                                 **({'candidate_commit': commit} if arm == 'Y' else {})),
                     manifest_sha256=manifest_digest(manifests[arm])) for arm, path in paths.items()}
    write(dest / 'arms.json', arms)
    return dest / 'arms.json'


def verify_arms(path):
    arms = read(path)
    require(set(arms) == {'X', 'Y'}, 'exactly two release records X and Y are required')
    paths = {}
    for arm, release in arms.items():
        require(release['version'] == '4.2.18' and release['tarball'] == arm + '.tgz', 'invalid arm release identity')
        paths[arm] = path.parent / release['tarball']
        require(identity(paths[arm]) == {key: release[key] for key in ('sha256', 'integrity')},
                arm + ': release SHA-256/integrity mismatch')
    registered = read(PRIOR / 'registration.json')['release']
    require(all(arms['X'][key] == registered[key] for key in ('version', 'sha256', 'integrity')),
            'X differs from the registered release')
    require(arms['X']['source'] == dict(registry='devlyn-cli@4.2.18') and
            set(arms['Y']['source']) == {'registry', 'candidate_commit'} and
            arms['Y']['source']['registry'] == arms['X']['source']['registry'] and
            re.fullmatch('[a-f0-9]{40}', arms['Y']['source']['candidate_commit']), 'invalid arm provenance')
    manifests = verify_pair(paths)
    for arm in arms:
        require(manifest_digest(manifests[arm]) == arms[arm]['manifest_sha256'], arm + ': manifest digest mismatch')
    return arms


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('registry', type=Path)
    parser.add_argument('dest', type=Path)
    parser.add_argument('--candidate', required=True)
    args = parser.parse_args()
    print(build(args.registry, args.dest, args.candidate))


if __name__ == '__main__':
    main()
