"""Offline rp-d6 registration/staging, frozen cache copies and snapshot renewal."""
import argparse
import importlib.util
from itertools import combinations
import json
import math
from pathlib import Path
import re
import shutil
import tarfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner_rpd6_stage', HERE / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
legacy = runner.load('stage_rpd4_rpd6', HERE.parent / 'rp-d4-helper-report/stage.py')
read, write, digest, require = runner.read, runner.write, runner.digest, runner.require
pack, auth = runner.prepare.pack, runner.auth
tree = legacy.tree
disjoint_auth, recorded_stage_root = legacy.disjoint_auth, legacy.recorded_stage_root


def cache_input(args):
    """Every stage reads a registered copy; no code path opens the host cache."""
    if args.phase == 'measured':
        previous = read(args.stage_dir / 'runtime-smoke.json')
        source, expected = Path(previous['models_cache']), previous['models_cache_sha256']
    elif args.smoke_attempt == 2:
        first = read(runner.smoke_registry(args.run_id) / 'attempt-1.json')
        previous = read(first['runtime'])
        source, expected = Path(previous['models_cache']), first['inputs']['models_cache_sha256']
        require(previous['models_cache_sha256'] == expected, 'first stage models cache binding changed')
    else:
        require(args.models_cache is not None and isinstance(args.models_cache_sha256, str) and
                re.fullmatch('[a-f0-9]{64}', args.models_cache_sha256),
                'registration requires frozen --models-cache and --models-cache-sha256')
        source, expected = args.models_cache, args.models_cache_sha256
    source = Path(source)
    require(source.resolve() != (Path.home() / '.codex/models_cache.json').resolve(),
            'host models cache cannot be a registration source; provide its frozen registration copy')
    require(not source.is_symlink() and source.is_file() and digest(source) == expected,
            'registered models cache is missing, unsafe or changed')
    return source.resolve(), expected


def token_gate_input(args):
    if args.phase == 'measured':
        previous = read(args.stage_dir / 'runtime-smoke.json')
        source, expected = Path(previous['token_gate']), previous['token_gate_sha256']
    elif args.smoke_attempt == 2:
        first = read(runner.smoke_registry(args.run_id) / 'attempt-1.json')
        previous = read(first['runtime'])
        source, expected = Path(previous['token_gate']), first['inputs']['token_gate_sha256']
    else:
        require(args.token_gate is not None, 'registration requires --token-gate')
        source, expected = args.token_gate, None
    source = Path(source)
    require(not source.is_symlink() and source.is_file(), 'rendered token gate must be a regular file')
    binding = digest(source)
    require(expected is None or expected == binding, 'registered rendered token gate changed')
    gate = read(source)
    require(gate.get('passed') is True and gate.get('arms_sha256') == digest(args.arms) and
            set(gate.get('rows', {})) == {'AGENTS.md', 'CLAUDE.md'}, 'rendered token gate missing pack binding or pass')
    for row in gate['rows'].values():
        for tokenizer in ('claude', 'o200k'):
            pair = row.get(tokenizer)
            require(isinstance(pair, list) and len(pair) == 2 and
                    all(type(value) in (int, float) and math.isfinite(value) and value >= 0 for value in pair)
                    and pair[1] <= pair[0], 'rendered token gate exceeds X or has invalid counts')
    return source.resolve(), binding


