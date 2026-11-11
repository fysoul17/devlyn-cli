"""Run one 0265 cell end to end: run_cell.py <runtime.json> <name> <task> <arm> <config>. After an assessor fault,
run_cell.py --regrade <runtime.json> <name> assesses the preserved cell again.

Exit 0 = verdict recorded (any product outcome), 3 = not dispatched (preflight, or a Claude login copy left with less
than the watchdog plus 300 s once the cell is prepared: the prepared folder is removed), 2 = STOP: a container that
could not be set up, a container survivor, a B launch fault, a memory kill, changed control or harness, model
identity collapse, a shared account fault, a failed per-cell assertion (instructions.check against the launch probe's
and SMOKE's seal), a locator defect, an evaluator or assessor that produced no verdict, or an assessor container whose
removal is unproved. Every verdict records owner_ran (DESIGN "The rule for attempts": false only before the cell and
for a B launch fault), and every verdict of a cell whose container ran records oom_killed (Docker's flag for any
process in the owner container). Every STOP whose owner ran keeps its graded tree and scope once its teardown is proved
(stop_evidence; an assessor STOP keeps its full checks.json), and says why when it has none. An owner at the
watchdog is never COMPLETE. Once a measured cell's verdict is
written and is not a STOP, Codex's own caches are pruned from its HOME (prune()).
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


prepare, cell_run, usage, locate, check, assess, quota = (load(n) for n in (
    'prepare', 'cell', 'record_usage', 'locate', 'check', 'assess', 'quota'))
base = load('run_cell0222', HERE.parent / '0222/run_cell.py')
instructions = load('instructions')
MIN_TOKEN_SECONDS = prepare.WALL_SECONDS + 900  # 3,600: no copied token is refreshed inside a cell
START_TOKEN_SECONDS = prepare.WALL_SECONDS + 300  # 3,000: what the copy must still hold once the cell is prepared
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


def token_life(runtime):
    """Seconds left on the Claude login copy a cell is about to mount (runtime['auth']/claude.json, which preflight's
    snapshot_auth wrote): DESIGN "Token guard" reads it again once the cell is prepared. Only expiresAt is read."""
    oauth = json.loads((Path(runtime['auth']) / 'claude.json').read_text())['claudeAiOauth']
    return oauth['expiresAt'] / 1000 - time.time()


def claude_limits(runtime, access_token):
    """The dispatching Claude account's own windows (utilization percent and reset), from its usage endpoint, read with
    the token the driver's ready() read."""
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


