"""Reuse rp-d2 offline staging with two packages and separate Codex/Claude snapshots."""
import argparse
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner_rpd4_stage', HERE / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
legacy = runner.load('stage_rpd2_rpd4', HERE.parent / 'rp-d2-report-lines/stage.py')
read, write, digest, require = runner.read, runner.write, runner.digest, runner.require
pack, auth = runner.prepare.pack, runner.auth
model_auth, tree = auth.model_auth, legacy.tree
legacy.runner, legacy.pack, legacy.model_auth = runner, pack, model_auth
legacy.smoke_catalogs = lambda _output, _attempt: {}
inherited_stage = legacy.stage


def disjoint_auth(auth_path, roots):
    model = Path(str(Path(auth_path).resolve()).casefold())
    for root in roots:
        boundary = Path(str(Path(root).resolve()).casefold())
        require(not (model.is_relative_to(boundary) or boundary.is_relative_to(model)),
                'model auth must be disjoint from output, smoke_output, scratch and stage roots')


def recorded_stage_root(runtime):
    # The frozen control path records the original stage, even through a runtime
    # symlink or copy. All staged paths must still describe that same layout.
    root = Path(runtime['control']).parent.resolve()
    for key, relative in (('control', 'control'), ('output', 'output'), ('scratch', 'scratch'),
                          ('sources', 'sources'), ('arms_file', 'arms/arms.json'),
                          ('models_cache', 'models_cache.json')):
        path = Path(runtime[key])
        require(path.is_absolute() and path.resolve() == root / relative,
                'runtime recorded stage roots do not match: ' + key)
    smoke = Path(runtime['smoke_output'])
    require(smoke.is_absolute() and smoke.resolve().is_relative_to(root) and smoke.resolve() != root,
            'runtime recorded stage roots do not match: smoke_output')
    return root


def stage(args):
    guard, guard_hash = auth.claude_model_auth(args.claude_auth)
    require(auth.codex_account(args.claude_auth) == auth.codex_account(args.auth),
            'guard transport requires the identical Codex account')
    dest = args.stage_dir.resolve()
    disjoint_auth(args.auth, (dest, dest / 'output', args.smoke_output or dest / 'smoke-output', dest / 'scratch'))
    disjoint_auth(args.claude_auth, (dest, args.auth, args.github_auth))
    for arm in runner.prepare.PROMPT_SHA256:
        runner.prepare.prompt_body(arm)
    if args.phase == 'measured':
        previous = read(args.stage_dir / 'runtime-smoke.json')
        require(auth.codex_account(args.auth) == previous['codex_account'] and
                guard['account'] == previous['claude_account'], 'staging changed the registered accounts')
        runner.Runner(args.stage_dir / 'runtime-smoke.json').prior_deleted('m01')
    target = inherited_stage(args)
    runtime = read(target)
    runtime.update(claude_auth=str(args.claude_auth.absolute()), claude_account=guard['account'],
                   claude_auth_manifest_sha256=guard_hash)
    write(target, runtime)
    return target


def renewal_allowed(previous, account, completed):
    require(account == previous['codex_account'], 'renewal requires the identical Codex account')
    require(previous['phase'] == 'measured' and len(completed) < 10 and len(completed) % 2 == 0,
            'model auth renewal is allowed only between measured pairs')
    require(all(row['status'] in ('PASS', 'ADJUDICATE', 'PRODUCT_INCOMPLETE') for row in completed),
            'stopped schedule cannot renew or resume')


