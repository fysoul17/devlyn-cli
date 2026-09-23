"""0211 deterministic checks plus the identical declared format gate, conjoined into completion."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare0216', HERE / 'prepare.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
spec = importlib.util.spec_from_file_location('check0211', HERE.parent / '0211/check_cell.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def check(cell, runtime_path):
    base.check(cell, runtime_path)
    runtime = json.loads(runtime_path.read_text())
    container = 'devlyn-0216-format-' + uuid.uuid4().hex
    argv = ['docker', 'run', '--name', container, '--rm', '--network', 'none', '--read-only',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--tmpfs', '/tmp',
            '--env', 'HOME=/tmp', '--mount', f'type=bind,src={cell / "work"},dst=/work,readonly',
            '--mount', f'type=bind,src={runtime["control"]},dst=/control,readonly', '-w', '/work',
            runtime['image'], 'timeout', '--kill-after=2s', '60s', 'sh', '-c', prepare.FORMAT]
    result = subprocess.run(argv, capture_output=True, text=True, timeout=70)
    if result.returncode not in (0, 1):
        raise RuntimeError('format gate did not produce a verdict; stop screen')
    checks = json.loads((cell / 'checks.json').read_text())
    checks['format'] = dict(argv=prepare.FORMAT, exit_code=result.returncode,
                            stdout=result.stdout, stderr=result.stderr)
    seal = json.loads((cell / 'local-seal.json').read_text())
    seal['product_check_pass'] = seal['product_check_pass'] and result.returncode == 0
    seal['format_pass'] = result.returncode == 0
    (cell / 'checks.json').write_text(json.dumps(checks, indent=2))
    (cell / 'local-seal.json').write_text(json.dumps(seal, indent=2))
    print(json.dumps(checks['format']))


if __name__ == '__main__':
    check(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
