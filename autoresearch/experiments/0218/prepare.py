"""Prepare one registered 0218 cell from 0211 with the frozen task-appropriate apparatus; never dispatch."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
PRETTIER = 'node /control/prettier/bin/prettier.cjs --check --no-error-on-unmatched-pattern '
FORMAT = {
    'D1': PRETTIER + 'lib/option.js tests/options.variadic.test.js tests/option.test.js',
    'D2': '/control/ruff format --check --no-cache src/click tests',
    'D3': PRETTIER + "lib/command.js tests/command.executableSubcommand.test.js tests/args.literal.test.js 'tests/fixtures/**'",
    'D4': '/control/ruff format --check --no-cache src/click tests',
}
TELEMETRY = 'Do not inspect telemetry outside /work.'
METER = ('Check observed usage only with `python3 /control/usage.py`; inspect no other telemetry outside /work. '
         'Before optional work, compare it with the targets and keep enough for required checks, review, '
         'repair and fresh review; cut optional exploration first.')


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def prepare(index, runtime_path):
    runtime = json.loads(Path(runtime_path).read_text())
    if Path(runtime['output']).name != runtime['pilot_id']:
        raise ValueError('pilot_id must match the distinct output directory name')
    cell = Path(subprocess.check_output([
        sys.executable, '-B', str(EXPERIMENTS / '0211/prepare.py'), str(index), str(Path(runtime_path).resolve()),
    ], text=True).strip())
    common = (EXPERIMENTS / '0211/common.txt').read_text()
    caller_path = cell / 'work/.devlyn/caller.json'
    caller = json.loads(caller_path.read_text())
    prompt = (cell / 'prompt.txt').read_text()
    plan = json.loads((cell / 'plan.json').read_text())
    baseline = json.loads((cell / 'baseline.json').read_text())
    task = baseline['task']['id']
    old = json.dumps(caller, indent=2)
    if (not prompt.startswith(common) or plan['argv'][-1] != prompt or common.count(TELEMETRY) != 1
            or prompt.count(old) != 1 or FORMAT[task] in caller['public_checks']):
        raise ValueError('upstream 0211 contract changed; do not launch')
    if task in ('D1', 'D3'):
        caller['public_checks'] = ['env -u NO_COLOR ' + c if c.startswith('node --test') else c
                                   for c in caller['public_checks']]
    caller['public_checks'].append(FORMAT[task])
    new = json.dumps(caller, indent=2)
    head = common.replace(TELEMETRY, METER) + '\n\n' + (EXPERIMENTS / '0214/common-wait.txt').read_text()
    prompt = head + prompt[len(common):].replace(old, new)
    caller_path.write_text(new)
    (cell / 'prompt.txt').write_text(prompt)
    plan['argv'][-1] = prompt
    baseline['prompt_sha256'] = digest(prompt)
    baseline['files']['.devlyn/caller.json'] = digest(new)
    (cell / 'plan.json').write_text(json.dumps(plan, indent=2))
    (cell / 'baseline.json').write_text(json.dumps(baseline, indent=2))
    (cell / 'pilot.json').write_text(json.dumps(dict(
        pilot_id=runtime['pilot_id'], entry=baseline['entry'], format_check=FORMAT[task],
        prepare_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()), indent=2))
    return cell


if __name__ == '__main__':
    print(prepare(int(sys.argv[1]), sys.argv[2]))
