#!/usr/bin/env python3
"""0228 replay runner: development evidence, never a 0227 regrade (autoresearch/iterations/0228-verify-rubric-rescreen.md).

A replay reruns one 0227 round's VERIFY from its sealed pristine tars with one product arm (F = 0227's product,
G = the candidate's skills archive). Isolation is by identity (Addendum C2): every judge process runs as the dedicated
account _devlynjudge, which cannot read the owner's files. The runner changes modes and ACLs only inside the three
experiment-owned roots (the 0227 root, the other devlyn-vr-0227-* roots and the 0228 root), and every mutation goes
through a helper that refuses, before acting, any target outside them. `stage` copies this runner to
/Users/Shared/devlyn-vr-0228-dev/runner/; every command except `plan`, `classify` and `scan` runs from that copy.

  stage <G commit>              (research checkout) G's skills archive, this runner, 0227's stubs
  plan                          (research checkout) print the fixed R2 and R3 replay orders
  product                       R1: G's product differs from 0227's only in verify.md
  stub                          R1: stub replay of all 64 rounds under G, run as the judge
  inventory <label>             every owner path holding 0227 hidden material (read-only)
  check <label>                 as the judge, open every inventoried path; any success fails closed
  probe <label> <transcript>    R1 isolation probe, run as the judge
  batch <plan> <label>          live replays as the judge; prints transport facts only
  classify <attempt>...         (research checkout) 0227's frozen infra classifier, per attempt
  scan <label> <attempt>...     (research checkout) read scan of each attempt's seat tool inputs
"""
import ctypes
import hashlib
import io
import json
import os
import pwd
import re
import runpy
import shutil
import shlex
import signal
import stat
import subprocess
import sys
import tarfile
import time
from contextlib import contextmanager
from pathlib import Path

sys.dont_write_bytecode = True
HOME = Path.home()
OWNER = pwd.getpwuid(os.getuid()).pw_name
SHARED = Path('/Users/Shared')
SRC = SHARED / 'devlyn-vr-0227'
DEV = SHARED / 'devlyn-vr-0228-dev'
RESEARCH = HOME / '.local/share/nx01/core-continuation-20260912'
EVIDENCE = RESEARCH / 'autoresearch/experiments/0227'
PRODUCT = {'F': SRC / 'product', 'G': DEV / 'product-G'}
RECORDS = DEV / 'records.jsonl'
RESULTS = DEV / 'results'  # runner records written after a judge ran never go inside the attempt
SCRATCH = DEV / 'scratch'
KINDS = ('F', 'G', 'stub-G', 'probe')
CORPUS_COMMIT = '8c589f2ec82a4ada4bf99cd6e60c38615a036055'
CLAUDE_SHA256 = 'a922981f6f3b55a251ef9f9dbaa0621a5f99cbcb5ca67f8a797476ccfc83f626'  # 0227's pinned bin/claude
VERIFY_MD = 'config/skills/devlyn:resolve/references/phases/verify.md'
SEATS = ('claude-judge.r0', 'codex-judge.r0')
INVENTORY_MAX_AGE = 1800  # a batch's inventory must be fresh (registration: "immediately before every batch")
MIN_MARKER = 40
MANIFEST_COMMIT = '1a6f026e3abc294a9d3bac9b0c4ef7be56eb049f'  # main after the 0228 registration; holds 0227's manifest
PENDING = []  # received TERM/INT; handlers only record them, so cancellation happens at safe points
# The judge account (created by the owner, Addendum C2). The runner never uses sudo for any other user.
JUDGE = '_devlynjudge'
JUDGE_UID = 450
SUDO = '/usr/bin/sudo'
TOKEN_FILE = HOME / '.config/devlyn-vr/judge-claude-token'
# ACL entries. A judge grant on an attempt is inherited by everything the judge creates there; the owner entry keeps
# those files readable and removable by the owner.
# The judge entry has no `delete`: inside the attempt, deleting works through the parent's delete_child, while the
# attempt root itself cannot be moved out (its parent grants the judge search only).
JUDGE_PERMS = ('read,write,execute,append,delete_child,readattr,writeattr,readextattr,writeextattr,readsecurity,'
               'file_inherit,directory_inherit')
OWNER_PERMS = ('read,write,execute,append,delete,delete_child,readattr,writeattr,readextattr,writeextattr,readsecurity,'
               'file_inherit,directory_inherit')
ATTEMPT_ACES = (f'user:{JUDGE} allow {JUDGE_PERMS}', f'user:{OWNER} allow {OWNER_PERMS}')
SEARCH_ACE = f'user:{JUDGE} allow search'
RUN_ACE = f'user:{JUDGE} allow read,execute,readattr,readextattr,readsecurity'
DENY_DIR_ACE = f'user:{JUDGE} deny list,search,readattr,readextattr,readsecurity'
DENY_FILE_ACE = f'user:{JUDGE} deny read,execute,readattr,readextattr,readsecurity'
SRC_VISIBLE = {'bin', 'toolchains'}  # everything else in the 0227 root is hidden from the judge (product is copied);
# each toolchain is denied too, except the active round's for the duration of its run


def fail(message):
    raise SystemExit(f'0228 replay: {message}')


