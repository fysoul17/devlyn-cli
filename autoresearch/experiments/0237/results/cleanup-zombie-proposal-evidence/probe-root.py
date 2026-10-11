import ctypes
import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
import tempfile
import time

BASE = Path('/proposal')
api = runpy.run_path(str(BASE / 'baseline/task-complete.py'))
results = {'uid': os.getuid(), 'pid': os.getpid(), 'kernel': os.uname().release, 'cases': []}

def status(pid):
    return dict(line.split(':', 1) for line in Path(f'/proc/{pid}/status').read_text().splitlines() if ':' in line)

def observe(pid, target, label):
    state = status(pid)
    item = {'case': label, 'pid': pid, 'state': state['State'].strip(), 'threads': state['Threads'].strip(), 'ppid': state['PPid'].strip()}
    for kind, fn in [('fd', lambda: [str(p) for p in Path(f'/proc/{pid}/fd').iterdir()]), ('cwd', lambda: os.readlink(f'/proc/{pid}/cwd'))]:
        try:
            item[kind] = fn()
        except OSError as exc:
            item[kind] = {'exception': type(exc).__name__, 'errno': exc.errno}
    try:
        api['stopped_writers'](target)
        item['baseline'] = 'RETURNED'
    except Exception as exc:
        item['baseline'] = {'exception': type(exc).__name__, 'message': str(exc)}
    results['cases'].append(item)
    return item

def wait_until(fn):
    end = time.monotonic() + 5
    while time.monotonic() < end:
        value = fn()
        if value:
            return value
        time.sleep(.02)
    raise AssertionError('fixture did not become ready')

with tempfile.TemporaryDirectory(prefix='zombie-fixture-') as tmp:
    target = Path(tmp)
    pid = os.fork()
    if not pid:
        os.setsid()
        os._exit(0)
    try:
        wait_until(lambda: status(pid)['State'].strip().startswith('Z'))
        observe(pid, target, 'unreaped-single-thread-zombie')
        procfd = os.open(f'/proc/{pid}', os.O_RDONLY | os.O_DIRECTORY)
    finally:
        os.waitpid(pid, 0)
    try:
        try:
            fd = os.open('status', os.O_RDONLY, dir_fd=procfd)
            try:
                value = os.read(fd, 65536).decode()
                results['pinned_proc_after_reap'] = {'unexpected_status': value}
            finally:
                os.close(fd)
        except OSError as exc:
            results['pinned_proc_after_reap'] = {'exception': type(exc).__name__, 'errno': exc.errno}
    finally:
        os.close(procfd)

    code = '''import ctypes, os, pathlib, threading, time
path = pathlib.Path(os.environ['PROBE_TARGET']) / 'heartbeat'
def worker():
    with path.open('w') as f:
        while True:
            f.write('x'); f.flush(); time.sleep(.02)
threading.Thread(target=worker).start()
ctypes.CDLL(None).pthread_exit(None)
'''
    child = subprocess.Popen([sys.executable, '-c', code], env={**os.environ, 'PROBE_TARGET': str(target)})
    try:
        wait_until(lambda: status(child.pid)['State'].strip().startswith('Z'))
        wait_until(lambda: (target / 'heartbeat').exists())
        before = (target / 'heartbeat').stat().st_size
        time.sleep(.12)
        after = (target / 'heartbeat').stat().st_size
        row = observe(child.pid, target, 'zombie-leader-with-live-writing-thread')
        row['heartbeat_bytes_before'] = before
        row['heartbeat_bytes_after'] = after
        row['thread_statuses'] = {p.name: dict(line.split(':', 1) for line in (p / 'status').read_text().splitlines() if ':' in line)['State'].strip() for p in Path(f'/proc/{child.pid}/task').iterdir()}
        assert after > before, row
    finally:
        child.kill()
        child.wait(timeout=5)

    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], cwd=target)
    try:
        observe(child.pid, target, 'live-cwd-holder')
    finally:
        child.terminate()
        child.wait(timeout=5)
    try:
        api['stopped_writers'](target)
        results['all_reaped'] = 'RETURNED'
    except Exception as exc:
        results['all_reaped'] = {'exception': type(exc).__name__, 'message': str(exc)}
print(json.dumps(results, indent=2), flush=True)
(BASE / 'probe-root-results.json').write_text(json.dumps(results, indent=2)+'\n')
