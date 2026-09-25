"""Run one cell end to end: run_cell.py <runtime.json> <name> <task> <arm> <config>.

Exit 0 = verdict recorded (any product outcome), 3 = not dispatched, 2 = stop the screen: container survivor,
control/source seal mismatch, model identity collapse, or an evaluator or assessor that produced no verdict.
"""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name + '0222', HERE / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare, cell_run, usage, check, assess = (load(n) for n in ('prepare', 'cell', 'record_usage', 'check', 'assess'))
TASKS = json.loads((HERE / 'tasks.json').read_text())
MIN_TOKEN_SECONDS = TASKS['watchdog_seconds']['owner'] + 900


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def snapshot_auth(runtime):
    """Fresh host logins before each cell, so no copied token needs refreshing mid-cell."""
    raw = subprocess.run(['security', 'find-generic-password', '-s', 'Claude Code-credentials', '-w'],
                         capture_output=True, text=True, check=True).stdout
    oauth = json.loads(raw)['claudeAiOauth']
    remaining = oauth['expiresAt'] / 1000 - time.time()
    if remaining < MIN_TOKEN_SECONDS:
        return None, f'Claude login token expires in {int(remaining)}s; refresh the host login first'
    auth = Path(runtime['auth'])
    old = os.umask(0o077)
    try:
        (auth / 'claude.json').write_text(raw)
        (auth / 'codex.json').write_bytes((Path.home() / '.codex/auth.json').read_bytes())
    finally:
        os.umask(old)
    request = urllib.request.Request('https://api.anthropic.com/api/oauth/profile', headers={
        'Authorization': 'Bearer ' + oauth['accessToken'], 'anthropic-beta': 'oauth-2025-04-20'})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            profile = json.load(response)
    except urllib.error.URLError as exc:
        return None, f'account check failed: {exc}'
    identity = [fingerprint(profile['account']['uuid']), fingerprint(profile['organization']['uuid'])]
    if identity != runtime['account']:
        return None, 'account/organization mismatch'
    return dict(account=identity, token_seconds_left=int(remaining)), None


def unassessed(assessments):
    """Assessors that returned no verdict (crash, timeout, account limit): the common evaluator failed (0221 §4)."""
    return [a['route']['model'] for a in assessments if a['exit_code'] != 0 or a['complete'] is None]


def verdict(checks, assessments):
    assessed = all(a['complete'] for a in assessments) and not any(a['severe'] for a in assessments)
    if checks['product_check_pass'] and assessed:
        return 'COMPLETE'
    return 'ADJUDICATE' if checks['adjudication_needed'] else 'PRODUCT_INCOMPLETE'


def run(runtime_path, name, task, arm, config):
    runtime = json.loads(Path(runtime_path).read_text())
    verdict_path = Path(runtime['output']) / f'verdict-{name}.json'
    identity, blocked = snapshot_auth(runtime)
    if blocked:  # not a verdict: the cell never ran and a resumed screen must run it
        (Path(runtime['output']) / f'not-dispatched-{name}.json').write_text(json.dumps(dict(reason=blocked), indent=2))
        return 3
    manifest = json.loads(Path(runtime['control'] + '.manifest.json').read_text())
    if {k: digest(Path(runtime['control']) / k) for k in manifest} != manifest:
        verdict_path.write_text(json.dumps(dict(cell=name, status='STOP', reason='control changed'), indent=2))
        return 2
    cell = prepare.prepare(runtime, name, task, arm, config)
    (cell / 'seal.json').write_text(json.dumps(dict(
        sealed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), account=identity,
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=HERE, text=True).strip(),
        apparatus={p.name: digest(p) for p in sorted(HERE.glob('*.py')) + [HERE / 'tasks.json', HERE / 'common.txt']},
        cell={n: digest(cell / n) for n in ('plan.json', 'prompt.txt', 'baseline.json')},
        control_manifest_sha256=hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()), indent=2))
    record = dict(cell=name, task=task, arm=arm, config=config)
    owner = cell_run.run(cell, runtime)
    try:
        recorded = usage.record(cell)['completeness']
    except (OSError, ValueError, KeyError, TypeError) as exc:  # usage is recorded, never a stop
        recorded = f'UNKNOWN ({type(exc).__name__}: {exc})'
    record.update(owner_status=owner['owner_status'], owner_seconds=owner['seconds'], teardown=owner['teardown'],
                  identity=owner['identity'], usage=recorded)
    stop = ('container survived teardown' if owner['teardown'] != 'CLEAN' else
            'model identity ' + owner['identity']['status'].lower()
            if owner['identity']['status'] in ('MISMATCH', 'UNVERIFIED') else None)
    if not stop:
        try:
            checks = check.check(cell, runtime)
        except check.NoVerdict as exc:
            stop = 'evaluator produced no verdict: ' + str(exc)
    if stop:
        record.update(status='STOP', reason=stop)
        verdict_path.write_text(json.dumps(record, indent=2))
        return 2
    assessments = assess.assess(cell, runtime)
    record.update(product_check_pass=checks['product_check_pass'], oracle=checks['oracle'],
                  scope_violations=checks['scope_violations'], assessments=assessments,
                  assessor_disagreement=len({a['complete'] for a in assessments}) > 1,
                  status=verdict(checks, assessments))
    if unassessed(assessments):
        record.update(status='STOP', reason='assessor produced no verdict: ' + ', '.join(unassessed(assessments)))
    verdict_path.write_text(json.dumps(record, indent=2))
    return 2 if record['status'] == 'STOP' else 0


if __name__ == '__main__':
    sys.exit(run(*sys.argv[1:6]))
