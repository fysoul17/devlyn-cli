"""0236 witness d4-writer-strict (registration 0236 §4, criterion 3): the strict form of the 0233 witness
d4-writer-death. A tree must positively show the bound for every FIFO test, under writer death and writer stall.

Obligation (D4 task, 6th): "Timeout/error probes terminate owned writer/readers and remove only their fixture paths;
no sleeps-as-proof race test."

Injection, without editing the tree: a sitecustomize module (on PYTHONPATH for the test process and every Python child
it starts) installs a Python audit hook. On the 'open' audit event (builtins.open, io.open, io.FileIO and os.open) for a
FIFO opened for writing (O_WRONLY or O_RDWR) without O_NONBLOCK, in a child process or a non-main thread of the test
process, it injects before the open happens:
- death: the writer ends just before opening (a child process exits with status 1, a thread's open raises EIO);
- stall: the writer pauses STALL seconds, then performs the real blocking open.
Every such write-open is injected. Nonblocking write-opens (probes that release a blocked reader) are legitimate and
never injected. A blocking write-open on the test process's main thread is recorded, never injected (the test's own
reader could not proceed); it is not by itself a defect. Every FIFO write-open is recorded, injected or not.

Each FIFO test of the tree (collected ids containing "fifo", from test files that call mkfifo) runs in its own pytest
process under each injection, all concurrently. A test reproduces only on a demonstrated defect:
- it is still running at DEADLINE seconds (it is killed; pytest's faulthandler dumps its stacks at 140 s);
- at the end of its pytest session a non-main thread or a descendant process is still alive.
For the tree, it also reproduces when:
- a FIFO or symlink that did not exist before the runs remains outside the runs' pytest base temp directories;
- no test file creates a FIFO, collection fails, or it collects no FIFO test;
- under an injection, no test starts a FIFO writer at all.
A test's result under an injection is STOP, never a reproduction and never a pass, when:
- it starts a child the injection cannot reach (a non-Python program, a shell from os.system, or Python without the
  witness environment or with -I, -E or -S): unsupported instrumentation;
- writer not injectable: it made a nonblocking FIFO write-open in a child or a blocking one on the main thread, or it
  made FIFO write-opens other than main-thread nonblocking probes and the injection fired zero times in it.
  Main-thread nonblocking write-opens are reader-release probes: never injected, never a STOP;
- its pytest session ended without recording its survivors.
Only a test that is not STOP can show a demonstrated defect.
Not seen: os.open with dir_fd, ctypes or another C extension, and a nonblocking writer thread next to an injected decoy
writer in the same test.

Known limit: the stall is per write-open. Sequential injected blocking write-opens in one test stall STALL seconds
each, so a test with several of them can still be running at DEADLINE, and reproduces, even when each open is bounded;
four or more always do (4 x 40 s > 150 s).

Run from the tree root (/work). Exit 1 = reproduces: a test that is not STOP or the tree shows a demonstrated defect;
else 2 = STOP: some test is STOP, or a witness error (the instrumentation did not load in a test process, or the witness
itself failed); else 0.
"""
import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
import time
import traceback

DEADLINE = 150
STALL = 40
MODES = ('death', 'stall')

