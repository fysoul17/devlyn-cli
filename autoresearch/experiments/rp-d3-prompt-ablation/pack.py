"""Verify and copy the single registered registry tarball; no repack or candidate."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pack_rpd2_rpd3', HERE.parent / 'rp-d2-report-lines/pack.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
read, write, require = legacy.read, legacy.write, legacy.require
identity, archive_manifest, tree_manifest = legacy.identity, legacy.archive_manifest, legacy.tree_manifest
FILE = legacy.FILE
RELEASE_SHA256 = '7b22cce865d99e1400f9c0b0bff41c1b9ae3645b132cbb868ec01cadc973393e'
REPORT_BLOB = 'faff9b9c8303ccc5bcbb52bbd19456f8584ea00b'


def check_blob(raw):
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    require(blob == REPORT_BLOB, 'reporting instruction differs from git blob 7516ebc9:' + FILE)


def registered():
    release = read(legacy.PRIOR / 'registration.json')['release']
    require(release['version'] == '4.2.18' and release['sha256'] == RELEASE_SHA256,
            'registered release identity changed')
    return release


def describe(path):
    release = registered()
    require(identity(path) == {key: release[key] for key in ('sha256', 'integrity')},
            'registry tarball SHA-256/integrity mismatch')
    check_blob(legacy.content(path))
    return dict(version='4.2.18', tarball='B.tgz', **identity(path),
                source=dict(registry='devlyn-cli@4.2.18'),
                manifest_sha256=legacy.manifest_digest(archive_manifest(path)))


def build(source, dest):
    release = describe(source)
    dest.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(source, dest / 'B.tgz')
    write(dest / 'arms.json', {'B': release})
    return dest / 'arms.json'


def verify_arms(path):
    records = read(path)
    require(set(records) == {'B'}, 'exactly one installed release B is required')
    require(records['B'] == describe(path.parent / 'B.tgz'), 'single release binding mismatch')
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('registry', type=Path)
    parser.add_argument('dest', type=Path)
    args = parser.parse_args()
    print(build(args.registry, args.dest))
