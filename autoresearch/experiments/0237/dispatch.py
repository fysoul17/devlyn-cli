"""Run one predeclared block serially, retaining results and stopping on apparatus faults."""
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('runtime', type=Path)
parser.add_argument('cells', type=Path)
parser.add_argument('journal', type=Path)
args = parser.parse_args()
repo = Path(__file__).resolve().parents[3]
output = Path(json.loads(args.runtime.read_text())['output'])
logs = args.journal.with_suffix('.logs')
logs.mkdir(exist_ok=False)

with args.journal.open('x') as journal:
    def emit(value):
        value['time'] = datetime.now(timezone.utc).isoformat()
        line = json.dumps(value, sort_keys=True)
        print(line, flush=True)
        journal.write(line + '\n')
        journal.flush()

    rows = args.cells.read_text().splitlines()
    for number, line in enumerate(rows, 1):
        name, task, arm, engine = line.split('\t')
        emit(dict(event='START', number=number, cell=name, task=task, arm=arm, engine=engine))
        with (logs / (name + '.log')).open('x') as log:
            done = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('runner.py')),
                'run', str(args.runtime.resolve()), name, task, arm, engine],
                cwd=repo, stdout=log, stderr=subprocess.STDOUT)
        verdict = output / ('verdict-' + name + '.json')
        result = json.loads(verdict.read_text()) if verdict.exists() else {}
        emit(dict(event='FINISH', number=number, cell=name, exit_code=done.returncode,
                  **{key: result.get(key) for key in ('status', 'reason', 'owner_seconds',
                    'usage', 'input_tokens', 'output_tokens', 'source_check_pass', 'delivery_pass')}))
        if done.returncode:
            raise SystemExit(done.returncode)
    emit(dict(event='REGISTERED_BLOCK_COMPLETE', cells=len(rows)))
