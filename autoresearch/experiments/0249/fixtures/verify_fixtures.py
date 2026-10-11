"""Verify final source seals, calibration predictions, and exact contract quotes."""
import argparse
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--calibration', type=Path, default=ROOT / 'calibration/v2')
CALIBRATION = parser.parse_args().calibration.resolve()
prediction = json.loads((CALIBRATION / 'prediction.json').read_text())
summary = json.loads((CALIBRATION / 'summary.json').read_text())
for row in summary['results']:
    if row['check'] == 'oracle':
        expected = prediction['expected'][row['task']]
        if row['variant'] == 'baseline':
            assert row['passed'] == expected['baseline_pass']
        elif row['variant'] == 'gold':
            assert row['passed'] == expected['gold_pass'] and row['failed'] == []
        else:
            assert row['failed'] == expected['fault_control_fail']
for task in ('OR1', 'OR2'):
    folder = ROOT / task
    spec = json.loads((folder / 'task.json').read_text())
    mapping = json.loads((folder / 'contract-map.json').read_text())
    assert spec['oracle'] == [row['id'] for row in mapping['manifestations']]
    for row in mapping['manifestations']:
        for cite in row['contract']:
            lines = (folder / cite['path']).read_text().splitlines()
            assert '\n'.join(lines[cite['start_line'] - 1:cite['end_line']]) == cite['quote']
    differences = [str(path.relative_to(folder / 'visible'))
                   for path in sorted((folder / 'visible').rglob('*')) if path.is_file()
                   and path.read_bytes() != (folder / 'gold' / path.relative_to(folder / 'visible')).read_bytes()]
    assert differences == [('folio/workspace.py' if task == 'OR1' else 'relay/loader.py')]
    assert not list(folder.rglob('__pycache__'))
    for variant in ('baseline', 'gold', 'fault'):
        for check in ('public', 'oracle'):
            raw = json.loads((CALIBRATION / f'{task}.{variant}.{check}.json').read_text())
            assert raw['source_unchanged']
            target = Path(raw['cwd'])
            actual = {str(path.relative_to(target)): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in sorted(target.rglob('*')) if path.is_file()}
            assert actual == raw['source_sha256']
print(json.dumps({'passed': True, 'checks': ['predictions', 'exact contract quotes', 'oracle IDs', 'full gold mappings', 'unchanged final source hashes']}))