def require(condition, message):
    if not condition:
        fail(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


# ---------------------------------------------------------------- ownership guard and the only mutating helpers

def owned_roots():
    return [SRC, DEV, *sorted(p for p in SHARED.glob('devlyn-vr-0227-*'))]


def owned(path):
    """Fail closed before any mutation outside the experiment-owned roots (Addendum C2). The final component is not
    followed, so a symlink inside a root is the link itself; a parent symlink that leaves the roots is refused."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        fail(f'refusing to modify {path}: not an absolute normalized path')
    real = path.parent.resolve() / path.name
    if not any(real == root or real.is_relative_to(root) for root in owned_roots()):
        fail(f'refusing to modify {path}: outside the experiment-owned roots')
    return path


def write_bytes(path, data, mode=0o600):
    path = owned(path)
    make_dir(path.parent)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(data)


def dump(path, data):
    path = owned(path)
    make_dir(path.parent)
    temporary = owned(path.with_name(path.name + '.tmp'))
    write_bytes(temporary, (json.dumps(data, indent=2, sort_keys=True) + '\n').encode('utf-8'))
    os.replace(temporary, path)


def append_line(path, line):
    path = owned(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a', encoding='utf-8') as handle:
        handle.write(line + '\n')


def open_out(path):
    path = owned(path)
    return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600), 'wb')


def make_dir(path, mode=0o700):
    path = owned(path)
    require(not path.is_symlink(), f'refusing to modify {path}: a symlink, not a directory')
    path.mkdir(mode=mode, parents=True, exist_ok=True)


def new_dir(path):
    """An attempt folder: created owner-only and never reused (FileExistsError)."""
    path = owned(path)
    make_dir(path.parent)
    path.mkdir(mode=0o700)


def copy_file(source, target, mode=0o600):
    target = owned(target)
    require(not os.path.lexists(target), f'{target} exists')
    shutil.copyfile(source, target)
    os.chmod(target, mode, follow_symlinks=False)


def copy_tree(source, target):
    target = owned(target)
    require(not os.path.lexists(target), f'{target} exists')
    shutil.copytree(source, target, symlinks=True)


def remove_file(path):
    path = owned(path)
    path.unlink(missing_ok=True)


def remove_tree(path):
    path = owned(path)
    if os.path.lexists(path):
        shutil.rmtree(path)


def make_symlink(link, target):
    link = owned(link)
    link.symlink_to(target, target_is_directory=Path(target).is_dir())


def set_mode(path, mode):
    path = owned(path)
    os.chmod(path, mode, follow_symlinks=False)


def chmod_acl(arguments, paths):
    """`chmod -h <arguments> <paths>` on owned, non-symlink paths only (chmod -R follows symlinks, so never -R)."""
    paths = [owned(p) for p in paths]
    paths = [p for p in paths if not os.path.islink(p)]
    for start in range(0, len(paths), 400):
        proc = subprocess.run(['/bin/chmod', '-h', *arguments, *map(str, paths[start:start + 400])],
                              capture_output=True, text=True)
        require(proc.returncode == 0, f'chmod {arguments[0]} failed: {proc.stderr[-300:]}')


def acl_tree(root, entries):
    """Add ACL entries to root and everything under it, never following a symlink (os.walk followlinks=False)."""
    owned(root)
    paths = [root]
    for folder, directories, names in os.walk(root, followlinks=False):
        paths += [Path(folder) / name for name in directories + names]
    for entry in entries:
        chmod_acl(['+a', entry], paths)


def acl_ensure(path, entry):
    """Add one ACL entry unless an equal entry is already present."""
    path = owned(path)
    if entry_present(path, entry):
        return
    chmod_acl(['+a', entry], [path])


def acl_clear(path):
    chmod_acl(['-N'], [path])


def extract(source, destination, trusted=True):
    """Extract a tar (a path, or bytes) into a new owned folder. Every member must be a regular file or a directory with
    a unique relative name inside it (all 128 pristine tars are), so nothing can be written through a link. Pristine
    round tars keep their modes (`fully_trusted`); skill archives use the `data` filter."""
    destination = owned(destination)
    require(not destination.is_symlink(), f'refusing to modify {destination}: a symlink, not a directory')
    require(not os.path.lexists(destination) or not any(destination.iterdir()), f'{destination} is not empty')
    opened = tarfile.open(fileobj=io.BytesIO(source)) if isinstance(source, bytes) else tarfile.open(source)
    with opened as archive:
        members = archive.getmembers()
        names = [os.path.normpath(m.name) for m in members]
        require(len(names) == len(set(names)), f'{source}: duplicate member names')
        for member, name in zip(members, names):
            require(member.isfile() or member.isdir(), f'{source}: member {member.name} is not a file or directory')
            require(not os.path.isabs(name) and name != '..' and not name.startswith('../'),
                    f'{source}: member {member.name} leaves the destination')
        make_dir(destination)
        archive.extractall(destination, filter='fully_trusted' if trusted else 'data')


# ---------------------------------------------------------------- read-only helpers

def entry_present(path, entry):
    listing = subprocess.run(['/bin/ls', '-led', str(path)], capture_output=True, text=True).stdout
    who, kind, perms = entry.split(' ')
    wanted = set(perms.split(','))
    for line in listing.splitlines()[1:]:
        fields = line.split(':', 1)[1].split() if ':' in line else []
        if len(fields) >= 3 and fields[0] == who and fields[1] == kind and set(fields[2].split(',')) == wanted:
            return True
    return False


def manifest(cache={}):
    """0227's committed manifest; the Shared copy must equal it byte for byte."""
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


def under(path, roots):
    return any(path == root or path.is_relative_to(root) for root in roots)


def staged():
    require(Path(__file__).resolve().parent == DEV / 'runner', 'run the staged copy in /Users/Shared/devlyn-vr-0228-dev/runner')


# ---------------------------------------------------------------- staging and fixed orders (research checkout)

def stage(commit):
    """Create the replay root once; on later calls verify G's archive and refresh only the runner copy."""
    raw = git(RESEARCH, 'archive', '--format=tar', commit, 'config/skills').stdout
    check_dir = SCRATCH / f'stage-{os.getpid()}'
    remove_tree(check_dir)
    extract(raw, check_dir, trusted=False)
    expected = files(check_dir)
    remove_tree(check_dir)
    if not PRODUCT['G'].exists():
        extract(raw, PRODUCT['G'], trusted=False)
        copy_tree(SRC / 'dry/bin', DEV / 'stub/bin')
        copy_tree(SRC / 'dry/codex-home', DEV / 'stub/codex-home')
    require(files(PRODUCT['G']) == expected, f'{PRODUCT["G"]} differs from the archive of {commit}')
    make_dir(DEV / 'runner')
    write_bytes(DEV / 'runner/replay.py', Path(__file__).read_bytes(), mode=0o700)
    entry = {'G': git(RESEARCH, 'rev-parse', commit).stdout.decode().strip(), 'staged_at': time.time(),
             'product_G_sha256': sha256(json.dumps(expected, sort_keys=True).encode()),
             'runner_sha256': sha256(Path(__file__).read_bytes())}
    append_line(DEV / 'stage.jsonl', json.dumps(entry))
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


# ---------------------------------------------------------------- judge access (experiment-owned paths only)

def isolate():
    """Before anything is granted: no judge process may be alive. Then the owner-only 0228 root with judge search; every
    earlier attempt closed (mode 0700, ACL cleared, no Codex login copy); judge search on the 0227 root with every entry
    denied except bin and toolchains, every toolchain denied, and read/execute on the pinned binaries. Owner paths are
    never touched: the judge account cannot read them."""
    judge_quiesce()
    set_mode(DEV, 0o700)
    acl_ensure(DEV, SEARCH_ACE)
    for child in DEV.iterdir():
        if child.is_symlink():
            fail(f'unexpected symlink in the 0228 root: {child}')
        if child.name in KINDS:
            set_mode(child, 0o700)
            acl_ensure(child, SEARCH_ACE)
            for sub in child.iterdir():
                if sub.is_dir() and not sub.name.startswith('rep-'):  # a token folder
                    set_mode(sub, 0o700)
                    acl_ensure(sub, SEARCH_ACE)
                    for attempt in sub.iterdir():
                        close_old(attempt)
                elif sub.is_dir():  # an attempt directly under the kind (the probe's first layout)
                    close_old(sub)
                else:
                    set_mode(sub, 0o600)
        else:
            set_mode(child, 0o700 if child.is_dir() else 0o600)
    acl_ensure(SRC, SEARCH_ACE)
    for child in SRC.iterdir():
        if child.name not in SRC_VISIBLE:
            acl_ensure(child, DENY_DIR_ACE if child.is_dir() else DENY_FILE_ACE)
    for toolchain in (SRC / 'toolchains').iterdir():
        acl_ensure(toolchain, DENY_DIR_ACE)
    for binary in ('claude', 'codex'):
        acl_ensure(SRC / 'bin' / binary, RUN_ACE)


def close_old(attempt):
    set_mode(attempt, 0o700)
    acl_clear(attempt)
    left = [str(p) for p in attempt.rglob('auth.json') if p.parent.name == '.codex']
    require(not left, f'Codex login copies left in an earlier attempt: {left}')


def path_search(base):
    """Judge search (never list) on the folders between the 0228 root and an attempt."""
    node = DEV
    for part in base.relative_to(DEV).parts[:-1]:
        node = node / part
        make_dir(node)
        acl_ensure(node, SEARCH_ACE)


# ---------------------------------------------------------------- attempts

def next_attempt(kind, tok):
    folder = DEV / kind / tok
    taken = [int(p.name.split('-')[1]) for p in folder.glob('rep-*')] if folder.is_dir() else []
    return folder / f'rep-{max(taken, default=0) + 1}'


def check_tars(tokens):
    rows = {r['token']: r for r in manifest()['rounds']}
    for tok in sorted(set(tokens)):
        for suffix in ('.tar', '.home.tar'):
            tar = SRC / 'private/pristine' / f'{tok}{suffix}'
            require(sha256(tar.read_bytes()) == rows[tok]['pristine'][suffix], f'{tok}{suffix}: digest differs from the manifest')


def prepare(base, tok, arm, *, stub=False):
    """One round's pristine inputs, the arm's product copy and the judge's own HOME and TMPDIR in a never-reused,
    owner-only folder, granted to the judge with the round's toolchain; returns the round row, work tree and judge
    environment."""
    row = next(r for r in manifest()['rounds'] if r['token'] == tok)
    require("'" not in str(base), f'{base} cannot be single-quoted for Git')
    path_search(base)
    new_dir(base)
    check_tars([tok])
    extract(SRC / 'private/pristine' / f'{tok}.tar', base)  # yields base/work
    extract(SRC / 'private/pristine' / f'{tok}.home.tar', base / 'homes')
    work = base / 'work'
    if row['repo'] == 'node-lru-cache':
        make_symlink(work / 'node_modules', SRC / 'toolchains/node-lru-cache/node_modules')
    copy_tree(PRODUCT[arm], base / 'product')  # F and G alike: the judge never reads either original
    make_dir(base / 'judge-home')
    make_dir(base / 'judge-tmp')
    # F and G get the same environment: the round's, with the work path relocated, the judge's own HOME and TMPDIR,
    # and Git trust for exactly this work tree (it is owned by the owner, the judge is another uid). USER and LOGNAME
    # are left to sudo (the judge's); SHELL is passed (sudo would set the judge's /usr/bin/false).
    env = {name: value.replace(row['work'], str(work)) for name, value in row['env'].items()
           if name not in ('USER', 'LOGNAME')}
    env.update(HOME=str(base / 'judge-home'), TMPDIR=str(base / 'judge-tmp'),
               CODEX_HOME=str(base / 'homes' / tok / '.codex'),
               GIT_CONFIG_PARAMETERS=f"'safe.directory'='{work}'")  # Git requires both parts single-quoted
    if stub:
        copy_tree(DEV / 'stub/bin', base / 'stub-bin')
        copy_tree(DEV / 'stub/codex-home', base / 'stub-codex-home')
        make_dir(base / 'stubs/barrier')
        env['PATH'] = env['PATH'].replace(str(SRC / 'bin'), str(base / 'stub-bin'), 1)
        env.update(CODEX_HOME=str(base / 'stub-codex-home'), STUB_DIR=str(base / 'stubs'), STUB_BARRIER='1')
    acl_tree(base, ATTEMPT_ACES)
    chmod_acl(['-a', DENY_DIR_ACE], [SRC / 'toolchains' / row['repo']])
    return row, work, env


def with_token(env):
    """The judge's Claude credential, read at launch and passed only through the environment (never argv or a file)."""
    token = TOKEN_FILE.read_text(encoding='utf-8').strip()
    require(token, f'{TOKEN_FILE} is empty')
    return {**env, 'CLAUDE_CODE_OAUTH_TOKEN': token}


def codex_auth(env):
    """A per-attempt copy of the Codex login, readable by the judge through the attempt grant; removed after the run."""
    auth = Path(env['CODEX_HOME']) / 'auth.json'
    copy_file(HOME / '.codex/auth.json', auth)  # inherits the attempt's judge and owner entries
    return auth


@contextmanager
def attempt(kind, tok, arm, *, stub=False):
    """An attempt from preparation to closure: whatever fails, the attempt is closed to the judge, the toolchain denied
    again and the Codex login copy deleted."""
    base = next_attempt(kind, tok)
    repo = next(r['repo'] for r in manifest()['rounds'] if r['token'] == tok)
    auth = None
    try:
        row, work, env = prepare(base, tok, arm, stub=stub)
        if not stub:
            auth = codex_auth(env)
        yield base, row, work, env
    finally:
        close_attempt(base, repo, auth)


def close_attempt(base, repo, auth):
    """After a run: no judge process; the attempt closed to the judge and the toolchain denied again (first, so nothing
    below can skip it); the Codex login copy still in place and then deleted; every file readable and none holding the
    judge token."""
    judge_quiesce()
    acl_ensure(SRC / 'toolchains' / repo, DENY_DIR_ACE)
    if os.path.lexists(base):
        acl_clear(base)
    if auth is not None:
        require(auth.is_file() and not auth.is_symlink(), f'the Codex login copy {auth} moved or changed')
        remove_file(auth)
    if not os.path.lexists(base):  # preparation failed before the folder existed
        return
    token = TOKEN_FILE.read_bytes().strip()
    require(token, f'{TOKEN_FILE} is empty')
    found = []
    for folder, _directories, names in os.walk(base, followlinks=False, onerror=lambda exc: found.append(str(exc))):
        for name in names:
            path = Path(folder) / name
            kind = os.lstat(path).st_mode
            if stat.S_ISLNK(kind):
                continue
            if not stat.S_ISREG(kind):  # a FIFO or device would block or mislead the scan
                found.append(f'{path}: not a regular file')
                continue
            if name == 'auth.json' and path.parent.name == '.codex':
                found.append(str(path))
                continue
            try:
                with open(path, 'rb') as handle:
                    previous = b''
                    while chunk := handle.read(1 << 20):
                        if token in previous[-len(token):] + chunk:
                            found.append(str(path))
                            break
                        previous = chunk
            except OSError as exc:  # an unreadable file cannot be shown credential-free
                found.append(f'{path}: {exc.strerror}')
    require(not found, f'credentials left in the attempt, or unreadable files: {found}')


# ---------------------------------------------------------------- judge processes

def record_signal(signum, _frame):
    PENDING.append(signum)


def handle_signals():
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, record_signal)


