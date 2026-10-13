"""Stage rp-d1 locally, or --check a runtime; no model, GitHub or PAT reads."""
import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner_rpd1_stage', HERE / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
read, write, digest = runner.read, runner.write, runner.digest
require = runner.github.require
auth = runner.cell.auth


def model_auth(path):
    root = auth.directory(path)
    require({p.name for p in root.iterdir()} == {'manifest.json', 'claude.env', 'codex.json'},
            'auth snapshot file set mismatch')
    raw = auth.read_private(root, 'manifest.json')
    manifest = json.loads(raw)
    require(set(manifest) == {'schema_version', 'account', 'expires_at_ms', 'files'}
            and type(manifest['schema_version']) is int and manifest['schema_version'] == 1
            and set(manifest['files']) == {'claude.env', 'codex.json'}, 'invalid auth manifest')
    account = manifest['account']
    require(isinstance(account, list) and len(account) == 2
            and all(isinstance(item, str) and re.fullmatch('[a-f0-9]{12}', item) for item in account),
            'invalid auth account')
    for name, expected in manifest['files'].items():
        require(auth.digest(auth.read_private(root, name)) == expected, 'auth file hash mismatch')
    return manifest, auth.digest(raw)


def tree(root):
    # Match the inherited control_unchanged file census exactly.
    return {str(p.relative_to(root)): digest(p) for p in sorted(root.rglob('*')) if p.is_file()}


def smoke_catalogs(output):
    path = output / 'verdict-smoke-claude.json'
    require(path.is_file(), 'smoke-claude recorded boot catalogs are required')
    catalogs = read(path).get('boot_catalogs')
    require(isinstance(catalogs, dict) and set(catalogs) == {'skills', 'plugins', 'mcp_servers'}
            and all(isinstance(items, list) for items in catalogs.values()),
            'smoke-claude recorded boot catalogs are required')
    return catalogs