SITE = r'''
import errno, json, os, re, shutil, stat, sys, threading, time
_mode, _log_path, _stall = os.environ['WITNESS_MODE'], os.environ['WITNESS_LOG'], int(os.environ['WITNESS_STALL'])
_site = os.path.dirname(os.path.abspath(__file__))
if 'WITNESS_OWNER_PID' not in os.environ and os.getppid() == int(os.environ['WITNESS_PARENT']):
    os.environ['WITNESS_OWNER_PID'] = str(os.getpid())  # the pytest process the witness started
_owner = int(os.environ.get('WITNESS_OWNER_PID', '0'))
_ENV = ('WITNESS_MODE', 'WITNESS_LOG', 'WITNESS_STALL', 'WITNESS_PARENT', 'WITNESS_OWNER_PID')
_real_open, _real_write, _real_close, _exit = os.open, os.write, os.close, os._exit
_local = threading.local()


def _log(kind, detail=None):
    fd = _real_open(_log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        _real_write(fd, (json.dumps([kind, os.getpid(), detail], default=repr) + '\n').encode())
    finally:
        _real_close(fd)


def _fifo(path):
    try:
        return stat.S_ISFIFO(os.stat(path).st_mode)
    except (OSError, TypeError, ValueError):
        return False



def _calls(count):
    # (id, code, instruction) of the innermost Python frames below this hook (_calls, _on_open, _hook): the frame that
    # is calling open, or the opener= function and its caller. A frame suspended in one call keeps its instruction.
    try:
        frame = sys._getframe(3)
    except ValueError:
        return []
    found = []
    while frame is not None and len(found) < count:
        found.append((id(frame), frame.f_code, frame.f_lasti))
        frame = frame.f_back
    return found


def _context():
    if os.getpid() != _owner:
        return 'child'
    return 'thread' if threading.current_thread() is not threading.main_thread() else 'main'


def _on_open(path, mode, flags):
    # One audit event per open: builtins.open, io.open and io.FileIO report their mode string, os.open reports None.
    # An opener= call reports both; its os.open inside a stalled FileIO open of the same FIFO is not stalled again. The
    # pending record is bound to the stalled call (frame and instruction) and is consumed by the next open event, so
    # it never matches an os.open made after that call returned or raised.
    pending, _local.pending = getattr(_local, 'pending', None), None
    if (isinstance(path, int) or not isinstance(flags, int)
            or flags & os.O_ACCMODE not in (os.O_WRONLY, os.O_RDWR) or not _fifo(path)):
        return
    name, context, blocking = os.fsdecode(path), _context(), not flags & os.O_NONBLOCK
    if mode is None and pending and pending[0] == name and pending[1] in _calls(2):
        return
    _log('fifo-write', [context, blocking, name])
    if not blocking or context == 'main':
        return
    _log('inject', [_mode, context, name])
    if _mode == 'death':
        if context == 'child':
            _exit(1)
        raise OSError(errno.EIO, 'injected writer failure before opening the FIFO', path)
    time.sleep(_stall)
    calls = _calls(1)
    if mode is not None and calls:
        _local.pending = (name, calls[0])


def _uninstrumented(event, executable, argv, env):
    # Why a child this spawn starts cannot carry the instrumentation, or None (Python with the witness environment and
    # no option that drops it, or a program that does not exist, so nothing runs).
    env = os.environ if env is None else {os.fsdecode(k): os.fsdecode(v) for k, v in env.items()}
    argv = [argv] if isinstance(argv, (str, bytes, os.PathLike)) else list(argv or ())
    argv = [os.fsdecode(a) for a in argv]
    program = os.fsdecode(executable) if executable is not None else argv[0] if argv else ''
    found = program if os.sep in program else shutil.which(program, path=env.get('PATH', os.defpath))
    if not found or not os.access(found, os.X_OK):
        return None
    if not re.fullmatch(r'python[0-9.]*', os.path.basename(os.path.realpath(found))):
        return '%s started %s, which is not Python' % (event, found)
    missing = [k for k in _ENV if env.get(k) != os.environ.get(k)]
    if _site not in env.get('PYTHONPATH', '').split(os.pathsep):
        missing.append('PYTHONPATH')
    if missing:
        return '%s started Python without the witness environment (%s)' % (event, ', '.join(missing))
    options = iter(argv[1:])
    for token in options:
        if token[:1] != '-' or token == '-' or token.startswith('--'):
            break
        letters = token[1:]
        cut = next((i for i, c in enumerate(letters) if c in 'cmWX'), len(letters))
        dropped = sorted(set(letters[:cut]) & set('IES'))
        if dropped:
            return '%s started Python with -%s, which skips the instrumentation' % (event, dropped[0])
        if cut < len(letters):
            if letters[cut] in 'cm':
                break
            if cut == len(letters) - 1:
                next(options, None)  # the argument of -W or -X
    return None


def _on_spawn(event, executable, argv, env):
    try:
        reason = _uninstrumented(event, executable, argv, env)
    except Exception as exc:  # a spawn the witness cannot classify cannot be shown to carry the instrumentation
        reason = '%s could not be classified: %r' % (event, exc)
    _log('unsupported' if reason else 'spawn', reason or [event, executable])


def _hook(event, args):
    if event == 'open':
        _on_open(*args)
    elif event == 'subprocess.Popen':
        _on_spawn(event, args[0], args[1], args[3])
    elif event in ('os.posix_spawn', 'os.exec'):
        _on_spawn(event, *args)
    elif event == 'os.system':
        _log('unsupported', 'os.system started a shell')


_log('start', os.getppid())
sys.addaudithook(_hook)
'''

