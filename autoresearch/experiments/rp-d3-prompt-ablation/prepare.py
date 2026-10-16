"""One registry artifact and two byte-bound prompts over the frozen rp-d2 materializer."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare_rpd2_rpd3', HERE.parent / 'rp-d2-report-lines/prepare.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
load, PRIOR, github = legacy.load, legacy.PRIOR, legacy.github
require = github.require
pack = load('pack_rpd3_prepare', HERE / 'pack.py')
SUFFIX = b' Finish with what you changed, what you verified and anything unresolved.'
PROMPT_SHA256 = {
    'P0': '2ccc7f6a11891f6270685c09ada44cc4376bbedb047f8a0864f950b415bf50cf',
    'P1': 'ea77742f3d54f28638d1ca5e7240b8ce7fa1df9644429784239d6c806f601a21',
}


def prompt_body(arm):
    require(arm in PROMPT_SHA256, 'unregistered rp-d3 arm')
    raw = (PRIOR / 'common.txt').read_bytes()
    require(raw.endswith(SUFFIX + b'\n'), 'registered prompt suffix changed')
    bodies = {'P0': raw, 'P1': raw[:-len(SUFFIX) - 1] + b'\n'}
    require(all(hashlib.sha256(body).hexdigest() == PROMPT_SHA256[key]
                for key, body in bodies.items()), 'registered prompt-body hash mismatch')
    return bodies[arm]


def native_prompt(caller, arm):
    return prompt_body(arm).decode() + '\nCALLER CONTRACT\n' + json.dumps(caller, indent=2)


def url(repository):
    require(isinstance(repository, str) and re.fullmatch(
        r'fysoul17/rpd3-[A-Za-z0-9][A-Za-z0-9-]*-(?:smoke2?-codex-P[01]|m0[1-8])', repository),
        'unregistered rp-d3 repository name')
    return 'https://github.com/' + repository + '.git'


def release_identity(runtime, arm):
    require(arm in PROMPT_SHA256, 'unregistered rp-d3 arm')
    return {key: runtime['releases']['B'][key]
            for key in ('version', 'sha256', 'integrity', 'source', 'manifest_sha256')}


def verify_release(runtime):
    path = Path(runtime['arms_file'])
    release = pack.verify_arms(path)['B']
    tarball = path.parent / release['tarball']
    require(runtime['releases'] == {'B': dict(release, tarball=str(tarball))}, 'runtime/release binding mismatch')
    package = Path(runtime['control']) / 'packages/B/package'
    require(not package.is_symlink() and pack.tree_manifest(package) == pack.archive_manifest(tarball),
            'extracted release differs from verified tarball')
    metadata = github.read(package / 'package.json')
    require(metadata['name'] == 'devlyn-cli' and metadata['version'] == '4.2.18', 'wrong release package')
    pack.check_blob((package / pack.FILE).read_bytes())


def binding(out, runtime, arm):
    expected = release_identity(runtime, arm)
    plan, baseline = (github.read(out / name) for name in ('plan.json', 'baseline.json'))
    require(all(row['arm'] == arm and row['release'] == expected and
                row['prompt_body_sha256'] == PROMPT_SHA256[arm] for row in (plan, baseline)),
            'attempt prompt/release binding mismatch')
    raw = prompt_body(arm) + b'\nCALLER CONTRACT\n' + (out / 'harness/caller.json').read_bytes()
    require((out / 'prompt.txt').read_bytes() == raw and plan['argv'][-1].encode() == raw and
            baseline['prompt_sha256'] == hashlib.sha256(raw).hexdigest(), 'attempt prompt binding mismatch')
    installed = [name for name in baseline['installed_files'] if name.endswith('/skills/_shared/task-completion.md')]
    require(bool(installed), 'installer produced no reporting instruction')
    for name in installed:
        pack.check_blob(github.safe_file(out / 'cell/work', name).read_bytes())


def prepare(runtime, name, task, arm, config, **kwargs):
    require(config == 'codex', 'rp-d3 is Codex only')
    # B is the one installed-product mount; prompt selection happens in native_prompt.
    out = legacy.legacy.prepare(runtime, name, task, 'B', config, **kwargs)
    for filename in ('plan.json', 'baseline.json'):
        path = out / filename
        github.write(path, dict(github.read(path), arm=arm, release=release_identity(runtime, arm),
                               prompt_body_sha256=PROMPT_SHA256[arm]))
    binding(out, runtime, arm)
    return out


# Private import instances only; frozen source files and other importers stay untouched.
github.url = url
legacy.legacy.verify_release = verify_release
