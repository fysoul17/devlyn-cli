"""0211 deterministic checks plus the cell's declared format gate, within one combined 120s allowance."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare = load('prepare0218', HERE / 'prepare.py')
base = load('check0211', HERE.parent / '0211/check_cell.py')


def check(cell, runtime_path):
    start = time.monotonic()
    base.check(cell, runtime_path)
    runtime = json.loads(runtime_path.read_text())
    command = prepare.FORMAT[json.loads((cell / 'baseline.json').read_text())['task']['id']]
    remaining = 120 - (time.monotonic() - start)
    if remaining < 15:
        raise TimeoutError('no combined check allowance left for the format gate; stop screen')
    container = 'devlyn-0218-format-' + uuid.uuid4().hex
    argv = ['docker', 'run', '--name', container, '--rm', '--network', 'none', '--read-only',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--tmpfs', '/tmp',
            '--env', 'HOME=/tmp', '--mount', f'type=bind,src={cell / "work"},dst=/work,readonly',
            '--mount', f'type=bind,src={runtime["control"]},dst=/control,readonly', '-w', '/work',
            runtime['image'], 'timeout', '--kill-after=2s', f'{int(remaining) - 10}s', 'sh', '-c', command]
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=remaining - 2)
    finally:
        probe = subprocess.run(['docker', 'inspect', container], capture_output=True, text=True, timeout=5)
        if probe.returncode == 0:
            subprocess.run(['docker', 'rm', '-f', container], capture_output=True, check=True, timeout=5)
        elif 'No such object' not in probe.stderr:
            raise RuntimeError('cannot verify format container teardown')
    if result.returncode not in (0, 1):
        raise RuntimeError('format gate did not produce a verdict; stop screen')
    checks = json.loads((cell / 'checks.json').read_text())
    checks['format'] = dict(argv=command, exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
    seal = json.loads((cell / 'local-seal.json').read_text())
    seal['product_check_pass'] = seal['product_check_pass'] and result.returncode == 0
    seal['format_pass'] = result.returncode == 0
    seal['seconds'] = time.monotonic() - start
    if seal['seconds'] > 120:
        raise TimeoutError('deterministic and format checks exceeded the combined 120s')
    (cell / 'checks.json').write_text(json.dumps(checks, indent=2))
    (cell / 'local-seal.json').write_text(json.dumps(seal, indent=2))
    print(json.dumps(checks['format']))


if __name__ == '__main__':
    check(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
