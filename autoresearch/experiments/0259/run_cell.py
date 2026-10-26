"""Run one 0232 cell end to end: run_cell.py <runtime.json> <name> <task> <arm> <config>. After an assessor fault,
run_cell.py --regrade <runtime.json> <name> assesses the preserved cell again.

Exit 0 = verdict recorded (any product outcome), 3 = not dispatched (preflight), 2 = STOP: a container survivor,
changed control or harness, model identity collapse, a shared account limit, a locator defect, or an evaluator or
assessor that produced no verdict.
"""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent


def load(name, path=None):
    local = HERE / f'{name}.py'
    prior = HERE.parent / '0256' / local.name
    source = path or (local if local.is_file() else prior if prior.is_file()
                      else HERE.parent / '0233' / local.name)
    spec = importlib.util.spec_from_file_location(name + '0259', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare, cell_run, usage, locate, check, assess, quota, diagnostics = (load(n) for n in (
    'prepare', 'cell', 'record_usage', 'locate', 'check', 'assess', 'quota', 'diagnostics'))
base = load('run_cell0222', HERE.parent / '0222/run_cell.py')
instructions = load('instructions')
HEADROOM_BYTES = 8 * 2**30  # free space on the output volume before a cell: one cell's traces (full request payloads) with margin


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot_auth(runtime):
    """Fresh host logins before each cell, so no copied token needs refreshing mid-cell."""
    raw = subprocess.run(['security', 'find-generic-password', '-s', 'Claude Code-credentials', '-w'],
                         capture_output=True, text=True, check=True).stdout
    oauth = json.loads(raw)['claudeAiOauth']
    remaining = oauth['expiresAt'] / 1000 - time.time()
    if remaining < base.MIN_TOKEN_SECONDS:
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
    identity = [base.fingerprint(profile['account']['uuid']), base.fingerprint(profile['organization']['uuid'])]
    return dict(account=identity, token_seconds_left=int(remaining)), None


def claude_limits(runtime, access_token=None):
    """The dispatching Claude account's own windows (utilization percent and reset), from its usage endpoint."""
    if access_token is None:
        access_token = json.loads((Path(runtime['auth']) / 'claude.json').read_text())['claudeAiOauth']['accessToken']
    request = urllib.request.Request('https://api.anthropic.com/api/oauth/usage', headers={
        'Authorization': 'Bearer ' + access_token, 'anthropic-beta': 'oauth-2025-04-20'})
    with urllib.request.urlopen(request, timeout=20) as response:
        windows = json.load(response)
    return {name: dict(used=value.get('utilization'), resets=value.get('resets_at'))
            for name, value in windows.items() if isinstance(value, dict) and isinstance(value.get('utilization'), (int, float))}


def claude_limits_with_account(runtime):
    """Read after-window usage and its account with one host credential."""
    raw = subprocess.run(['security', 'find-generic-password', '-s', 'Claude Code-credentials', '-w'],
                         capture_output=True, text=True, check=True).stdout
    oauth = json.loads(raw)['claudeAiOauth']
    request = urllib.request.Request('https://api.anthropic.com/api/oauth/profile', headers={
        'Authorization': 'Bearer ' + oauth['accessToken'], 'anthropic-beta': 'oauth-2025-04-20'})
    with urllib.request.urlopen(request, timeout=20) as response:
        profile = json.load(response)
    account = [base.fingerprint(profile['account']['uuid']), base.fingerprint(profile['organization']['uuid'])]
    return claude_limits(runtime, oauth['accessToken']), account


def codex_limits(runtime):
    """Fresh, account-bound Codex windows: one minimal call on the dispatching login, read from its own rollout."""
    with tempfile.TemporaryDirectory(prefix='limits-', dir=runtime['scratch']) as temp:
        home = Path(temp)
        (home / '.codex').mkdir()
        shutil.copyfile(Path(runtime['auth']) / 'codex.json', home / '.codex/auth.json')
        name = 'devlyn-0231-limits-' + uuid.uuid4().hex
        argv = ['docker', 'run', '--name', name, '--rm', '--network', 'bridge', '--read-only', '--cap-drop', 'ALL',
                '--security-opt', 'no-new-privileges', '--tmpfs', '/tmp:rw,exec',
                '--tmpfs', '/home/probe/.codex/tmp:rw,nosuid,exec,uid=501,gid=501',
                '--mount', f'type=bind,src={home},dst=/home/probe', '--env', 'HOME=/home/probe',
                '--env', 'CODEX_HOME=/home/probe/.codex', runtime['image'], 'timeout', '120s', 'codex', 'exec',
                '--ignore-user-config', '--ignore-rules', '--skip-git-repo-check', '-s', 'read-only',
                '-m', 'gpt-6-astra', '-c', 'model_reasoning_effort=low', '-C', '/tmp', 'Reply OK.']
        try:
            subprocess.run(argv, capture_output=True, timeout=180)
        except subprocess.TimeoutExpired:
            return {}
        finally:
            assess.reap(name)
        for path in (home / '.codex/sessions').rglob('*.jsonl'):
            for line in reversed(path.read_text(errors='replace').splitlines()):
                payload = (json.loads(line).get('payload') or {}) if line.startswith('{') else {}
                limits = payload.get('rate_limits') if isinstance(payload, dict) else None
                if isinstance(limits, dict):
                    return {k: dict(used=v.get('used_percent'), resets=v.get('resets_at'))
                            for k, v in limits.items() if isinstance(v, dict) and isinstance(v.get('used_percent'), (int, float))}
    return {}


def preflight(runtime, expected_account=None):
    free = shutil.disk_usage(runtime['output']).free
    if free < HEADROOM_BYTES:
        return None, f'output volume has {free} bytes free, below {HEADROOM_BYTES}'
    try:
        identity, blocked = snapshot_auth(runtime)
    except OSError as exc:
        return None, f'Claude account check failed: {exc}'
    if blocked:
        return None, blocked
    if expected_account is not None and identity['account'] != expected_account:
        return None, 'account changed after reserve check'
    try:
        claude = claude_limits(runtime)
    except (OSError, KeyError, ValueError) as exc:
        return None, f'Claude limit check failed: {exc}'
    try:
        codex = codex_limits(runtime)
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        return None, f'Codex limit check failed: {exc}'
    if not claude or not codex:
        return None, f'limit evidence unavailable (claude {bool(claude)}, codex {bool(codex)})'
    full = [f'{engine} {name} until {w["resets"]}' for engine, windows in (('claude', claude), ('codex', codex))
            for name, w in windows.items() if w['used'] >= 100]
    if full:
        return None, 'account limit reached: ' + ', '.join(full)
    return dict(identity, claude_limits=claude, codex_limits=codex), None


def image_identity(runtime):
    try:
        actual = subprocess.check_output(['docker', 'image', 'inspect', runtime['image'],
                                          '--format', '{{.Id}}'], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return False
    return actual == runtime['image']


def assessment_snapshot(runtime, venue):
    """Fresh 1,500-second assessor credential from the current host login."""
    raw = subprocess.run(['security', 'find-generic-password', '-s', 'Claude Code-credentials', '-w'],
                         capture_output=True, text=True, check=True).stdout
    oauth = json.loads(raw)['claudeAiOauth']
    remaining = oauth['expiresAt'] / 1000 - time.time()
    if remaining < 1500:
        return None, f'token expires in {int(remaining)}s'
    request = urllib.request.Request('https://api.anthropic.com/api/oauth/profile', headers={
        'Authorization': 'Bearer ' + oauth['accessToken'], 'anthropic-beta': 'oauth-2025-04-20'})
    with urllib.request.urlopen(request, timeout=20) as response:
        profile = json.load(response)
    account = [base.fingerprint(profile['account']['uuid']), base.fingerprint(profile['organization']['uuid'])]
    Path(runtime['auth'], 'claude.json').write_text(raw)
    return dict(account=account, token_seconds_left=int(remaining)), None


def seal_after_teardown(out):
    """After verified teardown: make the cell directory owner-only (its own mode only, so product file modes stay
    as the run left them) and seal every raw evidence file by sha256. Returns (manifest digest, failures)."""
    failures = []
    try:
        out.chmod(0o700)
        if out.stat().st_mode & 0o077:
            failures.append('cell directory is not owner-only')
        files = {}
        for root in (out / name for name in ('run', 'cell', 'tmp', 'home')):
            for path in sorted(p for p in root.rglob('*') if p.is_file() and not p.is_symlink()):
                try:
                    files[str(path.relative_to(out))] = digest(path)
                except OSError as exc:
                    failures.append(f'{path.relative_to(out)}: {exc}')
        (out / 'evidence.manifest.json').write_text(json.dumps(dict(files=files, failures=failures), indent=1, sort_keys=True))
        return digest(out / 'evidence.manifest.json'), failures
    except OSError as exc:
        return None, failures + [f'evidence collection failed: {exc}']


def control_unchanged(runtime):
    record = json.loads(Path(runtime['control'] + '.manifest.json').read_text())
    return all({str(p.relative_to(Path(runtime['control']) / name)): digest(p)
                for p in sorted((Path(runtime['control']) / name).rglob('*')) if p.is_file()} == manifest
               for name, manifest in record['manifests'].items())


def harness_unchanged(out, baseline):
    transport = baseline['transport']
    target = out / 'harness/mirror.git'
    git = lambda *a: subprocess.run(['git', '-C', str(target), *a], capture_output=True, text=True, check=True).stdout.strip()
    return (git('for-each-ref', '--format=%(refname) %(objectname)') == transport['refs']
            and hashlib.sha256(git('rev-list', '--objects', '--all').encode()).hexdigest() == transport['objects']
            and locate.git(out / 'cell/work', 'remote', 'get-url', 'origin') == '/harness/mirror.git'
            and locate.git(out / 'cell/work', 'rev-parse', 'origin/HEAD') == baseline['allocation_sha']
            and locate.git(out / 'cell/work', 'config', '--local', '--get', 'core.sshCommand', check=False) is None
            and locate.git(out / 'cell/work', 'config', '--local', '--get-regexp',
                           r'^url\..*\.insteadOf$', check=False) is None
            and digest(out / 'harness/roles.json') == baseline['roles_sha256']
            and digest(out / 'harness/caller.json') == baseline['caller_sha256'])


def run(runtime_path, name, task, arm, config, *, expected_account=None):
    if arm not in ('B', 'C') or config != 'claude':
        raise ValueError('0259 requires arm B/C and config claude')
    runtime = json.loads(Path(runtime_path).read_text())
    verdict_path = Path(runtime['output']) / f'verdict-{name}.json'
    if verdict_path.is_file():
        raise ValueError(f'{name}: verdict already exists')
    instruction_seal = Path(runtime['output']).parent / 'instructions.seal.json'
    if not instruction_seal.is_file():
        return write_verdict(verdict_path, dict(cell=name, status='STOP',
                                               reason='instruction assertion: seal missing'))
    try:
        sealed_instructions = json.loads(instruction_seal.read_text())
        expected_witness = sealed_instructions['witness_sha256']
        witness = HERE / 'results/witnesses/d3-parseoptions-override.js'
        if digest(witness) != expected_witness:
            return write_verdict(verdict_path, dict(cell=name, status='STOP',
                                                   reason='instruction assertion: D3 witness changed after seal'))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return write_verdict(verdict_path, dict(cell=name, status='STOP',
                                               reason=f'instruction assertion: witness seal unreadable: {exc}'))
    if task != 'SMOKE':
        try:
            forms = sealed_instructions['forms']
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return write_verdict(verdict_path, dict(cell=name, status='STOP',
                                                   reason=f'instruction assertion: seal unreadable: {exc}'))
        if set(forms) != {'B', 'C'}:
            return write_verdict(verdict_path, dict(cell=name, status='STOP',
                                                   reason='instruction assertion: owner forms unsealed'))
    if not image_identity(runtime):
        (Path(runtime['output']) / f'not-dispatched-{name}.json').write_text(json.dumps(
            dict(reason='image identity mismatch'), indent=2))
        return 3
    venue, blocked = preflight(runtime, expected_account=expected_account)
    if blocked:  # not a verdict: the cell never ran and a resumed comparison must run it
        (Path(runtime['output']) / f'not-dispatched-{name}.json').write_text(json.dumps(dict(reason=blocked), indent=2))
        return 3
    if not control_unchanged(runtime):
        verdict_path.write_text(json.dumps(dict(cell=name, status='STOP', reason='control changed'), indent=2))
        return 2
    out = prepare.prepare(runtime, name, task, arm, config)
    control_manifest = json.loads(Path(runtime['control'] + '.manifest.json').read_text())
    imported = {str(p.relative_to(HERE.parent)): digest(p) for iteration in ('0222', '0232', '0233', '0237', '0256')
                for p in sorted((HERE.parent / iteration).glob('*.py'))}
    (out / 'seal.json').write_text(json.dumps(dict(
        sealed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), venue=venue, image=runtime['image'],
        package_sha256=control_manifest['packages'][arm]['sha256'],
        models_cache_sha256=digest(runtime['models_cache']), imported=imported,
        instructions_seal_sha256=digest(Path(runtime['output']).parent / 'instructions.seal.json'),
        d3_witness_sha256=expected_witness,
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=HERE, text=True).strip(),
        apparatus={p.name: digest(p) for p in sorted(HERE.glob('*.py'))} |
                  {'0232/common.txt': digest(HERE.parent / '0232/common.txt')},
        cell={n: digest(out / n) for n in ('plan.json', 'prompt.txt', 'baseline.json',
                                          'home/.claude/settings.json')},
        control_manifest_sha256=digest(runtime['control'] + '.manifest.json')), indent=2))
    record = dict(cell=name, task=task, arm=arm, config=config, claude_limits_before=venue['claude_limits'],
                  claude_account_before=venue['account'])
    owner = cell_run.run(out, runtime)
    sealed, collection_failures = seal_after_teardown(out)
    if collection_failures:  # stop before any other reader touches evidence that could not be sealed
        record.update(owner_status=owner['owner_status'], teardown=owner['teardown'],
                      identity=owner['identity'], status='STOP',
                      reason='evidence collection failed: ' + '; '.join(collection_failures[:3]))
        return write_verdict(verdict_path, record)
    try:
        recorded = usage.record(out)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:  # usage is recorded, never a stop
        recorded = dict(completeness=f'UNKNOWN ({type(exc).__name__}: {exc})', input_tokens=None, output_tokens=None)
    limits = quota.classify(out)
    trace_bytes = sum(p.stat().st_size for p in (out / 'cell/trace').rglob('*') if p.is_file())
    record.update(owner_status=owner['owner_status'], owner_seconds=owner['seconds'], teardown=owner['teardown'],
                  identity=owner['identity'], usage=recorded['completeness'], input_tokens=recorded['input_tokens'],
                  output_tokens=recorded['output_tokens'],
                  quota=limits, trace_bytes=trace_bytes, evidence_manifest_sha256=sealed,
                  collection_failures=collection_failures)
    try:
        record['diagnostics'] = diagnostics.record(out)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        record['diagnostics'] = dict(status='UNKNOWN', error=f'{type(exc).__name__}: {exc}')
    baseline = json.loads((out / 'baseline.json').read_text())
    stop = ('teardown failed: ' + str(owner.get('teardown_error')) if owner['teardown'] != 'CLEAN' else
            'harness changed' if not harness_unchanged(out, baseline) else
            'shared account fault during execution: ' + ', '.join(sorted({h['kind'] for h in limits['execution']}))
            if limits['execution'] else
            'model identity ' + owner['identity']['status'].lower()
            if owner['identity']['status'] in ('MISMATCH', 'UNVERIFIED', 'UNKNOWN') else None)
    if not stop:
        try:
            assertion = instructions.check(out, json.loads((out / 'plan.json').read_text()),
                                           json.loads((out / 'instructions.pre.json').read_text()),
                                           json.loads(instruction_seal.read_text()))
            if assertion:
                stop = 'instruction assertion: ' + '; '.join(assertion)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            stop = f'instruction assertion: evidence unreadable: {exc}'
    if not stop:
        try:
            record['snapshot'] = locate.locate(out)
            checks = check.check(out, runtime)
        except locate.LocatorError as exc:
            stop = 'locator: ' + str(exc)
        except check.NoVerdict as exc:
            stop = 'evaluator produced no verdict: ' + str(exc)
    if stop:
        record.update(status='STOP', reason=stop)
        return write_verdict(verdict_path, record)
    return write_verdict(verdict_path, grade(out, runtime, record, checks, venue))