def renew(runtime_path, auth_path=None, claude_auth_path=None):
    previous = read(runtime_path)
    auth_path = Path(auth_path or previous['auth'])
    claude_auth_path = Path(claude_auth_path or previous['claude_auth'])
    disjoint_auth(auth_path, (recorded_stage_root(previous), claude_auth_path, previous['github_auth']))
    disjoint_auth(claude_auth_path, (recorded_stage_root(previous), previous['github_auth']))
    app = runner.Runner(runtime_path)
    completed = app.completed_prefix()
    renewal_allowed(previous, previous['codex_account'], completed)
    if completed:
        app.prior_deleted(runner.SCHEDULE[len(completed)][0])
    manifest, manifest_hash = model_auth(auth_path)
    renewal_allowed(previous, manifest['account'], completed)
    guard, guard_hash = auth.claude_model_auth(claude_auth_path)
    require(guard['account'] == previous['claude_account'] and
            auth.codex_account(claude_auth_path) == previous['codex_account'],
            'renewal requires the identical Claude and Codex accounts')
    if claude_auth_path != Path(previous['claude_auth']):
        auth.claude.lifetime(guard['expires_at_ms'])
    updated = dict(previous, auth=str(auth_path.absolute()), auth_manifest_sha256=manifest_hash,
                   claude_auth=str(claude_auth_path.absolute()), claude_auth_manifest_sha256=guard_hash,
                   renewed_from=dict(path=str(runtime_path.resolve()), sha256=digest(runtime_path)))
    target = runtime_path.parent / ('runtime-measured-auth-' + manifest_hash + '-' + guard_hash + '.json')
    require(not target.exists(), 'renewed runtime already exists; preserve it')
    write(target, updated)
    return target


def check(runtime_path):
    original = read(runtime_path)
    disjoint_auth(original['auth'], (recorded_stage_root(original), original['claude_auth'], original['github_auth']))
    disjoint_auth(original['claude_auth'], (recorded_stage_root(original), original['github_auth']))
    app = runner.Runner(runtime_path)
    runtime = app.runtime
    expected = runner.PRIOR / ('smoke-tasks.json' if runtime['phase'] == 'smoke' else 'tasks.json')
    require(app.tasks == read(expected) and read(runtime['tasks_file']) == app.tasks, 'phase requires frozen rp-d1 tasks')
    app.inputs()
    runner.prepare.verify_release(runtime)
    manifest, binding = auth.claude_model_auth(runtime['claude_auth'])
    require(binding == runtime['claude_auth_manifest_sha256'] and manifest['account'] == runtime['claude_account'],
            'guard snapshot binding mismatch')
    for output in (original['output'], original['smoke_output']):
        for engine in ('codex', 'claude'):
            runner.cell.credential_directory(dict(auth.for_engine(runtime, engine), output=output))
    hidden = Path(runtime['control']) / 'oracle/experiments/rp-d1-delivery-cost'
    require(digest(hidden / 'oracle.py') == digest(runner.PRIOR / 'oracle.py'), 'hidden oracle changed')
    for task in app.tasks['tasks']:
        for fixture in (Path(runtime['source_root']) / task['source_dir'], hidden / 'fixtures' / task['id']):
            require(app.packet.content(app.packet.tree(fixture)) == task['source_sha256'], 'registered source changed')
    require(all((Path(runtime['control']) / 'public' / name).is_dir() for name in ('python', 'autoresearch')),
            'public check mount missing')
    require(runtime['boot_catalogs'] == {}, 'rp-d4 has no boot catalogs')
    for name, _, config in app.slots():
        app.repository(name)
        app.boot_expectation(runner.arm_for(name), config)
    completed = app.completed_prefix()
    require(len(completed) < len(app.slots()), 'schedule already complete')
    name = app.slots()[len(completed)][0]
    app.prior_deleted(name)
    app.runtime = auth.for_engine(app.base_runtime, 'claude' if name.startswith('g') else 'codex')
    app.validate(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage_dir', type=Path, nargs='?')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--check', type=Path)
    action.add_argument('--renew', type=Path)
    parser.add_argument('--auth', type=Path)
    parser.add_argument('--claude-auth', type=Path)
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
        print('rp-d4 stage check: PASS')
    elif args.renew:
        if args.auth is None and args.claude_auth is None:
            parser.error('--renew requires --auth or --claude-auth')
        print(renew(args.renew, args.auth, args.claude_auth))
    else:
        if any(getattr(args, name) is None for name in
               ('stage_dir', 'arms', 'run_id', 'image', 'auth', 'claude_auth', 'github_auth', 'phase')):
            parser.error('staging requires stage-dir, arms, run-id, image, both auth snapshots, github-auth and phase')
        print(stage(args))

if __name__ == '__main__':
    main()
