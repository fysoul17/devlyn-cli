# Origin: 0256/results/witnesses/d4-writer-stall.py; sha256 68324906c689757e30d51122f60f24057a0efea9225dee41ed9d03a466798fd9.
# 0261 deviation: finished probes without any injection are not applicable.
# Exit 1: a probe remains hung at the origin's deadline; exit 0: all probes finished
# and at least one was injected, regardless of pytest pass/fail.
# Exit 2: witness exception, pytest/sitecustomize infrastructure error, pytest exit 2/3/4,
# or setup/collection outcome errors before injection takes effect.
# Exit 3: no mkfifo-bearing test file, no collected FIFO test, pytest exit 5, or
# no hung probe and no test-owned writer reached the injected point.
"""Claim W2 (D4; 0256 d28 codex:1): a FIFO probe in the tree's own tests cannot bound a writer that connects and then
stalls, so the test hangs instead of terminating its owned writer/readers. In d28 the read runs in a pool thread that
is abandoned on timeout (shutdown(wait=False)); leaving the context then closes the buffered stream, whose close waits
for the lock the blocked reader holds, before the writer fixture can kill the writer.

Obligation (D4 task, 6th): "Timeout/error probes terminate owned writer/readers and remove only their fixture paths;
no sleeps-as-proof race test."

Trigger (the finding's own): the test-owned FIFO writer opens the FIFO for writing and then stalls, keeping its
descriptor open and writing nothing. Realised without editing the tree: a sitecustomize module (on PYTHONPATH for the
test process and every child it starts) makes any blocking write-open of a FIFO in a child process -- builtins/io.open
in a write mode, or os.open with O_WRONLY/O_RDWR and without O_NONBLOCK -- perform the real open and then sleep
forever holding it. Nonblocking opens (probes that release a blocked reader), opens in the test process itself and
every other operation are untouched; a writer in a thread of the test process is reported as not injected.

Each FIFO test of the tree (collected test ids containing "fifo", from test files that call mkfifo) runs in its own
pytest process, all concurrently, with pytest's faulthandler dumping stacks of a test still running after 140 s.
Required behaviour: every such test finishes (it is expected to fail, since its writer stalled) within DEADLINE
seconds. A test still running at the deadline is killed and the defect reproduces. A tree with no FIFO writer test
cannot hang this way and exits 3; a FIFO test whose writer never reached the injected open is reported.

The harness below is d4-writer-death.py's (W1), unchanged except for the injected writer behaviour.

Run from the tree root (/work). Exit 1 = reproduces, 0 = every FIFO probe terminated with at least one injection,
2 = witness error, 3 = not applicable (including no injection when none hung).
"""
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import traceback

DEADLINE = 150

