"""D3 regression harness must execute the actual child (including help), and end its descendants.

Exit 1 = defect reproduces, 0 = correct/not applicable, 2 = witness error.
Run from /work in the cell image, without network.
"""
import os
from pathlib import Path
import signal
import subprocess


TEST = Path('tests/command.executableSubcommand.test.js')
NAME = 'executable delimiter: help command still invokes child help'


def main():
    if not TEST.is_file() or NAME not in TEST.read_text():
        print('not applicable: this regression check is absent')
        return 0
    process = subprocess.Popen(
        ['node', '--test', f'--test-name-pattern=^{NAME}$', str(TEST)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True, env={**os.environ, 'NODE_OPTIONS': ''},
    )
    try:
        stdout, stderr = process.communicate(timeout=18)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        print('WITNESS ERROR: targeted test did not exit within 18 seconds', (stdout + stderr)[-500:])
        return 2
    # The test's timeout may leave recursively spawned descendants alive.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    output = stdout + stderr
    if NAME not in output:
        print('WITNESS ERROR: targeted test did not run', output[-500:])
        return 2
    print(output[-1200:])
    if process.returncode == 0:
        return 0
    if 'ETIMEDOUT' in output and "'--eval'" in TEST.read_text():
        return 1
    print('WITNESS ERROR: targeted test failed for a different reason')
    return 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError) as error:
        print('WITNESS ERROR:', error)
        raise SystemExit(2)