# macOS per-user agents launchd starts for any account that uses notifications or preferences (seen 2026-10-01):
# command line -> the executable the kernel must report for it (on the read-only system volume).
OS_AGENTS = {'/usr/sbin/distnoted agent': '/usr/sbin/distnoted', '/usr/sbin/cfprefsd agent': '/usr/sbin/cfprefsd'}


def executable(pid):
    """The kernel's executable path for a pid (proc_pidpath); unlike argv it cannot be set by the process."""
    buffer = ctypes.create_string_buffer(4096)
    length = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True).proc_pidpath(int(pid), buffer, 4096)
    return buffer.value.decode() if length > 0 else None


def judge_rows(os_agents=False):
    """Live processes of the judge uid (real or effective), as ps rows. A zombie has already exited (it runs nothing and
    holds no files) and is left for its parent to reap. A macOS per-user agent that launchd itself starts for the
    account is not a judge process: launchd restarts it after any signal. One counts as such only when its parent is
    launchd, its command line is exactly one in OS_AGENTS and the kernel reports that agent's system executable; it is
    reported and never signalled (Addendum C2). Anything else counts."""
    proc = subprocess.run(['/bin/ps', '-axo', 'pid=,ppid=,ruid=,uid=,stat=,etime=,command='], capture_output=True,
                          text=True)
    require(proc.returncode == 0 and proc.stdout.strip(), f'ps failed: rc={proc.returncode} {proc.stderr[-200:]}')
    judges, agents = [], []
    for line in proc.stdout.splitlines():
        fields = line.split(None, 6)  # pid ppid ruid uid stat etime [command]; the command may be empty or blank
        require(len(fields) >= 6, f'unparsed ps row: {line!r}')
        if str(JUDGE_UID) not in fields[2:4] or 'Z' in fields[4]:
            continue
        command = fields[6].strip() if len(fields) > 6 else ''
        agent = fields[1] == '1' and command in OS_AGENTS and executable(fields[0]) == OS_AGENTS[command]
        (agents if agent else judges).append(line.strip())
    return agents if os_agents else judges


