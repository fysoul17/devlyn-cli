"""Offline two-file descendant of a verified devlyn-cli@4.2.22 registry tarball."""
import argparse
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
import tarfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pack_rpd2_rpd4', HERE.parent / 'rp-d2-report-lines/pack.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
read, write, require = legacy.read, legacy.write, legacy.require
identity, tree_manifest = legacy.identity, legacy.tree_manifest
digest, manifest_digest, git = legacy.digest, legacy.manifest_digest, legacy.git
FILES = ('config/skills/_shared/task-complete.py', 'config/skills/_shared/task-completion.md')
FILE = FILES[1]
VERSION = '4.2.22'
REGISTRY = 'devlyn-cli@' + VERSION


def archive_manifest(path):
    manifest = legacy.archive_manifest(path)
    # Avoid two tar names aliasing one tree path while retaining the inherited manifest.
    with tarfile.open(path, 'r:gz') as archive:
        require(all(member.name.rstrip('/') == str(Path(member.name)) for member in archive),
                'release archive paths must be canonical')
    return manifest


def content(path, name=FILE):
    with tarfile.open(path, 'r:gz') as archive:
        member = archive.getmember('package/' + name)
        require(member.isfile(), name + ': replacement must be a regular file')
        return archive.extractfile(member).read()


def blob_id(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def check_package(path):
    package = json.loads(content(path, 'package.json'))
    require(package.get('name') == 'devlyn-cli' and package.get('version') == VERSION,
            'registry package must be devlyn-cli@4.2.22')


def repack(source, target, replacements):
    require(set(replacements) == set(FILES), 'exactly the two candidate files are required')
    with tarfile.open(source, 'r:gz') as archive, target.open('xb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT) as output:
                for original in archive:
                    member = deepcopy(original)
                    data = archive.extractfile(original).read() if original.isfile() else None
                    relative = str(Path(member.name).relative_to('package'))
                    if relative in replacements:
                        require(member.isfile(), relative + ': replacement must be a regular file')
                        data = replacements[relative]
                        member.size = len(data)
                        if 'size' in member.pax_headers:
                            member.pax_headers['size'] = str(len(data))
                    output.addfile(member, io.BytesIO(data) if data is not None else None)


def verify_pair(paths, candidate_blobs):
    require(set(candidate_blobs) == set(FILES) and
            all(isinstance(value, str) and re.fullmatch('[a-f0-9]{40}', value)
                for value in candidate_blobs.values()), 'invalid registered candidate blobs')
    manifests = {arm: archive_manifest(path) for arm, path in paths.items()}
    x, y = manifests['X'], manifests['Y']
    require(x.keys() == y.keys() and {name for name in x if x[name] != y[name]} == set(FILES),
            'arm manifests must differ in exactly the two candidate files')
    for name in FILES:
        require(x[name]['type'] == y[name]['type'] == 'file' and x[name]['mode'] == y[name]['mode'],
                name + ': candidate file type/mode changed')
        require(blob_id(content(paths['Y'], name)) == candidate_blobs[name],
                name + ': candidate blob mismatch')
    with tarfile.open(paths['X'], 'r:gz') as control, tarfile.open(paths['Y'], 'r:gz') as candidate:
        left, right = control.getmembers(), candidate.getmembers()
        require(len(left) == len(right), 'archive member count changed')
        for a, b in zip(left, right):
            a_info, b_info = a.get_info(), b.get_info()
            a_info.pop('chksum')
            b_info.pop('chksum')
            a_pax, b_pax = dict(a.pax_headers), dict(b.pax_headers)
            if a.name in {'package/' + name for name in FILES}:
                a_info.pop('size')
                b_info.pop('size')
                a_pax.pop('size', None)
                b_pax.pop('size', None)
            require(a_info == b_info and a_pax == b_pax, 'archive member metadata/order changed')
    return manifests


def build(source, dest, candidate, sha256, integrity):
    require(identity(source) == dict(sha256=sha256, integrity=integrity),
            'registry tarball SHA-256/integrity mismatch')
    archive_manifest(source)
    check_package(source)
    require(isinstance(candidate, str) and re.fullmatch('[a-fA-F0-9]{8,40}', candidate),
            'candidate must be a commit hash')
    commit = git('rev-parse', '--verify', candidate + '^{commit}').decode().strip()
    require(re.fullmatch('[a-f0-9]{40}', commit), 'invalid resolved candidate commit')
    replacements, blobs = {}, {}
    for name in FILES:
        replacements[name] = git('show', commit + ':' + name)
        blobs[name] = git('rev-parse', '--verify', commit + ':' + name).decode().strip()
        require(blob_id(replacements[name]) == blobs[name], name + ': Git blob/content mismatch')
        require(content(source, name) != replacements[name], name + ': candidate must change both files')
    dest.mkdir(parents=True, exist_ok=False)
    paths = {arm: dest / (arm + '.tgz') for arm in ('X', 'Y')}
    shutil.copyfile(source, paths['X'])
    repack(source, paths['Y'], replacements)
    manifests = verify_pair(paths, blobs)
    arms = {arm: dict(version=VERSION, tarball=path.name, **identity(path),
                     source=dict(registry=REGISTRY, **(dict(candidate_commit=commit, candidate_blobs=blobs)
                                                      if arm == 'Y' else {})),
                     manifest_sha256=manifest_digest(manifests[arm])) for arm, path in paths.items()}
    write(dest / 'arms.json', arms)
    return dest / 'arms.json'


def verify_arms(path):
    arms = read(path)
    require(set(arms) == {'X', 'Y'}, 'exactly two release records X and Y are required')
    paths = {}
    for arm, release in arms.items():
        require(release['version'] == VERSION and release['tarball'] == arm + '.tgz',
                'invalid arm release identity')
        paths[arm] = path.parent / release['tarball']
        require(identity(paths[arm]) == {key: release[key] for key in ('sha256', 'integrity')},
                arm + ': release SHA-256/integrity mismatch')
        check_package(paths[arm])
    require(arms['X']['source'] == dict(registry=REGISTRY) and
            set(arms['Y']['source']) == {'registry', 'candidate_commit', 'candidate_blobs'} and
            arms['Y']['source']['registry'] == REGISTRY and
            re.fullmatch('[a-f0-9]{40}', arms['Y']['source']['candidate_commit']), 'invalid arm provenance')
    manifests = verify_pair(paths, arms['Y']['source']['candidate_blobs'])
    for arm in arms:
        require(manifest_digest(manifests[arm]) == arms[arm]['manifest_sha256'],
                arm + ': manifest digest mismatch')
    return arms


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('registry', type=Path)
    parser.add_argument('dest', type=Path)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--sha256', required=True, help='registered registry tarball SHA-256')
    parser.add_argument('--integrity', required=True, help='registry sha512- integrity value')
    args = parser.parse_args()
    print(build(args.registry, args.dest, args.candidate, args.sha256, args.integrity))


if __name__ == '__main__':
    main()
