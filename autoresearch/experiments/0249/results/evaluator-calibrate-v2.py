"""Calibrate unchanged Runner.evaluate on isolated copies; never dispatch a model."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import time
import traceback

NX = Path('/Users/aipalm/.local/share/nx01')
ROOT = NX / '0237-harness'
EXP = ROOT / 'autoresearch/experiments/0249'
OUT = EXP / 'results'
FIX = EXP / 'fixtures'
DEST = NX / '0249-live/staged-v1'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
    return json.loads(p.read_text())

def write(p, value):
    assert not p.exists(), p
    p.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def tree(p):
    return {str(f.relative_to(p)): sha(f) for f in sorted(p.rglob('*'))
            if f.is_file() and not f.is_symlink()}

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--runner', type=Path, required=True)
parser.add_argument('--prediction', type=Path, required=True)
args = parser.parse_args()
prediction_path = args.prediction.resolve()
prediction = read(prediction_path)
runtime_path = DEST / 'runtime-measured.json'
assert sha(runtime_path) == prediction['runtime_sha256']
assert sha(FIX / 'fixture-manifest.json') == prediction['fixture_manifest_sha256']
assert sha(Path(__file__)) == prediction['script_sha256']
assert str(args.runner.resolve()) == prediction['runner_path']
assert sha(args.runner) == prediction['runner_sha256']
spec = importlib.util.spec_from_file_location('runner0249_evaluator_calibration', args.runner)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
runner = module.Runner(runtime_path)
inputs_before = runner.inputs()
assert inputs_before == prediction['execution_inputs']
assert runner.frame.control_unchanged(runner.runtime)
image_probe = subprocess.run(['docker', 'image', 'inspect', runner.runtime['image'], '--format', '{{.Id}}'],
                             text=True, capture_output=True, check=True)
assert image_probe.stdout.strip() == runner.runtime['image']
container_argv = ['docker', 'ps', '-a', '--filter', 'name=devlyn-0231-check-', '--format', '{{.Names}}']
containers_before = subprocess.run(container_argv, text=True, capture_output=True, check=True).stdout
assert not containers_before.strip(), containers_before
work_root = DEST / 'evaluator-calibration-v2'
work_root.mkdir()
results = []
overall = 'PASS'
for case in prediction['cases']:
    task_id, variant = case['task'], case['variant']
    name = task_id + '-' + variant
    work = work_root / name
    task = runner.task(task_id)
    source = Path(case['source'])
    assert tree(source) == case['source_sha256']
    if task_id in ('OR1', 'OR2'):
        shutil.copytree(source, work / 'visible', symlinks=True)
    else:
        shutil.copytree(source, work, symlinks=True)
        if case.get('overlay'):
            overlay = Path(case['overlay'])
            assert tree(overlay) == case['overlay_sha256']
            shutil.copytree(overlay, work, dirs_exist_ok=True, symlinks=True)
    source_before = runner.packet.tree(work)
    if variant == 'baseline':
        assert runner.packet.content(source_before) == task['source_sha256']
    before = time.monotonic()
    record = dict(task=task_id, variant=variant, prediction=case,
                  source_before=source_before, result=None, exception=None)
    try:
        result = runner.evaluate(work, task_id, runner.runtime)
        record['result'] = result
        if any(r['exit_code'] != 0 or r['timeout'] for r in result['public']):
            raise ValueError('public calibration failed')
        if task_id in ('OR1', 'OR2'):
            if any(r['exit_code'] != 0 or r['timeout'] for r in result['raw']):
                raise ValueError('oracle apparatus failed: nonzero is not a valid product result')
            record['public_decoded'] = json.loads(result['public'][0]['stdout'].strip().split('\n')[-1])
            if record['public_decoded'] != {'public_passed': True, 'tests': 2}:
                raise ValueError('public test count differs from fixture contract')
        else:
            if any(r['exit_code'] not in (0, 1) or r['timeout'] for r in result['raw']):
                raise ValueError('legacy oracle apparatus failed')
            expected_oracle = '/control/autoresearch/experiments/' + ('0233' if task_id == 'B5' else '0234') + '/oracle.js'
            if len(result['raw']) != len(task['oracle']):
                raise ValueError('legacy oracle record count mismatch')
            for row, raw in zip(task['oracle'], result['raw']):
                if raw['argv'] != ['node', expected_oracle, task_id, row, '/cell/work']:
                    raise ValueError('legacy oracle route differs from registered task')
                if row in case['expected_pass']:
                    if raw['exit_code'] != 0 or json.loads(raw['stdout']) != {'row': row, 'pass': True}:
                        raise ValueError('legacy success does not match exact registered row')
                elif (raw['exit_code'] != 1 or raw['stdout'] != ''
                      or not raw['stderr'].startswith('Error: ' + row + '\n    at assert (' + expected_oracle + ':')):
                    raise ValueError('legacy failure does not match exact registered assertion')
        actual = {r['id']: r['status'] for r in result['rows']}
        if len(actual) != len(result['rows']) or set(actual) != set(task['oracle']):
            raise ValueError('calibration returned rows outside the registered oracle')
        expected = {row: ('PASS' if row in case['expected_pass'] else 'FAIL')
                    for row in task['oracle']}
        if actual != expected:
            raise ValueError('calibration rows differ from prospective prediction')
        record['status'] = 'PASS'
    except Exception:
        record['exception'] = traceback.format_exc()
        record['status'] = 'STOP_CALIBRATION'
        overall = 'STOP_CALIBRATION'
    record['elapsed_seconds'] = time.monotonic() - before
    record['source_after'] = runner.packet.tree(work)
    record['source_unchanged'] = record['source_after'] == source_before
    if not record['source_unchanged']:
        record['status'] = overall = 'STOP_CALIBRATION'
    path = OUT / ('evaluator-' + name + '-v2.json')
    write(path, record)
    results.append(dict(task=task_id, variant=variant, status=record['status'],
                        path=str(path), sha256=sha(path)))
    print(json.dumps(results[-1]), flush=True)
    if overall != 'PASS':
        break
inputs_after = runner.inputs()
unchanged = inputs_after == inputs_before
controls_unchanged = runner.frame.control_unchanged(runner.runtime)
containers_after = subprocess.run(container_argv, text=True, capture_output=True, check=True).stdout
provenance_unchanged = all(sha(Path(p)) == digest for p, digest in prediction['provenance'].items())
case_sources_unchanged = all(tree(Path(case['source'])) == case['source_sha256']
    and (not case.get('overlay') or tree(Path(case['overlay'])) == case['overlay_sha256'])
    for case in prediction['cases'])
if not (unchanged and controls_unchanged and provenance_unchanged and case_sources_unchanged
        and not containers_after.strip()):
    overall = 'STOP_CALIBRATION'
report = dict(schema='0249-evaluator-calibration-v2', status=overall,
    recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    prediction_sha256=sha(prediction_path), results=results,
    execution_inputs_before=inputs_before, execution_inputs_after=inputs_after,
    execution_inputs_unchanged=unchanged,
    controls_unchanged=controls_unchanged, provenance_unchanged=provenance_unchanged,
    case_sources_unchanged=case_sources_unchanged,
    image_identity=image_probe.stdout.strip(),
    containers_before=containers_before, containers_after=containers_after,
    teardown_probe_argv=container_argv,
    cases_not_run=prediction['cases'][len(results):],
    B5=prediction['B5'], runtime_sha256=sha(runtime_path),
    dispatch='NOT_AUTHORIZED_OR_PERFORMED', auth='NO_ACCESS',
    apparatus='Selected reviewed Runner.evaluate; inherited pinned Docker in_image and teardown',
    outcome_scope='Evaluator calibration only; no native performance or efficacy claim')
write(OUT / 'evaluator-calibration-v2.json', report)
print(json.dumps(dict(status=overall, cases=len(results), summary_sha256=sha(OUT / 'evaluator-calibration-v2.json'))))
raise SystemExit(0 if overall == 'PASS' else 2)
