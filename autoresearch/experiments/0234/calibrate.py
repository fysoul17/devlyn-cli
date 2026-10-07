"""Host or image calibration, with no model or Docker dependency.

Run `python3 calibrate.py`; inside devlyn-0231, bind this directory read-only and run the same command.
Each reference is an overlay onto the registered participant source. The overlay never enters a cell.
"""
import json
from pathlib import Path
import shutil
import shlex
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
TASKS = json.loads((HERE / 'tasks.json').read_text())
NEW = ('F16', 'F23', 'F25', 'F10', 'F11', 'E1', 'E2')


def run(source_root=HERE / 'sources', references=HERE / 'calibration', tasks=NEW):
    results = {}
    for task in tasks:
        spec = next(t for t in TASKS['tasks'] if t['id'] == task)
        rows = spec['oracle']
        variants = sorted(p.name for p in (Path(references) / task).iterdir() if p.is_dir())
        missing = [row for row in rows if not any(v == f'bad-{row}' or v.startswith(f'bad-{row}-') for v in variants)]
        if 'good' not in variants or missing:
            raise AssertionError(f'{task}: missing calibration references {sorted(missing)}')
        for variant in variants:
            with tempfile.TemporaryDirectory(prefix='0234-calibrate-') as temp:
                work = Path(temp) / 'work'
                source = Path(source_root) / task
                shutil.copytree(source, work, ignore=shutil.ignore_patterns('node_modules'))
                if (source / 'node_modules').exists():
                    (work / 'node_modules').symlink_to((source / 'node_modules').resolve(), target_is_directory=True)
                overlay = Path(references) / task / variant
                if not overlay.is_dir():
                    raise AssertionError(f'missing calibration reference {overlay}')
                for file in overlay.rglob('*'):
                    if file.is_file():
                        target = work / file.relative_to(overlay)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file, target)
                failed = []
                for row in rows:
                    result = subprocess.run(['node', str(HERE / 'oracle.js'), task, row, str(work)],
                                            capture_output=True, text=True, timeout=30)
                    if 'listen EPERM' in result.stderr:
                        raise RuntimeError(f'{task}/{row}: host forbids local server binds (listen EPERM); run in the image')
                    if result.returncode:
                        failed.append(row)
                expected = ([] if variant.startswith('good') else
                            [next((row for row in rows if variant == f'bad-{row}' or variant.startswith(f'bad-{row}-')),
                                  None)])
                if expected == [None]:
                    raise AssertionError(f'{task}/{variant}: unknown calibration reference name')
                if failed != expected:
                    raise AssertionError(f'{task}/{variant}: expected failures {expected}, got {failed}')
                if variant.startswith('good'):
                    for command in spec['public_checks']:
                        result = subprocess.run(shlex.split(command), cwd=work, capture_output=True, text=True, timeout=30)
                        if result.returncode:
                            raise AssertionError(f'{task}/good public check {command}: {(result.stdout + result.stderr)[-1500:]}')
                results[f'{task}/{variant}'] = failed
    return results


if __name__ == '__main__':
    result = run()
    print(json.dumps({'references': len(result), 'rows': sum(len(next(t for t in TASKS['tasks'] if t['id'] == task)['oracle'])
                                                       for task in NEW), 'results': result}, indent=2))
