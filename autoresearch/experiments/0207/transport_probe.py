"""Non-model admission falsifiers for the existing transport, not a new runner."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]

def alive(pid):
    p = subprocess.run(['ps', '-p', str(pid), '-o', 'stat='], capture_output=True, text=True, check=False)
    return p.returncode == 0 and bool(p.stdout.strip()) and not p.stdout.lstrip().startswith('Z')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); rows = []
    with tempfile.TemporaryDirectory(dir=args.scratch) as tmp:
        work = Path(tmp)
        for detached in [False, True]:
            pidfile = work / ('detached.pid' if detached else 'group.pid')
            child = "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"
            parent = f"""import subprocess,sys,time
p=subprocess.Popen([sys.executable,'-c',{child!r}],start_new_session={detached!r},stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
open({str(pidfile)!r},'w').write(str(p.pid))
time.sleep(60)
"""
            start = time.monotonic()
            try:
                p = subprocess.run([sys.executable, '-B', str(ROOT / 'config/skills/_shared/run-bounded.py'), '2', '--', sys.executable, '-c', parent], capture_output=True, text=True, timeout=10)
                duration = time.monotonic()-start
                pid = int(pidfile.read_text()); survivor = alive(pid)
                rows.append(dict(case='detached' if detached else 'same-group', exit_code=p.returncode, seconds=duration, child_survives_return=survivor, stdout=p.stdout, stderr=p.stderr))
                assert p.returncode == 124 and 7 <= duration < 9, rows[-1]
                assert survivor == detached, rows[-1]
            finally:
                if pidfile.exists():
                    pid = int(pidfile.read_text())
                    if alive(pid): os.kill(pid, signal.SIGKILL)
                    deadline = time.monotonic()+2
                    while alive(pid) and time.monotonic() < deadline: time.sleep(.02)
                    assert not alive(pid), pid
        # A transport which enforces the registered one-owner/four-descendant and
        # token ceilings must interrupt this emitter. Existing transport does not.
        emitter = "import json; [print(json.dumps({'type':'session.started','id':i})) for i in range(6)]; print(json.dumps({'type':'turn.completed','usage':{'input_tokens':400001,'output_tokens':20001}}))"
        p = subprocess.run([sys.executable, '-B', str(ROOT / 'config/skills/_shared/run-bounded.py'), '2', '--', sys.executable, '-c', emitter], capture_output=True, text=True, timeout=9)
        assert p.returncode == 0 and len(p.stdout.splitlines()) == 7, p
        rows.append(dict(case='unmetered-events', exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr, dispatches=6, input_tokens=400001, output_tokens=20001))
    record = dict(status='BLOCKED_EXISTING_TRANSPORT', model_calls=0, rows=rows,
        owned_probe_processes_quiescent=True,
        source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'config/skills/_shared/run-bounded.py',ROOT/'config/skills/_shared/platform-support.py',ROOT/'autoresearch/scripts/comparison-controller.py']},
        limitations=['Synthetic emitters validate transport behavior, not native counter semantics.',
                     'The 1830s historical controller tracks observed descendants but has fixed bounds and no token controller; not certified for 0206.',
                     'App-server usage notifications and isolated rollout files are possible sources, not yet demonstrated recursive budget control.'])
    with args.output.open('x') as f: json.dump(record, f, indent=2)
    print(json.dumps(record, indent=2))

if __name__ == '__main__': main()
