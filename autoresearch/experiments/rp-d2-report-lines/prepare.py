"""Bind X/Y to the unchanged rp-d1 materializer and 0233 installer."""
import importlib.util
from pathlib import Path
import re
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / 'rp-d1-delivery-cost'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = load('prepare_rpd1_rpd2', PRIOR / 'prepare.py')
pack = load('pack_rpd2_prepare', HERE / 'pack.py')
github = legacy.github
require = github.require


def url(repository):
    require(isinstance(repository, str) and re.fullmatch(
        r'fysoul17/rpd2-[A-Za-z0-9][A-Za-z0-9-]*-(?:smoke2?-(?:claude|codex)-[XY]|m(?:0[1-9]|1[0-6]))',
        repository), 'unregistered rp-d2 repository name')
    return 'https://github.com/' + repository + '.git'


github.url = url


def release_identity(runtime, arm):
    require(arm in ('X', 'Y'), 'unregistered rp-d2 arm')
    release = runtime['releases'][arm]
    return {key: release[key] for key in ('version', 'sha256', 'integrity', 'source', 'manifest_sha256')}


def verify_release(runtime):
    arms_path = Path(runtime['arms_file'])
    arms = pack.verify_arms(arms_path)
    require(set(runtime['releases']) == {'X', 'Y'}, 'runtime requires releases X and Y')
    for arm, release in arms.items():
        tarball = arms_path.parent / release['tarball']
        require(runtime['releases'][arm] == dict(release, tarball=str(tarball)), 'runtime/arm release mismatch')
        package = Path(runtime['control']) / 'packages' / arm / 'package'
        require(not package.is_symlink() and pack.tree_manifest(package) == pack.archive_manifest(tarball),
                arm + ': extracted release differs from verified tarball')
        metadata = github.read(package / 'package.json')
        require(metadata['name'] == 'devlyn-cli' and metadata['version'] == '4.2.18', 'wrong release package name/version')


legacy.verify_release = verify_release


def binding(out, runtime, arm):
    expected = release_identity(runtime, arm)
    plan, baseline = (github.read(out / name) for name in ('plan.json', 'baseline.json'))
    require(all(row['arm'] == arm and row['release'] == expected for row in (plan, baseline)),
            'attempt arm/installed package binding mismatch')
    installed = [name for name in baseline['installed_files'] if name.endswith('/skills/_shared/task-completion.md')]
    require(bool(installed), 'installer produced no reporting instruction')
    source = Path(runtime['control']) / 'packages' / arm / 'package' / pack.FILE
    require(all(github.digest(github.safe_file(out / 'cell/work', name)) == github.digest(source)
                for name in installed), 'installed reporting instruction differs from attempt arm')


def prepare(runtime, name, task, arm, config, *, inherited, tasks, tasks_path, repository, remaining):
    def install(selected, work, home, engine, route):
        require(route == 'B' and engine == config and selected is runtime, 'installed route binding mismatch')
        # B is the ancestor's installed-product route; only X/Y select package mounts.
        return inherited.install(selected, work, home, engine, arm)

    proxy = SimpleNamespace(**(vars(inherited) | {'install': install}))
    out = legacy.prepare(runtime, name, task, 'B', config, inherited=proxy, tasks=tasks,
                         tasks_path=tasks_path, repository=repository, remaining=remaining)
    for filename in ('plan.json', 'baseline.json'):
        path = out / filename
        github.write(path, dict(github.read(path), arm=arm, release=release_identity(runtime, arm)))
    binding(out, runtime, arm)
    return out
