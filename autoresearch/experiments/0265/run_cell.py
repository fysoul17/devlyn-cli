"""Run one 0265 cell end to end: run_cell.py <runtime.json> <name> <task> <arm> <config>. After an assessor fault,
run_cell.py --regrade <runtime.json> <name> assesses the preserved cell again.

Exit 0 = verdict recorded (any product outcome), 3 = not dispatched (preflight), 2 = STOP: a container survivor,
a B launch fault, a memory kill, changed control or harness, model identity collapse, a shared account fault, a
failed per-cell assertion (instructions.check against the launch probe's and SMOKE's seal), a locator defect, or an
evaluator or assessor that produced no verdict. Every verdict of a cell whose owner ran records oom_killed (Docker's
flag for any process in the owner container). Once a measured cell's verdict is written and is not a STOP, Codex's own
caches are pruned from its HOME (prune()).
"""
import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent


MODULES = {}  # module -> the file it was loaded from, sealed per cell


def load(name, path=None):
    local = HERE / f'{name}.py'
    prior = HERE.parent / '0256' / local.name
    source = path or (local if local.is_file() else prior if prior.is_file()
                      else HERE.parent / '0233' / local.name)
    spec = importlib.util.spec_from_file_location(name + '0265', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    MODULES[name] = Path(source)
    return module


prepare, cell_run, usage, locate, check, assess, quota, diagnostics = (load(n) for n in (
    'prepare', 'cell', 'record_usage', 'locate', 'check', 'assess', 'quota', 'diagnostics'))
base = load('run_cell0222', HERE.parent / '0222/run_cell.py')
instructions = load('instructions')
MIN_TOKEN_SECONDS = prepare.WALL_SECONDS + 900  # 3,600: no copied token is refreshed inside a cell
# Free space on the output volume before a cell: two lanes' cells and traces (full request payloads) with margin.
HEADROOM_BYTES = 16 * 2**30
# DESIGN Operations "Disk": every Codex session clones OpenAI's curated plugin marketplace into CODEX_HOME (30-100 MB a
# cell, both arms). These caches, and nothing else, leave a graded cell; evidence.manifest.json keeps their hashes.
PRUNED = ('home/.codex/.tmp', 'home/.codex/plugins/cache/openai-curated-remote',
          'home/.codex/plugins/.remote-plugin-install-staging')
# DESIGN Operations "Codex login" (O15): Codex renews a login by itself about eight days after its last renewal, and a
# renewal inside a cell, an assessor or a judge, which hold a copy, would be used up without being saved.
CODEX_LOGIN_MAX_AGE_SECONDS = 7 * 86400


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def codex_login(runtime):
    """The Codex login the runtime names (`codex_auth`, an absolute path to an auth.json), else the host default:
    (its bytes, the fingerprint of its account or None, None), or (None, None, why it is blocked). Of its fields only
    last_refresh and tokens.account_id are read; the rest are secrets and are never parsed out, logged or returned.
    Blocked while last_refresh is missing, unreadable, more than five minutes in the future or seven days old."""
    which = 'codex_auth' if runtime.get('codex_auth') else 'host default'
    source = Path(runtime.get('codex_auth') or Path.home() / '.codex/auth.json')
    try:
        data = source.read_bytes()
        login = json.loads(data)
    except OSError as exc:
        return None, None, f'Codex login ({which}) unreadable: {exc.strerror}'
    except ValueError:
        return None, None, f'Codex login ({which}) is not JSON'
    refreshed = login.get('last_refresh') if isinstance(login, dict) else None
    if refreshed is None:
        return None, None, f'Codex login ({which}) has no last_refresh'
    try:
        at = datetime.datetime.fromisoformat(refreshed) if isinstance(refreshed, str) else None
    except ValueError:
        at = None
    if at is None or at.tzinfo is None:
        return None, None, f'Codex login ({which}) last_refresh is not an ISO-8601 time with a time zone'
    age = time.time() - at.timestamp()
    if age < -300:
        return None, None, f'Codex login ({which}) last renewed {-age:.0f} s in the future; limit 300 s'
    if age >= CODEX_LOGIN_MAX_AGE_SECONDS:
        return None, None, f'Codex login ({which}) last renewed {age / 86400:.1f} days ago; limit 7 days'
    tokens = login.get('tokens')
    account = tokens.get('account_id') if isinstance(tokens, dict) else None
    return data, base.fingerprint(account) if isinstance(account, str) and account else None, None


def snapshot_auth(runtime):
    """Fresh host logins before each cell, so no copied token needs refreshing mid-cell."""
    raw = subprocess.run(['security', 'find-generic-password', '-s', 'Claude Code-credentials', '-w'],
                         capture_output=True, text=True, check=True).stdout
    oauth = json.loads(raw)['claudeAiOauth']
    remaining = oauth['expiresAt'] / 1000 - time.time()
    if remaining < MIN_TOKEN_SECONDS:
        return None, f'Claude login token expires in {int(remaining)}s; refresh the host login first'
    codex, codex_account, blocked = codex_login(runtime)
    if blocked:
        return None, blocked
    auth = Path(runtime['auth'])
    old = os.umask(0o077)
    try:
        (auth / 'claude.json').write_text(raw)
        (auth / 'codex.json').write_bytes(codex)
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
    return dict(account=identity, token_seconds_left=int(remaining), codex_account=codex_account), None


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


def preflight(runtime, expected_account=None):
    """Disk floor, fresh credential copies and the dispatching account. The usage windows are not read here: the
    driver's ready() read them seconds before (one read per cell)."""
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
    return identity, None


def image_identity(runtime):
    try:
        actual = subprocess.check_output(['docker', 'image', 'inspect', runtime['image'],
                                          '--format', '{{.Id}}'], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return False
    return actual == runtime['image']


def assessment_snapshot(runtime, venue):
    """Fresh 1,500-second assessor credential from the current host login, and a fresh copy of the Codex login under
    the same renewal guard as a cell's (a regrade can come long after its cell's copy was taken)."""
    raw = subprocess.run(['security', 'find-generic-password', '-s', 'Claude Code-credentials', '-w'],
                         capture_output=True, text=True, check=True).stdout
    oauth = json.loads(raw)['claudeAiOauth']
    remaining = oauth['expiresAt'] / 1000 - time.time()
    if remaining < 1500:
        return None, f'token expires in {int(remaining)}s'
    codex, codex_account, blocked = codex_login(runtime)
    if blocked:
        return None, blocked
    request = urllib.request.Request('https://api.anthropic.com/api/oauth/profile', headers={
        'Authorization': 'Bearer ' + oauth['accessToken'], 'anthropic-beta': 'oauth-2025-04-20'})
    with urllib.request.urlopen(request, timeout=20) as response:
        profile = json.load(response)
    account = [base.fingerprint(profile['account']['uuid']), base.fingerprint(profile['organization']['uuid'])]
    old = os.umask(0o077)
    try:
        Path(runtime['auth'], 'claude.json').write_text(raw)
        Path(runtime['auth'], 'codex.json').write_bytes(codex)
    finally:
        os.umask(old)
    return dict(account=account, token_seconds_left=int(remaining), codex_account=codex_account), None


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


def launch_fault(out, plan):
    """B's `devlyn run` refused to start the engine: a `devlyn run: <code>` line on stderr, no status line, and no
    owner evidence (no Claude init event, no Codex thread or rollout). Returns the text after `devlyn run: `."""
    if plan['arm'] != 'B':
        return None
    stderr = (out / 'run/stderr').read_text(errors='replace').splitlines()
    codes = [line[len('devlyn run: '):].strip() for line in stderr if line.startswith('devlyn run: ')]
    if not codes or any(line.startswith('devlyn: ') for line in stderr):
        return None
    if any((e.get('type') == 'system' and e.get('subtype') == 'init') or e.get('type') == 'thread.started'
           for e in cell_run.lines(out / 'run/stdout')) or any((out / 'home/.codex/sessions').rglob('*.jsonl')):
        return None
    return codes[0]


def memory_kill(owner):
    """The owner's own process was killed for memory (DESIGN Operations "Faults", O3): Docker reports an out-of-memory
    kill, the owner exited 137, and the watchdog had not fired. Docker's flag alone names any process in the container,
    so a cell whose owner went on is graded as it stands (its verdict records oom_killed); 137 alone is 0257's owner
    outcome."""
    state = owner.get('container') or {}
    if state.get('oom_killed') is True and state.get('exit_code') == 137 and owner['owner_status'] != 'HANG_TIMEOUT':
        return f'OOMKilled=True exit_code=137 owner {owner["owner_status"]}'
    return None


def checked(out, runtime):
    """check.check under the host check lock, so the two lanes never run checks at the same time (D3 and D4 rows have
    2-3 s deadlines). Released in a finally: a failing check never holds the other lane."""
    with open(runtime['check_lock'], 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            return check.check(out, runtime)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


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
    if arm not in prepare.ARMS or config not in prepare.CONFIGS:
        raise ValueError('0265 requires arm A/B and config claude/codex')
    runtime = json.loads(Path(runtime_path).read_text())
    verdict_path = Path(runtime['output']) / f'verdict-{name}.json'
    if verdict_path.is_file():
        raise ValueError(f'{name}: verdict already exists')
    instruction_seal = Path(runtime['output']).parent / 'instructions.seal.json'
    if not instruction_seal.is_file():
        return write_verdict(verdict_path, dict(cell=name, status='STOP',
                                               reason='instruction assertion: seal missing'))
    if task != 'SMOKE':
        try:
            forms = json.loads(instruction_seal.read_text())['forms']
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return write_verdict(verdict_path, dict(cell=name, status='STOP',
                                                   reason=f'instruction assertion: seal unreadable: {exc}'))
        if set(forms) != {'claude', 'codex'}:
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
    imported = {str(p.relative_to(HERE.parent)): digest(p) for iteration in ('0222', '0232', '0233', '0256')
                for p in sorted((HERE.parent / iteration).glob('*.py'))}
    (out / 'seal.json').write_text(json.dumps(dict(
        sealed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), venue=venue, image=runtime['image'],
        package_sha256=control_manifest['packages']['B']['sha256'] if arm == 'B' else None,
        modules={module: dict(path=str(path.relative_to(HERE.parent)), sha256=digest(path))
                 for module, path in MODULES.items()},
        models_cache_sha256=digest(runtime['models_cache']), imported=imported,
        instructions_seal_sha256=digest(Path(runtime['output']).parent / 'instructions.seal.json'),
        endpoints_sha256=digest(HERE / 'endpoints.json'),
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=HERE, text=True).strip(),
        apparatus={p.name: digest(p) for p in sorted(HERE.glob('*.py'))} |
                  {'0232/common.txt': digest(HERE.parent / '0232/common.txt')},
        cell={n: digest(out / n) for n in ('plan.json', 'prompt.txt', 'baseline.json',
                                          'home/.claude/settings.json') +
              (('home/.codex/config.toml',) if config == 'codex' else ())},
        control_manifest_sha256=digest(runtime['control'] + '.manifest.json')), indent=2))
    record = dict(cell=name, task=task, arm=arm, config=config, claude_account_before=venue['account'],
                  codex_account=venue['codex_account'])
    owner = cell_run.run(out, runtime)
    record['oom_killed'] = (owner.get('container') or {}).get('oom_killed') is True
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
    plan = json.loads((out / 'plan.json').read_text())
    fault, killed = launch_fault(out, plan), memory_kill(owner)
    stop = ('teardown failed: ' + str(owner.get('teardown_error')) if owner['teardown'] != 'CLEAN' else
            'B launch fault: ' + fault if fault is not None else
            'memory kill: ' + killed if killed else
            'harness changed' if not harness_unchanged(out, baseline) else
            'shared account fault during execution: ' + ', '.join(sorted({h['kind'] for h in limits['execution']}))
            if limits['execution'] else
            'model identity ' + owner['identity']['status'].lower()
            if owner['identity']['status'] in ('MISMATCH', 'UNVERIFIED', 'UNKNOWN') else None)
    if not stop and task != 'SMOKE':  # SMOKE is asserted by `instructions.py seal-forms`, once its forms exist
        try:
            assertion = instructions.check(out, plan, json.loads(instruction_seal.read_text()))
            if assertion:
                stop = 'instruction assertion: ' + '; '.join(assertion)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            stop = f'instruction assertion: evidence unreadable: {exc}'
    if not stop:
        try:
            record['snapshot'] = locate.locate(out)
            checks = checked(out, runtime)
        except locate.LocatorError as exc:
            stop = 'locator: ' + str(exc)
        except check.NoVerdict as exc:
            stop = 'evaluator produced no verdict: ' + str(exc)
    if stop:
        record.update(status='STOP', reason=stop)
        return write_verdict(verdict_path, record)
    return write_graded(out, verdict_path, grade(out, runtime, record, checks, venue))


def grade(out, runtime, record, checks, venue, assessment_venue=None):
    """The assessors on the checked snapshot, then the arm's methodology record: the verdict record."""
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
    return write_graded(out, verdict_path, grade(out, runtime, record, json.loads((out / 'checks.json').read_text()),
                                                 venue, assessment_venue=fresh))


def write_verdict(path, record):
    """Write the cell's verdict; if storage refuses it, fail closed with the record on stderr and exit code 2."""
    try:
        path.write_text(json.dumps(record, indent=2))
    except OSError as exc:
        print(f'VERDICT_UNWRITTEN ({exc}): ' + json.dumps(dict(record, status='STOP')), file=sys.stderr)
        return 2
    return 2 if record['status'] == 'STOP' else 0


def write_graded(out, path, record):
    """write_verdict for a graded record; once that verdict is written and is not a STOP, prune the cell. A SMOKE-task
    cell keeps its caches: `instructions.py seal-forms` asserts SMOKE's CODEX_HOME after the verdict, as run() asserts
    a measured cell's before it, so both read the same evidence."""
    code = write_verdict(path, record)
    if code == 0 and record['task'] != 'SMOKE':
        prune(out)
    return code


def prune(out):
    """Remove PRUNED from a graded cell and record each removed root's file count and bytes in pruned.json. Nothing
    else is touched: the devlyn projection, sessions, rollouts, sqlite state and skills/ stay. An absent root is
    skipped, so a Claude cell or a second call leaves the record as it was. A root reached through a symbolic link is
    never followed, and a root that cannot be removed is recorded with its error and printed; the verdict stands."""
    path = out / 'pruned.json'
    record = json.loads(path.read_text()) if path.is_file() else {}
    for root in PRUNED:
        target = out / root
        if not os.path.lexists(target):
            continue
        if target.resolve() != out.resolve() / root:
            record[root] = dict(error='not removed: reached through a symbolic link')
        else:
            files = size = 0
            for folder, dirs, names in os.walk(target):
                for name in names + [d for d in dirs if os.path.islink(os.path.join(folder, d))]:
                    files, size = files + 1, size + os.lstat(os.path.join(folder, name)).st_size
            record[root] = dict(files=files, bytes=size)
            try:
                shutil.rmtree(target)
            except OSError as exc:
                record[root]['error'] = f'not removed: {exc}'
        if 'error' in record[root]:
            print(f'{out.name}: {root} {record[root]["error"]}', file=sys.stderr)
    path.write_text(json.dumps(record, indent=2, sort_keys=True))
    return record


if __name__ == '__main__':
    sys.exit(regrade(*sys.argv[2:4]) if sys.argv[1] == '--regrade' else run(*sys.argv[1:6]))
