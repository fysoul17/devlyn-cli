# 0261 severe-finding witness (root, after unblinding): d023 claude:1 (full suite timed out) and codex:1 (a FIFO
# test blocks outside its timeout and never reaches cleanup).
# Trigger: none injected; the tree's own tests/test_types/test_File.py runs as the public check runs it.
# Exit 1 when it has not finished after 280 s (claim reproduced), 0 when pytest finishes (pass or fail), 2 when
# pytest reports an infrastructure error (exit 2-5). The tree's src is on PYTHONPATH, as the frozen D4 witnesses set it;
# a first run without it failed to import click on every tree (exit 2) and was discarded.
import os
import subprocess
import sys

argv = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', 'tests/test_types/test_File.py']
try:
    env = dict(os.environ, PYTHONPATH=os.path.join(os.getcwd(), 'src'), PYTHONDONTWRITEBYTECODE='1')
    done = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=280)
except subprocess.TimeoutExpired:
    print('tests/test_types/test_File.py did not finish in 280 s')
    sys.exit(1)
print(done.stdout[-600:], done.stderr[-600:])
sys.exit(0 if done.returncode in (0, 1) else 2)
