"""Reuse rp-d2 offline staging with one package, Codex auth and no boot catalogs."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner_rpd3_stage', HERE / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
legacy = runner.load('stage_rpd2_rpd3', HERE.parent / 'rp-d2-report-lines/stage.py')
read, write, digest, require = runner.read, runner.write, runner.digest, runner.require
pack, auth = runner.prepare.pack, runner.auth
model_auth, tree = auth.model_auth, legacy.tree
legacy.runner, legacy.pack, legacy.model_auth = runner, pack, model_auth
legacy.smoke_catalogs = lambda _output, _attempt: {}
inherited_stage = legacy.stage


def stage(args):
    for arm in runner.prepare.PROMPT_SHA256:
        runner.prepare.prompt_body(arm)
    if args.phase == 'measured':
        runner.Runner(args.stage_dir / 'runtime-smoke.json').prior_deleted('m01')
    return inherited_stage(args)


def renewal_allowed(previous, account, completed):
    require(account == previous['codex_account'], 'renewal requires the identical Codex account')
    require(previous['phase'] == 'measured' and len(completed) < 8 and len(completed) % 2 == 0,
            'model auth renewal is allowed only between measured pairs')
    require(all(row['status'] in ('PASS', 'ADJUDICATE', 'PRODUCT_INCOMPLETE') for row in completed),
            'stopped schedule cannot renew or resume')


def renew(runtime_path, auth_path):
    app = runner.Runner(runtime_path)
    previous = read(runtime_path)
    completed = app.completed_prefix()
    renewal_allowed(previous, previous['codex_account'], completed)
    if completed:
        app.prior_deleted(runner.SCHEDULE[len(completed)][0])
    manifest, manifest_hash = model_auth(auth_path)
    renewal_allowed(previous, manifest['account'], completed)
    updated = dict(previous, auth=str(auth_path.absolute()), auth_manifest_sha256=manifest_hash,
                   renewed_from=dict(path=str(runtime_path.resolve()), sha256=digest(runtime_path)))
    target = runtime_path.parent / ('runtime-measured-auth-' + manifest_hash + '.json')
    require(not target.exists(), 'renewed runtime already exists; preserve it')
    write(target, updated)
    return target


def check(runtime_path):
    app = runner.Runner(runtime_path)
    runtime = app.runtime
    expected = runner.PRIOR / ('smoke-tasks.json' if runtime['phase'] == 'smoke' else 'tasks.json')
    require(app.tasks == read(expected) and read(runtime['tasks_file']) == app.tasks, 'phase requires frozen rp-d1 tasks')
    app.inputs()
    runner.prepare.verify_release(runtime)
    app.check_auth(runtime)
    original = read(runtime_path)
    for output in (original['output'], original['smoke_output']):
        runner.cell.credential_directory(dict(runtime, output=output))
    hidden = Path(runtime['control']) / 'oracle/experiments/rp-d1-delivery-cost'
    require(digest(hidden / 'oracle.py') == digest(runner.PRIOR / 'oracle.py'), 'hidden oracle changed')
    for task in app.tasks['tasks']:
        for fixture in (Path(runtime['source_root']) / task['source_dir'], hidden / 'fixtures' / task['id']):
            require(app.packet.content(app.packet.tree(fixture)) == task['source_sha256'], 'registered source changed')
    require(all((Path(runtime['control']) / 'public' / name).is_dir() for name in ('python', 'autoresearch')),
            'public check mount missing')
    require(runtime['boot_catalogs'] == {}, 'rp-d3 has no boot catalogs')
    for name, _, config in app.slots():
        app.repository(name)
        app.boot_expectation(runner.arm_for(name), config)
    completed = app.completed_prefix()
    require(len(completed) < len(app.slots()), 'schedule already complete')
    name = app.slots()[len(completed)][0]
    app.prior_deleted(name)
    app.validate(name)


legacy.stage, legacy.renew, legacy.check = stage, renew, check
main = legacy.main

if __name__ == '__main__':
    main()