def judge_pids():
    return [row.split()[0] for row in judge_rows()]


def judge_signal(name):
    """Signal every judge process (not the OS agents), as the judge, by pid; never any other uid. kill exits non-zero
    when a pid has already gone, so the outcome is judged by judge_rows() afterwards."""
    pids = judge_pids()
    if not pids:
        return
    proc = subprocess.run([SUDO, '-n', '-u', JUDGE, '/bin/kill', f'-{name}', *pids], capture_output=True, text=True)
    errors = [line for line in proc.stderr.splitlines() if line.strip()]
    gone = all(re.fullmatch(r'kill: \d+: No such process', line.strip()) for line in errors)
    require(proc.returncode == 0 or (errors and gone),
            f'kill as the judge failed: rc={proc.returncode} {proc.stderr[-200:]}')


def judge_quiesce():
    """No judge process may remain: TERM, a grace period, KILL, a longer grace (a process may need time to leave the
    kernel), then none may be alive; the failure names each survivor."""
    agents = judge_rows(os_agents=True)
    if agents:
        print(json.dumps({'os_agents_not_signalled': agents}), file=sys.stderr, flush=True)
    if not judge_pids():
        return
    for name, grace in (('TERM', 30), ('KILL', 60)):
        judge_signal(name)
        deadline = time.time() + grace
        while judge_pids() and time.time() < deadline:
            time.sleep(0.5)
        if not judge_pids():
            return
    fail(f'judge processes survive SIGKILL: {judge_rows()}')


