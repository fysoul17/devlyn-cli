"""Claim D1 (D4): writer startup stalls before its readiness message, so FIFO tests must
bound the writer's stdin write/readiness read and terminate owned processes.
Obligation 6: timeout/error probes terminate owned writer/readers.
The test-owned Python writer is replaced at Popen with one that sleeps before reading
stdin. The large stdin payload then blocks its parent, or stdout.readline blocks.
Each FIFO test runs in a separate process; a test still running after 60 s is killed.
Run from /work. Exit 1 = defect, 0 = correct, 2 = witness error.
"""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import traceback

DEADLINE = 60

SITE = r'''
import os, subprocess
_real_popen = subprocess.Popen
_log = os.environ.get('WITNESS_LOG')

def _popen(args, *other, **kwargs):
    if isinstance(args, (list, tuple)) and '-c' in args:
        index = args.index('-c')
        if index + 1 < len(args):
            code = args[index + 1]
            if isinstance(code, str) and 'open(sys.argv[1]' in code and ('"wb"' in code or "'wb'" in code):
                if _log:
                    fd = os.open(_log, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
                    os.write(fd, b'child writer-startup-stall\n')
                    os.close(fd)
                args = list(args)
                args[index + 1] = """import os, time
with open(os.environ['WITNESS_LOG'], 'a') as log:
    log.write('writer-pid %d\\n' % os.getpid())
time.sleep(3600)"""
    return _real_popen(args, *other, **kwargs)

subprocess.Popen = _popen
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
                                    '-o', 'faulthandler_timeout=50', '--basetemp', os.path.join(work, 'bt%d' % index),
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
        if 'No module named pytest' in output or 'Error in sitecustomize' in output:
            raise RuntimeError('FIFO test infrastructure failed: ' + output[-500:])
        fired = open(run['log']).read().split('\n') if os.path.exists(run['log']) else []
        writer_pids = [int(line.split()[1]) for line in fired if line.startswith('writer-pid ')]
        orphaned = [pid for pid in writer_pids if process_running(pid)]
        if orphaned and not hung:
            try:
                os.killpg(run['process'].pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        results.append(dict(test=run['test'], hung=hung, orphaned=orphaned,
                            exit=None if hung else run['process'].returncode,
                            injected=[line for line in fired if line][:3],
                            stack=stack(output) if hung else None, last=output.strip().splitlines()[-1:]))
    hung = [r for r in results if r['hung']]
    finish(bool(hung) or any(r['orphaned'] for r in results), {'tests': len(results), 'hung': len(hung),
                        'orphaned': sum(bool(r['orphaned']) for r in results),
                        'not_injected': [r['test'] for r in results if not r['injected']], 'results': results})


def process_running(pid):
    stat_path = '/proc/%d/stat' % pid
    if os.path.exists(stat_path):
        try:
            return open(stat_path).read().split(') ', 1)[1][:1] != 'Z'
        except FileNotFoundError:
            return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


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
