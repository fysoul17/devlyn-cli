"""Offline one-path descendant of the frozen registry archive."""
import argparse
from fnmatch import fnmatchcase
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pack_rpd6_rpd8', HERE.parent / 'rp-d6-claude-delivery/pack.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
legacy = base.legacy
FILES = ('config/skills/_shared/task-completion.md',)
FILE = FILES[0]
DESIGN_COMMIT = '7c5dcdf2fca05f8d17d9e7fb3bc340461f8713c1'
CANDIDATE_COMMIT = 'e22dbaf3b7d4a458768c86e7ec8ff85e0f8bdb8c'
legacy.FILES, legacy.FILE = FILES, FILE
read, write, require = legacy.read, legacy.write, legacy.require
identity, tree_manifest = legacy.identity, legacy.tree_manifest
digest, manifest_digest = legacy.digest, legacy.manifest_digest
archive_manifest, check_package = legacy.archive_manifest, legacy.check_package
blob_id, repack = legacy.blob_id, legacy.repack
VERSION, REGISTRY = legacy.VERSION, legacy.REGISTRY
verify_pair = legacy.verify_pair


def build(source, dest, candidate, sha256, integrity):
    require(isinstance(candidate, str) and re.fullmatch('[a-fA-F0-9]{8,40}', candidate),
            'candidate must be a commit hash')
    commit = legacy.git('rev-parse', '--verify', candidate + '^{commit}').decode().strip()
    require(commit == CANDIDATE_COMMIT, 'candidate differs from frozen rp-d8 commit')
    frozen = json.loads(legacy.git('show', DESIGN_COMMIT + ':package.json'))
    current = json.loads(legacy.git('show', commit + ':package.json'))
    require(current['files'] == frozen['files'], 'candidate package files declaration changed')
    included = [pattern for pattern in frozen['files'] if not pattern.startswith('!')]
    excluded = [pattern[1:] for pattern in frozen['files'] if pattern.startswith('!')]

    def matches(name, patterns):
        return any(fnmatchcase(name, pattern) or name.startswith(pattern + '/') for pattern in patterns)

    changed = legacy.git('diff-tree', '--no-commit-id', '-r', '--name-only', '-z',
                         '--no-renames', DESIGN_COMMIT, commit, '--').decode().split('\0')
    # npm also includes package metadata and top-level readme/license files.
    shipped = {name for name in changed if name and (
        name == 'package.json' or '/' not in name and re.match(r'(?i)^(readme|licen[sc]e)(\.|$)', name)
        or matches(name, included) and not matches(name, excluded))}
    require(shipped == set(FILES), 'candidate must change exactly task-completion.md among shipped paths')
    return legacy.build(source, dest, commit, sha256, integrity)


def verify_arms(path):
    arms = legacy.verify_arms(Path(path))
    require(arms['Y']['source']['candidate_commit'] == CANDIDATE_COMMIT,
            'candidate differs from frozen rp-d8 commit')
    return arms


def content(path, name=FILE):
    return legacy.content(path, name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('registry', type=Path)
    parser.add_argument('dest', type=Path)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--integrity', required=True)
    args = parser.parse_args()
    print(build(args.registry, args.dest, args.candidate, args.sha256, args.integrity))


if __name__ == '__main__':
    main()