def assessment_snapshot(runtime):
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
        return write_verdict(verdict_path, dict(cell=name, status='STOP', owner_ran=False,
                                               reason='instruction assertion: seal missing'))
    if task != 'SMOKE':
        try:
            forms = json.loads(instruction_seal.read_text())['forms']
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return write_verdict(verdict_path, dict(cell=name, status='STOP', owner_ran=False,
                                                   reason=f'instruction assertion: seal unreadable: {exc}'))
        if set(forms) != {'claude', 'codex'}:
            return write_verdict(verdict_path, dict(cell=name, status='STOP', owner_ran=False,
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
        verdict_path.write_text(json.dumps(dict(cell=name, status='STOP', owner_ran=False, reason='control changed'),
                                           indent=2))
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
    left = token_life(runtime)
    if left < START_TOKEN_SECONDS:  # DESIGN "Token guard": prepare has no time limit; nothing ran in the folder
        shutil.rmtree(out)
        (Path(runtime['output']) / f'not-dispatched-{name}.json').write_text(json.dumps(dict(
            reason=f'Claude login copy expires in {int(left)}s after prepare, below {START_TOKEN_SECONDS}s'), indent=2))
        return 3
    record = dict(cell=name, task=task, arm=arm, config=config, claude_account_before=venue['account'],
                  codex_account=venue['codex_account'])
    try:
        owner = cell_run.run(out, runtime)
    except (OSError, subprocess.SubprocessError) as exc:  # DESIGN Faults: a container that could not be set up (or
        ended = out / 'run/result.json'  # recorded) is a STOP; cell.run has removed what it had made
        ended = json.loads(ended.read_text()) if ended.is_file() else {}
        record.update({key: ended[key] for key in ('owner_status', 'teardown', 'teardown_error') if key in ended},
                      owner_ran=ended.get('owner_status') is not None, status='STOP',
                      reason=f'cell setup failed: {type(exc).__name__}: {exc}')
        if record['owner_ran']:
            record = stop_evidence(out, record, proved=record.get('teardown') == 'CLEAN')
        return write_verdict(verdict_path, record)
    record['oom_killed'] = (owner.get('container') or {}).get('oom_killed') is True
    sealed, collection_failures = seal_after_teardown(out)
    if collection_failures:  # stop before reading usage, quota or launch evidence that could not be sealed; nothing
        record.update(owner_status=owner['owner_status'], teardown=owner['teardown'],  # shows a launch fault, so
                      identity=owner['identity'], status='STOP', owner_ran=True,  # the owner is taken to have run
                      reason='evidence collection failed: ' + '; '.join(collection_failures[:3]))
        return write_verdict(verdict_path, stop_evidence(out, record, proved=owner['teardown'] == 'CLEAN'))
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
    baseline = json.loads((out / 'baseline.json').read_text())
    plan = json.loads((out / 'plan.json').read_text())
    fault, killed = launch_fault(out, plan), memory_kill(owner)
    record['owner_ran'] = fault is None
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
            stop, record = 'locator: ' + str(exc), unchosen(out, record, exc)
        except check.NoVerdict as exc:
            stop = 'evaluator produced no verdict: ' + str(exc)
    if stop:
        record.update(status='STOP', reason=stop)
        if record['owner_ran'] and 'scope_violations' not in record:  # a locator STOP has its scope_error already
            record = stop_evidence(out, record, proved=owner['teardown'] == 'CLEAN')
        return write_verdict(verdict_path, record)
    return write_graded(out, verdict_path, grade(out, runtime, record, checks))


def unchosen(out, record, exc):
    """No graded tree: scope_violations null with the reason in scope_error, and no snapshot (a partial copy is moved
    to snapshot.partial, out of the graders' way)."""
    if (out / 'snapshot').exists():
        (out / 'snapshot').rename(out / 'snapshot.partial')
    return dict({key: value for key, value in record.items() if key != 'snapshot'}, scope_violations=None,
                scope_error=str(exc))


def stop_evidence(out, record, proved=True):
    """DESIGN "Attempts": an attempt whose owner ran and that ends in a STOP keeps, once its teardown is proved, its
    graded tree (locate.locate: snapshot/ and snapshot.json; an evaluator STOP keeps the one locate already chose) and
    its scope result (check.scope, the check phase's own reading of tree against baseline and allowed paths), in the
    record and in a checks.json of those fields alone: nothing else was checked. An assessor STOP never comes here: its
    full checks.json stays and grade() records its scope. A teardown not proved (proved=False; driver.py's recover
    proves a Docker loss and calls this again), a tree locate cannot choose or evidence that cannot be read leaves no
    graded tree (unchosen) and says why in scope_error. Returns the record."""
    record = {key: value for key, value in record.items() if key != 'scope_error'}
    if not proved:
        return unchosen(out, record, 'not taken: the teardown is not proved')
    try:
        selection = record['snapshot'] if 'snapshot' in record else locate.locate(out)
        changed, violations = check.scope(out)
    except (locate.LocatorError, OSError, ValueError) as exc:
        return unchosen(out, record, exc)
    (out / 'checks.json').write_text(json.dumps(dict(scope_violations=violations, changed=changed), indent=2))
    return dict(record, snapshot=selection, scope_violations=violations, changed=changed)


def grade(out, runtime, record, checks, assessment_venue=None):
    """The assessors on the checked snapshot, then the arm's methodology record: the verdict record. An owner at the
    watchdog is PRODUCT_INCOMPLETE whatever its checks and assessors say (DESIGN "Details every count uses"). The scope
    result is recorded before any assessor runs, so an assessor STOP keeps it (DESIGN "Attempts")."""
    record.pop('assessor_account', None)
    record['scope_violations'] = checks['scope_violations']
    try:
        fresh, blocked = assessment_snapshot(runtime) if assessment_venue is None else (assessment_venue, None)
        if blocked:
            return dict(record, status='STOP', reason='assessment held: ' + blocked)
        record['assessment_venue'] = fresh
        record['assessor_account'] = fresh['account']
        assessments = assess.assess(out, runtime)
    except assess.TeardownUnproved as exc:  # never regraded: another assessment could run beside the survivor
        record.update(status='STOP', reason=f'assessor teardown unproved: {exc}')
    except (RuntimeError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        record.update(status='STOP', reason=f'assessment failed: {exc}')
    else:
        record.update(product_check_pass=checks['product_check_pass'], oracle=checks['oracle'], assessments=assessments,
                      assessor_disagreement=len({a['complete'] for a in assessments}) > 1,
                      status='PRODUCT_INCOMPLETE' if record['owner_status'] == 'HANG_TIMEOUT'
                      else base.verdict(checks, assessments))
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
    fresh, blocked = assessment_snapshot(runtime)
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
                                                 assessment_venue=fresh))


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


def replace(path, record):
    """Write a JSON record through a temp file in its folder and os.replace, so no reader sees part of it."""
    temp = path.with_name(f'.{path.name}.{os.getpid()}')
    temp.write_text(json.dumps(record, indent=2, sort_keys=True))
    os.replace(temp, path)


def prune(out):
    """Remove PRUNED from a graded cell. Before anything is deleted, pruned.json lists each present root with its file
    count, bytes and every symbolic link under it (path and target: evidence.manifest.json holds regular files only),
    marked "removed": false; once every listed root is gone the mark becomes true (an atomic replace). Nothing else is
    touched: the devlyn projection, sessions, rollouts, sqlite state and skills/ stay. An existing pruned.json is
    returned as it is, so a second call (a regrade) or a cell left at "removed": false keeps its record. A root reached
    through a symbolic link is never followed, and a root that cannot be removed keeps its error and is printed; the
    mark then stays false and the verdict stands."""
    path = out / 'pruned.json'
    if path.is_file():
        return json.loads(path.read_text())
    roots = {}
    for root in PRUNED:
        target = out / root
        if not os.path.lexists(target):
            continue
        if target.resolve() != out.resolve() / root:
            roots[root] = dict(error='not removed: reached through a symbolic link')
            continue
        files = size = 0
        links = {}
        for folder, dirs, names in os.walk(target):
            for name in names + [d for d in dirs if os.path.islink(os.path.join(folder, d))]:
                item = os.path.join(folder, name)
                files, size = files + 1, size + os.lstat(item).st_size
                if os.path.islink(item):
                    links[os.path.relpath(item, out)] = os.readlink(item)
        roots[root] = dict(files=files, bytes=size, symlinks=links)
    record = dict(removed=False, roots=roots)
    replace(path, record)
    for root, entry in roots.items():
        if 'error' not in entry:
            try:
                shutil.rmtree(out / root)
            except OSError as exc:
                entry['error'] = f'not removed: {exc}'
        if 'error' in entry:
            print(f'{out.name}: {root} {entry["error"]}', file=sys.stderr)
    record['removed'] = not any('error' in entry for entry in roots.values())
    replace(path, record)
    return record


if __name__ == '__main__':
    sys.exit(regrade(*sys.argv[2:4]) if sys.argv[1] == '--regrade' else run(*sys.argv[1:6]))
