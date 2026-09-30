"""0227 diagnostic replay (not a screen): rerun one sealed round's VERIFY from its pristine inputs in a separate root.
usage: replay.py <token> <n>   -> /Users/Shared/devlyn-vr-0227-diag/<token>/rep-<i>/  (work, home), prints seat verdicts."""
import json, os, shutil, subprocess, sys, tarfile
from pathlib import Path
SRC = Path('/Users/Shared/devlyn-vr-0227')
DIAG = Path('/Users/Shared/devlyn-vr-0227-diag')
tok, n = sys.argv[1], int(sys.argv[2])
first = int(sys.argv[3]) if len(sys.argv) > 3 else 1
manifest = json.load(open(SRC / 'manifest.json'))
row = next(r for r in manifest['rounds'] if r['token'] == tok)
for i in range(first, first + n):
    base = DIAG / tok / f'rep-{i}'
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    with tarfile.open(SRC / 'private/pristine' / f'{tok}.tar') as t:
        t.extractall(base, filter='fully_trusted')
    with tarfile.open(SRC / 'private/pristine' / f'{tok}.home.tar') as t:
        t.extractall(base / 'homes', filter='fully_trusted')
    work = base / 'work'
    if row['repo'] == 'node-lru-cache':
        (work / 'node_modules').symlink_to(SRC / 'toolchains/node-lru-cache/node_modules', target_is_directory=True)
    env = dict(row['env'])
    env['CODEX_HOME'] = str(base / 'homes' / tok / '.codex')
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = str(work / 'src')
    auth = base / 'homes' / tok / '.codex/auth.json'
    shutil.copyfile(Path.home() / '.codex/auth.json', auth)
    auth.chmod(0o600)
    try:
        proc = subprocess.run([sys.executable, str(SRC / 'product/config/skills/_shared/verify-judges.py'),
                               '--devlyn-dir', str(work / '.devlyn')], cwd=work, env=env, capture_output=True, text=True,
                              timeout=1800)
    finally:
        auth.unlink(missing_ok=True)
    out = {}
    for eng in ('codex', 'claude'):
        f = work / '.devlyn' / f'{eng}-judge.stdout'
        lines = f.read_text().strip().splitlines() if f.is_file() else []
        out[eng] = {'verdict': lines[-1] if lines else None, 'findings': [json.loads(l) for l in lines[:-1] if l.startswith('{')]}
    summary = json.loads(proc.stdout) if proc.stdout.strip().startswith('{') else {'raw': proc.stdout[-300:], 'err': proc.stderr[-500:]}
    rec = {'token': tok, 'rep': i, 'rc': proc.returncode, 'merged': summary.get('verdict'), 'source_verdicts': summary.get('source_verdicts'),
           'seats': {e: {'verdict': v['verdict'], 'findings': [(f.get('severity'), f.get('verdict_binding'), f.get('rule_id'), f.get('message', '')[:160]) for f in v['findings']]} for e, v in out.items()}}
    with open(DIAG / 'replays.jsonl', 'a') as h:
        h.write(json.dumps(rec) + '\n')
    print(json.dumps({'rep': i, 'rc': proc.returncode, 'merged': rec['merged'], 'codex': rec['seats']['codex']['verdict'],
                      'claude': rec['seats']['claude']['verdict'],
                      'codex_high': [f[2] for f in rec['seats']['codex']['findings'] if f[0] in ('HIGH', 'CRITICAL') or f[1] is True]}), flush=True)