def run(argv, cwd, env, out, err, timeout, stdin_path=None):
    """Run argv as the judge with exactly env: sudo keeps only the names listed (HOME and TMPDIR are always in env),
    and no secret is ever in argv. stdin, stdout and stderr are regular files opened by the runner (the Codex wrapper
    refuses pipes). On timeout or a recorded signal, TERM then KILL every judge process; after every run none remains."""
    require({'HOME', 'TMPDIR'} <= set(env), 'the judge environment must set HOME and TMPDIR')
    command = [SUDO, '-n', '-u', JUDGE, f'--preserve-env={",".join(sorted(env))}', '--', *map(str, argv)]
    error, child = None, None
    with open(stdin_path or os.devnull, 'rb') as stdin, open_out(out) as stdout, open_out(err) as stderr:
        try:
            child = subprocess.Popen(command, cwd=cwd, env=env, stdin=stdin, stdout=stdout, stderr=stderr)
            deadline = time.time() + timeout
            while child.poll() is None:
                if PENDING or time.time() > deadline:
                    error = f'signal {PENDING[0]}' if PENDING else 'runner-timeout'
                    break
                time.sleep(0.25)
            if child.poll() is None:
                judge_signal('TERM')  # verify-judges tears down its seat runners on TERM
                stopped = time.time() + 120
                while child.poll() is None and time.time() < stopped:
                    time.sleep(0.25)
                if child.poll() is None:
                    judge_signal('KILL')
            wait_child(child)
        finally:
            if child is not None and child.poll() is None:
                judge_signal('KILL')
                wait_child(child)
            judge_quiesce()
    return (child.returncode if error is None else None), error


def wait_child(child):
    try:
        child.wait(timeout=60)
    except subprocess.TimeoutExpired:
        fail(f'sudo child {child.pid} did not exit after its judge processes were stopped')


def judge(work, env, base):
    argv = [sys.executable, base / 'product/config/skills/_shared/verify-judges.py', '--devlyn-dir', work / '.devlyn']
    return run(argv, work, env, base / 'judges.stdout', base / 'judges.stderr', 1800)


def transport(work):
    facts = []
    for stem in SEATS:
        path = work / '.devlyn' / f'{stem}.prompt.transport.json'
        record = load(path) if path.is_file() else {}
        facts.append({'seat': stem, 'outcome': record.get('outcome'), 'exit_code': record.get('exit_code'),
                      'elapsed_ms': record.get('elapsed_ms')})
    return facts


def claude_sessions(base):
    return sorted((base / 'judge-home/.claude/projects').rglob('*.jsonl'))


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
    isolate()
    rows = manifest()['rounds']
    rubric = (PRODUCT['G'] / VERIFY_MD).read_bytes()
    code = {name: runpy.run_path(str(PRODUCT['G'] / 'config/skills/_shared' / file)) for name, file in (
        ('role', 'role-config.py'), ('auth', 'judge-role-evidence.py'), ('judges', 'verify-judges.py'),
        ('parser', 'judge-output-parser.py'))}
    results = []
    for row in rows:
        tok = row['token']
        with attempt('stub-G', tok, 'G', stub=True) as (base, _row, work, env):
            code_, error = judge(work, env, base)
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
        results.append({'token': tok, 'attempt': str(base.relative_to(DEV)), 'verdict': summary['verdict'],
                        'carriers': carriers})
    dump(DEV / 'stub-G/result.json', {'rounds': len(results), 'results': results})
    print(json.dumps({'rounds': len(results), 'all_pass': True}))


