"""Offline staging and same-account Claude snapshot renewal between serial slots."""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner_rpd5_stage', HERE / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
legacy = runner.load('stage_rpd4_rpd5', HERE.parent / 'rp-d4-helper-report/stage.py')
read, write, digest, require = runner.read, runner.write, runner.digest, runner.require
pack, auth = runner.prepare.pack, runner.auth
model_auth, tree = auth.model_auth, legacy.tree
disjoint_auth, recorded_stage_root = legacy.disjoint_auth, legacy.recorded_stage_root
# rp-d4's unchanged rp-d2 staging supports an arbitrary verified release mapping.
inherited = legacy.legacy
inherited.runner, inherited.pack, inherited.model_auth = runner, pack, model_auth
inherited.smoke_catalogs = lambda _output, _attempt: {}


def reserve_smoke(args, manifest):
    runner.smoke_slots(args.smoke_attempt)
    root = runner.smoke_registry(args.run_id)
    inputs = runner.smoke_inputs(dict(arms_file=args.arms, image=args.image,
        codex_account=auth.codex_account(args.auth), claude_account=manifest['account'],
        models_cache_sha256=digest(Path.home() / '.codex/models_cache.json')))
    previous = root / 'attempt-1.json'
    if args.smoke_attempt == 2:
        first = read(previous)
        runner.smoke_registration(read(first['runtime']))
        require(first['status'] == 'FAILED', 'spare requires a failed first smoke without credential revocation or effort failure')
        require(first['inputs'] == inputs, 'spare changed registered release, accounts, image or models cache')
        for verdict in first['verdicts']:
            row = read(verdict)
            if row['dispatched']:
                receipt = row.get('repository_cleanup', {})
                require(receipt.get('repository') == f'fysoul17/rpd5-{args.run_id}-{row["cell"]}' and
                        receipt.get('status') == 'DELETED' and receipt.get('http_status') == 404 and
                        receipt.get('archive_manifest_sha256'), 'failed smoke has no archived deletion/404 receipt')
    else:
        require(not previous.exists() and not (root / 'attempt-2.json').exists(), 'run already staged; never replay')
    state = dict(status='STAGING', inputs=inputs, runtime=str(args.stage_dir.resolve() / 'runtime-smoke.json'))
    if args.smoke_attempt == 2:
        state['previous_sha256'] = digest(previous)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = root / f'attempt-{args.smoke_attempt}.json'
    with path.open('x') as stream:
        json.dump(state, stream, indent=2)
    return path, state


def stage(args):
    manifest, binding = model_auth(args.auth)
    auth.claude.lifetime(manifest['expires_at_ms'])
    dest = args.stage_dir.resolve()
    disjoint_auth(args.auth, (dest, args.github_auth))
    runner.prepare.prompt_body('X')
    if args.phase == 'measured':
        previous = read(dest / 'runtime-smoke.json')
        require(manifest['account'] == previous['claude_account'] and
                auth.codex_account(args.auth) == previous['codex_account'], 'staging changed registered accounts')
        app = runner.Runner(dest / 'runtime-smoke.json')
        app.finish_smoke()
        app.prior_deleted('c01')
    else:
        registration, state = reserve_smoke(args, manifest)
    target = inherited.stage(args)
    runtime = read(target)
    runtime.update(auth_engine='claude', claude_auth=runtime['auth'], claude_account=manifest['account'],
                   claude_auth_manifest_sha256=binding)
    tasks_dir = dest / 'tasks'
    tasks_dir.mkdir(exist_ok=True)
    for name, _, _ in runner.SCHEDULE + runner.smoke_slots(args.smoke_attempt):
        tasks_path = tasks_dir / (name + '.json')
        phase = 'measured' if name in runner.ARMS else 'smoke'
        expected = runner.slot_tasks(phase, name)
        if tasks_path.exists():
            require(read(tasks_path) == expected, 'staged task projection changed')
        else:
            write(tasks_path, expected)
    write(target, runtime)
    if args.phase == 'smoke':
        state.update(status='STAGED', runtime_sha256=digest(target))
        require(state['inputs'] == runner.smoke_inputs(runtime), 'staged smoke inputs changed')
        write(registration, state)
    return target


