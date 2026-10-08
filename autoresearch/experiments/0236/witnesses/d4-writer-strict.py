"""0236 witness d4-writer-strict (registration 0236 §4, criterion 3): the strict form of the 0233 witness
d4-writer-death. A tree must positively show the bound for every FIFO test, under writer death and writer stall.

Obligation (D4 task, 6th): "Timeout/error probes terminate owned writer/readers and remove only their fixture paths;
no sleeps-as-proof race test."

Injection, without editing the tree: a sitecustomize module (on PYTHONPATH for the test process and every child it
starts) intercepts the test-owned writer's blocking write-open of a FIFO -- builtins/io/_io.open in a write mode, or
os.open with O_WRONLY/O_RDWR and without O_NONBLOCK -- in a child process or a non-main thread of the test process:
- death: the writer ends just before opening (a child process exits with status 1, a thread raises EIO);
- stall: the writer pauses STALL seconds, then performs the real blocking open.
Nonblocking opens (probes that release a blocked reader) and every other operation are untouched.

Each FIFO test of the tree (collected ids containing "fifo", from test files that call mkfifo) runs in its own pytest
process under each injection, all concurrently. The defect reproduces (exit 1) when any of these holds:
- no test file creates a FIFO, collection fails, or it collects no FIFO test;
- under an injection, the injection fires in no test;
- a test started a writer that did not get the injection: the main thread of the test process opens a FIFO for
  writing through open(); data is written through a FIFO descriptor os.open returned without the injection (or that
  descriptor is wrapped in a writable file object); or the test starts a child process that cannot be injected
  because it did not load the instrumentation (not Python, a shell from os.system, or started without the
  environment);
- a test is still running at DEADLINE seconds (it is killed; pytest's faulthandler dumps its stacks at 140 s);
- at the end of its pytest session a non-main thread or a descendant process is still alive, or the session never
  reaches its end;
- a FIFO or symlink that did not exist before the runs remains outside the runs' pytest base temp directories.
Not seen: writer opens through io.FileIO, ctypes or another C extension.

Run from the tree root (/work). Exit 1 = reproduces, 0 = none of the above, 2 = witness error (the instrumentation did
not load in a test process, or the witness itself failed).
"""
import collections
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
import _io, builtins, errno, io, json, os, stat, subprocess, threading, time
_mode, _log_path, _stall = os.environ['WITNESS_MODE'], os.environ['WITNESS_LOG'], int(os.environ['WITNESS_STALL'])
_owner = int(os.environ.setdefault('WITNESS_OWNER_PID', str(os.getpid())))
_real_open, _real_os_open, _real_write, _real_writev = builtins.open, os.open, os.write, os.writev
_real_close, _real_fdopen, _real_system = os.close, os.fdopen, os.system
_real_execv, _real_execve, _real_spawn, _real_spawnp = os.execv, os.execve, os.posix_spawn, os.posix_spawnp
_real_execute = subprocess.Popen._execute_child
_free = set()  # FIFO descriptors opened for writing without the injection


