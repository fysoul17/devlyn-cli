# 0261 severe-finding witness (root, after unblinding): d022 claude:0/claude:1/codex:0, d023 claude:0/codex:0.
# Claim: FIFO conversion still opens the pipe, so click.File("rb", lazy=True).convert blocks while no writer exists.
# Trigger: a fresh FIFO with no writer; convert it in a child process with the tree's src on PYTHONPATH.
# Exit 1 when conversion is still blocked after 10 s (claim reproduced), 0 when it returns, 2 on any other outcome.
import os
import subprocess
import sys
import tempfile

fifo = os.path.join(tempfile.mkdtemp(), 'fifo')
os.mkfifo(fifo)
code = f"import click; click.File('rb', lazy=True).convert({fifo!r}, None, None); print('returned')"
env = dict(os.environ, PYTHONPATH=os.path.join(os.getcwd(), 'src'))
try:
    done = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, timeout=10)
except subprocess.TimeoutExpired:
    print('conversion blocked for 10 s with no writer')
    sys.exit(1)
if done.returncode == 0 and 'returned' in done.stdout:
    print('conversion returned without a writer')
    sys.exit(0)
print(done.stdout, done.stderr)
sys.exit(2)
