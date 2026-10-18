"""P1 and the unchanged X installed-instruction binding over rp-d6."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare_rpd6_rpd7', HERE.parent / 'rp-d6-claude-delivery/prepare.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
load, PRIOR, github, require = legacy.load, legacy.PRIOR, legacy.github, legacy.require
pack = load('pack_rpd7_prepare', HERE / 'pack.py')
COMMON_SHA256 = '2ccc7f6a11891f6270685c09ada44cc4376bbedb047f8a0864f950b415bf50cf'
P1_SHA256 = '2387dddebad66fa3204f54668c4e1ec17487660dcc6e07def50526ae409ccf2e'
PROMPT_SHA256 = {'X': P1_SHA256}
REPLACEMENTS = (
    (b'Restrict source and test edits to its listed allowed paths, and preserve existing user files.',
     b'Preserve existing user files.'),
    (b"Git's internal metadata writes needed for normal repository operations are allowed; do not change Git configuration, dependencies or installed tools.",
     b'Do not change Git configuration, dependencies or installed tools.'))


def derive(raw):
    require(hashlib.sha256(raw).hexdigest() == COMMON_SHA256, 'common.txt hash mismatch')
    for before, after in REPLACEMENTS:
        require(raw.count(before) == 1, 'P1 replacement must occur exactly once')
        raw = raw.replace(before, after)
    require(len(raw) == 353 and hashlib.sha256(raw).hexdigest() == P1_SHA256, 'P1 bytes/hash mismatch')
    return raw


def registered(name):
    require(name in ('m01', 'm02', 'm03', 'm04', 'smoke-claude', 'smoke2-claude'), 'unregistered rp-d7 slot')


def prompt_body(arm, name=None):
    require(arm == 'X', 'unregistered rp-d7 arm')
    if name is not None:
        registered(name)
    return derive((PRIOR / 'common.txt').read_bytes())


def prompt_sha256(name):
    return hashlib.sha256(prompt_body('X', name)).hexdigest()


def native_prompt(caller, arm, name=None):
    return prompt_body(arm, name).decode() + '\nCALLER CONTRACT\n' + json.dumps(caller, indent=2)


def url(repository):
    require(isinstance(repository, str) and re.fullmatch(
        r'fysoul17/rpd7-[A-Za-z0-9][A-Za-z0-9-]*-(?:smoke2?-claude|m0[1-4])', repository),
        'unregistered rp-d7 repository name')
    return 'https://github.com/' + repository + '.git'


def release_identity(runtime, arm):
    require(arm == 'X', 'unregistered rp-d7 arm')
    return legacy.release_identity(runtime, arm)


def verify_release(runtime):
    path = Path(runtime['arms_file'])
    arms = pack.verify_arms(path)
    require(set(runtime['releases']) == {'X'}, 'runtime requires release X only')
    release = arms['X']
    tarball = path.parent / release['tarball']
    require(runtime['releases']['X'] == dict(release, tarball=str(tarball)), 'runtime/release binding mismatch')
    package = Path(runtime['control']) / 'packages/X/package'
    require(not package.is_symlink() and pack.tree_manifest(package) == pack.archive_manifest(tarball),
            'extracted release differs from verified tarball')


def installed_binding(out, runtime, arm):
    legacy.installed_binding(out, runtime, arm)
    work = Path(out) / 'cell/work'
    path = github.safe_file(work, 'CLAUDE.md')
    require(path.is_file(), 'installed CLAUDE.md missing')
    package = Path(runtime['control']) / 'packages' / arm / 'package'
    template = (package / 'CLAUDE.md').read_bytes().replace(b'\r\n', b'\n')
    body = (b'Project-specific instructions outside this managed block take precedence over these defaults.\n\n'
            + template.removesuffix(b'\n') + b'\n')
    block = (b'<!-- devlyn:instructions:begin sha256=' + hashlib.sha256(body).hexdigest().encode()
             + b' -->\n' + body + b'<!-- devlyn:instructions:end -->\n')
    # devlyn-cli@4.2.22 package/bin/devlyn.js writes this exact 11-byte import.
    require(path.read_bytes() in (block, b'@AGENTS.md\n'), 'installed CLAUDE.md differs from verified X instructions')


def prompt_binding(out, release):
    out = Path(out)
    plan, baseline = (github.read(out / name) for name in ('plan.json', 'baseline.json'))
    require(all(row['arm'] == 'X' and row['release'] == release and
                row['prompt_body_sha256'] == prompt_sha256(out.name) for row in (plan, baseline)),
            'attempt prompt/release binding mismatch')
    raw = prompt_body('X', out.name) + b'\nCALLER CONTRACT\n' + (out / 'harness/caller.json').read_bytes()
    require((out / 'prompt.txt').read_bytes() == raw and plan['argv'][-1].encode() == raw and
            baseline['prompt_sha256'] == hashlib.sha256(raw).hexdigest(), 'attempt prompt binding mismatch')


def binding(out, runtime, arm):
    prompt_binding(out, release_identity(runtime, arm))
    require(github.digest(out / 'home/.codex/models_cache.json') == runtime['models_cache_sha256'],
            'cell models cache differs from frozen registration copy')
    installed_binding(out, runtime, arm)


prepare = legacy.prepare
# Private path-loaded modules keep the inherited installer and prelaunch hooks.
legacy.prompt_body, legacy.prompt_sha256, legacy.binding = prompt_body, prompt_sha256, binding
legacy.verify_release = verify_release
github.url = url
for module in (legacy.legacy, legacy.legacy.legacy, legacy.legacy.legacy.legacy):
    module.pack = pack
    module.verify_release = verify_release