PLUGIN = r'''
import json, os, threading
import pytest


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session):
    """Survivors at session end: live non-main threads, and live descendant processes (by parent chain or session)."""
    me, table = os.getpid(), {}
    for entry in os.listdir('/proc'):
        if entry.isdigit():
            try:
                with open('/proc/%s/stat' % entry) as handle:
                    fields = handle.read().rsplit(')', 1)[1].split()
                with open('/proc/%s/cmdline' % entry, 'rb') as handle:
                    command = handle.read().replace(b'\0', b' ').decode(errors='replace').strip()
            except OSError:
                continue
            table[int(entry)] = (fields[0], int(fields[1]), int(fields[3]), command)
    descendants, frontier = set(), {me}
    while frontier:
        frontier = {pid for pid, row in table.items() if row[1] in frontier} - descendants
        descendants |= frontier
    processes = ['%d %s' % (pid, row[3][:200]) for pid, row in sorted(table.items())
                 if pid != me and (pid in descendants or row[2] == me) and row[0] not in ('Z', 'X')]
    threads = [t.name for t in threading.enumerate() if t is not threading.main_thread() and t.is_alive()]
    with open(os.environ['WITNESS_END'], 'w') as handle:
        json.dump(dict(threads=threads, processes=processes), handle)
'''


def main():
    root = os.getcwd()
    files = []
    for top, _, names in os.walk(os.path.join(root, 'tests')):
        for name in sorted(names):
            path = os.path.join(top, name)
            if name.endswith('.py') and 'mkfifo' in open(path, encoding='utf-8').read():
                files.append(os.path.relpath(path, root))
    base_env = dict(os.environ, PYTHONPATH=os.path.join(root, 'src'), PYTHONDONTWRITEBYTECODE='1')
    if not files:
        return finish(['no test file creates a FIFO'], {})
    collect = subprocess.run([sys.executable, '-m', 'pytest', '--collect-only', '-q', '-p', 'no:cacheprovider', *files],
                             capture_output=True, text=True, env=base_env, timeout=120)
    ids = [line.strip() for line in collect.stdout.splitlines() if '::' in line and 'fifo' in line.lower()]
    if collect.returncode != 0 or not ids:
        return finish(['collection failed or found no FIFO test'],
                      {'collect_exit': collect.returncode, 'tail': (collect.stdout + collect.stderr)[-600:]})
    work = tempfile.mkdtemp(prefix='witness-d4-')
    for name, text in (('sitecustomize.py', SITE), ('witness_session_end.py', PLUGIN)):
        with open(os.path.join(work, name), 'w') as handle:
            handle.write(text)
    runs = [dict(test=test, mode=mode, dir=os.path.join(work, 'run%d' % index))
            for index, (mode, test) in enumerate((mode, test) for mode in MODES for test in ids)]
    base_temps = {os.path.join(run['dir'], 'basetemp') for run in runs}
    before = fifos_and_links(base_temps)
    for run in runs:
        os.mkdir(run['dir'])
        env = dict(base_env, PYTHONPATH=work + os.pathsep + base_env['PYTHONPATH'], WITNESS_MODE=run['mode'],
                   WITNESS_STALL=str(STALL), WITNESS_LOG=os.path.join(run['dir'], 'log'),
                   WITNESS_END=os.path.join(run['dir'], 'end.json'), WITNESS_PARENT=str(os.getpid()))
        env.pop('WITNESS_OWNER_PID', None)
        run['out'] = open(os.path.join(run['dir'], 'out'), 'w')
        run['process'] = subprocess.Popen(
            [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-p', 'witness_session_end',
             '-o', 'faulthandler_timeout=140', '--basetemp', os.path.join(run['dir'], 'basetemp'), run['test']],
            stdout=run['out'], stderr=subprocess.STDOUT, env=env, start_new_session=True)
    end = time.monotonic() + DEADLINE
    while time.monotonic() < end and any(run['process'].poll() is None for run in runs):
        time.sleep(0.5)
    for run in runs:
        run['hung'] = run['process'].poll() is None
        if run['hung']:
            os.killpg(run['process'].pid, signal.SIGKILL)
            run['process'].wait()
        run['out'].close()
    left = sorted(fifos_and_links(base_temps) - before)
    defects, stops = [], []
    results = [evaluate(run, defects, stops) for run in runs]
    for mode in MODES:  # a mode where writers ran or could not be observed has a STOP or injected test already
        if not any(r['fifo_writes'] or r['unsupported'] for r in results if r['mode'] == mode):
            defects.append(f'{mode}: no FIFO test starts a FIFO writer')
    if left:
        defects.append(f'{len(left)} FIFO or symlink left outside the pytest base temp directories: {left[:5]}')
    finish(defects, {'tests': len(ids), 'runs': len(runs), 'stops': stops, 'results': results})


