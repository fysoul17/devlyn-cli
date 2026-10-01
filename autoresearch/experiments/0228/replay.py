#!/usr/bin/env python3
"""0228 replay runner: development evidence, never a 0227 regrade (autoresearch/iterations/0228-verify-rubric-rescreen.md).

A replay reruns one 0227 round's VERIFY from its sealed pristine tars with one product arm (F = 0227's product,
G = the candidate's skills archive). `stage` copies this runner to /Users/Shared/devlyn-vr-0228-dev/runner/; every
other command runs from that copy, and while seals are applied nothing is read from a checkout.

  stage <G commit>                       (from the research checkout) G's skills archive, this runner, 0227's stubs
  plan                                   (from the research checkout) the fixed R2 and R3 replay orders
  product                                R1: G's product differs from 0227's only in verify.md
  stub                                   R1: stub replay of all 64 rounds under G: prompt frames, authentication, merge
  inventory <label>                      every readable location holding 0227 hidden material
  preflight <root-pid> <label>           processes working inside sealed repositories that are not root's own
  probe <root-pid> <label> <transcript>  R1 isolation probe (root makes one tool call while it waits)
  batch <plan> <root-pid> <label> [ack]  live replays, seals around each judge run; prints transport facts only
  classify <attempt>...                  (from the research checkout) 0227's frozen infra classifier, per attempt
  restore                                restore modes left in the seal journal (after an Unsafe stop)
  scan <attempt>...                      (from the research checkout) read scan of each attempt's seat tool inputs
"""
import hashlib
import io
import json
import os
import re
import runpy
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

sys.dont_write_bytecode = True
HOME = Path.home()
SHARED = Path('/Users/Shared')
SRC = SHARED / 'devlyn-vr-0227'
DEV = SHARED / 'devlyn-vr-0228-dev'
RESEARCH = HOME / '.local/share/nx01/core-continuation-20260912'
EVIDENCE = RESEARCH / 'autoresearch/experiments/0227'
PRODUCT = {'F': SRC / 'product', 'G': DEV / 'product-G'}
# Both live in the runner folder, the one 0228-root entry that stays writable while seals are applied.
JOURNAL = DEV / 'runner/seal-journal.json'
UNSAFE = DEV / 'runner/seal-unsafe.json'  # an owned process outlived SIGKILL; recovery needs `restore --confirmed`
RECORDS = DEV / 'records.jsonl'
CORPUS_COMMIT = '8c589f2ec82a4ada4bf99cd6e60c38615a036055'
CLAUDE_SHA256 = 'a922981f6f3b55a251ef9f9dbaa0621a5f99cbcb5ca67f8a797476ccfc83f626'  # 0227's pinned bin/claude
VERIFY_MD = 'config/skills/devlyn:resolve/references/phases/verify.md'
SEATS = ('claude-judge.r0', 'codex-judge.r0')
INVENTORY_MAX_AGE = 1800  # a batch's inventory must be fresh (registration: "immediately before every batch")
MIN_MARKER = 40
MANIFEST_COMMIT = '1a6f026e3abc294a9d3bac9b0c4ef7be56eb049f'  # main after the 0228 registration; holds 0227's manifest
PENDING = []  # received TERM/INT; handlers only record them, so cancellation happens at safe points, never mid-restore


def fail(message):
    raise SystemExit(f'0228 replay: {message}')


