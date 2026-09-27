"""0225 registered replay: the 7 archived VERIFY rounds x 2 judges through the product's verify-judges.py.

  replay.py prepare   materialize every round in a disposable copy, pre-flight it (the product's stub judges run in a
                      separate dry copy), inventory the archives and write the manifest; no model call
  replay.py run       one verify-judges.py call per round in the frozen order, then the after-inventory
  replay.py score     extract each round's pass-rule facts into score.json; no model call

Contract: autoresearch/iterations/0225-resolve-cost-cuts.md "Replay mechanics"; design .devlyn/0225/replay-design.md.
The driver only reads the archives: every copy is fetched from them, and no command runs inside them.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import signal
import stat
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SHARED = REPO / 'config/skills/_shared'
SCREEN = REPO / '.devlyn/0224/screen-out'
ROOT = Path.home() / '.local/share/nx01/0225-replay'  # no CLAUDE.md/AGENTS.md in any ancestor
FROZEN = HERE / 'replay-manifest.json'
CLAUDE = Path.home() / '.local/share/claude/versions/2.1.281'  # the archived judges' Claude Code
CODEX = Path(shutil.which('codex'))
VERIFY_BODY = 'config/skills/devlyn:resolve/references/phases/verify.md'
ROLE = runpy.run_path(str(SHARED / 'role-config.py'))
RENDER = runpy.run_path(str(SHARED / 'phase-prompt-render.py'))
MERGE = runpy.run_path(str(SHARED / 'verify-merge-findings.py'))
EVIDENCE = runpy.run_path(str(SHARED / 'process-evidence.py'))
JUDGES = runpy.run_path(str(SHARED / 'verify-judges.py'))
PARSER = runpy.run_path(str(SHARED / 'judge-output-parser.py'))
# The archived Claude-owner judges inherited the owner's user-settings env (home/.claude/settings.json, 3.2.1 installer).
OWNER_ENV = {'CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING': '1', 'ENABLE_PROMPT_CACHING_1H': 'true'}
CELLS = {
    's6-04': dict(cell='s6-04-D4-F-claude', run_id='rs-20260925T165548Z-c9478a93b257', branch='devlyn/lazyfile-fifo',
                  heads=('69c1546aa744ead3c2558f2ceae3abbc10682d18', 'f17ef40de6af85c36ae5f572d876aa0f44d0d629',
                         'df453187cc37de78a21fb1c3444cee711f97bf26'),
                  reasons=['pair.default'], owner_env=OWNER_ENV),
    's6-16': dict(cell='s6-16-I0185-F-claude', run_id='rs-20260926T020744Z-29aa3488b235', branch='main',
                  heads=('ef83e44a3a8c4b01f2daf21c153b223ffe44a065', '85d8a902af387a742a5da9e03bed99f039d280fd'),
                  reasons=['pair.default', 'spec.complexity.high', 'risk.high'], owner_env=OWNER_ENV),
    's6-07': dict(cell='s6-07-I0185-F-codex', run_id='rs-20260925T235205Z-6370c90271d2', branch='main',
                  heads=('709f1fb3f9baa0cbaaa43bb67b176780586f674c', 'ff5517bdbb7dd481fb5968b9828c8268fa17a57b'),
                  reasons=['pair.default', 'complexity.large', 'spec.complexity.high', 'risk.high'], owner_env={}),
}
ORDER = [f'{key}-r{n}' for key in CELLS for n in range(len(CELLS[key]['heads']))]
KEPT = ('version', 'run_id', 'engine', 'engine_source', 'mode', 'complexity', 'pair_verify', 'role_no_pair',
        'role_config_input', 'base_ref', 'source', 'risk_profile', 'role_resolution', 'criteria', 'bypasses', 'started_at')
INPUTS = ('criteria.generated.md', 'goal.raw.txt', 'plan.md', 'spec-verify.json')  # from the archived run dir
# The archived judges ran in a container whose HOME held only its CODEX_HOME. On the host, HOME would add ~/.agents
# skills and shell dotfiles to the Codex seat, so its CLI runs with HOME set to the round's own home. Claude keeps the
# real HOME (its login lives in the user keychain); --setting-sources project already keeps user config out.
CODEX_SHIM = f'''#!/bin/sh
case "$CODEX_HOME" in */.codex) ;; *) echo "replay codex shim: CODEX_HOME must end in /.codex" >&2; exit 97 ;; esac
HOME="${{CODEX_HOME%/.codex}}" exec {CODEX} "$@"
'''
# Harness blockers whose cause is the judges' input, not the judges or the product (0225 "0 input BLOCKEDs").
INPUT_BLOCKERS = ('verify-input-invalid', 'verify-mechanical-evidence-invalid', 'verify-merge-required-source-missing',
                  'verify.state.', 'verify-pair-trigger', 'verify-dispatch-invalid', 'verify-state-changed',
                  'verify-not-open', 'verify-already-supervised')


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def parse(rid):
    key, _, n = rid.rpartition('-r')
    return key, int(n)


def archived_run(key):
    cell = CELLS[key]
    return SCREEN / cell['cell'] / 'work/.devlyn/runs' / cell['run_id']


def minimal_env(path):
    env = {name: os.environ[name] for name in ('HOME', 'USER', 'LOGNAME', 'SHELL', 'TMPDIR', 'LANG') if name in os.environ}
    return {**env, 'PATH': os.pathsep.join(map(str, path)), 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1',
            'DISABLE_AUTOUPDATER': '1'}


def replay_env(rid, work):
    """What a real judge sees: an allowlist, never the operator's shell (it carries CLAUDECODE, effort and session vars)."""
    env = minimal_env([ROOT / 'bin', CODEX.parent, '/opt/homebrew/bin', '/usr/bin', '/bin', '/usr/sbin', '/sbin'])
    return {**env, 'CODEX_HOME': str(ROOT / 'homes' / rid / '.codex'), 'PYTHONPATH': str(work / 'src'),
            **CELLS[parse(rid)[0]]['owner_env']}