def _log(kind, detail=None):
    fd = _real_os_open(_log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        _real_write(fd, (json.dumps([kind, os.getpid(), detail], default=repr) + '\n').encode())
    finally:
        _real_close(fd)


def _fifo(path, dir_fd=None):
    try:
        return isinstance(path, (str, bytes, os.PathLike)) and stat.S_ISFIFO(os.stat(path, dir_fd=dir_fd).st_mode)
    except (OSError, ValueError):
        return False


def _writer():
    """'child' or 'thread' when the caller is a writer the injection reaches, None on the test's main thread."""
    if os.getpid() != _owner:
        return 'child'
    return 'thread' if threading.current_thread() is not threading.main_thread() else None


def _inject(path, kind):
    _log('inject', [_mode, kind, os.fsdecode(path)])
    if _mode == 'death':
        if kind == 'child':
            os._exit(1)
        raise OSError(errno.EIO, 'injected writer failure before opening the FIFO', path)
    time.sleep(_stall)


def _write_mode(mode):
    return isinstance(mode, str) and any(c in mode for c in 'wax+')


def _open(file, mode='r', *args, **kwargs):
    if not isinstance(file, int) and _write_mode(mode) and _fifo(file):
        kind = _writer()
        if kind:
            _inject(file, kind)
        else:
            _log('escape', 'the main thread of the test process opened a FIFO for writing with open()')
    return _real_open(file, mode, *args, **kwargs)


def _os_open(path, flags, mode=0o777, *, dir_fd=None):
    if flags & (os.O_WRONLY | os.O_RDWR) and _fifo(path, dir_fd):
        kind = _writer()
        if kind and not flags & os.O_NONBLOCK:
            _inject(path, kind)
        else:
            fd = _real_os_open(path, flags, mode, dir_fd=dir_fd)
            _free.add(fd)
            return fd
    return _real_os_open(path, flags, mode, dir_fd=dir_fd)


def _wrote(fd, size, how):
    if size and fd in _free:
        _log('escape', 'data written by %s through a FIFO descriptor opened without the injection' % how)


def _write(fd, data):
    _wrote(fd, len(data), 'os.write')
    return _real_write(fd, data)


def _writev(fd, buffers):
    buffers = list(buffers)
    _wrote(fd, sum(len(b) for b in buffers), 'os.writev')
    return _real_writev(fd, buffers)


def _fdopen(fd, mode='r', *args, **kwargs):
    if fd in _free and _write_mode(mode):
        _log('escape', 'a FIFO descriptor opened without the injection wrapped in a writable file object')
    return _real_fdopen(fd, mode, *args, **kwargs)


def _close(fd):
    _free.discard(fd)
    return _real_close(fd)


def _execute_child(self, *args, **kwargs):
    _real_execute(self, *args, **kwargs)
    _log('spawn', self.pid)


def _spawner(real):
    def call(*args, **kwargs):
        pid = real(*args, **kwargs)
        _log('spawn', pid)
        return pid
    return call


def _exec(real):
    def call(*args, **kwargs):
        _log('exec')
        try:
            return real(*args, **kwargs)
        except BaseException:
            _log('exec-failed')
            raise
    return call


def _system(command):
    _log('escape', 'os.system started a shell, which the injection cannot reach')
    return _real_system(command)


_log('start')
builtins.open = io.open = _io.open = _open
os.open, os.write, os.writev, os.fdopen, os.close, os.system = _os_open, _write, _writev, _fdopen, _close, _system
os.execv, os.execve = _exec(_real_execv), _exec(_real_execve)
os.posix_spawn, os.posix_spawnp = _spawner(_real_spawn), _spawner(_real_spawnp)
subprocess.Popen._execute_child = _execute_child
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
                   WITNESS_END=os.path.join(run['dir'], 'end.json'))
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
    reasons = []
    results = [evaluate(run, reasons) for run in runs]
    for mode in MODES:
        if not any(r['injected'] for r in results if r['mode'] == mode):
            reasons.append(f'{mode}: the injection fired in no test')
    if left:
        reasons.append(f'{len(left)} FIFO or symlink left outside the pytest base temp directories: {left[:5]}')
    finish(reasons, {'tests': len(ids), 'runs': len(runs), 'results': results})


def evaluate(run, reasons):
    """One run's record; appends its reproduction reasons. A test process without the instrumentation is an error."""
    label = f'{run["test"]} [{run["mode"]}]'
    log = os.path.join(run['dir'], 'log')
    records = [json.loads(line) for line in open(log)] if os.path.exists(log) else []
    starts = collections.Counter(pid for kind, pid, _ in records if kind == 'start')
    if not starts[run['process'].pid]:
        raise RuntimeError(f'{label}: the instrumentation did not load in the test process')
    escapes = [detail for kind, _, detail in records if kind == 'escape']
    spawned = {detail for kind, _, detail in records if kind == 'spawn'}
    execs = (collections.Counter(pid for kind, pid, _ in records if kind == 'exec')
             - collections.Counter(pid for kind, pid, _ in records if kind == 'exec-failed'))
    escapes += [f'child process {pid} did not load the instrumentation' for pid in sorted(spawned | set(execs))
                if starts[pid] < (pid in spawned) + execs[pid]]
    injected = [detail for kind, _, detail in records if kind == 'inject']
    output = open(os.path.join(run['dir'], 'out'), errors='replace').read()
    survivors = None
    if escapes:
        reasons.append(f'{label}: a writer did not get the injection: {escapes[0]}')
    if run['hung']:
        reasons.append(f'{label}: still running at {DEADLINE} s')
    elif not os.path.exists(os.path.join(run['dir'], 'end.json')):
        reasons.append(f'{label}: the pytest session never reached its end')
    else:
        survivors = json.load(open(os.path.join(run['dir'], 'end.json')))
        if survivors['threads'] or survivors['processes']:
            reasons.append(f'{label}: alive at session end: {survivors}')
    return dict(test=run['test'], mode=run['mode'], hung=run['hung'],
                exit=None if run['hung'] else run['process'].returncode, injected=injected[:3], escapes=escapes[:3],
                survivors=survivors, stack=stack(output) if run['hung'] else None,
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


def finish(reasons, detail):
    print(json.dumps(dict(reproduced=bool(reasons), reasons=reasons, **detail)))
    sys.stdout.flush()
    sys.exit(1 if reasons else 0)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        print('WITNESS ERROR: ' + traceback.format_exc())
        sys.stdout.flush()
        sys.exit(2)