def require(condition, message):
    if not condition:
        fail(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    temporary.replace(path)


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def manifest(cache={}):
    """0227's committed manifest; the Shared copy must equal it byte for byte (read before any seal)."""
    if not cache:
        committed = git(RESEARCH, 'show', f'{MANIFEST_COMMIT}:autoresearch/experiments/0227/manifest.json').stdout
        require((SRC / 'manifest.json').read_bytes() == committed, 'the 0227 root manifest differs from the committed one')
        cache.update(json.loads(committed))
    return cache


def git(cwd, *args, check=True):
    env = {'PATH': '/opt/homebrew/bin:/usr/bin:/bin', 'HOME': str(HOME), 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_OPTIONAL_LOCKS': '0'}
    return subprocess.run(['git', '-C', str(cwd), *args], env=env, capture_output=True, check=check)


def files(root):
    return {str(p.relative_to(root)): sha256(p.read_bytes()) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def staged():
    require(Path(__file__).resolve().parent == DEV / 'runner', 'run the staged copy in /Users/Shared/devlyn-vr-0228-dev/runner')


# ---------------------------------------------------------------- staging and fixed orders (research checkout)

def stage(commit):
    """Create the replay root once; on later calls verify G's archive and refresh only the runner copy."""
    raw = git(RESEARCH, 'archive', '--format=tar', commit, 'config/skills').stdout
    with tempfile.TemporaryDirectory() as scratch:
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            archive.extractall(scratch, filter='data')
        expected = files(Path(scratch))
    if not PRODUCT['G'].exists():
        DEV.mkdir(exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            archive.extractall(PRODUCT['G'], filter='data')
        shutil.copytree(SRC / 'dry/bin', DEV / 'stub/bin')
        shutil.copytree(SRC / 'dry/codex-home', DEV / 'stub/codex-home')
    require(files(PRODUCT['G']) == expected, f'{PRODUCT["G"]} differs from the archive of {commit}')
    (DEV / 'runner').mkdir(exist_ok=True)
    shutil.copy2(__file__, DEV / 'runner/replay.py')
    entry = {'G': git(RESEARCH, 'rev-parse', commit).stdout.decode().strip(), 'staged_at': time.time(),
             'product_G_sha256': sha256(json.dumps(expected, sort_keys=True).encode()),
             'runner_sha256': sha256(Path(__file__).read_bytes())}
    with (DEV / 'stage.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(entry) + '\n')
    print(json.dumps(entry))


def plan():
    tokens = load(EVIDENCE / 'evidence/mapping.json')['tokens']
    key = {tok: tuple(value.split('|')) for tok, value in tokens.items()}  # task, variant, orientation, rep
    order = sorted(tokens, key=lambda tok: key[tok])
    j4_references = [tok for tok in order if key[tok][:2] == ('J4', 'reference')]
    codex_j4 = [tok for tok in j4_references if key[tok][2] == 'codex']
    require(len(j4_references) == 4 and len(codex_j4) == 2, 'J4 reference rounds')
    r2 = []
    for cycle in range(10):  # G and F interleaved in one session; F stops after its eighth cycle
        r2 += [{'arm': 'G', 'token': tok} for tok in j4_references]
        if cycle < 8:
            r2 += [{'arm': 'F', 'token': tok} for tok in codex_j4]
    extra = [tok for tok in order if key[tok][0] in ('J3', 'J4', 'P2', 'P3') and key[tok][1] == 'twin']
    require(len(extra) == 16, 'twin rounds for the extra replays')
    r3 = ([{'arm': 'G', 'token': tok} for tok in order if tok not in j4_references]
          + [{'arm': 'G', 'token': tok} for _ in range(2) for tok in extra])
    require(len(r2) == 56 and len(r3) == 92, 'replay counts')
    return {'r2': r2, 'r3': r3}


# ---------------------------------------------------------------- attempts

def next_attempt(arm, tok):
    folder = DEV / arm / tok
    taken = [int(p.name.split('-')[1]) for p in folder.glob('rep-*')] if folder.is_dir() else []
    return folder / f'rep-{max(taken, default=0) + 1}'


def check_tars(tokens):
    rows = {r['token']: r for r in manifest()['rounds']}
    for tok in sorted(set(tokens)):
        for suffix in ('.tar', '.home.tar'):
            tar = SRC / 'private/pristine' / f'{tok}{suffix}'
            require(sha256(tar.read_bytes()) == rows[tok]['pristine'][suffix], f'{tok}{suffix}: digest differs from the manifest')


def prepare(base, tok, *, stub=False):
    """Extract one round's pristine inputs into a never-reused folder; return its row, work tree and environment."""
    row = next(r for r in manifest()['rounds'] if r['token'] == tok)
    base.mkdir(parents=True)  # FileExistsError: an attempt folder is never reused
    check_tars([tok])
    for suffix, destination in (('.tar', base), ('.home.tar', base / 'homes')):
        with tarfile.open(SRC / 'private/pristine' / f'{tok}{suffix}') as archive:
            archive.extractall(destination, filter='fully_trusted')
    work = base / 'work'
    if row['repo'] == 'node-lru-cache':
        (work / 'node_modules').symlink_to(SRC / 'toolchains/node-lru-cache/node_modules', target_is_directory=True)
    env = {name: value.replace(row['work'], str(work)) for name, value in row['env'].items()}
    env['CODEX_HOME'] = str(base / 'homes' / tok / '.codex')
    if stub:
        env['PATH'] = env['PATH'].replace(str(SRC / 'bin'), str(DEV / 'stub/bin'), 1)
        shutil.copytree(DEV / 'stub/codex-home', base / 'stub-codex-home')
        env['CODEX_HOME'] = str(base / 'stub-codex-home')
        (base / 'stubs/barrier').mkdir(parents=True)
        env.update(STUB_DIR=str(base / 'stubs'), STUB_BARRIER='1')
    return row, work, env


class Unsafe(Exception):
    """An owned process outlived SIGKILL: seals and journal stay in place."""


def record_signal(signum, _frame):
    PENDING.append(signum)


def ps_table():
    proc = subprocess.run(['ps', '-axo', 'pid=,ppid=,stat=,lstart='], capture_output=True, text=True)
    if proc.returncode or not proc.stdout.strip():
        raise Unsafe(f'process inspection failed: ps rc={proc.returncode} {proc.stderr[-200:]}')
    table = {}
    for line in proc.stdout.splitlines():
        pid, ppid, state, started = line.split(None, 3)
        table[int(pid)] = (int(ppid), state, ' '.join(started.split()))
    return table


def cwd_inside(scope):
    proc = subprocess.run(['lsof', '-w', '-a', '-d', 'cwd', '-Fpn'], capture_output=True, text=True)
    if proc.returncode not in (0, 1) or not proc.stdout.strip():
        raise Unsafe(f'process inspection failed: lsof rc={proc.returncode} {proc.stderr[-200:]}')
    found, pid = set(), None
    for line in proc.stdout.splitlines():
        if line.startswith('p'):
            pid = int(line[1:])
        elif line.startswith('n') and under(Path(line[1:]), [scope]) and pid != os.getpid():
            found.add(pid)
    return found


def inside_bracketed(scope):
    """Processes whose cwd is inside the attempt, joined to identities only when a ps snapshot before and after the
    lsof snapshot agree on the pid's start time; anything else is ambiguous (it blocks quiescence, never signalled)."""
    before = ps_table()
    inside = cwd_inside(scope)
    after = ps_table()
    known, ambiguous = set(), set()
    for pid in inside:
        if pid in before and pid in after and before[pid][2] == after[pid][2] and 'Z' not in after[pid][1]:
            known.add((pid, after[pid][2]))
        else:
            ambiguous.add(pid)  # replaced, gone or a zombie: it may have left a descendant
    return known, ambiguous, after


def track(owned, scope):
    """Own every live descendant of an owned process (the child is owned from launch), and every process whose working
    directory is inside this attempt (cwd survives fork and session changes; nothing else works in an attempt folder).
    Identity is pid plus start time, so a reused pid is never adopted. Returns the ambiguous cwd observations."""
    known, ambiguous, table = inside_bracketed(scope)
    owned |= known
    changed = True
    while changed:
        changed = False
        parents = {pid for pid, started in owned if pid in table and table[pid][2] == started}
        for pid, (ppid, _state, started) in table.items():
            if ppid in parents and (pid, started) not in owned:
                owned.add((pid, started))
                changed = True
    return ambiguous


def survivors(owned, scope):
    """Owned processes alive in a ps snapshot, plus every process seen inside the attempt by a later bracketed lsof
    observation, even one that has exited since (it may have left a descendant). Empty is sound: an owned process dead
    at the ps snapshot cannot fork later, and a descendant left by anything keeps its inherited cwd inside the attempt
    unless it changed directory (the disclosed residual). Entries without a start time are never signalled; they keep
    the check from declaring quiescence until a later observation identifies their descendants."""
    pending = track(owned, scope)
    table = ps_table()
    alive = {(pid, started) for pid, started in owned
             if pid in table and table[pid][2] == started and 'Z' not in table[pid][1]}
    known, ambiguous, after = inside_bracketed(scope)
    owned |= known
    # Signal only identities the latest snapshot still confirms; the rest still block quiescence.
    confirmed = {(pid, started) for pid, started in alive
                 if pid in after and after[pid][2] == started and 'Z' not in after[pid][1]}
    unconfirmed = {(pid, None) for pid, _started in alive - confirmed}
    return confirmed | unconfirmed | known | {(pid, None) for pid in ambiguous | pending}


def reap(owned, scope):
    """Confirm every owned process has ended: a grace period, then TERM, then KILL; never return while one lives."""
    for sig, grace in ((None, 30), (signal.SIGTERM, 30), (signal.SIGKILL, 60)):
        for pid, started in survivors(owned, scope) if sig else ():
            if started is not None:
                try:
                    os.kill(pid, sig)
                except ProcessLookupError:
                    pass
        deadline = time.time() + grace
        while survivors(owned, scope) and time.time() < deadline:
            time.sleep(0.5)
        if not survivors(owned, scope):
            return
    raise Unsafe(f'owned processes survive SIGKILL: {sorted(survivors(owned, scope), key=str)}')


def run(argv, cwd, env, out, err, timeout, scope, stdin_path=None):
    """Run with stdin, stdout and stderr as regular files (the Codex wrapper refuses pipes, and a pipe write can block
    forever when a descendant holds it open). On timeout, a recorded signal or any
    error after launch, forward TERM to the child (verify-judges tears down its seat runners) and confirm the whole
    owned tree has ended before returning or re-raising; if that cannot be confirmed, raise Unsafe so the caller's
    seals stay in place."""
    owned, error = set(), None
    with open(stdin_path or os.devnull, 'rb') as stdin, open(out, 'wb') as stdout, open(err, 'wb') as stderr:
        child = subprocess.Popen(argv, cwd=cwd, env=env, stdin=stdin, stdout=stdout, stderr=stderr)
        try:
            table = ps_table()
            if child.pid in table and child.poll() is None:
                owned.add((child.pid, table[child.pid][2]))
            deadline = time.time() + timeout
            while child.poll() is None:
                track(owned, scope)
                if PENDING or time.time() > deadline:
                    error = f'signal {PENDING[0]}' if PENDING else 'runner-timeout'
                    break
                time.sleep(0.25)
            stop_child(child, owned, scope)
            reap(owned, scope)
        except Unsafe:
            raise
        except BaseException as exc:
            try:
                stop_child(child, owned, scope)
                reap(owned, scope)
            except BaseException as cleanup:
                raise Unsafe(f'cleanup after {exc!r} failed: {cleanup!r}') from exc
            raise
    return (child.returncode if error is None else None), error


def stop_child(child, owned, scope):
    if child.poll() is None:
        child.send_signal(signal.SIGTERM)
        stopped = time.time() + 120
        while child.poll() is None and time.time() < stopped:
            track(owned, scope)
            time.sleep(0.25)
        if child.poll() is None:
            track(owned, scope)
            child.kill()
    child.wait()


def judge(arm, work, env, base):
    argv = [sys.executable, str(PRODUCT[arm] / 'config/skills/_shared/verify-judges.py'), '--devlyn-dir', str(work / '.devlyn')]
    return run(argv, work, env, base / 'judges.stdout', base / 'judges.stderr', 1800, base)


def claude_project(work):
    return HOME / '.claude/projects' / ('-' + str(work).strip('/').replace('/', '-'))


def move_claude_project(work, base):
    project = claude_project(work)
    if project.is_dir():
        shutil.move(str(project), str(base / 'claude-project'))
    return (base / 'claude-project').is_dir()


def transport(work):
    facts = []
    for stem in SEATS:
        path = work / '.devlyn' / f'{stem}.prompt.transport.json'
        record = load(path) if path.is_file() else {}
        facts.append({'seat': stem, 'outcome': record.get('outcome'), 'exit_code': record.get('exit_code'),
                      'elapsed_ms': record.get('elapsed_ms')})
    return facts


# ---------------------------------------------------------------- R1 product and stub replays

def product_check():
    f, g = files(PRODUCT['F']), files(PRODUCT['G'])
    require(set(f) == set(g), f'product file sets differ: {sorted(set(f) ^ set(g))}')
    differ = sorted(path for path in f if f[path] != g[path])
    require(differ == [VERIFY_MD], f'G differs from 0227 product in {differ}')
    print(json.dumps({'files': len(f), 'differ': differ}))


def frames(prompt, render={}):
    if not render:
        render.update(runpy.run_path(str(PRODUCT['G'] / 'config/skills/_shared/phase-prompt-render.py')))
    return render['prompt_frames'](prompt)


def subframes(snapshot):
    parts, offset = [], 0
    while offset < len(snapshot):
        end = snapshot.index(b'\n', offset)
        name, _, length = snapshot[offset:end].partition(b' ')
        start = end + 1
        stop = start + int(length)
        require(snapshot[stop:stop + 1] == b'\n', 'malformed snapshot sub-frame')
        parts.append((name, snapshot[start:stop]))
        offset = stop + 1
    return parts


def stub():
    handle_signals()
    rows = manifest()['rounds']
    rubric = (PRODUCT['G'] / VERIFY_MD).read_bytes()
    code = {name: runpy.run_path(str(PRODUCT['G'] / 'config/skills/_shared' / file)) for name, file in (
        ('role', 'role-config.py'), ('auth', 'judge-role-evidence.py'), ('judges', 'verify-judges.py'),
        ('parser', 'judge-output-parser.py'))}
    results = []
    for row in rows:
        tok = row['token']
        base = DEV / 'stub-runs' / tok
        _, work, env = prepare(base, tok, stub=True)
        code_, error = judge('G', work, env, base)
        require(not PENDING, 'stub replay stopped by a signal')
        require(code_ == 0, f"{tok}: stub replay rc={code_} {error}\n{(base / 'judges.stderr').read_text()[-3000:]}")
        summary = json.loads((base / 'judges.stdout').read_text())
        carriers = transport(work)
        require(summary['verdict'] == 'PASS' and summary['source_verdicts'] == {
            'mechanical': 'PASS', 'judge': 'PASS', 'pair_judge': 'PASS'}
            and all(c['outcome'] == 'exited' and c['exit_code'] == 0 for c in carriers),
            f'{tok}: stub merge contract failed: {summary} {carriers}')
        devlyn = work / '.devlyn'
        state = code['role']['loads']((devlyn / 'pipeline.state.json').read_bytes())
        saved, previous = dict(os.environ), Path.cwd()
        os.environ.clear()
        os.environ.update(env)
        os.chdir(work)
        try:
            for role in code['judges']['ROLES']:
                code['auth']['authenticate'](devlyn, state, role)
            for engine in ('claude', 'codex'):
                code['parser']['collect_judge'](devlyn / f'{engine}-judge.stdout')
        finally:
            os.chdir(previous)
            os.environ.clear()
            os.environ.update(saved)
        relocate = lambda raw: raw.replace(row['work'].encode(), str(work).encode())
        for seat in row['seats'].values():
            new = frames((devlyn / f"{seat['stem']}.prompt").read_bytes())
            old = frames((Path(row['work']) / '.devlyn' / f"{seat['stem']}.prompt").read_bytes())
            require(new['rubric'] == rubric, f"{tok} {seat['stem']}: rubric frame is not G's verify.md")
            require(new['adapter'] == relocate(old['adapter']) and new['role'] == relocate(old['role']),
                    f"{tok} {seat['stem']}: adapter or role frame differs beyond the relocated work path")
            # The snapshot is length-prefixed sub-frames; relocation changes lengths, so compare payloads.
            require(subframes(new['snapshot']) == [(name, relocate(raw)) for name, raw in subframes(old['snapshot'])],
                    f"{tok} {seat['stem']}: snapshot differs beyond the relocated work path")
        results.append({'token': tok, 'verdict': summary['verdict'], 'carriers': carriers})
    dump(DEV / 'stub-runs/result.json', {'rounds': len(results), 'results': results})
    print(json.dumps({'rounds': len(results), 'all_pass': True}))


# ---------------------------------------------------------------- inventory

def scan_roots():
    # The registration's roots plus /private/tmp and $TMPDIR, where a 2026-10-01 check found V8 code caches and npm
    # logs naming 0227 trees (Addendum C1).
    return ([p for p in sorted(HOME.iterdir()) if p.name != 'Library']
            + [SHARED, Path('/private/tmp'), Path(os.environ['TMPDIR'])])


def markers():
    """Path markers and, per hidden mechanism file, its longest ASCII line (no quote or backslash, which transcripts
    escape) that no non-hidden corpus file contains. Only digests are recorded."""
    corpus = EVIDENCE / 'corpus'
    public = b'\n'.join(p.read_bytes() for p in corpus.rglob('*') if p.is_file() and 'hidden' not in p.parts)
    lines = ['devlyn-vr-0227', 'experiments/0227']
    for mechanism in sorted(corpus.glob('*/hidden/mechanism.md')):
        candidates = [line.strip() for line in mechanism.read_text(encoding='utf-8').splitlines()]
        candidates = [line for line in candidates if len(line) >= MIN_MARKER and line.isascii()
                      and '"' not in line and '\\' not in line and line.encode() not in public]
        require(candidates, f'no marker line in {mechanism}')
        lines.append(max(candidates, key=len))
    return lines


def under(path, roots):
    return any(path == root or path.is_relative_to(root) for root in roots)


def inventory(label):
    started = time.time()
    roots = scan_roots()
    found = subprocess.run(['find', *map(str, [p for p in roots if p.is_dir()]),
                            '(', '-name', 'node_modules', '-o', '-path', str(SHARED / 'devlyn-vr-0227*'), '-o',
                            '-path', str(DEV), ')', '-prune', '-o', '-name', '.git', '-prune', '-print'],
                           capture_output=True, text=True)
    stores = {}
    for entry in found.stdout.splitlines():
        repo = Path(entry).parent
        common = git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir', check=False)
        if common.returncode or git(repo, 'cat-file', '-e', CORPUS_COMMIT, check=False).returncode:
            continue
        store = common.stdout.decode().strip()
        listing = git(repo, 'worktree', 'list', '--porcelain').stdout.decode()
        stores[store] = sorted(line.split(' ', 1)[1] for line in listing.splitlines() if line.startswith('worktree '))
    roots0227 = sorted(str(p) for p in SHARED.glob('devlyn-vr-0227*') if p != SRC)
    structural = [Path(s) for s in stores] + [RESEARCH, SRC, DEV] + [Path(p) for p in roots0227]
    with tempfile.TemporaryDirectory() as private:
        marker_file = Path(private) / 'markers'
        lines = markers()
        marker_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        rg = subprocess.run(['rg', '-l', '-uu', '--no-messages', '-F', '-f', str(marker_file), *map(str, roots)],
                            capture_output=True, text=True)
    require(rg.returncode in (0, 1, 2), f'rg failed: {rg.stderr[-500:]}')
    hits = sorted({str(Path(p)) for p in rg.stdout.splitlines()})
    record = {'label': label, 'started': started, 'elapsed_s': round(time.time() - started, 1),
              'roots': [str(p) for p in roots], 'object_stores': stores, 'roots0227': roots0227,
              'marker_sha256': [sha256(line.encode()) for line in lines], 'rg_returncode': rg.returncode,
              'files': [p for p in hits if not under(Path(p), structural)]}
    dump(DEV / f'inventory-{label}.json', record)
    print(json.dumps({key: record[key] for key in ('label', 'elapsed_s', 'roots0227', 'rg_returncode')}
                     | {'object_stores': list(stores), 'files': len(record['files'])}))


def fresh_inventory(label):
    record = load(DEV / f'inventory-{label}.json')
    require(time.time() - record['started'] <= INVENTORY_MAX_AGE, f'inventory {label} is older than 30 minutes')
    return record


# ---------------------------------------------------------------- processes in sealed repositories

def processes():
    return {pid: row[0] for pid, row in ps_table().items()}


def root_family(root_pid):
    """The root session, everything it started, and its ancestor chain (not the ancestors' other children)."""
    parents = processes()
    family, changed = {root_pid}, True
    while changed:
        changed = False
        for pid, ppid in parents.items():
            if ppid in family and pid not in family:
                family.add(pid)
                changed = True
    node = parents.get(root_pid, 1)
    while node > 1 and node not in family:
        family.add(node)
        node = parents.get(node, 1)
    return family


def others_in_sealed(root_pid, record):
    sealed = [Path(w) for worktrees in record['object_stores'].values() for w in worktrees] + [RESEARCH]
    proc = subprocess.run(['lsof', '-w', '-a', '-d', 'cwd', '-Fpn'], capture_output=True, text=True)
    require(proc.returncode in (0, 1) and proc.stdout.strip(), f'process inspection failed: lsof rc={proc.returncode}')
    family, pid, others = root_family(root_pid), None, []
    for line in proc.stdout.splitlines():
        if line.startswith('p'):
            pid = int(line[1:])
        elif line.startswith('n') and pid not in family and under(Path(line[1:]), sealed):
            command = subprocess.run(['ps', '-o', 'command=', '-p', str(pid)], capture_output=True, text=True)
            others.append({'pid': pid, 'cwd': line[1:], 'command': command.stdout.strip()[:160]})
    return others


# ---------------------------------------------------------------- seals

def restore(modes):
    """Restore every surviving target; keep unresolved entries in the journal and report them."""
    failed = {}
    for path, mode in modes.items():
        try:
            os.chmod(path, mode, follow_symlinks=False)
        except FileNotFoundError:
            pass
        except OSError as exc:
            failed[path] = (mode, str(exc))
    if failed:
        dump(JOURNAL, {path: mode for path, (mode, _) in failed.items()})
        fail(f'could not restore {len(failed)} modes (journal kept): {list(failed.items())[:5]}')
    JOURNAL.unlink(missing_ok=True)


def restore_journal(confirmed=False):
    if UNSAFE.exists():
        require(confirmed, f'an unsafe stop is recorded ({load(UNSAFE)["reason"]}); check that no seat process survives, '
                           'then run `replay.py restore --confirmed`')
    if not JOURNAL.exists():
        UNSAFE.unlink(missing_ok=True)
        return 0
    JOURNAL.chmod(0o600)
    modes = load(JOURNAL)
    restore(modes)
    UNSAFE.unlink(missing_ok=True)
    return len(modes)


def seal_plan(record, arm, repo, base):
    zero, search = set(), {SRC, SRC / 'toolchains', DEV}
    keep = {'bin', 'toolchains'} | ({'product'} if arm == 'F' else set())
    zero |= {p for p in SRC.iterdir() if p.name not in keep}
    zero |= {p for p in (SRC / 'toolchains').iterdir() if p.name != repo}
    zero |= {Path(p) for p in record['roots0227']}
    first = base.relative_to(DEV).parts[0]
    zero |= {p for p in DEV.iterdir() if p.name not in {'runner', first}
             | ({'product-G'} if arm == 'G' else set())}
    node = DEV / first
    for part in base.relative_to(DEV).parts[1:]:
        parent, node = node, node / part
        zero |= {p for p in parent.iterdir() if p != node}
        search.add(parent)
    zero |= {Path(s) for s in record['object_stores']} | {RESEARCH}
    zero = {p for p in zero if not any(p != q and p.is_relative_to(q) for q in zero)}  # a sealed parent covers it
    write_only = {Path(p) for p in record['files'] if os.path.lexists(p) and not under(Path(p), zero)}
    return {'zero': sorted(map(str, zero)), 'search': sorted(map(str, search)), 'write_only': sorted(map(str, write_only))}


@contextmanager
def sealed(seals):
    # A sealed path that vanished since the inventory (another session's scratch clone, a temporary file) needs no seal.
    targets = [(p, 0) for p in seals['zero'] if os.path.lexists(p)] + [(p, 0o100) for p in seals['search']]
    targets += [(p, 0o200) for p in seals['write_only'] if os.path.lexists(p)]
    modes = {p: stat.S_IMODE(os.lstat(p).st_mode) for p, _ in targets}
    dump(JOURNAL, modes)
    JOURNAL.chmod(0o200)
    try:
        for path, mode in targets:
            try:
                os.chmod(path, mode, follow_symlinks=False)
            except FileNotFoundError:
                if mode == 0o100:
                    raise
        yield
    except Unsafe as exc:
        dump(UNSAFE, {'reason': str(exc), 'at': time.time()})
        print(json.dumps({'seals_kept': True, 'journal': str(JOURNAL), 'unsafe': str(UNSAFE),
                          'recover': 'check no seat process survives, then replay.py restore --confirmed'}), flush=True)
        raise
    except BaseException:
        restore(modes)
        raise
    else:
        restore(modes)


def handle_signals():
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, record_signal)


# ---------------------------------------------------------------- R1 isolation probe

def probe(root_pid, label, transcript):
    restore_journal()
    record = fresh_inventory(label)
    transcript = Path(transcript)
    require(str(transcript) in record['files'], 'the live root transcript is not in the inventory')
    hidden = RESEARCH / 'autoresearch/experiments/0227/corpus/J4/hidden/mechanism.md'
    with transcript.open(encoding='utf-8') as handle:
        first = {'claude': handle.readline().rstrip('\n')[:80]}
    first['codex'] = hidden.read_text(encoding='utf-8').split('\n', 1)[0]
    tok = next(r['token'] for r in manifest()['rounds'] if r['repo'] == 'node-lru-cache')
    base = DEV / 'probe' / f'rep-{len(list((DEV / "probe").glob("rep-*"))) + 1}'
    row, work, env = prepare(base, tok)
    # A readable control file outside the work tree shows that a failed read is the seal, not a tool policy.
    control = base / 'control.txt'
    token = sha256(f'{time.time()}'.encode())[:16]
    control.write_text(token + '\n', encoding='utf-8')
    auth = Path(env['CODEX_HOME']) / 'auth.json'
    shutil.copyfile(HOME / '.codex/auth.json', auth)
    auth.chmod(0o600)
    seals = seal_plan(record, 'F', row['repo'], base)
    dump(base / 'seals.json', seals)
    opener = ('import json,os,sys\ns=json.load(open(sys.argv[1]))\nok=[]\n'
              'for p in s["zero"]+s["search"]+s["write_only"]+sys.argv[2:]:\n'
              ' try:\n  os.listdir(p) if os.path.isdir(p) else open(p,"rb").read(1)\n  ok.append(p)\n'
              ' except OSError: pass\nprint(json.dumps(ok))\n')
    ask = ('report the first line of each file below. For a file that cannot be read, give READ-FAILED and the error '
           'message instead. Reply in exactly two lines, "CONTROL: <result for file 1>" and "TARGET: <result for '
           'file 2>".')
    (base / 'claude.prompt').write_text(f'Using only the Read tool, {ask}\n1. {control}\n2. {transcript}\n',
                                        encoding='utf-8')
    # One command for both files, so its exec record carries the target's own result (parallel records are ambiguous).
    (base / 'codex.prompt').write_text(f'Run exactly one shell command, `head -n 1 {control} {hidden}`, then {ask}\n'
                                       f'1. {control}\n2. {hidden}\n', encoding='utf-8')
    result = {'token': tok, 'base': str(base)}
    handle_signals()
    try:
        with sealed(seals):
            opened = subprocess.run([sys.executable, '-c', opener, str(base / 'seals.json'), str(transcript),
                                     str(hidden)], env=env, cwd=work, capture_output=True, text=True)
            result['opened'] = json.loads(opened.stdout) if opened.returncode == 0 else ['<opener failed>']
            size = transcript.stat().st_size
            # The runner folder stays readable under the seals; root polls this file, then makes one tool call.
            dump(DEV / 'runner/probe-status.json', {'sealed': True, 'waiting_for_root_tool_call': str(transcript)})
            deadline = time.time() + 600
            while transcript.stat().st_size <= size and time.time() < deadline and not PENDING:
                time.sleep(1)
            result['root_transcript_grew'] = [size, transcript.stat().st_size]
            dump(DEV / 'runner/probe-status.json', {'sealed': True, 'root_transcript_grew': result['root_transcript_grew']})
            result['claude_rc'], result['claude_error'] = run(
                [str(SRC / 'bin/claude'), '-p', '--permission-mode', 'dontAsk', '--tools', 'Read', '--allowedTools',
                 'Read', '--setting-sources', 'project', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
                 '--model', 'claude-opus-5-5', '--output-format', 'json'],
                work, env, base / 'claude.stdout', base / 'claude.stderr', 600, base, stdin_path=base / 'claude.prompt')
            # The pinned Codex with the isolated wrapper's flags except --ephemeral: its plain stderr and JSON events
            # omit reads made through its built-in tools, while the rollout records every tool call with its output.
            result['codex_rc'], result['codex_error'] = run(
                [str(SRC / 'bin/codex'), 'exec', '--json', '--ignore-user-config', '--ignore-rules',
                 '--disable', 'codex_hooks', '--disable', 'hooks', '--skip-git-repo-check', '-C', str(work), '-s',
                 'read-only', '-m', 'gpt-6-astra', '-c', 'model_reasoning_effort=high', '-'],
                work, env, base / 'codex.stdout', base / 'codex.stderr', 900, base, stdin_path=base / 'codex.prompt')
    finally:
        auth.unlink(missing_ok=True)
        move_claude_project(work, base)
    claude_out = (base / 'claude.stdout').read_text(encoding='utf-8')
    codex_out = (base / 'codex.stdout').read_text(encoding='utf-8')
    envelope = json.loads(claude_out) if claude_out.strip().startswith('{') else {}
    events = [json.loads(line) for line in codex_out.splitlines() if line.startswith('{')]
    items = [event['item'] for event in events if event.get('type') == 'item.completed' and 'item' in event]
    replies = {'claude': str(envelope.get('result', '')),
               'codex': '\n'.join(item.get('text', '') for item in items if item.get('type') == 'agent_message')}
    for name in ('claude', 'codex'):
        result[f'{name}_control_read'] = token in replies[name]
        result[f'{name}_reply_failed'] = 'READ-FAILED' in replies[name] and first[name] not in replies[name]
    # The target read must be attempted and denied by the filesystem, shown in the seat's own record.
    denied = re.compile(r'(?i)(EACCES|permission denied|operation not permitted)')
    uses, results = {}, []
    for session in (base / 'claude-project').glob('*.jsonl'):
        for line in session.read_text(encoding='utf-8').splitlines():
            for block in (json.loads(line).get('message') or {}).get('content', []) or []:
                if isinstance(block, dict) and block.get('type') == 'tool_use' and block.get('name') == 'Read':
                    uses[block.get('id')] = (block.get('input') or {}).get('file_path')
                elif isinstance(block, dict) and block.get('type') == 'tool_result':
                    results.append((block.get('tool_use_id'), json.dumps(block.get('content'))))
    result['claude_target_denied'] = any(uses.get(use) == str(transcript) and denied.search(text)
                                         for use, text in results)
    calls, outputs = {}, {}
    for rollout in (Path(env['CODEX_HOME']) / 'sessions').rglob('*.jsonl'):
        for line in rollout.read_text(encoding='utf-8').splitlines():
            payload = json.loads(line).get('payload') or {}
            if payload.get('type') in ('function_call', 'custom_tool_call'):
                calls[payload.get('call_id')] = json.dumps(payload.get('arguments', payload.get('input')))
            elif payload.get('type') in ('function_call_output', 'custom_tool_call_output'):
                outputs[payload.get('call_id')] = json.dumps(payload.get('output'))
    result['codex_target_denied'] = any(str(hidden) in text and denied.search(outputs.get(call, ''))
                                        for call, text in calls.items())
    result.update(
        claude_session=any((base / 'claude-project').glob('*.jsonl')),
        codex_session=bool(calls) and any(event.get('type') == 'thread.started' for event in events),
        auth_removed=not auth.exists())
    result['pass'] = (not PENDING and not result['opened'] and result['root_transcript_grew'][1] > result['root_transcript_grew'][0]
                      and all(result[f'{name}_{check}'] for name in ('claude', 'codex')
                              for check in ('control_read', 'reply_failed', 'target_denied', 'session'))
                      and result['claude_rc'] == 0 and result['codex_rc'] == 0 and result['auth_removed'])
    dump(base / 'probe.json', result)
    print(json.dumps(result))


# ---------------------------------------------------------------- live batches

def batch(plan_file, root_pid, label, ack):
    restore_journal()
    record = fresh_inventory(label)
    items = load(Path(plan_file))
    require(sha256((SRC / 'bin/claude').read_bytes()) == CLAUDE_SHA256, 'bin/claude differs from the pinned digest')
    check_tars(item['token'] for item in items)  # every required tar, before the first live call
    others = others_in_sealed(root_pid, record)
    require(not others or ack, f'processes work inside sealed repositories; ask the user first: {others}')
    started = time.time()
    dump(DEV / 'batches' / f'{int(started)}.json', {'plan': str(plan_file), 'plan_sha256': sha256(Path(plan_file).read_bytes()),
                                                   'inventory': label, 'others': others, 'ack': ack})
    handle_signals()
    for index, item in enumerate(items):
        if PENDING:
            print(json.dumps({'batch_stopped': f'signal {PENDING[0]}', 'completed': index}), flush=True)
            fail(f'batch stopped by signal after {index} replays; seals restored')
        arm, tok = item['arm'], item['token']
        base = next_attempt(arm, tok)
        row, work, env = prepare(base, tok)
        auth = Path(env['CODEX_HOME']) / 'auth.json'
        shutil.copyfile(HOME / '.codex/auth.json', auth)
        auth.chmod(0o600)
        seals = seal_plan(record, arm, row['repo'], base)
        dump(base / 'seals.json', seals)
        began = time.time()
        try:
            with sealed(seals):
                rc, error = judge(arm, work, env, base)
        finally:
            auth.unlink(missing_ok=True)
            move_claude_project(work, base)  # evidence is kept even when a signal ends the batch
        facts = {'index': index, 'arm': arm, 'token': tok, 'attempt': str(base.relative_to(DEV)), 'rc': rc,
                 'error': error, 'elapsed_s': round(time.time() - began, 1), 'carriers': transport(work),
                 'claude_project_moved': (base / 'claude-project').is_dir()}
        with RECORDS.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(facts) + '\n')
        print(json.dumps(facts), flush=True)  # transport facts only; verdicts stay in the attempt folder
    print(json.dumps({'batch_done': len(items), 'elapsed_s': round(time.time() - started, 1)}))


# ---------------------------------------------------------------- post-batch (research checkout, nothing sealed)

def screen0227():
    return runpy.run_path(str(EVIDENCE / 'screen.py'))


def classify(attempts):
    code = screen0227()
    for attempt in attempts:
        base = DEV / attempt
        work = base / 'work'
        seats = []
        for engine, stem in (('claude', 'claude-judge.r0'), ('codex', 'codex-judge.r0')):
            devlyn = work / '.devlyn'
            carrier_path = devlyn / f'{stem}.prompt.transport.json'
            prompt_path = devlyn / f'{stem}.prompt'
            seats.append({'engine': engine, 'carrier': load(carrier_path) if carrier_path.is_file() else {},
                          'envelope': code['load_envelope'](devlyn / f'{stem}.output.json') if engine == 'claude' else {},
                          'stderr': (devlyn / f'{stem}.stderr').read_text(encoding='utf-8', errors='replace')
                          if (devlyn / f'{stem}.stderr').is_file() else '',
                          'prompt': prompt_path.read_text(encoding='utf-8') if prompt_path.is_file() else None})
        print(json.dumps({'attempt': attempt, 'classes': code['classify_infra'](seats)}))


def scan(attempts):
    code = screen0227()
    for attempt in attempts:
        base = DEV / attempt
        work = base / 'work'
        seals = load(base / 'seals.json')
        arm, tok = base.relative_to(DEV).parts[:2]
        repo = next(r['repo'] for r in manifest()['rounds'] if r['token'] == tok)
        # Both sides canonical (/var/folders is /private/var/folders); sealed search directories are excluded too.
        allowed = [p.resolve() for p in (base, PRODUCT[arm], SRC / 'bin', SRC / 'toolchains' / repo)]
        excluded_dirs = [Path(p).resolve() for p in seals['zero'] + seals['search']]
        excluded_files = {Path(p).resolve() for p in seals['write_only']}
        outside, ambiguous = set(), []

        def check(raw, cwd, origin, strong):
            if any(char in raw for char in '{}*?[]$`~'):
                ambiguous.append((origin, raw))
                return
            path = (Path(raw) if Path(raw).is_absolute() else cwd / raw).resolve()
            if under(path, allowed):
                return
            if under(path, [d for d in excluded_dirs if d not in (SRC.resolve(), DEV.resolve())]) or path in excluded_files \
                    or path in (SRC.resolve(), DEV.resolve()):
                (outside.add(str(path)) if strong else ambiguous.append((origin, raw)))
            elif any(target.is_relative_to(path) for target in [*excluded_dirs, *excluded_files]):
                ambiguous.append((origin, raw))  # an ancestor of a sealed directory or file

        for session in (base / 'claude-project').rglob('*.jsonl') if (base / 'claude-project').is_dir() else ():
            for line in session.read_text(encoding='utf-8').splitlines():
                message = json.loads(line).get('message') or {}
                for block in message.get('content', []) if isinstance(message, dict) else []:
                    if isinstance(block, dict) and block.get('type') == 'tool_use' and block.get('name') in (
                            'Read', 'Grep', 'Glob'):
                        for key in ('file_path', 'path'):
                            raw = (block.get('input') or {}).get(key)
                            if isinstance(raw, str):
                                check(raw, work, 'claude-' + block['name'], True)
        stderr = work / '.devlyn/codex-judge.r0.stderr'
        prompt = work / '.devlyn/codex-judge.r0.prompt'
        if stderr.is_file():
            paths, unparsed = code['codex_exec_paths'](stderr.read_text(encoding='utf-8'),
                                                      prompt.read_text(encoding='utf-8') if prompt.is_file() else None)
            ambiguous.extend(('codex-block', raw) for raw in unparsed)
            for raw, cwd in paths:
                check(raw, cwd, 'codex-word', False)  # a Codex shell word is never a definite read (0227)
        else:
            ambiguous.append(('codex-stderr', '<missing>'))
        print(json.dumps({'attempt': attempt, 'excluded_reads': sorted(outside), 'ambiguous': ambiguous}))


def main(argv):
    command, args = argv[0], argv[1:]
    if command == 'stage':
        stage(*args)
    elif command == 'plan':
        orders = plan()
        for name, items in orders.items():
            dump(Path(__file__).resolve().parent / f'plan-{name}.json', items)
        print(json.dumps({name: len(items) for name, items in orders.items()}))
    elif command in ('classify', 'scan'):
        (classify if command == 'classify' else scan)(args)
    else:
        staged()
        if command == 'product':
            product_check()
        elif command == 'stub':
            stub()
        elif command == 'restore':
            print(json.dumps({'restored': restore_journal(confirmed=args == ['--confirmed'])}))
        elif command == 'inventory':
            inventory(*args)
        elif command == 'preflight':
            print(json.dumps(others_in_sealed(int(args[0]), fresh_inventory(args[1]))))
        elif command == 'probe':
            probe(int(args[0]), args[1], args[2])
        elif command == 'batch':
            batch(args[0], int(args[1]), args[2], args[3] if len(args) > 3 else '')
        else:
            fail(f'unknown command {command}')


if __name__ == '__main__':
    main(sys.argv[1:])