def git(cwd, *args):
    env = {**minimal_env(['/opt/homebrew/bin', '/usr/bin', '/bin']), 'GIT_OPTIONAL_LOCKS': '0'}
    return subprocess.run(['git', *args], cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout.strip()


@contextmanager
def environment(env, cwd):
    """Product helpers read PATH/CODEX_HOME from the process and resolve criteria_path against cwd."""
    saved, previous = dict(os.environ), Path.cwd()
    os.environ.clear()
    os.environ.update(env)
    os.chdir(cwd)
    try:
        yield
    finally:
        os.chdir(previous)
        os.environ.clear()
        os.environ.update(saved)


def product():
    """Every file a VERIFY call can execute or render: all of _shared (scripts, adapters) plus the rubric."""
    paths = [p for p in SHARED.rglob('*') if p.is_file() and '__pycache__' not in p.parts] + [REPO / VERIFY_BODY]
    return {str(p.relative_to(REPO)): sha256(p.read_bytes()) for p in sorted(paths)}


def runtime():
    """The judge CLIs and model metadata exactly as the judges resolve them (replay PATH, shims, per-round homes)."""
    rid = ORDER[0]
    with environment(replay_env(rid, ROOT / 'rounds' / rid), ROOT):
        versions = {engine: subprocess.run([engine, '--version'], capture_output=True, text=True).stdout.strip()
                    for engine in ('claude', 'codex')}
        resolved = {name: str(Path(shutil.which(name)).resolve()) for name in ('claude', 'codex', 'bash', 'python3', 'git')}
    return dict(versions=versions, resolved=resolved, python=sys.executable, codex=str(CODEX.resolve()),
                claude_sha256=sha256(CLAUDE.read_bytes()), codex_shim_sha256=sha256((ROOT / 'bin/codex').read_bytes()))


def inventory():
    """Sorted [relative_path, bytes, sha256] for every file under the 0224 screen output (symlinks by their text)."""
    rows = []
    for folder, dirs, files in os.walk(SCREEN):
        dirs.sort()
        for name in files + [d for d in dirs if (Path(folder) / d).is_symlink()]:
            path = Path(folder) / name
            raw = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
            rows.append([str(path.relative_to(SCREEN)), len(raw), sha256(raw)])
    return sorted(rows)


def open_state(archived, n, head):
    """The round-n state as do_spawn opens VERIFY, from bootstrap-time fields only: later rounds' durability receipts,
    judge history and process evidence stay out (the product binds the VERIFY carrier at merge, not before)."""
    verify = archived['phases']['verify']
    span = verify if verify['round'] == n else next(h for h in verify['history'] if h['round'] == n)
    cleanup = archived['phases']['cleanup']
    closed = cleanup if cleanup['round'] == n else next(h for h in cleanup['history'] if h['round'] == n)
    if closed['post_sha'] != head or span['round'] != n:
        raise SystemExit(f'round {n}: archived CLEANUP post_sha {closed["post_sha"]} is not {head}')
    state = {key: archived[key] for key in KEPT}
    state['verify'] = {'coverage_failed': False, 'pair_trigger': None}
    surface = {k: v for k, v in archived['phases']['surface_close'].items() if k != 'durability'}
    state['phases'] = {**({'surface_close': surface} if surface else {}), 'verify': {
        'engine': verify['engine'], 'model_requested': verify['model_requested'], 'model_effective': None,
        'round': n, 'started_at': span['started_at'], 'completed_at': None, 'duration_ms': None,
        'triggered_by': None if n == 0 else 'verify', 'verdict': None,
        'artifacts': {'findings_file': None, 'log_file': None}, 'sub_verdicts': None, 'judge_durations_ms': None}}
    return state


def materialize(rid, work):
    """Fetch only the history reachable from the round HEAD into a fresh repo, then write the round's .devlyn inputs."""
    key, n = parse(rid)
    cell, run = CELLS[key], archived_run(key)
    archived = load(run / 'pipeline.state.json')
    head, base = cell['heads'][n], archived['base_ref']['sha']
    work.mkdir(parents=True)
    git(work, 'init', '-q')
    refs = [f'{head}:refs/heads/{cell["branch"]}'] + ([f'{base}:refs/heads/main'] if cell['branch'] != 'main' else [])
    # No reflog, remote or FETCH_HEAD: nothing in the copy may point a judge back at the archive.
    git(work, '-c', 'core.logAllRefUpdates=false', 'fetch', '-q', '--no-tags', '--update-shallow',
        '--upload-pack=git -c uploadpack.allowAnySHA1InWant=true upload-pack', str(SCREEN / cell['cell'] / 'work'), *refs)
    git(work, 'symbolic-ref', 'HEAD', f'refs/heads/{cell["branch"]}')
    git(work, '-c', 'core.logAllRefUpdates=false', 'reset', '-q', '--hard')
    for name in ('FETCH_HEAD', 'ORIG_HEAD'):
        (work / '.git' / name).unlink(missing_ok=True)
    assert git(work, 'rev-parse', 'HEAD') == head and git(work, 'rev-parse', base + '^{commit}') == base
    assert git(work, 'status', '--porcelain', '--untracked-files=all') == '', 'copy is not a clean checkout'
    later = [sha for sha in cell['heads'][n + 1:] if subprocess.run(
        ['git', 'cat-file', '-e', sha + '^{commit}'], cwd=work, capture_output=True).returncode == 0]
    assert not later, f'later-round commits reachable in the copy: {later}'

    devlyn = work / '.devlyn'
    devlyn.mkdir()
    for name in INPUTS:
        shutil.copyfile(run / name, devlyn / name)
    for name in ('caller.json', 'engines.json'):
        shutil.copyfile(run.parents[1] / name, devlyn / name)
    (devlyn / 'verify-mechanical.findings.jsonl').write_bytes(b'')  # 0 B in every archived round
    evidence = f'process-evidence/{cell["run_id"]}/verify/round-{n}'
    shutil.copytree(run / evidence, devlyn / evidence)
    source = archived['source']
    assert sha256((devlyn / 'criteria.generated.md').read_bytes()) == source['criteria_sha256']
    assert sha256((devlyn / 'goal.raw.txt').read_bytes()) == source['goal_sha256']
    assert sha256((devlyn / 'plan.md').read_bytes()) == archived['phases']['plan']['output_sha256']
    assert sha256((devlyn / 'engines.json').read_bytes()) == archived['role_resolution']['inputs'][0]['sha256']
    state = open_state(archived, n, head)
    (devlyn / 'pipeline.state.json').write_bytes(ROLE['encoded'](state))

    carrier = EVIDENCE['validate_manifest'](work, f'.devlyn/{evidence}/manifest.json', cell['run_id'], 'verify', n,
                                            None, require_expectations=False)
    bound = [c for c in archived['process_evidence'] if c['phase'] == 'verify' and c['round'] == n]
    assert bound == [carrier], f'{rid}: rebuilt carrier differs from the archived state-bound carrier'
    results = json.dumps({'commands': EVIDENCE['bound_carrier_summary_commands'](work, carrier),
                          'process_evidence': carrier}, indent=2) + '\n'
    (devlyn / 'spec-verify.results.json').write_text(results, encoding='utf-8')
    final = archived['phases']['verify']['round'] == n
    if final:  # only each cell's final round kept its results file
        assert json.loads(results) == load(run / 'spec-verify.results.json'), f'{rid}: rebuilt results differ'
    return state, dict(results_sha256=sha256(results.encode()),
                       results_bytes_equal_archive=final and results.encode() == (run / 'spec-verify.results.json').read_bytes())


def preflight(rid, work, state):
    """Everything verify-judges.py derives before launching, computed here from the same product code; no model call."""
    key, n = parse(rid)
    devlyn = work / '.devlyn'
    with environment(replay_env(rid, work), work):
        resolution = ROLE['snapshot'](state)
        assert resolution['sha256'] == state['role_resolution']['sha256']
        _findings, mechanical = MERGE['mechanical_source'](devlyn)
        assert mechanical == 'PASS', f'{rid}: MECHANICAL {mechanical}'
        reasons = MERGE['outcome_independent_reasons'](devlyn)
        assert reasons == CELLS[key]['reasons'], f'{rid}: pair-trigger reasons {reasons}'
        snapshot = RENDER['build_verify_snapshot'](devlyn, state)
        header, _, rest = snapshot.partition(b'\n')
        label, _, length = header.partition(b' ')
        metadata = json.loads(rest[:int(length)])
        assert label == b'metadata' and metadata['head_sha'] == CELLS[key]['heads'][n] and metadata['round'] == n
        seats = {}
        for role in JUDGES['ROLES']:
            entry = JUDGES['decide'](state, resolution, role, False)
            assert entry['decision'] == 'dispatch', f'{rid} {role}: {entry}'
            prompt = RENDER['render_verify'](role, entry['engine'], snapshot)
            argv, extra = JUDGES['launch_argv'](devlyn, entry)
            seats[role] = dict(engine=entry['engine'], model=entry['model_requested'], effort=entry['effort'],
                               requested_effort=resolution['roles'][role]['effort_requested'],
                               channel=entry['channel'], stem=entry['stem'], prompt_sha256=sha256(prompt),
                               argv_sha256=sha256(ROLE['encoded'](argv)), environment=extra)
    return dict(snapshot_sha256=sha256(snapshot), snapshot_bytes=len(snapshot), reasons=reasons, seats=seats)


def dry_run(rid):
    """The whole verify-judges.py path on an identical dry copy with the product's own stub judges (STUB_BARRIER makes
    a serial start fail); proves every input is accepted before any real call. Real copies are never stub-touched."""
    key, n = parse(rid)
    dry = ROOT / 'dry' / rid
    materialize(rid, dry)
    stubs = ROOT / 'dry/stubs' / rid
    (stubs / 'barrier').mkdir(parents=True)
    env = {**minimal_env([ROOT / 'dry/bin', '/opt/homebrew/bin', '/usr/bin', '/bin']), 'CODEX_HOME': str(ROOT / 'dry/codex-home'),
           'STUB_DIR': str(stubs), 'STUB_BARRIER': '1'}
    proc = subprocess.run([sys.executable, str(SHARED / 'verify-judges.py'), '--devlyn-dir', str(dry / '.devlyn')],
                          cwd=dry, env=env, capture_output=True, text=True)
    summary = json.loads(proc.stdout) if proc.stdout.strip() else None
    devlyn = dry / '.devlyn'
    carriers = [load(devlyn / f'{engine}-judge.r{n}.prompt.transport.json') for engine in ('claude', 'codex')]
    record = load(devlyn / f'verify-judge.r{n}.dispatch.json')
    ok = (proc.returncode == 0 and summary and summary['verdict'] == 'PASS'
          and summary['source_verdicts'] == {'mechanical': 'PASS', 'judge': 'PASS', 'pair_judge': 'PASS'}
          and all(c['outcome'] == 'exited' and c['exit_code'] == 0 for c in carriers)
          and min(c['ended_at'] for c in carriers) > max(c['started_at'] for c in carriers)
          and record['pair_trigger'] == {'eligible': True, 'reasons': CELLS[key]['reasons'], 'skipped_reason': None})
    if not ok:
        raise SystemExit(f'{rid}: dry run failed rc={proc.returncode}\n{proc.stdout}\n{proc.stderr[-4000:]}')
    return dict(verdict=summary['verdict'], source_verdicts=summary['source_verdicts'],
                carriers=[{k: c[k] for k in ('outcome', 'started_at', 'ended_at')} for c in carriers])


def prepare():
    if ROOT.exists():
        raise SystemExit(f'{ROOT} exists; prepare runs once, on a fresh root')
    frozen_product = product()
    assert subprocess.run(['git', 'diff', '--quiet', 'origin/main', '--', 'config/skills'], cwd=REPO).returncode == 0, \
        'the product under test must be main as merged'
    before = inventory()
    ROOT.mkdir(parents=True)
    dump(ROOT / 'inventory-before.json', before)
    (ROOT / 'bin').mkdir()
    (ROOT / 'bin/claude').symlink_to(CLAUDE)
    (ROOT / 'bin/codex').write_text(CODEX_SHIM, encoding='utf-8')
    (ROOT / 'bin/codex').chmod(0o500)
    for rid in ORDER:  # the round's own HOME; auth.json is added only for its call (see call())
        (ROOT / 'homes' / rid / '.codex').mkdir(parents=True)
        shutil.copyfile(Path.home() / '.codex/models_cache.json', ROOT / 'homes' / rid / '.codex/models_cache.json')
    (ROOT / 'dry/bin').mkdir(parents=True)
    for engine in ('claude', 'codex'):
        (ROOT / 'dry/bin' / engine).write_text(JUDGES['STUB'], encoding='utf-8')
        (ROOT / 'dry/bin' / engine).chmod(0o755)
    (ROOT / 'dry/codex-home').mkdir()
    dump(ROOT / 'dry/codex-home/models_cache.json', {'client_version': '9.9.9', 'models': [
        {'slug': 'gpt-6-astra', 'supported_reasoning_levels': [{'effort': 'medium'}, {'effort': 'high'}]}]})
    rounds = []
    for rid in ORDER:
        key, n = parse(rid)
        work = ROOT / 'rounds' / rid
        state, facts = materialize(rid, work)
        rounds.append(dict(id=rid, cell=CELLS[key]['cell'], run_id=CELLS[key]['run_id'], round=n,
                           base=state['base_ref']['sha'], head=CELLS[key]['heads'][n],
                           verify_started_at=state['phases']['verify']['started_at'], work=str(work),
                           resolution_sha256=state['role_resolution']['sha256'], env=replay_env(rid, work),
                           models_cache_sha256=sha256((ROOT / 'homes' / rid / '.codex/models_cache.json').read_bytes()), **facts, **preflight(rid, work, state), dry_run=dry_run(rid)))
        print(f'[replay] prepared {rid}', file=sys.stderr, flush=True)
    manifest = dict(schema=1, contract='autoresearch/iterations/0225-resolve-cost-cuts.md#replay-mechanics',
                    repo_head=git(REPO, 'rev-parse', 'HEAD'), product_commit=git(REPO, 'rev-parse', 'origin/main'),
                    product_sha256=frozen_product, driver_sha256=sha256(Path(__file__).read_bytes()), order=ORDER,
                    runtime=runtime(), git=git(REPO, '--version'),
                    codex_auth_last_refresh=load(Path.home() / '.codex/auth.json').get('last_refresh'),
                    inventory_before=dict(files=len(before), sha256=sha256((ROOT / 'inventory-before.json').read_bytes())),
                    rounds=rounds)
    dump(ROOT / 'manifest.json', manifest)
    print(f'[replay] manifest sha256 {sha256((ROOT / "manifest.json").read_bytes())}', file=sys.stderr)


def frozen(calls=True):
    """The manifest, only once it is committed byte for byte and the product and driver (and, before calls, the judge
    runtime) still match it. A judge may refresh its own round's model cache, so that is checked per call instead."""
    manifest = load(ROOT / 'manifest.json')
    committed = subprocess.run(['git', 'show', f'HEAD:{FROZEN.relative_to(REPO)}'], cwd=REPO, capture_output=True)
    if committed.returncode or committed.stdout != (ROOT / 'manifest.json').read_bytes():
        raise SystemExit('the manifest is not frozen: commit it byte for byte first')
    if product() != manifest['product_sha256'] or manifest['driver_sha256'] != sha256(Path(__file__).read_bytes()):
        raise SystemExit('the product or the driver changed since freeze')
    if calls and runtime() != manifest['runtime']:
        raise SystemExit(f'judge runtime changed since freeze: {runtime()}')
    if sha256((ROOT / 'inventory-before.json').read_bytes()) != manifest['inventory_before']['sha256']:
        raise SystemExit('the archive baseline inventory changed since freeze')
    return manifest


@contextmanager
def sealed(rid):
    """While a round runs, nothing under ROOT is readable but that round's copy and home and the CLI shims: no other
    round's copy (later repairs, earlier judge output), no manifest, no dry run. Modes are restored on every exit."""
    hidden = [p for p in ROOT.iterdir() if p.name not in ('rounds', 'homes', 'bin')]
    hidden += [p for folder in ('rounds', 'homes') for p in (ROOT / folder).iterdir() if p.name != rid]
    search_only = [ROOT, ROOT / 'rounds', ROOT / 'homes', ROOT / 'bin']
    modes = {p: stat.S_IMODE(p.lstat().st_mode) for p in hidden + search_only}
    try:
        for path in hidden:
            path.chmod(0)
        for path in search_only:
            path.chmod(0o100)
        yield
    finally:
        for path in search_only + hidden:
            path.chmod(modes[path])


CHILD, STOP = [], []


def forward(signum, _frame):
    """Never raises: a stop is recorded, reaches a running supervisor as the SIGTERM it handles (it tears both judges
    down and still merges), and ends the replay at the next safe point, so no cleanup is ever cut short."""
    STOP.append(signum)
    if CHILD and CHILD[0].poll() is None:
        CHILD[0].send_signal(signal.SIGTERM)


def call(rid, entry):
    """One real round: re-derive every frozen per-round value from the untouched copy, then the product's VERIFY command."""
    work = Path(entry['work'])
    devlyn = work / '.devlyn'
    leftovers = sorted(p.name for p in devlyn.iterdir() if re.match(r'(claude|codex)-judge\.|verify-judge\.|verify-merge', p.name))
    if leftovers:
        raise SystemExit(f'{rid}: copy already used: {leftovers}')
    state = ROLE['loads']((devlyn / 'pipeline.state.json').read_bytes())
    env = replay_env(rid, work)
    checks = preflight(rid, work, state)
    cache = sha256((ROOT / 'homes' / rid / '.codex/models_cache.json').read_bytes())
    if checks != {k: entry[k] for k in checks} or env != entry['env'] or cache != entry['models_cache_sha256'] \
            or state['role_resolution']['sha256'] != entry['resolution_sha256']:
        raise SystemExit(f'{rid}: inputs, dispatch or environment differ from the frozen manifest')
    auth = ROOT / 'homes' / rid / '.codex/auth.json'
    started, clock, code, child = now(), time.monotonic(), None, None
    stdout = stderr = b''
    try:
        shutil.copyfile(Path.home() / '.codex/auth.json', auth)
        auth.chmod(0o400)  # never refreshed or rewritten here (the 0222 apparatus mounted it read-only); removed after
        with sealed(rid):
            if not STOP:
                print(f'[replay] {rid} started {started}', file=sys.stderr, flush=True)
                # Its own session: a signal to the operator's group reaches the supervisor only as the SIGTERM
                # forward() sends, which it handles (it does not handle SIGHUP, and its judges have their own sessions).
                child = subprocess.Popen([sys.executable, str(SHARED / 'verify-judges.py'), '--devlyn-dir', str(devlyn)],
                                         cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, start_new_session=True)
                CHILD.append(child)
                if STOP:  # a stop that landed while it was being launched, before forward() could see it
                    child.send_signal(signal.SIGTERM)
                stdout, stderr = child.communicate()
                code = child.returncode
    finally:
        CHILD.clear()
        auth.unlink(missing_ok=True)
        if child is not None:  # once launched, the round is retained as run (never rerun), whatever happened
            (work.parent / f'{rid}.driver.stdout').write_bytes(stdout)
            (work.parent / f'{rid}.driver.stderr').write_bytes(stderr)
            dump(work.parent / f'{rid}.driver.json', dict(exit_code=code, started_at=started, ended_at=now(),
                                                           wall_ms=round((time.monotonic() - clock) * 1000),
                                                           stop_signals=list(STOP)))
    print(f'[replay] {rid} exit={code} {stdout.decode(errors="replace").strip()}', file=sys.stderr, flush=True)


def integrity():
    after = inventory()
    dump(ROOT / 'inventory-after.json', after)
    same = after == load(ROOT / 'inventory-before.json')
    dump(ROOT / 'integrity.json', dict(checked_at=now(), files=len(after), unchanged=same))
    if not same:
        raise SystemExit('ARCHIVE CHANGED: diff inventory-before.json against inventory-after.json')


def run():
    """Each round runs once; a failed round is retained as is (the registration's only repeat is the whole replay).
    Every frozen value is rechecked before each round, and a stop signal ends the replay between rounds."""
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, forward)
    try:
        for rid in ORDER:
            if STOP:
                raise SystemExit(128 + STOP[0])
            entry = next(e for e in frozen()['rounds'] if e['id'] == rid)
            if not (ROOT / 'rounds' / f'{rid}.driver.json').exists():
                call(rid, entry)
    finally:
        integrity()


