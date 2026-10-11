"""Stage an absent 0238 control/runtime from explicitly selected, already built inputs.
No package build, authentication read, profile request, model call or dispatch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

EXPERIMENT = Path(__file__).resolve().parents[1]
REPO = EXPERIMENT.parents[2]
IMAGE = 'sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(root, regular_only=False):
    return {str(path.relative_to(root)): sha(path) for path in sorted(root.rglob('*'))
            if path.is_file() and (not regular_only or not path.is_symlink())}


def stage(args):
    dest = args.destination.resolve()
    old = read(args.template_runtime)
    freeze = read(args.review_manifest)
    packs = read(args.packs / 'packages.json')
    tasks = read(args.tasks)
    if old['image'] != IMAGE:
        raise ValueError('runtime template does not name the pinned current-CLI image')
    if set(packs['packages']) != {'B', 'S', 'H', 'P'}:
        raise ValueError('require explicit four-arm package metadata')
    if tasks['watchdog_seconds']['owner'] != 5400:
        raise ValueError('registered owner watchdog changed')
    for name, expected in freeze['files'].items():
        if sha(EXPERIMENT / name) != expected:
            raise ValueError('reviewed source changed: ' + name)
    dependency = freeze['shared_process_dependency']
    if sha(REPO / dependency['path']) != dependency['sha256']:
        raise ValueError('reviewed shared process primitive changed')
    native = freeze.get('pair_native_dependencies')
    required = {f'autoresearch/experiments/0234/{name}'
                for name in ('cell.py', 'evidence.py', 'record_usage.py')}
    if not isinstance(native, dict) or set(native) != required:
        raise ValueError('review manifest must bind the three pair native dependencies')
    for path, expected in native.items():
        if sha(REPO / path) != expected:
            raise ValueError('reviewed pair native dependency changed: ' + path)
    for arm, record in packs['packages'].items():
        if sha(args.packs / (arm + '.tgz')) != record['sha256']:
            raise ValueError('package archive changed: ' + arm)
        if arm in ('H', 'P'):
            if record['files'].get('package/config/skills/_shared/peer.py') != freeze['files']['peer.py']:
                raise ValueError('packaged helper differs from reviewed candidate: ' + arm)
            if record['files'].get('package/config/skills/_shared/platform-support.py') != dependency['sha256']:
                raise ValueError('packaged process primitive differs from reviewed candidate: ' + arm)
    dest.mkdir(parents=True, exist_ok=False, mode=0o700)
    control = dest / 'control'
    control.mkdir()
    for name in ('public', 'oracle'):
        shutil.copytree(Path(old['control']) / name, control / name, symlinks=True)
    for relative in ('0234/oracle.js', '0234/fixture_oracle.js', '0238/f23_precision.py'):
        target = control / 'oracle/experiments' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(EXPERIMENT.parent / relative, target)
    for arm, record in packs['packages'].items():
        folder = control / 'packages' / arm
        folder.mkdir(parents=True)
        with tarfile.open(args.packs / (arm + '.tgz')) as archive:
            actual = {member.name: hashlib.sha256(archive.extractfile(member).read()).hexdigest()
                      for member in archive if member.isfile()}
            if actual != record['files']:
                raise ValueError('archive payload differs from package metadata: ' + arm)
            archive.extractall(folder, filter='data')
        if tree(folder, regular_only=True) != record['files']:
            raise ValueError('extracted package differs from sealed regular files: ' + arm)
    manifests = {name: tree(control / name) for name in ('public', 'oracle', 'packages')}
    write(dest / 'control.manifest.json', dict(manifests=manifests))
    shutil.copyfile(args.tasks, dest / 'tasks.json')
    shutil.copyfile(args.review_manifest, dest / 'review-manifest.json')
    shutil.copyfile(args.packs / 'packages.json', dest / 'packages.json')
    for name in ('auth', 'scratch', 'out-smoke'):
        (dest / name).mkdir(mode=0o700)
    # Copy nonsecret paths and account fingerprints only; credentials are absent
    # until the inherited preflight explicitly snapshots the supported host login.
    runtime = {key: old[key] for key in ('sources', 'account', 'models_cache', 'image')}
    runtime.update(control=str(control), output=str(dest / 'out-smoke'), auth=str(dest / 'auth'),
                   scratch=str(dest / 'scratch'), tasks_file=str(dest / 'tasks.json'),
                   source_root=str(REPO), phase='smoke', boot_catalogs={})
    write(dest / 'runtime-smoke.json', runtime)
    write(dest / 'staging.json', dict(schema='0238-staging-v1', stage_sha256=sha(Path(__file__)),
        template_runtime_sha256=sha(args.template_runtime), selected_tasks_sha256=sha(dest / 'tasks.json'),
        selected_review_manifest_sha256=sha(dest / 'review-manifest.json'),
        package_metadata_sha256=sha(dest / 'packages.json'),
        control_manifest_sha256=sha(dest / 'control.manifest.json'), runtime_sha256=sha(dest / 'runtime-smoke.json'),
        dispatch='NOT_AUTHORIZED_OR_PERFORMED', baseline_selection='explicit caller-selected packages'))
    return dest / 'runtime-smoke.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path, help='must not exist')
    parser.add_argument('--packs', type=Path, required=True)
    parser.add_argument('--tasks', type=Path, required=True)
    parser.add_argument('--template-runtime', type=Path, required=True)
    parser.add_argument('--review-manifest', type=Path, required=True)
    args = parser.parse_args()
    print(stage(args))


if __name__ == '__main__':
    main()
