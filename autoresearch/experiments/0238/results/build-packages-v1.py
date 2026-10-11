"""Prospective 0238 package builder. Never invokes a model or edits the delivery worktree.

Builds history-aware packages in a caller-owned absent destination. The baseline
is explicit: 4.2.3 plus the two admitted 0237 delivery fixes. Caller-discovery is
excluded unless a later preregistration changes this builder before any run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
BASE = '975a01e6200750b75ca4b77b4fcbb95521ed1214'
TRIGGER = ('When a change makes ordering or identity depend on representation, or changes '
           'shared-state ownership or recovery, follow `_shared/pair.md` in the skills '
           'installation used for delivery before declaring completion.')
ROOTS = ('AGENTS.md', 'CLAUDE.md', 'config/skills/_shared/runtime-principles.md',
         '.agents/skills/_shared/runtime-principles.md')
FIXES = ('task-complete.py', 'task-completion.md')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(dest, toolchain):
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, 'PATH': str(toolchain) + os.pathsep + os.environ['PATH'],
           'npm_config_cache': str(dest / 'npm-cache'),
           'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_AUTHOR_NAME': 'Devlyn experiment', 'GIT_COMMITTER_NAME': 'Devlyn experiment',
           'GIT_AUTHOR_EMAIL': 'experiment@localhost', 'GIT_COMMITTER_EMAIL': 'experiment@localhost'}
    def command(argv, cwd=None):
        return subprocess.check_output(argv, cwd=cwd, env=env, text=True).strip()
    versions = {name: command([name, '--version']) for name in ('node', 'npm')}
    if not versions['node'].startswith('v20.') or not versions['npm'].startswith('10.'):
        raise ValueError('registered packing requires Node 20 / npm 10')
    clone = dest / 'repo'
    command(['git', 'clone', '-q', '--shared', '--no-checkout', str(REPO), str(clone)])
    def git(*args):
        return command(['git', '-C', str(clone), *args])
    git('checkout', '-q', '--detach', BASE)
    for prefix in ('config/skills/_shared', '.agents/skills/_shared'):
        for name in FIXES:
            shutil.copyfile(REPO / prefix / name, clone / prefix / name)
    git('add', '--', *[prefix + '/' + name for prefix in
        ('config/skills/_shared', '.agents/skills/_shared') for name in FIXES])
    git('commit', '-qm', '0238 experimental baseline: admitted delivery fixes')
    baseline = git('rev-parse', 'HEAD')
    command(['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund'], cwd=clone)
    packages = {}
    for arm in ('B', 'S', 'H', 'P'):
        git('checkout', '-q', '--detach', baseline)
        # Prior generated fingerprints are not committed to the experimental tree.
        git('restore', '--', 'bin/instruction-templates.json')
        if arm != 'B':
            for name in ROOTS:
                path = clone / name
                text = path.read_text()
                anchor = 'Zero CRITICAL, zero HIGH security/design findings on the shippable path.'
                if text.count(anchor) != 1:
                    raise ValueError('Worldclass anchor is not unique: ' + name)
                path.write_text(text.replace(anchor, anchor + ' ' + TRIGGER))
            guide = (HERE / 'guides' / (arm + '.md')).read_text()
            if 'PLACEHOLDER' in guide:
                raise ValueError('candidate guide is not complete')
            for prefix in ('config/skills/_shared', '.agents/skills/_shared'):
                (clone / prefix / 'pair.md').write_text(guide)
                if arm in ('H', 'P'):
                    shutil.copyfile(HERE / 'peer.py', clone / prefix / 'peer.py')
            git('add', '--', *ROOTS, 'config/skills/_shared', '.agents/skills/_shared')
            git('commit', '-qm', '0238 experimental arm ' + arm)
        commit = git('rev-parse', 'HEAD')
        command(['node', 'scripts/update-instruction-templates.js'], cwd=clone)
        packed = command(['npm', 'pack', '--silent', '--ignore-scripts',
                          '--pack-destination', str(dest)], cwd=clone).splitlines()[-1]
        archive = dest / (arm + '.tgz')
        (dest / packed).rename(archive)
        with tarfile.open(archive) as tar:
            members = {entry.name: hashlib.sha256(tar.extractfile(entry).read()).hexdigest()
                       for entry in tar if entry.isfile()}
        packages[arm] = dict(commit=commit, sha256=sha(archive), files=members)
    result = dict(base=BASE, baseline_commit=baseline, versions=versions,
                  builder_sha256=sha(Path(__file__)), trigger=TRIGGER, packages=packages)
    (dest / 'packages.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--toolchain', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.destination, args.toolchain.resolve())
    print(json.dumps({arm: record['sha256'] for arm, record in result['packages'].items()}))