def reserve_smoke(args, guard, cache_sha256, gate_sha256):
    runner.smoke_slots(args.smoke_attempt)
    root = runner.smoke_registry(args.run_id)
    inputs = runner.smoke_inputs(dict(arms_file=args.arms, image=args.image,
        codex_account=auth.codex_account(args.auth), claude_account=guard['account'],
        models_cache_sha256=cache_sha256, token_gate_sha256=gate_sha256))
    previous = root / 'attempt-1.json'
    if args.smoke_attempt == 2:
        first = read(previous)
        runner.smoke_registration(read(first['runtime']))
        require(first['status'] == 'FAILED', 'spare requires a failed first smoke without credential revocation')
        require(first['inputs'] == inputs, 'spare changed registered arms, accounts, image or frozen models cache')
        for verdict in first['verdicts']:
            row = read(verdict)
            if row['dispatched']:
                receipt = row.get('repository_cleanup', {})
                require(receipt.get('repository') == f'fysoul17/rpd6-{args.run_id}-{row["cell"]}' and
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
    runner.smoke_slots(args.smoke_attempt)
    source_cache, cache_sha256 = cache_input(args)
    source_gate, gate_sha256 = token_gate_input(args)
    dest, phase = args.stage_dir.resolve(), args.phase
    target = dest / f'runtime-{phase}.json'
    require(not target.exists(), 'runtime already staged; preserve it')
    require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9-]*', args.run_id), 'invalid run_id')
    require(re.fullmatch('sha256:[a-f0-9]{64}', args.image), 'image must be its exact sha256 identity')
    smoke_output = (args.smoke_output or dest / 'smoke-output').resolve()
    require(smoke_output.is_relative_to(dest) and smoke_output != dest, 'smoke output must be under stage directory')
    control = dest / 'control'
    roots = [Path(str(path.resolve()).casefold()) for path in (control, dest / 'output', smoke_output, dest / 'scratch')]
    for left, right in combinations(roots, 2):
        require(not (left.is_relative_to(right) or right.is_relative_to(left)), 'stage roots must be disjoint')
    disjoint_auth(args.auth, (dest, args.claude_auth, args.github_auth))
    disjoint_auth(args.claude_auth, (dest, args.github_auth))
    manifest, manifest_hash = auth.model_auth(args.auth)
    guard, guard_hash = auth.claude_model_auth(args.claude_auth)
    auth.claude.lifetime(guard['expires_at_ms'])
    require(auth.codex_account(args.claude_auth) == auth.codex_account(args.auth), 'Claude transport Codex account differs')
    arms = pack.verify_arms(args.arms)
    for name, _, _ in runner.SCHEDULE + runner.smoke_slots(args.smoke_attempt):
        runner.prepare.prompt_body(runner.arm_for(name), name)
    if phase == 'measured':
        previous = read(dest / 'runtime-smoke.json')
        require(manifest['account'] == previous['account'] and guard['account'] == previous['claude_account'],
                'staging changed registered accounts')
        app = runner.Runner(dest / 'runtime-smoke.json')
        app.finish_smoke()
        app.prior_deleted('m01')
    else:
        require(not dest.exists(), 'stage already exists; preserve it')
        registration, state = reserve_smoke(args, guard, cache_sha256, gate_sha256)
    arms_file = dest / 'arms/arms.json'
    releases = {arm: dict(value, tarball=str(arms_file.parent / value['tarball'])) for arm, value in arms.items()}
    runtime = dict(run_id=args.run_id, phase=phase, smoke_attempt=args.smoke_attempt, releases=releases,
        arms_file=str(arms_file), image=args.image, control=str(control), output=str(dest / 'output'),
        smoke_output=str(smoke_output), scratch=str(dest / 'scratch'), sources=str(dest / 'sources'),
        source_root=str(HERE.parents[2]), auth=str(args.auth.absolute()), github_auth=str(args.github_auth.absolute()),
        account=manifest['account'], codex_account=auth.codex_account(args.auth), auth_manifest_sha256=manifest_hash,
        claude_auth=str(args.claude_auth.absolute()), claude_account=guard['account'], claude_auth_manifest_sha256=guard_hash,
        boot_catalogs={}, tasks_file=str(runner.PRIOR / ('smoke-tasks.json' if phase == 'smoke' else 'tasks.json')),
        models_cache=str(dest / 'models_cache.json'), models_cache_sha256=cache_sha256,
        token_gate=str(dest / 'token-gate.json'), token_gate_sha256=gate_sha256)
    for output in (runtime['output'], runtime['smoke_output']):
        for engine in ('codex', 'claude'):
            runner.cell.credential_directory(dict(auth.for_engine(runtime, engine), output=output))
    if phase == 'measured':
        for key in ('run_id', 'image', 'releases', 'arms_file', 'control', 'models_cache', 'models_cache_sha256',
                    'smoke_output', 'smoke_attempt', 'github_auth', 'token_gate', 'token_gate_sha256'):
            require(runtime[key] == previous[key], 'measured inputs differ from staged smoke: ' + key)
        runtime.update(smoke_account=previous['account'], smoke_codex_account=previous['codex_account'])
    else:
        # This follows rp-d2 staging exactly except that its implicit host cache
        # source is replaced by the explicit, already verified registration copy.
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
        shutil.copyfile(source_cache, runtime['models_cache'])
        shutil.copyfile(source_gate, runtime['token_gate'])
        require(digest(runtime['models_cache']) == cache_sha256, 'frozen cache copy differs from registration')
        require(digest(runtime['token_gate']) == gate_sha256, 'rendered gate copy differs from registration')
        write(dest / 'control.manifest.json', dict(manifests={
            name: tree(control / name) for name in ('public', 'oracle', 'packages')}))
    runner.prepare.verify_release(runtime)
    for key in ('output', 'smoke_output', 'scratch', 'sources'):
        Path(runtime[key]).mkdir(parents=True, exist_ok=True, mode=0o700)
    tasks_dir = dest / 'tasks'
    tasks_dir.mkdir(exist_ok=True)
    for name, _, _ in runner.SCHEDULE + runner.smoke_slots(args.smoke_attempt):
        path = tasks_dir / (name + '.json')
        expected = runner.slot_tasks('measured' if name in runner.ARMS else 'smoke', name)
        if path.exists():
            require(read(path) == expected, 'staged task projection changed')
        else:
            write(path, expected)
    write(target, runtime)
    if phase == 'smoke':
        state.update(status='STAGED', runtime_sha256=digest(target))
        require(state['inputs'] == runner.smoke_inputs(runtime), 'staged smoke inputs changed')
        write(registration, state)
    return target