def score():
    manifest = frozen(calls=False)
    if not (ROOT / 'integrity.json').exists() or not load(ROOT / 'integrity.json')['unchanged'] \
            or inventory() != load(ROOT / 'inventory-before.json'):
        raise SystemExit('no score without an unchanged archive: run `run` to completion first')
    rows = [facts(entry) for entry in manifest['rounds']]
    dump(ROOT / 'score.json', dict(scored_at=now(), archive_unchanged=True, rounds=rows))
    for row in rows:
        print(f"{row['id']}: {row['verdict']} {row['sub_verdicts']} overlap={row['overlap']} harness={len(row['harness_rows'])} "
              f"binding={[(b['severity'], b['seat'], b['rule_id']) for b in row['binding']]} outside={row['outside_paths']}")


def facts(entry):
    """One round's pass-rule facts from the files the product wrote; judgments (same defect, input cause) stay root's.
    A round that stopped early still scores: missing product files are reported, never skipped."""
    rid = entry['id']
    key, n = parse(rid)
    work = Path(entry['work'])
    devlyn = work / '.devlyn'
    def read(path, default):
        try:
            return load(path)
        except (OSError, ValueError):
            return default
    driver = read(work.parent / f'{rid}.driver.json', {})
    record = read(devlyn / f'verify-judge.r{n}.dispatch.json', {})
    state = read(devlyn / 'pipeline.state.json', {}).get('phases', {}).get('verify', {})
    carriers = {e: read(p, {}) for e in ('claude', 'codex') if (p := devlyn / f'{e}-judge.r{n}.prompt.transport.json').is_file()}
    merged_path = devlyn / 'verify-merged.findings.jsonl'
    merged = [json.loads(line) for line in merged_path.read_text().splitlines() if line.strip()] if merged_path.is_file() else []
    text = lambda row: ' '.join(str(row.get(k, '')) for k in ('id', 'rule_id', 'message'))
    # Origin comes from the output of each seat the merge authenticated (role evidence retained), parsed with the
    # product's own parser: a finding's own fields ("source", "id") are judge-controlled and prove nothing.
    authenticated = {}
    for role in state.get('role_evidence') or {}:
        stem = f'{entry["seats"][role]["engine"]}-judge.r{n}'
        try:
            authenticated[role] = PARSER['collect_judge'](devlyn / (stem + '.stdout'))
        except (SystemExit, OSError, UnicodeError, ValueError) as exc:
            authenticated[role] = ([], {'verdict': None, 'error': str(exc)})
    binding = [{'seat': role, **{k: row.get(k) for k in ('id', 'rule_id', 'severity', 'file', 'line', 'message')}}
               for role, (found, _summary) in authenticated.items() for row in found
               if str(row.get('severity', '')).upper() in ('HIGH', 'CRITICAL')]
    # Every other merged row (harness blockers, a failed or timed-out seat's rows): root classifies each by its cause,
    # since an input BLOCKED can hide behind a wrapper id.
    canon = lambda row: json.dumps({k: v for k, v in row.items() if k != 'source'}, sort_keys=True)
    seat_rows = {canon(row) for found, _summary in authenticated.values() for row in found}
    harness = [{k: row.get(k) for k in ('id', 'rule_id', 'source', 'message')} for row in merged if canon(row) not in seat_rows]
    # Early refusals (verify-not-open, verify-already-supervised, verify-state-changed) never reach the merged file.
    stops = [line for name in (f'{rid}.driver.stdout', f'{rid}.driver.stderr') if (work.parent / name).is_file()
             for line in (work.parent / name).read_text(errors='replace').splitlines() if 'BLOCKED' in line]
    usage = {'claude': dict(status='UNKNOWN', reason='no Claude result envelope')}
    output = devlyn / f'claude-judge.r{n}.output.json'
    envelope = read(output, None) if output.is_file() and output.stat().st_size else None
    if not isinstance(envelope, dict) and output.is_file() and output.stat().st_size:
        usage['claude'] = dict(status='UNKNOWN', reason='Claude capture is not a JSON result envelope')
    if isinstance(envelope, dict):
        counters = ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens')
        counted = all(isinstance((envelope.get('usage') or {}).get(k), int) for k in counters)
        usage['claude'] = dict(status='COMPLETE' if counted else 'UNKNOWN', usage=envelope.get('usage'),
                               model_usage=envelope.get('modelUsage'), session_id=envelope.get('session_id'))
    codex_log = devlyn / f'codex-judge.r{n}.stderr'
    tokens = re.findall(rb'tokens used\n([\d,]+)', codex_log.read_bytes()) if codex_log.is_file() else []
    usage['codex'] = dict(status='PARTIAL' if tokens else 'UNKNOWN', output_tokens='UNKNOWN',
                          total_tokens=int(tokens[-1].replace(b',', b'')) if tokens else None)
    # What the judges authored or ran (argv and carriers name the product scripts by design): Codex's log and output,
    # Claude's result and its session transcript (retained here). Flag any path under the user's home outside this
    # round's copy and home, and any other round's id, so a read beyond the copy cannot pass silently.
    authored = [codex_log, devlyn / f'codex-judge.r{n}.stdout', output]
    if usage['claude'].get('session_id'):
        found = list((Path.home() / '.claude/projects').glob(f'*/{usage["claude"]["session_id"]}.jsonl'))
        if len(found) == 1:
            (ROOT / 'transcripts').mkdir(exist_ok=True)
            authored.append(Path(shutil.copyfile(found[0], ROOT / 'transcripts' / f'{rid}.jsonl')))
        usage['claude']['transcript'] = len(found) == 1
    own = tuple(str(p) for p in (work, ROOT / 'homes' / rid, ROOT / 'bin'))
    others = '|'.join(re.escape(other) for other in ORDER if other != rid)
    pattern = re.compile(rf'{re.escape(str(Path.home()))}/[^\s"\'`)\]]*|\b(?:{others})\b'.encode())
    outside = sorted({m.group(0).decode(errors='replace') for p in authored if p.is_file()
                      for m in pattern.finditer(p.read_bytes())} - {''})
    outside = [path for path in outside if not path.startswith(own)]
    stamps = [c.get(k) for c in carriers.values() for k in ('started_at', 'ended_at')]
    return dict(
        id=rid, exit_code=driver.get('exit_code'), wall_ms=driver.get('wall_ms'),
        verdict=state.get('verdict'), sub_verdicts=state.get('sub_verdicts'), stops=stops,
        snapshot_matches=record.get('snapshot_sha256') == entry['snapshot_sha256'],
        resolution_matches=record.get('resolution_sha256') == entry['resolution_sha256'],
        argv_matches={role: (devlyn / (s['stem'] + '.argv.json')).is_file()
                      and sha256((devlyn / (s['stem'] + '.argv.json')).read_bytes()) == s['argv_sha256']
                      for role, s in entry['seats'].items()},
        decisions={role: (r['decision'], r['reason']) for role, r in record.get('roles', {}).items()},
        pair_trigger=record.get('pair_trigger'),
        carriers={e: {k: c.get(k) for k in ('outcome', 'exit_code', 'started_at', 'ended_at', 'elapsed_ms')}
                  for e, c in carriers.items()},
        overlap=len(stamps) == 4 and all(isinstance(s, str) for s in stamps)
        and min(c['ended_at'] for c in carriers.values()) > max(c['started_at'] for c in carriers.values()),
        effort={role: dict(requested=s['requested_effort'], dispatched=s['effort'],
                           observed=((state.get('role_evidence') or {}).get(role) or {}).get('effort_observed'))
                for role, s in entry['seats'].items()},
        models_observed={role: v.get('model_observed') for role, v in (state.get('role_evidence') or {}).items()},
        harness_rows=harness, input_flags=[text(row) for row in merged if any(tag in text(row) for tag in INPUT_BLOCKERS)]
        + [line for line in stops if any(tag in line for tag in INPUT_BLOCKERS)],
        seat_verdicts={role: summary.get('verdict') for role, (_found, summary) in authenticated.items()},
        binding=binding,
        usage=usage, outside_paths=outside)


if __name__ == '__main__':
    command = sys.argv[1:2] or ['']
    if command == ['prepare'] and len(sys.argv) == 2:
        prepare()
    elif command == ['run'] and len(sys.argv) == 2:
        run()
    elif command == ['score'] and len(sys.argv) == 2:
        score()
    else:
        raise SystemExit(__doc__)
