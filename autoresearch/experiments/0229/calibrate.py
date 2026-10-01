"""0229 corpus calibration (model-free; 0227's script with the 0229 roots and repositories): per task, on fresh copies of the pinned tree, run the public checks and the
hidden oracle on base, reference and twin, offline, with the screen's own toolchains. Registration 0229 "Corpus"
(as 0228, 0227 and 0226): each reference passes the public checks (version checks included) and every oracle row; each twin passes
the public checks, fails exactly its designated witness and changes exactly the reference's files.

usage: calibrate.py <task> [<task> ...]    writes <workspaces>/calibration/<task>.json
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path('/Users/Shared/devlyn-vr-0228-dev/screen-0229/private/workspaces')
TOOLS = Path('/Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains')
SANDBOX = ['sandbox-exec', '-f', str(BASE / 'offline.sb')]
REPOS = {'P': 'dateutil', 'J': 'markdown-it'}
ENV = {
    'dateutil': {'PATH': f'{TOOLS}/dateutil/venv/bin:/usr/bin:/bin', 'PYTHONPATH': 'src', 'PYTHONDONTWRITEBYTECODE': '1',
                 'PYTEST_ADDOPTS': '-p no:cacheprovider'},
    'markdown-it': {'PATH': f'{TOOLS}/markdown-it/node-bin:/usr/bin:/bin'},
}
# Provisioned files symlinked into each tree from its toolchain (the screen driver's TOOLCHAINS links).
LINKS = {'dateutil': {'src/dateutil/zoneinfo/dateutil-zoneinfo.tar.gz': 'zoneinfo/dateutil-zoneinfo.tar.gz'},
         'markdown-it': {'node_modules': 'node_modules'}}


def run(argv, cwd, env, timeout=900):
    full = {'HOME': os.environ['HOME'], 'LANG': 'en_US.UTF-8', 'TMPDIR': os.environ.get('TMPDIR', '/tmp'), **env}
    proc = subprocess.run(SANDBOX + argv, cwd=cwd, env=full, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def files(patch):
    return sorted(set(re.findall(r'^diff --git a/(\S+) b/', patch.read_text(), re.M)))


GIT = ['git', '-c', 'user.name=dev', '-c', 'user.email=dev@example.invalid', '-c', 'core.logAllRefUpdates=false']


def tree(task, variant, scratch):
    """As the screen materializes a round: a Git checkout whose `base` commit is the pinned tree and whose HEAD commits
    the variant's patch, with the provisioned links excluded from Git (public checks may compare against HEAD)."""
    repo = REPOS[task[0]]
    work = Path(scratch) / variant
    work.mkdir()
    subprocess.run(GIT + ['init', '-q', '-b', 'main'], cwd=work, check=True)
    subprocess.run(f'git -C {BASE.parent}/repos/{repo} archive HEAD | tar -x -C {work}', shell=True, check=True)
    (work / '.git/info/exclude').write_text(''.join(f'/{name}\n' for name in LINKS[repo]))
    subprocess.run(GIT + ['add', '-A'], cwd=work, check=True)
    subprocess.run(GIT + ['commit', '-qm', 'base'], cwd=work, check=True)
    if variant != 'base':
        subprocess.run(GIT + ['apply', '--index', str(BASE / 'impl' / task / f'{variant}.patch')], cwd=work, check=True)
        subprocess.run(GIT + ['commit', '-qm', 'change'], cwd=work, check=True)
    for name, target in LINKS[repo].items():
        (work / name).symlink_to(TOOLS / repo / target)
    return work, repo


def snapshot(work):
    # Hashes every file present before the public checks, so a check that rewrites sources (a fix-mode linter or
    # formatter) is recorded instead of passing silently; build outputs created by the checks are not compared.
    import hashlib
    return {str(path.relative_to(work)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in work.rglob('*') if path.is_file() and not path.is_symlink()
            and not {'node_modules', '.git'} & set(path.relative_to(work).parts)}


def check(task):
    expected = json.loads((BASE / 'author/corpus' / task / 'spec.expected.json').read_text())
    oracle = BASE / 'impl' / task / 'oracle/run.sh'
    out = {'task': task, 'files': {v: files(BASE / 'impl' / task / f'{v}.patch') for v in ('reference', 'twin')}}
    with tempfile.TemporaryDirectory(dir=BASE) as scratch:
        for variant in ('base', 'reference', 'twin'):
            work, repo = tree(task, variant, scratch)
            env = {**ENV[repo], 'HYPOTHESIS_STORAGE_DIRECTORY': str(Path(scratch) / f'hypothesis-{variant}')}
            row = {}
            if variant != 'base':
                row['public'] = []
                before = snapshot(work)
                for command in expected['verification_commands']:
                    code, stdout, stderr = run(['/bin/sh', '-c', command['cmd']], work, env,
                                               command.get('timeout_sec', 900) + 60)
                    text = stdout + stderr
                    ok = code == command.get('exit_code', 0) and all(s in text for s in command.get('stdout_contains', [])) \
                        and not any(s in text for s in command.get('stdout_not_contains', []))
                    row['public'].append({'cmd': command['cmd'], 'exit': code, 'expected': command.get('exit_code', 0),
                                          'ok': ok, 'stdout_tail': stdout[-2000:], 'stderr_tail': stderr[-600:]})
            if variant != 'base':
                after = snapshot(work)
                row['rewritten_by_public'] = sorted(name for name, digest in before.items() if after.get(name) != digest)
            code, stdout, stderr = run(['/bin/bash', str(oracle), str(work)], work, env)
            try:
                row['oracle'] = json.loads(stdout.strip().splitlines()[-1])['rows']
            except (IndexError, ValueError, KeyError):
                row['oracle'] = None
                row['oracle_error'] = (stdout + stderr)[-1500:]
            row['oracle_exit'] = code
            out[variant] = row
    ref, twin = out['reference'], out['twin']
    failed = lambda r: sorted(k for k, v in (r['oracle'] or {}).items() if v is not True)
    out['verdict'] = {
        'same_files': out['files']['reference'] == out['files']['twin'],
        'reference_public_pass': all(c['ok'] for c in ref['public']),
        'twin_public_pass': all(c['ok'] for c in twin['public']),
        'public_rewrote_nothing': not ref['rewritten_by_public'] and not twin['rewritten_by_public'],
        'reference_oracle_all_true': ref['oracle'] is not None and not failed(ref),
        'twin_oracle_failed_rows': failed(twin) if twin['oracle'] is not None else None,
        'base_oracle_failed_rows': failed(out['base']) if out['base']['oracle'] is not None else None,
    }
    return out


if __name__ == '__main__':
    (BASE / 'calibration').mkdir(exist_ok=True)
    for task in sys.argv[1:]:
        result = check(task)
        (BASE / 'calibration' / f'{task}.json').write_text(json.dumps(result, indent=2) + '\n')
        print(task, json.dumps(result['verdict']), flush=True)
