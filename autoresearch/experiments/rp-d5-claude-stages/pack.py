"""Stage only the registered, unmodified devlyn-cli@4.2.22 registry artifact."""
import argparse
import importlib.util
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pack_rpd4_rpd5', HERE.parent / 'rp-d4-helper-report/pack.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
read, write, require = legacy.read, legacy.write, legacy.require
identity, tree_manifest = legacy.identity, legacy.tree_manifest
archive_manifest, check_package = legacy.archive_manifest, legacy.check_package
manifest_digest, FILES, FILE = legacy.manifest_digest, legacy.FILES, legacy.FILE
VERSION, REGISTRY = legacy.VERSION, legacy.REGISTRY


def build(source, dest, sha256, integrity):
    require(identity(source) == dict(sha256=sha256, integrity=integrity),
            'registry tarball SHA-256/integrity mismatch')
    manifest = archive_manifest(source)
    check_package(source)
    dest.mkdir(parents=True, exist_ok=False)
    target = dest / 'X.tgz'
    shutil.copyfile(source, target)
    write(dest / 'arms.json', {'X': dict(version=VERSION, tarball='X.tgz', **identity(target),
        source=dict(registry=REGISTRY), manifest_sha256=manifest_digest(manifest))})
    return dest / 'arms.json'


def verify_arms(path):
    path = Path(path)
    arms = read(path)
    require(set(arms) == {'X'}, 'exactly the registry release X is required')
    release = arms['X']
    require(release['version'] == VERSION and release['tarball'] == 'X.tgz' and
            release['source'] == dict(registry=REGISTRY), 'invalid registry release identity')
    target = path.parent / release['tarball']
    require(identity(target) == {key: release[key] for key in ('sha256', 'integrity')},
            'registry tarball SHA-256/integrity mismatch')
    check_package(target)
    require(manifest_digest(archive_manifest(target)) == release['manifest_sha256'],
            'registry manifest digest mismatch')
    return arms


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('registry', type=Path)
    parser.add_argument('dest', type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--integrity', required=True)
    args = parser.parse_args()
    print(build(args.registry, args.dest, args.sha256, args.integrity))


if __name__ == '__main__':
    main()