def evaluate(run, defects, stops):
    """One run's record. Appends its demonstrated defects, or, when the test cannot be instrumented, its writers were
    never injected or its session end was not recorded, a STOP reason instead: such a test never reproduces and never
    passes. A test process without the instrumentation is a witness error."""
    label = f'{run["test"]} [{run["mode"]}]'
    log = os.path.join(run['dir'], 'log')
    records = [json.loads(line) for line in open(log)] if os.path.exists(log) else []
    if not any(kind == 'start' and pid == run['process'].pid for kind, pid, _ in records):
        raise RuntimeError(f'{label}: the instrumentation did not load in the test process')
    unsupported = [detail for kind, _, detail in records if kind == 'unsupported']
    writes = [detail for kind, _, detail in records if kind == 'fifo-write']
    injected = [detail for kind, _, detail in records if kind == 'inject']
    output = open(os.path.join(run['dir'], 'out'), errors='replace').read()
    end = os.path.join(run['dir'], 'end.json')
    survivors = json.load(open(end)) if os.path.exists(end) else None
    if unsupported:
        stops.append(f'{label}: unsupported instrumentation: {unsupported[0]}')
    elif uninjectable := [w for w in writes if (w[0] == 'child' and not w[1]) or (w[0] == 'main' and w[1])]:
        stops.append(f'{label}: writer not injectable: {len(uninjectable)} nonblocking child or blocking main-thread '
                     f'FIFO write-open(s): {uninjectable[0]}')
    elif any(not (w[0] == 'main' and not w[1]) for w in writes) and not injected:
        stops.append(f'{label}: writer not injectable: {len(writes)} FIFO write-open(s), none injected: {writes[0]}')
    elif run['hung']:
        defects.append(f'{label}: still running at {DEADLINE} s')
    elif survivors is None:
        stops.append(f'{label}: the pytest session ended without recording its survivors')
    elif survivors['threads'] or survivors['processes']:
        defects.append(f'{label}: alive at session end: {survivors}')
    return dict(test=run['test'], mode=run['mode'], hung=run['hung'],
                exit=None if run['hung'] else run['process'].returncode, injected=injected[:3],
                fifo_writes=len(writes), main_thread_blocking_writes=sum(w[0] == 'main' and w[1] for w in writes),
                unsupported=unsupported[:3], survivors=survivors, stack=stack(output) if run['hung'] else None,
                last=output.strip().splitlines()[-1:])


def fifos_and_links(skip):
    """Every FIFO and symlink on the container's file systems outside /proc, /sys, /dev (except /dev/shm) and skip."""
    found = set()
    for top in ('/', '/dev/shm'):
        for path, dirs, names in os.walk(top):
            dirs[:] = [d for d in dirs if os.path.join(path, d) not in skip
                       and not (path == '/' and d in ('proc', 'sys', 'dev'))]
            for name in dirs + names:
                entry = os.path.join(path, name)
                try:
                    mode = os.lstat(entry).st_mode
                except OSError:
                    continue
                if stat.S_ISFIFO(mode) or stat.S_ISLNK(mode):
                    found.add(entry)
    return found


def stack(output):
    """Innermost frames of the main thread from pytest's faulthandler dump, or the output tail."""
    lines = output.splitlines()
    for index, line in enumerate(lines):
        if 'most recent call first' in line and ('Current thread' in line or 'Thread' in line):
            frames = [l.strip() for l in lines[index + 1:index + 40] if l.strip().startswith('File')]
            if any('test_' in f for f in frames):
                return frames[:8]
    return output[-500:]


def finish(defects, detail):
    """Exit 1 on a demonstrated defect, else 2 when a test is STOP, else 0."""
    stops = detail.get('stops', [])
    print(json.dumps(dict(reproduced=bool(defects), reasons=defects, **detail)))
    sys.stdout.flush()
    sys.exit(1 if defects else 2 if stops else 0)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        print('WITNESS ERROR: ' + traceback.format_exc())
        sys.stdout.flush()
        sys.exit(2)