def stage(args):
    dest = args.stage_dir.resolve()
    phase = args.phase
    target = dest / f'runtime-{phase}.json'
    require(not target.exists(), 'runtime already staged; preserve it')
    smoke_output = args.smoke_output.resolve() if args.smoke_output else dest / 'smoke-output'
    require(smoke_output.is_relative_to(dest) and smoke_output != dest,
            'smoke output must be under the stage directory')
    catalogs = {'claude': {'B': smoke_catalogs(smoke_output)}} if phase == 'measured' else {}
    manifest, manifest_hash = model_auth(args.auth)
    release = dict(version='4.2.18', tarball=str(dest / 'release.tgz'), sha256=digest(args.release_tarball),
        integrity='sha512-' + base64.b64encode(hashlib.sha512(args.release_tarball.read_bytes()).digest()).decode())
    control = dest / 'control'
    runtime = dict(run_id=args.run_id, phase=phase, release=release, image=args.image,
        control=str(control), output=str(dest / 'output'), smoke_output=str(smoke_output),
        scratch=str(dest / 'scratch'), sources=str(dest / 'sources'), source_root=str(HERE.parents[2]),
        auth=str(args.auth.absolute()), github_auth=str(args.github_auth.absolute()),
        account=manifest['account'], auth_manifest_sha256=manifest_hash,
        tasks_file=str(HERE / ('smoke-tasks.json' if phase == 'smoke' else 'tasks.json')),
        models_cache=str(dest / 'models_cache.json'), boot_catalogs=catalogs)
    require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9-]*', args.run_id), 'invalid run_id')
    require(re.fullmatch('sha256:[a-f0-9]{64}', args.image), 'image must be its exact sha256 identity')
    for output in (runtime['output'], runtime['smoke_output']):
        runner.cell.credential_directory(dict(runtime, output=output))
    if dest.exists():
        require(phase == 'measured', 'stage already exists; preserve it')
        previous = read(dest / 'runtime-smoke.json')
        for key in ('run_id', 'image', 'release', 'control', 'models_cache', 'smoke_output'):
            require(runtime[key] == previous[key], 'measured inputs differ from staged smoke')
        runtime['models_cache_sha256'] = previous['models_cache_sha256']
        require(digest(Path(runtime['models_cache'])) == runtime['models_cache_sha256'], 'models cache changed')
    else:
        dest.mkdir(parents=True, mode=0o700)
        for mount in ('python', 'autoresearch'):
            (control / 'public' / mount).mkdir(parents=True)
        hidden = control / 'oracle/experiments/rp-d1-delivery-cost'
        hidden.mkdir(parents=True)
        shutil.copyfile(HERE / 'oracle.py', hidden / 'oracle.py')
        shutil.copytree(HERE / 'fixtures', hidden / 'fixtures',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache'))
        package = control / 'packages/B'
        package.mkdir(parents=True)
        shutil.copyfile(args.release_tarball, release['tarball'])
        with tarfile.open(release['tarball'], 'r:gz') as archive:
            archive.extractall(package, filter='data')
        shutil.copyfile(Path.home() / '.codex/models_cache.json', runtime['models_cache'])
        runtime['models_cache_sha256'] = digest(Path(runtime['models_cache']))
        write(dest / 'control.manifest.json', dict(manifests={
            name: tree(control / name) for name in ('public', 'oracle', 'packages')}))
    runner.prepare.verify_release(runtime)
    require(read(control / 'packages/B/package/package.json')['name'] == 'devlyn-cli', 'wrong release package')
    for key in ('output', 'smoke_output', 'scratch', 'sources'):
        Path(runtime[key]).mkdir(parents=True, exist_ok=True, mode=0o700)
    write(target, runtime)
    return target


def check(runtime_path):
    app = runner.Runner(runtime_path)
    runtime = app.runtime
    expected_tasks = HERE / ('smoke-tasks.json' if runtime['phase'] == 'smoke' else 'tasks.json')
    require(app.tasks == read(expected_tasks) and read(runtime['tasks_file']) == app.tasks,
            'phase requires its frozen rp-d1 tasks')
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
    require(digest(hidden / 'oracle.py') == digest(HERE / 'oracle.py'), 'hidden oracle changed')
    for task in app.tasks['tasks']:
        for fixture in (Path(runtime['source_root']) / task['source_dir'], hidden / 'fixtures' / task['id']):
            require(app.packet.content(app.packet.tree(fixture)) == task['source_sha256'], 'registered source changed')
    require(all((Path(runtime['control']) / 'public' / name).is_dir() for name in ('python', 'autoresearch')),
            'public check mount missing')
    for name, _, config in app.slots():
        app.repository(name)
        app.boot_expectation('B', config)
    if runtime['phase'] == 'measured':
        require(runtime['boot_catalogs']['claude']['B'] == smoke_catalogs(Path(runtime['smoke_output'])),
                'registered boot catalogs differ from smoke-claude')
    app.prior_deleted(app.slots()[0][0])
    app.validate(app.slots()[0][0])  # includes control seal and docker image inspect


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage_dir', type=Path, nargs='?')
    parser.add_argument('--check', type=Path, metavar='RUNTIME')
    parser.add_argument('--run-id')
    parser.add_argument('--release-tarball', type=Path)
    parser.add_argument('--image')
    parser.add_argument('--auth', type=Path)
    parser.add_argument('--github-auth', type=Path)
    parser.add_argument('--phase', choices=('smoke', 'measured'))
    parser.add_argument('--smoke-output', type=Path)
    args = parser.parse_args(argv)
    if args.check:
        if any(value is not None for key, value in vars(args).items() if key != 'check'):
            parser.error('--check accepts only a runtime path')
    elif any(getattr(args, key) is None for key in (
            'stage_dir', 'run_id', 'release_tarball', 'image', 'auth', 'github_auth', 'phase')):
        parser.error('staging requires stage-dir, --run-id, --release-tarball, --image, --auth, --github-auth and --phase')
    try:
        if args.check:
            check(args.check)
            print('rp-d1 stage check: PASS (inputs, release, credential shape, boot catalogs, image)')
        else:
            print(stage(args))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError, tarfile.TarError) as exc:
        print('rp-d1 stage: STOP (' + type(exc).__name__ + ')')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
