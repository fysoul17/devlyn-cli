"""Run one registered 0218 screen cell end to end; exit 0 = continue, 2 = stop the screen, 3 = not dispatched."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
ACCOUNT = ('9f2f3a391923', 'ea65f3b4f086')
MIN_TOKEN_SECONDS = 3600


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def snapshot_auth(auth):
    """Fresh current-login snapshot before each cell, so no copied token needs refreshing mid-cell."""
    claude = subprocess.run(['security', 'find-generic-password', '-s', 'Claude Code-credentials', '-w'],
                            capture_output=True, text=True, check=True).stdout
    oauth = json.loads(claude)['claudeAiOauth']
    remaining = oauth['expiresAt'] / 1000 - time.time()
    if remaining < MIN_TOKEN_SECONDS:
        return None, f'Fable login token expires in {int(remaining)}s; refresh the host login first'
    old = os.umask(0o077)
    try:
        (auth / 'claude.json').write_text(claude)
        (auth / 'codex.json').write_bytes((Path.home() / '.codex/auth.json').read_bytes())
    finally:
        os.umask(old)
    request = urllib.request.Request('https://api.anthropic.com/api/oauth/profile', headers={
        'Authorization': 'Bearer ' + oauth['accessToken'], 'anthropic-beta': 'oauth-2025-04-20'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                profile = json.load(response)
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 2:
                return None, f'account check failed: {exc}'
            time.sleep(20)
    identity = fingerprint(profile['account']['uuid']), fingerprint(profile['organization']['uuid'])
    if identity != ACCOUNT:
        return None, 'account/organization mismatch'
    return dict(account=identity[0], organization=identity[1], token_seconds_left=int(remaining),
                codex_auth_sha256_prefix=digest(auth / 'codex.json')[:12]), None


def run(index, runtime_path):
    runtime = json.loads(runtime_path.read_text())
    root = Path(runtime['output'])
    verdict_path = root.parent / f'verdict-{index + 1:02d}.json'
    identity, blocked = snapshot_auth(Path(runtime['auth']))
    if blocked:
        verdict_path.write_text(json.dumps(dict(index=index, status='NOT_DISPATCHED', reason=blocked), indent=2))
        print(blocked)
        return 3
    cell = Path(subprocess.check_output([sys.executable, '-B', str(HERE / 'prepare.py'), str(index),
                                         str(runtime_path)], text=True).strip())
    (cell / 'seal.json').write_text(json.dumps(dict(
        sealed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), account=identity,
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=HERE, text=True).strip(),
        cell={name: digest(cell / name) for name in ('plan.json', 'prompt.txt', 'baseline.json', 'pilot.json')},
        control={str(p.relative_to(runtime['control'])): digest(p)
                 for p in Path(runtime['control']).rglob('*') if p.is_file()}), indent=2))
    record = dict(index=index, cell=cell.name)
    owner = subprocess.run([sys.executable, '-B', str(HERE.parent / '0210/native_cell.py'),
                            str(cell / 'plan.json'), str(cell / 'run')], capture_output=True, text=True)
    result = json.loads((cell / 'run/result.json').read_text())
    if result.get('model_dispatched') is False:
        attempts = len(list(root.glob(cell.name + '.setup-failed-*'))) + 1
        cell.rename(root / f'{cell.name}.setup-failed-{attempts}')
        record.update(status='NOT_DISPATCHED', failure=result['failure'][-300:], setup_attempt=attempts)
        verdict_path.write_text(json.dumps(record, indent=2))
        print(json.dumps(record))
        return 3
    last = result['terminal']['combined'] if result['terminal'] else (result['snapshots'] or [{}])[-1].get('combined')
    record.update(owner_seconds=result['seconds'], owner_pool=last, classes=result['classes'],
                  failure=result['failure'], terminal_known=result['terminal'] is not None)
    if owner.returncode:
        record['status'] = 'BUDGET_EXCEEDED' if 'BUDGET_EXCEEDED' in result['classes'] else 'INFRA_INVALID'
        verdict_path.write_text(json.dumps(record, indent=2))
        print(json.dumps(record))
        return 2
    for step, script, env in (('checks', HERE / 'check_cell.py', None),
                              ('assessment', HERE.parent / '0211/assess.py',
                               dict(os.environ, PATH=f"{runtime['scratch']}/bin:" + os.environ['PATH']))):
        done = subprocess.run([sys.executable, '-B', str(script), str(cell), str(runtime_path)],
                              capture_output=True, text=True, env=env)
        (cell / f'{step}.log').write_text(done.stdout + done.stderr)
        if done.returncode:
            record.update(status='INFRA_INVALID', failure=f'{step} failed; see {step}.log')
            verdict_path.write_text(json.dumps(record, indent=2))
            print(json.dumps(record))
            return 2
    seal = json.loads((cell / 'local-seal.json').read_text())
    answer = (cell / 'assessment/answer.txt').read_text()
    assessed = json.loads(re.search(r'\{.*\}', answer, re.S).group(0))
    severe = [f for f in assessed.get('findings', []) if str(f.get('severity', '')).lower() in ('high', 'critical')]
    record.update(product_check_pass=seal['product_check_pass'], format_pass=seal['format_pass'],
                  check_seconds=seal['seconds'], assessment_complete=assessed.get('complete') is True,
                  severe_findings=len(severe),
                  assessment_usage=json.loads((cell / 'assessment/usage.json').read_text()))
    record['status'] = ('COMPLETE' if seal['product_check_pass'] and record['assessment_complete'] and not severe
                        else 'PRODUCT_INCOMPLETE')
    verdict_path.write_text(json.dumps(record, indent=2))
    print(json.dumps(record))
    return 0


if __name__ == '__main__':
    sys.exit(run(int(sys.argv[1]), Path(sys.argv[2]).resolve()))