# ---------------------------------------------------------------- inventory and the judge's read check

def scan_roots():
    # The registration's roots plus /private/tmp and $TMPDIR (Addendum C1).
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


def inventory(label):
    """Read-only: Git object stores holding the 0227 corpus commit and files naming 0227 hidden material. Nothing found
    is changed; `check` then shows the judge cannot open any of it."""
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
    marker_file = SCRATCH / f'markers-{os.getpid()}'
    lines = markers()
    write_bytes(marker_file, ('\n'.join(lines) + '\n').encode('utf-8'))
    try:
        rg = subprocess.run(['rg', '-l', '-uu', '--no-messages', '-F', '-f', str(marker_file), *map(str, roots)],
                            capture_output=True, text=True)
    finally:
        remove_file(marker_file)
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


def hidden_paths(record):
    """Everything the judge must not open: inventoried files, each object store and its HEAD, the research tree and its
    hidden corpus files, the other 0227 roots, the hidden entries of the 0227 root, and the 0228 root's own files."""
    paths = list(record['files'])
    for store in record['object_stores']:
        paths += [store, str(Path(store) / 'HEAD')]
    paths += [str(RESEARCH), *map(str, sorted(EVIDENCE.glob('corpus/*/hidden/*')))]
    paths += record['roots0227']
    paths += [str(p) for p in SRC.iterdir() if p.name not in SRC_VISIBLE]
    paths += [str(p) for p in (SRC / 'toolchains').iterdir()]  # each opened only for its own round's run
    paths += [str(p) for p in DEV.iterdir()] + [str(DEV)]
    for kind in KINDS:  # every earlier attempt, by its known name, and its work tree
        for root in sorted((DEV / kind).glob('rep-*')) + sorted((DEV / kind).glob('*/rep-*')):
            paths += [str(root), str(root / 'work'), str(root / 'work/.devlyn')]
    return sorted(set(paths))


OPENER = ('import json,os,sys\nopened=[]\nfor p in json.load(sys.stdin):\n try:\n'
          '  os.listdir(p) if os.path.isdir(p) else open(p,"rb").read(1)\n  opened.append(p)\n'
          ' except OSError: pass\nprint(json.dumps(opened))\n')


