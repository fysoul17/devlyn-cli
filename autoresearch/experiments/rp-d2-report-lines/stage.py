"""Stage two offline arms, check a runtime, or renew auth between measured pairs."""
import argparse
import importlib.util
from itertools import combinations
from pathlib import Path
import re
import shutil
import tarfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner_rpd2_stage', HERE / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
legacy = runner.load('stage_rpd1_rpd2', runner.PRIOR / 'stage.py')
read, write, digest, require = runner.read, runner.write, runner.digest, runner.require
pack, auth = runner.prepare.pack, legacy.auth
model_auth, tree = legacy.model_auth, legacy.tree


def smoke_catalogs(output, attempt):
    result = {}
    for name, _, engine in runner.smoke_slots(attempt):
        if engine != 'claude':
            continue
        path = output / f'verdict-{name}.json'
        require(path.is_file(), name + ': recorded boot catalogs are required')
        catalogs = read(path).get('boot_catalogs')
        require(isinstance(catalogs, dict) and set(catalogs) == {'skills', 'plugins', 'mcp_servers'} and
                all(isinstance(items, list) for items in catalogs.values()), name + ': invalid boot catalogs')
        result[runner.arm_for(name)] = catalogs
    return {'claude': result}


def stage(args):
    runner.smoke_slots(args.smoke_attempt)
    dest, phase = args.stage_dir.resolve(), args.phase
    target = dest / f'runtime-{phase}.json'
    require(not target.exists(), 'runtime already staged; preserve it')
    smoke_output = (args.smoke_output or dest / 'smoke-output').resolve()
    require(smoke_output.is_relative_to(dest) and smoke_output != dest, 'smoke output must be under stage directory')
    control = dest / 'control'
    roots = [Path(str(path.resolve()).casefold()) for path in (control, dest / 'output', smoke_output, dest / 'scratch')]
    for left, right in combinations(roots, 2):
        require(not (left.is_relative_to(right) or right.is_relative_to(left)), 'stage roots must be disjoint')
    require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9-]*', args.run_id), 'invalid run_id')
    require(re.fullmatch('sha256:[a-f0-9]{64}', args.image), 'image must be its exact sha256 identity')
    arms = pack.verify_arms(args.arms)
    manifest, manifest_hash = model_auth(args.auth)
    catalogs = smoke_catalogs(smoke_output, args.smoke_attempt) if phase == 'measured' else {}
    arms_file = dest / 'arms/arms.json'
    releases = {arm: dict(value, tarball=str(arms_file.parent / value['tarball'])) for arm, value in arms.items()}
    runtime = dict(run_id=args.run_id, phase=phase, smoke_attempt=args.smoke_attempt, releases=releases,
        arms_file=str(arms_file), image=args.image, control=str(control), output=str(dest / 'output'),
        smoke_output=str(smoke_output), scratch=str(dest / 'scratch'), sources=str(dest / 'sources'),
        source_root=str(HERE.parents[2]), auth=str(args.auth.absolute()), github_auth=str(args.github_auth.absolute()),
        account=manifest['account'], codex_account=runner.codex_account(args.auth),
        auth_manifest_sha256=manifest_hash, boot_catalogs=catalogs,
        tasks_file=str(runner.PRIOR / ('smoke-tasks.json' if phase == 'smoke' else 'tasks.json')),
        models_cache=str(dest / 'models_cache.json'))
    for output in (runtime['output'], runtime['smoke_output']):
        runner.cell.credential_directory(dict(runtime, output=output))
    if dest.exists():
        require(phase == 'measured', 'stage already exists; preserve it')
        previous = read(dest / 'runtime-smoke.json')
        for key in ('run_id', 'image', 'releases', 'arms_file', 'control', 'models_cache', 'smoke_output',
                    'smoke_attempt', 'github_auth'):
            require(runtime[key] == previous[key], 'measured inputs differ from staged smoke: ' + key)
        runtime['smoke_account'] = previous['account']
        runtime['smoke_codex_account'] = previous['codex_account']
        runtime['models_cache_sha256'] = previous['models_cache_sha256']
        require(digest(Path(runtime['models_cache'])) == runtime['models_cache_sha256'], 'models cache changed')
    else:
        require(phase == 'smoke', 'stage smoke before measurement')
        dest.mkdir(parents=True, mode=0o700)
        arms_file.parent.mkdir()
        for arm, value in arms.items():
            shutil.copyfile(args.arms.parent / value['tarball'], releases[arm]['tarball'])
            package = control / 'packages' / arm
            package.mkdir(parents=True)
            with tarfile.open(releases[arm]['tarball'], 'r:gz') as archive:
                archive.extractall(package, filter='data')
        shutil.copyfile(args.arms, arms_file)
        for mount in ('python', 'autoresearch'):
            (control / 'public' / mount).mkdir(parents=True)
        hidden = control / 'oracle/experiments/rp-d1-delivery-cost'
        hidden.mkdir(parents=True)
        shutil.copyfile(runner.PRIOR / 'oracle.py', hidden / 'oracle.py')
        shutil.copytree(runner.PRIOR / 'fixtures', hidden / 'fixtures',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache'))
        shutil.copyfile(Path.home() / '.codex/models_cache.json', runtime['models_cache'])
        runtime['models_cache_sha256'] = digest(Path(runtime['models_cache']))
        write(dest / 'control.manifest.json', dict(manifests={
            name: tree(control / name) for name in ('public', 'oracle', 'packages')}))
    runner.prepare.verify_release(runtime)
    for key in ('output', 'smoke_output', 'scratch', 'sources'):
        Path(runtime[key]).mkdir(parents=True, exist_ok=True, mode=0o700)
    write(target, runtime)
    return target


def renewal_allowed(previous, account, completed):
    require(account == previous['account'], 'model auth renewal requires the identical account pair')
    require(previous['phase'] == 'measured' and len(completed) < 16 and len(completed) % 2 == 0,
            'model auth renewal is allowed only between measured pairs')
    require(all(row['status'] in ('PASS', 'ADJUDICATE', 'PRODUCT_INCOMPLETE') for row in completed),
            'stopped schedule cannot renew or resume')


def renew(runtime_path, auth_path):
    app = runner.Runner(runtime_path)
    previous = read(runtime_path)
    completed = app.completed_prefix()
    # Reject a half-pair before reading the replacement snapshot.
    renewal_allowed(previous, previous['account'], completed)
    if completed:
        app.prior_deleted(runner.SCHEDULE[len(completed)][0])
    manifest, manifest_hash = model_auth(auth_path)
    renewal_allowed(previous, manifest['account'], completed)
    require(runner.codex_account(auth_path) == previous['codex_account'],
            'model auth renewal requires the identical Codex account')
    auth.lifetime(manifest['expires_at_ms'])
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
    require(digest(Path(runtime['models_cache'])) == runtime['models_cache_sha256'], 'models cache changed')
    manifest, manifest_hash = model_auth(Path(runtime['auth']))
    require(manifest_hash == runtime['auth_manifest_sha256'] and manifest['account'] == runtime['account'],
            'auth manifest/account binding mismatch')
    auth.lifetime(manifest['expires_at_ms'])
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
    for name, _, config in app.slots():
        app.repository(name)
        app.boot_expectation(runner.arm_for(name), config)
    if runtime['phase'] == 'measured':
        require(runtime['boot_catalogs'] == smoke_catalogs(Path(runtime['smoke_output']), runtime['smoke_attempt']),
                'registered boot catalogs differ from smoke Claude cells')
    completed = app.completed_prefix()
    require(len(completed) < len(app.slots()), 'schedule already complete')
    name = app.slots()[len(completed)][0]
    app.prior_deleted(name)
    app.validate(name)


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
        print('rp-d2 stage check: PASS')
    elif args.renew:
        if args.auth is None:
            parser.error('--renew requires --auth')
        print(renew(args.renew, args.auth))
    else:
        if any(getattr(args, name) is None for name in
               ('stage_dir', 'arms', 'run_id', 'image', 'auth', 'github_auth', 'phase')):
            parser.error('staging requires stage-dir, --arms, --run-id, --image, --auth, --github-auth and --phase')
        print(stage(args))


if __name__ == '__main__':
    main()
