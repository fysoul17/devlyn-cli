"""Two candidate-bound releases, unchanged P0, frozen rp-d2/rp-d1 materialization."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare_rpd2_rpd4', HERE.parent / 'rp-d2-report-lines/prepare.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
load, PRIOR, github = legacy.load, legacy.PRIOR, legacy.github
require = github.require
pack = load('pack_rpd4_prepare', HERE / 'pack.py')
smoke = load('smoke_rpd4_prepare', HERE / 'smoke.py')
prompts = load('prepare_rpd3_prompt_rpd4', HERE.parent / 'rp-d3-prompt-ablation/prepare.py')
PROMPT_SHA256 = {arm: prompts.PROMPT_SHA256['P0'] for arm in ('X', 'Y')}


def prompt_body(arm):
    require(arm in PROMPT_SHA256, 'unregistered rp-d4 arm')
    return prompts.prompt_body('P0')


def native_prompt(caller, arm):
    return prompt_body(arm).decode() + '\nCALLER CONTRACT\n' + json.dumps(caller, indent=2)


def url(repository):
    require(isinstance(repository, str) and re.fullmatch(
        r'fysoul17/rpd4-[A-Za-z0-9][A-Za-z0-9-]*-(?:smoke2?-codex-[XY]|m0[1-8]|g0[12])', repository),
        'unregistered rp-d4 repository name')
    return 'https://github.com/' + repository + '.git'


release_identity = legacy.release_identity


def verify_release(runtime):
    path = Path(runtime['arms_file'])
    arms = pack.verify_arms(path)
    require(set(runtime['releases']) == {'X', 'Y'}, 'runtime requires releases X and Y')
    for arm, release in arms.items():
        tarball = path.parent / release['tarball']
        require(runtime['releases'][arm] == dict(release, tarball=str(tarball)), 'runtime/release binding mismatch')
        package = Path(runtime['control']) / 'packages' / arm / 'package'
        require(not package.is_symlink() and pack.tree_manifest(package) == pack.archive_manifest(tarball),
                'extracted release differs from verified tarball')
        metadata = github.read(package / 'package.json')
        require(metadata['name'] == 'devlyn-cli' and metadata['version'] == '4.2.22', 'wrong release package')


def binding(out, runtime, arm):
    expected = release_identity(runtime, arm)
    plan, baseline = (github.read(out / name) for name in ('plan.json', 'baseline.json'))
    require(all(row['arm'] == arm and row['release'] == expected and
                row['prompt_body_sha256'] == PROMPT_SHA256[arm] for row in (plan, baseline)),
            'attempt prompt/release binding mismatch')
    raw = prompt_body(arm) + b'\nCALLER CONTRACT\n' + (out / 'harness/caller.json').read_bytes()
    require((out / 'prompt.txt').read_bytes() == raw and plan['argv'][-1].encode() == raw and
            baseline['prompt_sha256'] == hashlib.sha256(raw).hexdigest(), 'attempt prompt binding mismatch')
    for source in pack.FILES:
        suffix = source.removeprefix('config')
        installed = [name for name in baseline['installed_files'] if name.endswith(suffix)]
        require(bool(installed), 'installer produced no helper/reporting instruction')
        original = Path(runtime['control']) / 'packages' / arm / 'package' / source
        require(all(github.digest(github.safe_file(out / 'cell/work', name)) == github.digest(original)
                    for name in installed), 'installed helper/reporting instruction differs from arm')
    if runtime['phase'] == 'smoke' and arm == 'Y':
        smoke.verify_observer(out)


def prepare(runtime, name, task, arm, config, **kwargs):
    out = legacy.prepare(runtime, name, task, arm, config, **kwargs)
    for filename in ('plan.json', 'baseline.json'):
        path = out / filename
        github.write(path, dict(github.read(path), prompt_body_sha256=PROMPT_SHA256[arm]))
    if runtime['phase'] == 'smoke' and arm == 'Y':
        smoke.install_observer(out)
        path = out / 'plan.json'
        plan = github.read(path)
        plan['env']['PYTHONPATH'] = '/harness:' + plan['env']['PYTHONPATH']
        github.write(path, plan)
    binding(out, runtime, arm)
    return out


# Mutate private path-loaded modules only, never inherited source files.
github.url = url
legacy.pack = pack
legacy.verify_release = legacy.legacy.verify_release = verify_release
# rp-d2 binds its own two-file-independent release/installed checks before returning.