def renewal_allowed(previous, codex_account, claude_account, completed):
    require(codex_account == previous['codex_account'] and claude_account == previous['claude_account'],
            'renewal requires identical Codex and Claude accounts')
    count = len(completed)
    require(previous['phase'] == 'measured' and count < len(runner.SCHEDULE) and (count >= 8 or count % 2 == 0),
            'renewal requires an unfinished guard or a measured pair boundary')
    require(all(row['status'] in ('PASS', 'ADJUDICATE', 'PRODUCT_INCOMPLETE') and
                (row['config'] != 'claude' or row.get('effort_binding') == 'MATCH') for row in completed),
            'stopped schedule cannot renew or resume')


def renew(runtime_path, auth_path=None, claude_auth_path=None):
    previous = read(runtime_path)
    auth_path = Path(auth_path or previous['auth'])
    claude_auth_path = Path(claude_auth_path or previous['claude_auth'])
    disjoint_auth(auth_path, (recorded_stage_root(previous), claude_auth_path, previous['github_auth']))
    disjoint_auth(claude_auth_path, (recorded_stage_root(previous), previous['github_auth']))
    app = runner.Runner(runtime_path)
    completed = app.completed_prefix()
    renewal_allowed(previous, previous['codex_account'], previous['claude_account'], completed)
    app.prior_deleted(runner.SCHEDULE[len(completed)][0])
    manifest, binding = auth.model_auth(auth_path)
    guard, guard_binding = auth.claude_model_auth(claude_auth_path)
    renewal_allowed(previous, auth.codex_account(auth_path), guard['account'], completed)
    require(auth.codex_account(claude_auth_path) == previous['codex_account'], 'Claude transport changed Codex account')
    auth.claude.lifetime(guard['expires_at_ms'])
    updated = dict(previous, auth=str(auth_path.absolute()), auth_manifest_sha256=binding,
        claude_auth=str(claude_auth_path.absolute()), claude_auth_manifest_sha256=guard_binding,
        renewed_from=dict(path=str(runtime_path.resolve()), sha256=digest(runtime_path)))
    target = runtime_path.parent / ('runtime-measured-auth-' + binding + '-' + guard_binding + '.json')
    require(not target.exists(), 'renewed runtime already exists; preserve it')
    write(target, updated)
    return target


def check(runtime_path):
    original = read(runtime_path)
    disjoint_auth(original['auth'], (recorded_stage_root(original), original['claude_auth'], original['github_auth']))
    disjoint_auth(original['claude_auth'], (recorded_stage_root(original), original['github_auth']))
    app = runner.Runner(runtime_path)
    runtime = app.runtime
    runner.prepare.verify_release(runtime)
    require(digest(runtime['models_cache']) == runtime['models_cache_sha256'], 'frozen models cache changed')
    require(digest(runtime['token_gate']) == runtime['token_gate_sha256'], 'rendered gate changed')
    guard, binding = auth.claude_model_auth(runtime['claude_auth'])
    auth.claude.lifetime(guard['expires_at_ms'])
    require(binding == runtime['claude_auth_manifest_sha256'] and guard['account'] == runtime['claude_account'],
            'Claude snapshot binding mismatch')
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
    require(runtime['boot_catalogs'] == {}, 'rp-d6 has no boot catalogs')
    completed = app.completed_prefix()
    require(len(completed) < len(app.slots()), 'schedule already complete')
    name, _, engine = app.slots()[len(completed)]
    app.prior_deleted(name)
    app.runtime = auth.for_engine(app.base_runtime, engine)
    app.validate(name)
    app.inputs()


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
    parser.add_argument('--models-cache', type=Path)
    parser.add_argument('--models-cache-sha256')
    parser.add_argument('--token-gate', type=Path)
    parser.add_argument('--phase', choices=('smoke', 'measured'))
    parser.add_argument('--smoke-output', type=Path)
    parser.add_argument('--smoke-attempt', type=int, default=1)
    args = parser.parse_args()
    if args.check:
        check(args.check)
        print('rp-d6 stage check: PASS')
    elif args.renew:
        if args.auth is None and args.claude_auth is None:
            parser.error('--renew requires --auth or --claude-auth')
        print(renew(args.renew, args.auth, args.claude_auth))
    else:
        if any(getattr(args, name) is None for name in
               ('stage_dir', 'arms', 'run_id', 'image', 'auth', 'claude_auth', 'github_auth', 'phase')):
            parser.error('staging requires stage-dir, arms, run-id, image, auth, claude-auth, github-auth and phase')
        print(stage(args))


if __name__ == '__main__':
    main()
