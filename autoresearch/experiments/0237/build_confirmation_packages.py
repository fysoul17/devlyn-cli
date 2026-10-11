"""Build fresh B/C packages sharing the admitted delivery fixes; no model calls."""
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
CLAUSE = ('Before editing behavior, follow its callers and consumers far enough to identify '
          'the contracts the change must preserve; use those contracts to choose the smallest '
          'fix and its checks. ')
ROOTS = ('AGENTS.md', 'CLAUDE.md', 'config/skills/_shared/runtime-principles.md',
         '.agents/skills/_shared/runtime-principles.md')


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
    fixes = [prefix + '/' + name for prefix in ('config/skills/_shared', '.agents/skills/_shared')
             for name in ('task-complete.py', 'task-completion.md')]
    for name in fixes:
        shutil.copyfile(REPO / name, clone / name)
    git('add', '--', *fixes)
    git('commit', '-qm', '0237 confirmation baseline: admitted delivery fixes')
    baseline = git('rev-parse', 'HEAD')
    command(['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund'], cwd=clone)
    packages = {}
    for arm in ('B', 'C'):
        if arm == 'C':
            git('restore', '--', 'bin/instruction-templates.json')
            for name in ROOTS:
                path = clone / name
                original = path.read_text()
                anchor = 'State the falsifiable prediction BEFORE the experiment;'
                if original.count(anchor) != 1 or CLAUSE in original:
                    raise ValueError('unexpected principle 3 baseline: ' + name)
                path.write_text(original.replace(anchor, CLAUSE + anchor))
                if path.read_bytes() != (REPO / name).read_bytes():
                    raise ValueError('confirmation clause differs from provisional candidate: ' + name)
            git('add', '--', *ROOTS)
            git('commit', '-qm', '0237 confirmation candidate: discover caller contracts')
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
                  builder_sha256=sha(Path(__file__)), clause=CLAUSE.strip(), packages=packages)
    (dest / 'packages.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--toolchain', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.destination, args.toolchain.resolve())
    print(json.dumps({arm: row['sha256'] for arm, row in result['packages'].items()}))
