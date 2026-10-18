"""Offline materialization of the single verified registry release X."""
import argparse
import importlib.util
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pack_rpd6_rpd7', HERE.parent / 'rp-d6-claude-delivery/pack.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
read, write, require = legacy.read, legacy.write, legacy.require
identity, tree_manifest = legacy.identity, legacy.tree_manifest
archive_manifest, manifest_digest = legacy.archive_manifest, legacy.manifest_digest
check_package, VERSION, REGISTRY = legacy.check_package, legacy.VERSION, legacy.REGISTRY


def build(source, dest, sha256, integrity):
    require(identity(source) == dict(sha256=sha256, integrity=integrity),
            'registry tarball SHA-256/integrity mismatch')
    manifest = archive_manifest(source)
    check_package(source)
    dest.mkdir(parents=True, exist_ok=False)
    target = dest / 'X.tgz'
    shutil.copyfile(source, target)
    require(identity(target) == dict(sha256=sha256, integrity=integrity), 'registry archive changed while copying')
    write(dest / 'arms.json', dict(X=dict(version=VERSION, tarball=target.name,
        **identity(target), source=dict(registry=REGISTRY), manifest_sha256=manifest_digest(manifest))))
    verify_arms(dest / 'arms.json')
    return dest / 'arms.json'


def verify_arms(path):
    path = Path(path)
    arms = read(path)
    require(set(arms) == {'X'}, 'exactly one release X is required')
    release = arms['X']
    require(release['version'] == VERSION and release['tarball'] == 'X.tgz' and
            release['source'] == dict(registry=REGISTRY), 'invalid X release identity/provenance')
    tarball = path.parent / 'X.tgz'
    require(identity(tarball) == {key: release[key] for key in ('sha256', 'integrity')},
            'X: release SHA-256/integrity mismatch')
    check_package(tarball)
    require(manifest_digest(archive_manifest(tarball)) == release['manifest_sha256'], 'X: manifest digest mismatch')
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
