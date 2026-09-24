"""Prepare one registered 0220 cell: 0219 preparation with the completion-reserve budgeting sentence; never dispatch."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
RESERVE = ('Check observed usage only with `python3 /control/usage.py`; inspect no other telemetry outside /work. '
           'Observed totals exclude the call in flight. Use `last_generation_input` as an advisory estimate of one '
           'owner generation’s input, not a guaranteed next-generation cost. Before optional work or another '
           'round trip, compare against the stated targets and reserve for unreported in-flight usage plus all '
           'remaining work required by your instructions, including applicable checks, review, repair, fresh review, '
           'final audit, evidence retention and final response. Batch independent bookkeeping and meter reads into '
           'required tool rounds; cut optional exploration first.')

spec = importlib.util.spec_from_file_location('prepare0219', HERE.parent / '0219/prepare.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def prepare(index, runtime_path):
    cell = base.prepare(index, runtime_path)
    prompt = (cell / 'prompt.txt').read_text()
    plan = json.loads((cell / 'plan.json').read_text())
    meter = base.base.METER
    if plan['argv'][-1] != prompt or prompt.count(meter) != 1:
        raise ValueError('upstream 0219 contract changed; do not launch')
    prompt = prompt.replace(meter, RESERVE)
    baseline = json.loads((cell / 'baseline.json').read_text())
    pilot = json.loads((cell / 'pilot.json').read_text())
    plan['argv'][-1] = prompt
    baseline['prompt_sha256'] = base.base.digest(prompt)
    pilot['reserve_prepare_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (cell / 'prompt.txt').write_text(prompt)
    (cell / 'plan.json').write_text(json.dumps(plan, indent=2))
    (cell / 'baseline.json').write_text(json.dumps(baseline, indent=2))
    (cell / 'pilot.json').write_text(json.dumps(pilot, indent=2))
    return cell


if __name__ == '__main__':
    print(prepare(int(sys.argv[1]), sys.argv[2]))
