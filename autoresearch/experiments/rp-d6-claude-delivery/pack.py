"""Offline three-path descendant of verified devlyn-cli@4.2.22 registry bytes."""
import argparse
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'pack_rpd4_rpd6', HERE.parent / 'rp-d4-helper-report/pack.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)

# This module instance is private: rp-d4 keeps its original two-file contract.
# The user's explicit three shipped paths narrow DESIGN's optional mirror and
# generated-template list; neither of those additional paths is changed here.
FILES = ('CLAUDE.md', 'AGENTS.md', 'config/skills/_shared/runtime-principles.md')
FILE = FILES[0]
legacy.FILES, legacy.FILE = FILES, FILE
read, write, require = legacy.read, legacy.write, legacy.require
identity, tree_manifest = legacy.identity, legacy.tree_manifest
digest, manifest_digest = legacy.digest, legacy.manifest_digest
archive_manifest, check_package = legacy.archive_manifest, legacy.check_package
blob_id, repack = legacy.blob_id, legacy.repack
VERSION, REGISTRY = legacy.VERSION, legacy.REGISTRY
build, verify_pair, verify_arms = legacy.build, legacy.verify_pair, legacy.verify_arms


def content(path, name=FILE):
    # rp-d4's default argument was bound before the private FILE override.
    return legacy.content(path, name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('registry', type=Path)
    parser.add_argument('dest', type=Path)
    parser.add_argument('--candidate', required=True, help='local candidate commit hash')
    parser.add_argument('--sha256', required=True, help='registered registry tarball SHA-256')
    parser.add_argument('--integrity', required=True, help='registered registry sha512- integrity')
    args = parser.parse_args()
    print(build(args.registry, args.dest, args.candidate, args.sha256, args.integrity))


if __name__ == '__main__':
    main()
