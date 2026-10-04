"""Run one 0231 cell end to end: run_cell.py <runtime.json> <name> <task> <arm> <config>.

Exit 0 = verdict recorded (any product outcome), 3 = not dispatched (preflight), 2 = STOP: a container survivor,
changed control or harness, model identity collapse, a shared account limit, a locator defect, or an evaluator or
assessor that produced no verdict.
"""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import uuid
import urllib.request

HERE = Path(__file__).resolve().parent


def load(name, path=None):
    spec = importlib.util.spec_from_file_location(name + '0231', path or HERE / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare, cell_run, usage, locate, check, assess, quota, obligations = (
    load(n) for n in ('prepare', 'cell', 'record_usage', 'locate', 'check', 'assess', 'quota', 'obligations'))
base = load('run_cell0222', HERE.parent / '0222/run_cell.py')
HEADROOM_BYTES = 20 * 2**30  # free space on the output volume before a cell; traces keep full request payloads


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def claude_limits(runtime):
    """The dispatching Claude account's own windows (utilization percent and reset), from its usage endpoint."""
    oauth = json.loads((Path(runtime['auth']) / 'claude.json').read_text())['claudeAiOauth']
    request = urllib.request.Request('https://api.anthropic.com/api/oauth/usage', headers={
        'Authorization': 'Bearer ' + oauth['accessToken'], 'anthropic-beta': 'oauth-2025-04-20'})
    with urllib.request.urlopen(request, timeout=20) as response:
        windows = json.load(response)
    return {name: dict(used=value.get('utilization'), resets=value.get('resets_at'))
            for name, value in windows.items() if isinstance(value, dict) and isinstance(value.get('utilization'), (int, float))}


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


def preflight(runtime):
    free = shutil.disk_usage(runtime['output']).free
    if free < HEADROOM_BYTES:
        return None, f'output volume has {free} bytes free, below {HEADROOM_BYTES}'
    identity, blocked = base.snapshot_auth(runtime)
    if blocked:
        return None, blocked
    try:
        claude = claude_limits(runtime)
    except (urllib.error.URLError, KeyError, ValueError) as exc:
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
            and digest(out / 'harness/git-ssh') == transport['script_sha256']
            and digest(out / 'harness/roles.json') == baseline['roles_sha256']
            and digest(out / 'harness/caller.json') == baseline['caller_sha256'])


def run(runtime_path, name, task, arm, config):
    runtime = json.loads(Path(runtime_path).read_text())
    verdict_path = Path(runtime['output']) / f'verdict-{name}.json'
    venue, blocked = preflight(runtime)
    if blocked:  # not a verdict: the cell never ran and a resumed comparison must run it
        (Path(runtime['output']) / f'not-dispatched-{name}.json').write_text(json.dumps(dict(reason=blocked), indent=2))
        return 3
    if not control_unchanged(runtime):
        verdict_path.write_text(json.dumps(dict(cell=name, status='STOP', reason='control changed'), indent=2))
        return 2
    out = prepare.prepare(runtime, name, task, arm, config)
    (out / 'seal.json').write_text(json.dumps(dict(
        sealed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), venue=venue, image=runtime['image'],
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=HERE, text=True).strip(),
        apparatus={p.name: digest(p) for p in sorted(HERE.glob('*.py')) + [HERE / 'common.txt']},
        cell={n: digest(out / n) for n in ('plan.json', 'prompt.txt', 'baseline.json')},
        control_manifest_sha256=digest(runtime['control'] + '.manifest.json')), indent=2))
    record = dict(cell=name, task=task, arm=arm, config=config)
    owner = cell_run.run(out, runtime)
    sealed, collection_failures = seal_after_teardown(out)
    try:
        recorded = usage.record(out)
    except (OSError, ValueError, KeyError, TypeError) as exc:  # usage is recorded, never a stop
        recorded = dict(completeness=f'UNKNOWN ({type(exc).__name__}: {exc})', output_tokens=None)
    limits = quota.classify(out)
    trace_bytes = sum(p.stat().st_size for p in (out / 'cell/trace').rglob('*') if p.is_file())
    record.update(owner_status=owner['owner_status'], owner_seconds=owner['seconds'], teardown=owner['teardown'],
                  identity=owner['identity'], usage=recorded['completeness'], output_tokens=recorded['output_tokens'],
                  quota=limits, trace_bytes=trace_bytes, evidence_manifest_sha256=sealed,
                  collection_failures=collection_failures)
    baseline = json.loads((out / 'baseline.json').read_text())
    stop = ('container survived teardown' if owner['teardown'] != 'CLEAN' else
            'harness changed' if not harness_unchanged(out, baseline) else
            'evidence collection failed: ' + '; '.join(collection_failures[:3]) if collection_failures else
            'shared account fault during execution: ' + ', '.join(sorted({h['kind'] for h in limits['execution']}))
            if limits['execution'] else
            'model identity ' + owner['identity']['status'].lower()
            if owner['identity']['status'] in ('MISMATCH', 'UNVERIFIED', 'UNKNOWN') else None)
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
    try:
        assessments = assess.assess(out, runtime)
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        record.update(status='STOP', reason=f'assessment failed: {exc}')
        return write_verdict(verdict_path, record)
    record.update(product_check_pass=checks['product_check_pass'], oracle=checks['oracle'],
                  scope_violations=checks['scope_violations'], assessments=assessments,
                  assessor_disagreement=len({a['complete'] for a in assessments}) > 1,
                  status=base.verdict(checks, assessments), obligations=obligations.meter(out))
    if base.unassessed(assessments):
        regrade = quota.classify(out)['assessment']
        record.update(status='STOP', reason='assessor produced no verdict: ' + ', '.join(base.unassessed(assessments))
                      + ('; account limit: regrade from preserved evidence' if regrade else ''))
    return write_verdict(verdict_path, record)


def write_verdict(path, record):
    """Write the cell's verdict; if storage refuses it, fail closed with the record on stderr and exit code 2."""
    try:
        path.write_text(json.dumps(record, indent=2))
    except OSError as exc:
        print(f'VERDICT_UNWRITTEN ({exc}): ' + json.dumps(dict(record, status='STOP')), file=sys.stderr)
        return 2
    return 2 if record['status'] == 'STOP' else 0


if __name__ == '__main__':
    sys.exit(run(*sys.argv[1:6]))