def grade(out, runtime, record, checks, venue, assessment_venue=None):
    """The assessors on the checked snapshot, then the arm's methodology record: the verdict record."""
    record.pop('claude_limits_after', None)
    record.pop('claude_limits_after_error', None)
    record.pop('claude_account_after', None)
    record.pop('assessor_account', None)
    try:
        fresh, blocked = (assessment_snapshot(runtime, venue) if assessment_venue is None
                          else (assessment_venue, None))
        if blocked:
            return dict(record, status='STOP', reason='assessment held: ' + blocked)
        record['assessment_venue'] = fresh
        record['assessor_account'] = fresh['account']
        assessments = assess.assess(out, runtime)
    except (RuntimeError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        record.update(status='STOP', reason=f'assessment failed: {exc}')
    else:
        record.update(product_check_pass=checks['product_check_pass'], oracle=checks['oracle'],
                      scope_violations=checks['scope_violations'], assessments=assessments,
                      assessor_disagreement=len({a['complete'] for a in assessments}) > 1,
                      status=base.verdict(checks, assessments))
        if base.unassessed(assessments):
            regrade = quota.classify(out)['assessment']
            record.update(status='STOP', reason='assessor produced no verdict: ' + ', '.join(base.unassessed(assessments))
                          + ('; account limit: regrade from preserved evidence' if regrade else ''))
    try:
        record['claude_limits_after'], record['claude_account_after'] = claude_limits_with_account(runtime)
    except Exception as exc:  # telemetry must not discard an assessed verdict
        record['claude_limits_after_error'] = str(exc)
    return record


def regrade(runtime_path, name, *, expected_account=None):
    """Assess a cell again from its preserved evidence after an assessor fault (0231 Faults: regrade, never re-dispatch).
    Its execution record, snapshot and checks stay; the STOP verdict and any partial assessment are kept as .stop-N."""
    runtime = json.loads(Path(runtime_path).read_text())
    output = Path(runtime['output'])
    out, verdict_path = output / name, output / f'verdict-{name}.json'
    record = json.loads(verdict_path.read_text())
    if record.get('status') != 'STOP' or not str(record.get('reason')).startswith(('assessment failed', 'assessor produced', 'assessment held:')):
        raise SystemExit(f'{name}: only an assessor STOP is regraded')
    venue = json.loads((out / 'seal.json').read_text())['venue']
    fresh, blocked = assessment_snapshot(runtime, venue)
    if blocked:
        print(f'{name}: not regraded: {blocked}', file=sys.stderr)
        return 3
    if expected_account is not None and fresh['account'] != expected_account:
        (output / f'not-dispatched-{name}.json').write_text(json.dumps(
            dict(reason='account changed after reserve check'), indent=2))
        return 3
    stop = next(n for n in range(1, 100) if not (output / f'verdict-{name}.stop-{n}.json').exists())
    verdict_path.rename(output / f'verdict-{name}.stop-{stop}.json')
    if (out / 'assessment').exists():
        (out / 'assessment').rename(out / f'assessment.stop-{stop}')
    record = {k: v for k, v in record.items() if k not in ('status', 'reason')} | dict(
        regraded=dict(after=f'stop-{stop}', venue=venue, at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    record.setdefault('claude_account_before', venue['account'])
    return write_verdict(verdict_path, grade(out, runtime, record, json.loads((out / 'checks.json').read_text()),
                                             venue, assessment_venue=fresh))


def write_verdict(path, record):
    """Write the cell's verdict; if storage refuses it, fail closed with the record on stderr and exit code 2."""
    try:
        path.write_text(json.dumps(record, indent=2))
    except OSError as exc:
        print(f'VERDICT_UNWRITTEN ({exc}): ' + json.dumps(dict(record, status='STOP')), file=sys.stderr)
        return 2
    return 2 if record['status'] == 'STOP' else 0


if __name__ == '__main__':
    sys.exit(regrade(*sys.argv[2:4]) if sys.argv[1] == '--regrade' else run(*sys.argv[1:6]))