def judge_opens(paths, workdir):
    """As the judge, try to list or open each path; returns those that succeeded (read-only, nothing changed)."""
    request = SCRATCH / f'open-{os.getpid()}.json'
    out, err = SCRATCH / f'open-{os.getpid()}.out', SCRATCH / f'open-{os.getpid()}.err'
    write_bytes(request, json.dumps(paths).encode('utf-8'))
    env = {'HOME': '/var/empty', 'TMPDIR': '/var/empty', 'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}
    try:
        code, error = run([sys.executable, '-c', OPENER], workdir, env, out, err, 600, stdin_path=request)
        require(code == 0 and error is None, f'judge open check failed: rc={code} {error} {err.read_text()[-300:]}')
        return json.loads(out.read_text())
    finally:
        for path in (request, out, err):
            remove_file(path)


def check(label):
    handle_signals()
    isolate()
    record = fresh_inventory(label)
    paths = hidden_paths(record)
    opened = judge_opens(paths, '/var/empty')
    print(json.dumps({'checked': len(paths), 'opened': opened}))
    require(not opened, f'the judge can open {len(opened)} hidden paths: {opened[:10]}')
    return paths


# ---------------------------------------------------------------- R1 isolation probe

def probe(label, transcript):
    handle_signals()
    paths = check(label)
    transcript = Path(transcript)
    hidden = EVIDENCE / 'corpus/J4/hidden/mechanism.md'
    head = Path('/Users/aipalm/Documents/GitHub/devlyn-cli/.git/HEAD')
    targets = {'transcript': transcript, 'hidden': hidden, 'git_head': head}
    tok = next(r['token'] for r in manifest()['rounds'] if r['repo'] == 'node-lru-cache')
    marker = sha256(f'{time.time()}'.encode())[:16]
    result = {'token': tok, 'checked': len(paths)}
    with attempt('probe', tok, 'F') as (base, _row, work, env):
        result['attempt'] = str(base.relative_to(DEV))
        # Prompts and outputs live in an owner-only folder: after one judge process has run in the attempt, the runner
        # writes no path there (a planted link could redirect it); it reads attempt files only once no judge remains.
        io_dir = RESULTS / f'probe-{tok}-{base.name}'
        make_dir(io_dir)
        # A judge-readable control file outside the work tree shows that a failed read is the filesystem, not a policy.
        control = base / 'control.txt'
        write_bytes(control, (marker + '\n').encode())
        files_ = [control, *targets.values()]
        listing = '\n'.join(f'{index}. {path}' for index, path in enumerate(files_, 1))
        ask = ('report the first line of each file below. For a file that cannot be read, give READ-FAILED and the '
               'error message instead. Reply with one line per file, "<number>: <result>".')
        write_bytes(io_dir / 'claude.prompt', f'Using only the Read tool, read each file separately and {ask}\n{listing}\n'.encode())
        # 2>&1: one pipe, so head's error lines and the control's line stay whole in the tool output.
        command = 'head -n 1 ' + ' '.join(shlex.quote(str(p)) for p in files_) + ' 2>&1'
        write_bytes(io_dir / 'codex.prompt', f'Run exactly one shell command, `{command}`, then {ask}\n{listing}\n'.encode())
        acl_tree(base, ATTEMPT_ACES)
        result['opened'] = judge_opens([str(p) for p in targets.values()], work)
        result['control_opened'] = judge_opens([str(control)], work) == [str(control)]
        result['claude_rc'], result['claude_error'] = run(
            [SRC / 'bin/claude', '-p', '--permission-mode', 'dontAsk', '--tools', 'Read', '--allowedTools', 'Read',
             '--setting-sources', 'project', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
             '--model', 'claude-opus-5-5', '--output-format', 'json'],
            work, with_token(env), io_dir / 'claude.stdout', io_dir / 'claude.stderr', 600,
            stdin_path=io_dir / 'claude.prompt')
        # The pinned Codex with the isolated wrapper's flags except --ephemeral: its plain stderr and JSON events omit
        # reads made through its built-in tools, while the rollout records every tool call with its output.
        result['codex_rc'], result['codex_error'] = run(
            [SRC / 'bin/codex', 'exec', '--json', '--ignore-user-config', '--ignore-rules', '--disable', 'codex_hooks',
             '--disable', 'hooks', '--skip-git-repo-check', '-C', work, '-s', 'read-only', '-m', 'gpt-6-astra',
             '-c', 'model_reasoning_effort=high', '-'],
            work, env, io_dir / 'codex.stdout', io_dir / 'codex.stderr', 900, stdin_path=io_dir / 'codex.prompt')
    # Claude: each target has its own Read call, whose own result names EACCES.
    reads, outcomes = {}, {}
    for session in claude_sessions(base):
        for line in session.read_text(encoding='utf-8').splitlines():
            for block in (json.loads(line).get('message') or {}).get('content', []) or []:
                if isinstance(block, dict) and block.get('type') == 'tool_use' and block.get('name') == 'Read':
                    reads[block.get('id')] = (block.get('input') or {}).get('file_path')
                elif isinstance(block, dict) and block.get('type') == 'tool_result' and block.get('is_error'):
                    outcomes[block.get('tool_use_id')] = json.dumps(block.get('content'))  # errors only
    # Codex: the one head command's own output carries a separate `head: <path>: Permission denied` line per target
    # (strerror(EACCES)), and the control file's first line.
    calls, outputs = {}, {}
    for rollout in (Path(env['CODEX_HOME']) / 'sessions').rglob('*.jsonl'):
        for line in rollout.read_text(encoding='utf-8').splitlines():
            payload = json.loads(line).get('payload') or {}
            if payload.get('type') in ('function_call', 'custom_tool_call'):
                calls[payload.get('call_id')] = runs_only(payload, command)
            elif payload.get('type') in ('function_call_output', 'custom_tool_call_output'):
                outputs[payload.get('call_id')] = '\n'.join(collect_text(payload.get('output')))
    # One call that ran exactly the prescribed command, and nothing else, must carry every denial and the control.
    complete = [call for call, ok in calls.items() if ok and marker in outputs.get(call, '').splitlines()
                and all(f'head: {target}: Permission denied' in outputs.get(call, '').splitlines()
                        for target in targets.values())]
    for key, target in targets.items():
        result[f'claude_{key}_denied'] = any(path == str(target) and 'EACCES' in outcomes.get(use, '')
                                             for use, path in reads.items())
        result[f'codex_{key}_denied'] = bool(complete)
    envelope = load(io_dir / 'claude.stdout') if (io_dir / 'claude.stdout').read_text().strip().startswith('{') else {}
    result['claude_control_read'] = marker in str(envelope.get('result', ''))
    result['codex_control_read'] = bool(complete)
    result.update(claude_session=bool(claude_sessions(base)), codex_session=bool(calls), judge_processes=judge_rows())
    checks = [not PENDING, result['opened'] == [], result['control_opened'], result['claude_rc'] == 0,
              result['codex_rc'] == 0, result['claude_control_read'], result['codex_control_read'],
              result['claude_session'], result['codex_session'], not result['judge_processes']]
    checks += [result[f'{seat}_{key}_denied'] for seat in ('claude', 'codex') for key in targets]
    result['pass'] = all(checks)
    dump(io_dir / 'probe.json', result)
    print(json.dumps(result))


def runs_only(payload, command):
    """True when a rollout tool call ran exactly `command` and did nothing else: a shell function call whose cmd is the
    command or whose argv is `<shell> -c|-lc <command>`, or a code-mode `exec` whose entire input runs the command and
    returns that run's `.output` (the form Codex used in the earlier probes). A second `cmd` key, any option outside a
    short allowlist, or any extra statement is refused."""
    raw = payload.get('input') if payload.get('type') == 'custom_tool_call' else payload.get('arguments')
    if not isinstance(raw, str):
        return False
    if payload.get('type') == 'function_call':
        try:
            arguments = json.loads(raw)
        except ValueError:
            return False
        value = arguments.get('cmd', arguments.get('command')) if isinstance(arguments, dict) else None
        if isinstance(value, str):
            return value == command
        shells = {'sh', 'bash', 'zsh', '/bin/sh', '/bin/bash', '/bin/zsh'}
        return isinstance(value, list) and len(value) == 3 and value[0] in shells and value[1] in ('-c', '-lc') \
            and value[2] == command
    literal = re.escape(json.dumps(command)[1:-1])
    option = r'\s*,\s*(?:max_output_tokens|yield_time_ms|timeout_ms)\s*:\s*\d+'
    call = r'await\s+tools\.exec_command\(\s*\{\s*cmd\s*:\s*"' + literal + '"(?:' + option + r')*\s*\}\s*\)'
    forms = (r'text\(\s*\(\s*' + call + r'\s*\)\.output\s*\)\s*;?',
             r'const\s+(\w+)\s*=\s*' + call + r'\s*;?\s*text\(\s*\1\.output\s*\)\s*;?')
    return any(re.fullmatch(form, raw.strip()) for form in forms)


def collect_text(value):
    """Every string inside a rollout tool output (a string, or a list of {"text": ...} parts)."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [text for item in value for text in collect_text(item)]
    if isinstance(value, dict):
        return [text for item in value.values() for text in collect_text(item)]
    return []


# ---------------------------------------------------------------- live batches

def batch(plan_file, label):
    handle_signals()
    check(label)  # fail closed if the judge can open any inventoried hidden path
    items = load(Path(plan_file))
    require(sha256((SRC / 'bin/claude').read_bytes()) == CLAUDE_SHA256, 'bin/claude differs from the pinned digest')
    check_tars(item['token'] for item in items)  # every required tar, before the first live call
    started = time.time()
    dump(DEV / 'batches' / f'{int(started)}.json', {'plan': str(plan_file), 'plan_sha256': sha256(Path(plan_file).read_bytes()),
                                                   'inventory': label})
    for index, item in enumerate(items):
        if PENDING:
            print(json.dumps({'batch_stopped': f'signal {PENDING[0]}', 'completed': index}), flush=True)
            fail(f'batch stopped by signal after {index} replays')
        arm, tok = item['arm'], item['token']
        began = time.time()
        with attempt(arm, tok, arm) as (base, _row, work, env):
            rc, error = judge(work, with_token(env), base)
        facts = {'index': index, 'arm': arm, 'token': tok, 'attempt': str(base.relative_to(DEV)), 'rc': rc,
                 'error': error, 'elapsed_s': round(time.time() - began, 1), 'carriers': transport(work),
                 'claude_sessions': len(claude_sessions(base))}
        append_line(RECORDS, json.dumps(facts))
        print(json.dumps(facts), flush=True)  # transport facts only; verdicts stay in the attempt folder
    print(json.dumps({'batch_done': len(items), 'elapsed_s': round(time.time() - started, 1)}))


# ---------------------------------------------------------------- post-batch (research checkout)

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


def scan(label, attempts):
    """Seat tool inputs naming hidden paths (the judge could not open them; this records attempts). Claude reads are
    definite; Codex shell words are leads (0227), and Codex code-mode reads leave no stderr record (Addendum C1)."""
    code = screen0227()
    record = load(DEV / f'inventory-{label}.json')
    excluded = [Path(p).resolve() for p in hidden_paths(record)]
    for attempt in attempts:
        base = DEV / attempt
        work = base / 'work'
        tok = base.relative_to(DEV).parts[1]
        repo = next(r['repo'] for r in manifest()['rounds'] if r['token'] == tok)
        allowed = [p.resolve() for p in (base, SRC / 'bin', SRC / 'toolchains' / repo)]
        outside, ambiguous = set(), []

        def check_read(raw, cwd, origin, strong):
            if any(char in raw for char in '{}*?[]$`~'):
                ambiguous.append((origin, raw))
                return
            path = (Path(raw) if Path(raw).is_absolute() else cwd / raw).resolve()
            if under(path, allowed):
                return
            if under(path, excluded):
                (outside.add(str(path)) if strong else ambiguous.append((origin, raw)))
            elif any(target.is_relative_to(path) for target in excluded):
                ambiguous.append((origin, raw))  # an ancestor of a hidden path

        for session in claude_sessions(base):
            for line in session.read_text(encoding='utf-8').splitlines():
                message = json.loads(line).get('message') or {}
                for block in message.get('content', []) if isinstance(message, dict) else []:
                    if isinstance(block, dict) and block.get('type') == 'tool_use' and block.get('name') in (
                            'Read', 'Grep', 'Glob'):
                        for key in ('file_path', 'path'):
                            raw = (block.get('input') or {}).get(key)
                            if isinstance(raw, str):
                                check_read(raw, work, 'claude-' + block['name'], True)
        stderr = work / '.devlyn/codex-judge.r0.stderr'
        prompt = work / '.devlyn/codex-judge.r0.prompt'
        if stderr.is_file():
            paths, unparsed = code['codex_exec_paths'](stderr.read_text(encoding='utf-8'),
                                                      prompt.read_text(encoding='utf-8') if prompt.is_file() else None)
            ambiguous.extend(('codex-block', raw) for raw in unparsed)
            for raw, cwd in paths:
                check_read(raw, cwd, 'codex-word', False)
        else:
            ambiguous.append(('codex-stderr', '<missing>'))
        print(json.dumps({'attempt': attempt, 'excluded_reads': sorted(outside), 'ambiguous': ambiguous}))


def main(argv):
    command, args = argv[0], argv[1:]
    if command == 'stage':
        stage(*args)
    elif command == 'plan':
        print(json.dumps(plan(), indent=2))
    elif command == 'classify':
        classify(args)
    elif command == 'scan':
        scan(args[0], args[1:])
    else:
        staged()
        if command == 'product':
            product_check()
        elif command == 'stub':
            stub()
        elif command == 'inventory':
            inventory(*args)
        elif command == 'check':
            check(*args)
        elif command == 'probe':
            probe(*args)
        elif command == 'batch':
            batch(*args)
        else:
            fail(f'unknown command {command}')


if __name__ == '__main__':
    main(sys.argv[1:])
