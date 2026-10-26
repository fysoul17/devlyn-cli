"""Reclassify final measured verdicts under amendment 1: reclassify.py <runtime.json> <cells.tsv>."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile


HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('reclassify0259_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


quota = load('quota')
driver = load('driver')


def verdict(path, name):
    original = path.read_bytes()
    try:
        record = json.loads(original)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f'{path}: malformed verdict: {exc}') from exc
    if (not isinstance(record, dict) or not isinstance(record.get('status'), str) or not record['status']
            or ('reason' in record and record['reason'] is not None and not isinstance(record['reason'], str))
            or ('cell' in record and record['cell'] != name)
            or (('quota' in record or record['status'] != 'STOP')
                and (not isinstance(record.get('quota'), dict)
                     or not isinstance(record['quota'].get('execution'), list)))):
        raise ValueError(f'{path}: malformed verdict')
    return original, record


def atomic_write(path, record):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=path.parent, prefix=path.name + '.', suffix='.tmp',
                                         encoding='utf8', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(record, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(runtime_path, cells_path):
    runtime = json.loads(Path(runtime_path).read_text())
    output = Path(runtime['output'])
    pending = []
    checked = skipped = 0
    for name, task, *_ in driver.rows([str(cells_path)]):
        if task == 'SMOKE':
            continue
        path = output / f'verdict-{name}.json'
        if not path.is_file():
            continue
        checked += 1
        original, record = verdict(path, name)
        if record['status'] == 'STOP' or record['quota']['execution']:
            skipped += 1
            continue
        cell_dir = output / name
        if not cell_dir.is_dir():
            raise FileNotFoundError(f'{name}: missing cell directory: {cell_dir}')
        updated_quota = quota.classify(cell_dir)
        if not updated_quota['execution']:
            skipped += 1
            continue
        kinds = sorted({hit['kind'] for hit in updated_quota['execution']})
        updated = dict(record)
        updated.update(status='STOP', reason='shared account fault during execution: ' + ', '.join(kinds),
                       quota=updated_quota,
                       reclassified=dict(from_status=record['status'], from_reason=record.get('reason'),
                                         from_sha256=hashlib.sha256(original).hexdigest(),
                                         amendment='amendment-1.md'))
        pending.append((name, path, updated))
    for name, path, updated in pending:
        atomic_write(path, updated)
        print(json.dumps(dict(cell=name, status='STOP', reason=updated['reason'])))
    summary = dict(checked=checked, skipped=skipped, reclassified=len(pending))
    print(json.dumps(summary))
    return summary


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: reclassify.py <runtime.json> <cells.tsv>')
    main(*sys.argv[1:])
