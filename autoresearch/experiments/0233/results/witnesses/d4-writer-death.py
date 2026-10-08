"""Claim W1 (D4): a FIFO probe in the tree's own tests cannot bound a writer failure, so the test hangs instead of
terminating its owned writer/readers.

Obligation (D4 task, 6th): "Timeout/error probes terminate owned writer/readers and remove only their fixture paths;
no sleeps-as-proof race test."

Trigger (the finding's own): the test-owned FIFO writer dies just before it opens the FIFO for writing. Realised
without editing the tree: a sitecustomize module (on PYTHONPATH for the test process and every child it starts) makes
any blocking write-open of a FIFO -- builtins/io.open in a write mode, or os.open with O_WRONLY/O_RDWR and without
O_NONBLOCK -- end the writer: a child process exits with status 1, a non-main thread of the test process raises EIO.
Nonblocking opens (probes that release a blocked reader) and every other operation are untouched.

Each FIFO test of the tree (collected test ids containing "fifo", from test files that call mkfifo) runs in its own
pytest process, all concurrently, with pytest's faulthandler dumping stacks of a test still running after 140 s.
Required behaviour: every such test finishes (it is expected to fail, since its writer died) within DEADLINE seconds.
A test still running at the deadline is killed and the defect reproduces. A tree with no FIFO writer test cannot hang
this way and passes; a FIFO test whose writer never reached the injected open is reported.

Run from the tree root (/work). Exit 1 = reproduces, 0 = every FIFO probe terminated, 2 = witness error.
"""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import traceback

DEADLINE = 150

SITE = r'''
import builtins, errno, io, os, stat, threading
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

def _writer_dies(path):
    child = os.getpid() != int(_owner)
    if _log:
        fd = _real_os_open(_log, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        _real_write(fd, ('%s %s %s\n' % ('child' if child else 'thread', os.getpid(), os.fspath(path))).encode()
                    if not isinstance(path, bytes) else b'bytes-path\n')
        _real_close(fd)
    if child:
        os._exit(1)
    raise OSError(errno.EIO, 'injected writer failure before opening the FIFO', path)

def _injected():
    return os.getpid() != int(_owner) or threading.current_thread() is not threading.main_thread()

def _open(file, mode='r', *args, **kwargs):
    if not isinstance(file, int) and any(c in mode for c in 'wax+') and _injected() and _fifo(file):
        _writer_dies(file)
    return _real_open(file, mode, *args, **kwargs)

def _os_open(path, flags, *args, **kwargs):
    if flags & (os.O_WRONLY | os.O_RDWR) and not flags & os.O_NONBLOCK and _injected() and _fifo(path):
        _writer_dies(path)
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
        return finish(False, {'note': 'no test file creates a FIFO'})
    collect = subprocess.run([sys.executable, '-m', 'pytest', '--collect-only', '-q', '-p', 'no:cacheprovider', *files],
                             capture_output=True, text=True, env=base_env, timeout=120)
    ids = [line.strip() for line in collect.stdout.splitlines() if '::' in line and 'fifo' in line.lower()]
    if collect.returncode != 0 or not ids:
        raise RuntimeError('collection failed or found no FIFO test: %s' % (collect.stdout + collect.stderr)[-600:])
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
    for run in runs:
        hung = run['process'].poll() is None
        if hung:
            os.killpg(run['process'].pid, signal.SIGKILL)
            run['process'].wait()
        run['out'].close()
        output = open(run['out'].name, errors='replace').read()
        fired = open(run['log']).read().split('\n') if os.path.exists(run['log']) else []
        results.append(dict(test=run['test'], hung=hung, exit=None if hung else run['process'].returncode,
                            injected=[line for line in fired if line][:3],
                            stack=stack(output) if hung else None, last=output.strip().splitlines()[-1:]))
    hung = [r for r in results if r['hung']]
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
    sys.stdout.flush()
    sys.exit(1 if reproduced else 0)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        print('WITNESS ERROR: ' + traceback.format_exc())
        sys.stdout.flush()
        sys.exit(2)
