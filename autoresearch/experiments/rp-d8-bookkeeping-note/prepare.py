"""The frozen two-arm pack and P1 plus registered guard suffixes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare_rpd6_rpd8', HERE.parent / 'rp-d6-claude-delivery/prepare.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
load, PRIOR, github, require = legacy.load, legacy.PRIOR, legacy.github, legacy.require
p1 = load('prepare_p1_rpd8', HERE.parent / 'rp-d7-prompt-delivery/prepare.py')
pack = load('pack_rpd8_prepare', HERE / 'pack.py')
P1_SHA256 = p1.P1_SHA256
PROMPT_SHA256 = dict(X=P1_SHA256, Y=P1_SHA256)
SUFFIXES = {
    'g03': b'Do not push or open a pull request.',
    'g04': b'Commit.',
    'g05': b'Do not commit.',
    'g07': b'Open a pull request.',
    'g08': b'Do not create or change any file outside the allowed paths.',
}
SLOTS = tuple(f'm{i:02}' for i in range(1, 17)) + tuple(f'g{i:02}' for i in range(1, 9)) + (
    'smoke-claude', 'smoke-codex', 'smoke2-claude', 'smoke2-codex')


def registered(name):
    require(name in SLOTS, 'unregistered rp-d8 slot')


def prompt_body(arm, name=None):
    require(arm in PROMPT_SHA256, 'unregistered rp-d8 arm')
    if name is not None:
        registered(name)
    raw = p1.derive((PRIOR / 'common.txt').read_bytes())
    return raw + b'\n' + SUFFIXES[name] + b'\n' if name in SUFFIXES else raw


def prompt_sha256(name):
    return hashlib.sha256(prompt_body('Y', name)).hexdigest()


def native_prompt(caller, arm, name=None):
    return prompt_body(arm, name).decode() + '\nCALLER CONTRACT\n' + json.dumps(caller, indent=2)


def url(repository):
    require(isinstance(repository, str) and re.fullmatch(
        r'fysoul17/rpd8-[A-Za-z0-9][A-Za-z0-9-]*-(?:smoke2?-(?:claude|codex)|m(?:0[1-9]|1[0-6])|g0[1-578])',
        repository), 'unregistered rp-d8 repository name')
    return 'https://github.com/' + repository + '.git'


release_identity = legacy.release_identity
verify_release = legacy.verify_release


def installed_binding(out, runtime, arm):
    # Retain rp-d7's strict installed CLAUDE/AGENTS binding (including import).
    p1.installed_binding(out, runtime, arm)
    baseline = github.read(Path(out) / 'baseline.json')
    copies = [name for name in baseline['installed_files'] if name.endswith(pack.FILE.removeprefix('config'))]
    original = Path(runtime['control']) / 'packages' / arm / 'package' / pack.FILE
    require(copies and all(github.safe_file(Path(out) / 'cell/work', name).read_bytes() == original.read_bytes()
                          for name in copies), 'installed task-completion.md differs from arm')


def prompt_binding(out, release, arm=None):
    out = Path(out)
    plan, baseline = (github.read(out / name) for name in ('plan.json', 'baseline.json'))
    arm = baseline['arm'] if arm is None else arm
    require(arm in PROMPT_SHA256 and all(row['arm'] == arm and row['release'] == release and
                row['prompt_body_sha256'] == prompt_sha256(out.name) for row in (plan, baseline)),
            'attempt prompt/release binding mismatch')
    raw = prompt_body(arm, out.name) + b'\nCALLER CONTRACT\n' + (out / 'harness/caller.json').read_bytes()
    require((out / 'prompt.txt').read_bytes() == raw and plan['argv'][-1].encode() == raw and
            baseline['prompt_sha256'] == hashlib.sha256(raw).hexdigest(), 'attempt prompt binding mismatch')


def binding(out, runtime, arm):
    out = Path(out)
    prompt_binding(out, release_identity(runtime, arm), arm)
    require(github.digest(out / 'home/.codex/models_cache.json') == runtime['models_cache_sha256'],
            'cell models cache differs from frozen registration copy')
    installed_binding(out, runtime, arm)


prepare = legacy.prepare
legacy.prompt_body, legacy.prompt_sha256, legacy.binding = prompt_body, prompt_sha256, binding
legacy.installed_binding = installed_binding
github.url = url
for module in (legacy, legacy.legacy, legacy.legacy.legacy, legacy.legacy.legacy.legacy):
    module.pack = pack
    module.verify_release = verify_release