def renewal_allowed(previous, account, completed):
    require(account == previous['claude_account'], 'renewal requires the identical Claude account')
    require(previous['phase'] == 'measured' and len(completed) < len(runner.SCHEDULE),
            'model auth renewal is allowed only before an unfinished measured slot')
    require(all(row['status'] in ('PASS', 'ADJUDICATE', 'PRODUCT_INCOMPLETE') and
                row.get('effort_binding') == 'MATCH' for row in completed),
            'stopped schedule cannot renew or resume')


def renew(runtime_path, auth_path):
    previous = read(runtime_path)
    disjoint_auth(auth_path, (recorded_stage_root(previous), previous['github_auth']))
    app = runner.Runner(runtime_path)
    completed = app.completed_prefix()
    renewal_allowed(previous, previous['claude_account'], completed)
    app.prior_deleted(runner.SCHEDULE[len(completed)][0])
    manifest, binding = model_auth(auth_path)
    renewal_allowed(previous, manifest['account'], completed)
    require(auth.codex_account(auth_path) == previous['codex_account'], 'renewal requires identical bundled Codex account')
    auth.claude.lifetime(manifest['expires_at_ms'])
    updated = dict(previous, auth=str(auth_path.absolute()), auth_manifest_sha256=binding,
        claude_auth=str(auth_path.absolute()), claude_auth_manifest_sha256=binding,
        renewed_from=dict(path=str(runtime_path.resolve()), sha256=digest(runtime_path)))
    target = runtime_path.parent / ('runtime-measured-auth-' + binding + '.json')
    require(not target.exists(), 'renewed runtime already exists; preserve it')
    write(target, updated)
    return target


def check(runtime_path):
    original = read(runtime_path)
    disjoint_auth(original['auth'], (recorded_stage_root(original), original['github_auth']))
    app = runner.Runner(runtime_path)
    runtime = app.runtime
    runner.prepare.verify_release(runtime)
    manifest, binding = model_auth(runtime['auth'])
    auth.claude.lifetime(manifest['expires_at_ms'])
    require(binding == runtime['auth_manifest_sha256'] == runtime['claude_auth_manifest_sha256'] and
            manifest['account'] == runtime['account'] == runtime['claude_account'], 'snapshot binding mismatch')
    for output in (original['output'], original['smoke_output']):
        runner.cell.credential_directory(dict(runtime, output=output))
    hidden = Path(runtime['control']) / 'oracle/experiments/rp-d1-delivery-cost'
    require(digest(hidden / 'oracle.py') == digest(runner.PRIOR / 'oracle.py'), 'hidden oracle changed')
    for task in app.tasks['tasks']:
        for fixture in (Path(runtime['source_root']) / task['source_dir'], hidden / 'fixtures' / task['id']):
            require(app.packet.content(app.packet.tree(fixture)) == task['source_sha256'], 'registered source changed')
    require(all((Path(runtime['control']) / 'public' / name).is_dir() for name in ('python', 'autoresearch')),
            'public check mount missing')
    require(runtime['boot_catalogs'] == {}, 'rp-d5 has no boot catalogs')
    for name, _, config in app.slots():
        app.repository(name)
        app.boot_expectation('X', config)
    completed = app.completed_prefix()
    require(len(completed) < len(app.slots()), 'schedule already complete')
    name = app.slots()[len(completed)][0]
    app.prior_deleted(name)
    app.validate(name)
    app.inputs()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage_dir', type=Path, nargs='?')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--check', type=Path)
    action.add_argument('--renew', type=Path)
    parser.add_argument('--auth', type=Path)
    parser.add_argument('--arms', type=Path)
    parser.add_argument('--run-id')
    parser.add_argument('--image')
    parser.add_argument('--github-auth', type=Path)
    parser.add_argument('--phase', choices=('smoke', 'measured'))
    parser.add_argument('--smoke-output', type=Path)
    parser.add_argument('--smoke-attempt', type=int, default=1)
    args = parser.parse_args()
    if args.check:
        check(args.check)
        print('rp-d5 stage check: PASS')
    elif args.renew:
        if args.auth is None:
            parser.error('--renew requires --auth')
        print(renew(args.renew, args.auth))
    else:
        if any(getattr(args, name) is None for name in
               ('stage_dir', 'arms', 'run_id', 'image', 'auth', 'github_auth', 'phase')):
            parser.error('staging requires stage-dir, arms, run-id, image, auth, github-auth and phase')
        print(stage(args))


if __name__ == '__main__':
    main()
