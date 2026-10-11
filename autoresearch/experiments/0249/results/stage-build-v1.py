"""0249 isolated task composition and staging; no native execution or auth access."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import time

NX = Path('/Users/aipalm/.local/share/nx01')
ROOT = NX / '0237-harness'
EXP = ROOT / 'autoresearch/experiments/0249'
OUT = EXP / 'results'
FIX = EXP / 'fixtures'
DEST = NX / '0249-live/staged-v1'
OLD = NX / '0247-live/staged-v1'
PACKS = NX / '0249-live/selected-packs-v1'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
    return json.loads(p.read_text())

def write(p, value):
    assert not p.exists(), p
    p.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def tree(p):
    return {str(f.relative_to(p)): sha(f) for f in sorted(p.rglob('*')) if f.is_file()}

assert not DEST.exists()
assert sha(FIX / 'fixture-manifest.json') == 'd398372f7da50144c285281a1572417fc58ca0affd96f8a1d198d74866303c38'
manifest = read(FIX / 'fixture-manifest.json')
for name, entry in manifest['files'].items():
    assert sha(FIX / name) == entry['sha256'], name
template_path = NX / '0248-live/runtime-measured.json'
template = read(template_path)
inherited = read(OLD / 'tasks.json')
old_tasks_path = EXP.parent / '0237/tasks.json'
old_tasks = read(old_tasks_path)
tasks = {key: value for key, value in inherited.items() if key != 'tasks'}
tasks['schema'] = '0249-fresh-s-confirmation-v1'
tasks['tasks'] = []
for task_id in ('OR1', 'OR2'):
    spec = read(FIX / task_id / 'task.json')
    registered = manifest['runner_source_sha256'][task_id]
    assert {'visible/' + k: v for k, v in tree(FIX / task_id / 'visible').items()} == registered
    tasks['tasks'].append(dict(id=task_id, repository='devlyn-confirmation-fixtures',
        stratum='confirmation', domain='ownership_and_recovery',
        eq3_dir=str((FIX / task_id).relative_to(ROOT)), source_sha256=registered,
        request=spec['goal'], obligations=[], allowed=spec['allowed'],
        public_checks=spec['public_checks'], oracle=spec['oracle']))
for task_id in ('E1', 'B5'):
    task = next(t for t in old_tasks['tasks'] if t['id'] == task_id)
    assert tree(ROOT / task['source_dir']) == task['source_sha256'], task_id
    tasks['tasks'].append(task)
stage = EXP.parent / '0247/results/stage.py'
protected_paths = [stage, EXP.parent / '0238/results/stage.py', OLD / 'review-manifest.json',
    OLD / 'tasks.json', template_path, old_tasks_path, PACKS / 'packages.json',
    FIX / 'fixture-manifest.json', FIX / 'REPORT.md', FIX / 'calibration/final/summary.json',
    OUT / 'package-integrity-v1.json', OUT / 'stage-prediction-v1.json']
protected_paths += [PACKS / (arm + '.tgz') for arm in ('B', 'S', 'H', 'P')]
protected_paths += [FIX / name for name in manifest['files']]
protected = {str(p): sha(p) for p in protected_paths}
write(EXP / 'tasks-v1.json', tasks)
argv = ['python3', '-B', str(stage), str(DEST), '--packs', str(PACKS),
        '--tasks', str(EXP / 'tasks-v1.json'), '--template-runtime', str(template_path),
        '--review-manifest', str(OLD / 'review-manifest.json')]
started = time.monotonic()
done = subprocess.run(argv, text=True, capture_output=True)
write(OUT / 'stage-command-v1.json', dict(argv=argv, exit_code=done.returncode,
      elapsed_seconds=time.monotonic() - started, stdout=done.stdout, stderr=done.stderr))
if done.returncode:
    raise SystemExit(done.returncode)
journal_sha = sha(DEST / 'staging.json')
smoke_sha = sha(DEST / 'runtime-smoke.json')
base_manifest = read(DEST / 'control.manifest.json')
shutil.copyfile(DEST / 'control.manifest.json', DEST / 'control.manifest.base-stage.json')
for task_id in ('OR1', 'OR2'):
    shutil.copytree(FIX / task_id / 'hidden', DEST / 'control/oracle/eq3' / task_id)
final_manifest = dict(manifests={name: tree(DEST / 'control' / name)
                                for name in ('public', 'oracle', 'packages')})
assert final_manifest['manifests']['public'] == base_manifest['manifests']['public']
assert final_manifest['manifests']['packages'] == base_manifest['manifests']['packages']
added = {k: v for k, v in final_manifest['manifests']['oracle'].items()
         if k not in base_manifest['manifests']['oracle']}
assert set(added) == {'eq3/OR1/oracle.py', 'eq3/OR2/oracle.py'}
assert all(final_manifest['manifests']['oracle'][k] == v
           for k, v in base_manifest['manifests']['oracle'].items())
(DEST / 'control.manifest.json').write_text(json.dumps(final_manifest, indent=2, sort_keys=True) + '\n')
(DEST / 'out-measured').mkdir(mode=0o700)
runtime = read(DEST / 'runtime-smoke.json')
runtime.update(phase='measured', output=str(DEST / 'out-measured'),
    boot_catalogs={'claude': {arm: template['boot_catalogs']['claude'][arm] for arm in ('A', 'B', 'S')}})
write(DEST / 'runtime-measured.json', runtime)
spec = importlib.util.spec_from_file_location('runner0249_stage_audit', EXP.parent / '0247/runner.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
runner = module.Runner(DEST / 'runtime-measured.json')
for arm in ('A', 'B', 'S'):
    assert runner.boot_expectation(arm, 'claude') == template['boot_catalogs']['claude'][arm]
    assert runner.boot_expectation(arm, 'codex') is None
inputs = runner.inputs()
assert sha(DEST / 'staging.json') == journal_sha
assert sha(DEST / 'runtime-smoke.json') == smoke_sha
assert all(sha(Path(p)) == digest for p, digest in protected.items())
assert read(DEST / 'tasks.json') == tasks
for name in ('auth', 'scratch', 'out-smoke', 'out-measured'):
    assert not any((DEST / name).iterdir())
    assert (DEST / name).stat().st_mode & 0o777 == 0o700
report = dict(schema='0249-stage-extension-v1', status='PASS',
    recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    original_journal_sha256=journal_sha, original_smoke_runtime_sha256=smoke_sha,
    original_control_manifest_sha256=sha(DEST / 'control.manifest.base-stage.json'),
    final_control_manifest_sha256=sha(DEST / 'control.manifest.json'),
    runtime_measured_sha256=sha(DEST / 'runtime-measured.json'),
    tasks_sha256=sha(DEST / 'tasks.json'), added_hidden_oracles=added,
    control_counts={k: len(v) for k, v in final_manifest['manifests'].items()},
    execution_inputs=inputs, execution_input_count=len(inputs),
    protected_before=protected, protected_unchanged=True,
    task_source_counts={t['id']: len(t['source_sha256']) for t in tasks['tasks']},
    routes_and_watchdogs='EXACT_0247', existing_controls='EXACT_0237',
    measured_catalogs='EXACT_0248_A_B_S',
    dispatch='NOT_AUTHORIZED_OR_PERFORMED', auth='EMPTY_NO_CREDENTIAL_ACCESS',
    freeze='NOT_CREATED_PENDING_REVIEW', script_sha256=sha(Path(__file__)))
write(DEST / 'staging-extension.json', report)
write(OUT / 'stage-report-v1.json', report)
print(json.dumps({k: report[k] for k in ('status', 'execution_input_count', 'control_counts',
       'runtime_measured_sha256', 'tasks_sha256', 'final_control_manifest_sha256')}))