SITE = r'''
import builtins, errno, io, os, stat, threading, time
_owner = os.environ.get('WITNESS_OWNER_PID')
if not _owner:
    os.environ['WITNESS_OWNER_PID'] = _owner = str(os.getpid())
_real_open, _real_os_open, _real_write, _real_close = builtins.open, os.open, os.write, os.close
_log = os.environ.get('WITNESS_LOG')

def _fifo(path):
    try:
        return isinstance(path, (str, bytes, os.PathLike)) and stat.S_ISFIFO(os.stat(path).st_mode)
    except OSError:
        return False

def _writer_stalls(path):
    if _log:
        fd = _real_os_open(_log, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        _real_write(fd, ('child %s %s\n' % (os.getpid(), os.fspath(path))).encode()
                    if not isinstance(path, bytes) else b'bytes-path\n')
        _real_close(fd)
    while True:
        time.sleep(3600)

def _note_thread(path):
    if _log:
        fd = _real_os_open(_log, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        _real_write(fd, b'thread-not-injected\n')
        _real_close(fd)

def _child():
    return os.getpid() != int(_owner)

def _open(file, mode='r', *args, **kwargs):
    if not isinstance(file, int) and any(c in mode for c in 'wax+') and _fifo(file):
        if _child():
            handle = _real_open(file, mode, *args, **kwargs)
            _writer_stalls(file)
        elif threading.current_thread() is not threading.main_thread():
            _note_thread(file)
    return _real_open(file, mode, *args, **kwargs)

def _os_open(path, flags, *args, **kwargs):
    if flags & (os.O_WRONLY | os.O_RDWR) and not flags & os.O_NONBLOCK and _fifo(path):
        if _child():
            fd = _real_os_open(path, flags, *args, **kwargs)
            _writer_stalls(path)
        elif threading.current_thread() is not threading.main_thread():
            _note_thread(path)
    return _real_os_open(path, flags, *args, **kwargs)

builtins.open = io.open = _open
os.open = _os_open
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
        print('not applicable: no test file creates a FIFO')
        sys.exit(3)
    collect = subprocess.run([sys.executable, '-m', 'pytest', '--collect-only', '-q', '-p', 'no:cacheprovider', *files],
                             capture_output=True, text=True, env=base_env, timeout=120)
    ids = [line.strip() for line in collect.stdout.splitlines() if '::' in line and 'fifo' in line.lower()]
    collection_output = collect.stdout + collect.stderr
    if (collect.returncode not in (0, 5) or 'No module named pytest' in collection_output or
            'Error in sitecustomize' in collection_output):
        raise RuntimeError('collection failed: %s' % (collect.stdout + collect.stderr)[-600:])
    if collect.returncode == 5 or not ids:
        print('not applicable: no collected FIFO test')
        sys.exit(3)
    work = tempfile.mkdtemp(prefix='witness-d4-')
    with open(os.path.join(work, 'sitecustomize.py'), 'w') as handle:
        handle.write(SITE)
    runs = []
    for index, test in enumerate(ids):
        log = os.path.join(work, 'log%d' % index)
        out = open(os.path.join(work, 'out%d' % index), 'w')
        env = dict(base_env, PYTHONPATH=work + os.pathsep + base_env['PYTHONPATH'], WITNESS_LOG=log)
        env.pop('WITNESS_OWNER_PID', None)
        process = subprocess.Popen([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                                    '-o', 'faulthandler_timeout=140', '--basetemp', os.path.join(work, 'bt%d' % index),
                                    test], stdout=out, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        runs.append(dict(test=test, process=process, out=out, log=log, started=time.monotonic()))
    end = time.monotonic() + DEADLINE
    while time.monotonic() < end and any(run['process'].poll() is None for run in runs):
        time.sleep(0.5)
    results = []
    setup_errors = []
    for run in runs:
        hung = run['process'].poll() is None
        if hung:
            os.killpg(run['process'].pid, signal.SIGKILL)
            run['process'].wait()
        run['out'].close()
        output = open(run['out'].name, errors='replace').read()
        fired = open(run['log']).read().split('\n') if os.path.exists(run['log']) else []
        injected = any(line.startswith('child') for line in fired)
        if ('No module named pytest' in output or 'Error in sitecustomize' in output or
                (not hung and (run['process'].returncode in (2, 3, 4) or
                 (not injected and re.search(r'ERROR at setup|\b[1-9]\d* errors?\b', output))))):
            setup_errors.append('FIFO test infrastructure failed: ' + output[-500:])
        results.append(dict(test=run['test'], hung=hung, exit=None if hung else run['process'].returncode,
                            injected=[line for line in fired if line.startswith('child')][:3],
                            threads=[line for line in fired if line.startswith('thread')][:1],
                            stack=stack(output) if hung else None, last=output.strip().splitlines()[-1:]))
    if setup_errors:
        raise RuntimeError('; '.join(setup_errors))
    hung = [r for r in results if r['hung']]
    if not hung and any(r['exit'] == 5 for r in results):
        print('not applicable: no collected FIFO test')
        sys.exit(3)
    finish(bool(hung), {'tests': len(results), 'hung': len(hung),
                        'not_injected': [r['test'] for r in results if not r['injected']], 'results': results})


def stack(output):
    """Innermost frames of the main thread from pytest's faulthandler dump, or the output tail."""
    lines = output.splitlines()
    for index, line in enumerate(lines):
        if 'most recent call first' in line and ('Current thread' in line or 'Thread' in line):
            frames = [l.strip() for l in lines[index + 1:index + 40] if l.strip().startswith('File')]
            if any('test_' in f for f in frames):
                return frames[:8]
    return output[-500:]


def finish(reproduced, detail):
    print(json.dumps(dict(reproduced=reproduced, **detail)))
    code = 1 if reproduced else 0
    if not reproduced and not any(r['injected'] for r in detail['results']):
        print('not applicable: no test-owned writer reached the injected point')
        code = 3
    sys.stdout.flush()
    sys.exit(code)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        print('WITNESS ERROR: ' + traceback.format_exc())
        sys.stdout.flush()
        sys.exit(2)
