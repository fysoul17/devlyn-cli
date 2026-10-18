"""rp-d4 release materialization, with registered per-slot prompt bodies."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare_rpd4_rpd6', HERE.parent / 'rp-d4-helper-report/prepare.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
load, PRIOR, github, require = legacy.load, legacy.PRIOR, legacy.github, legacy.require
pack = load('pack_rpd6_prepare', HERE / 'pack.py')
COMMON_SHA256 = legacy.PROMPT_SHA256['X']
SUFFIXES = {'g04': b'Do not push or open a pull request.', 'g05': b'Commit.'}
PROMPT_SHA256 = {arm: COMMON_SHA256 for arm in ('X', 'Y')}


def prompt_body(arm, name=None):
    require(arm in PROMPT_SHA256, 'unregistered rp-d6 arm')
    raw = legacy.prompt_body(arm)
    return raw + b'\n' + SUFFIXES[name] + b'\n' if name in SUFFIXES else raw


def prompt_sha256(name):
    return hashlib.sha256(prompt_body('Y', name)).hexdigest()


def native_prompt(caller, arm, name=None):
    return prompt_body(arm, name).decode() + '\nCALLER CONTRACT\n' + json.dumps(caller, indent=2)


def url(repository):
    require(isinstance(repository, str) and re.fullmatch(
        r'fysoul17/rpd6-[A-Za-z0-9][A-Za-z0-9-]*-(?:smoke2?-(?:claude|codex)|m0[1-8]|g0[1-5])', repository),
        'unregistered rp-d6 repository name')
    return 'https://github.com/' + repository + '.git'


release_identity = legacy.release_identity
verify_release = legacy.verify_release


def installed_binding(out, runtime, arm):
    """Check installed instruction bodies against this arm's verified package."""
    baseline = github.read(out / 'baseline.json')
    work = out / 'cell/work'
    package = Path(runtime['control']) / 'packages' / arm / 'package'
    principles = 'config/skills/_shared/runtime-principles.md'
    copies = [name for name in baseline['installed_files'] if name.endswith(principles.removeprefix('config'))]
    require(copies and all(github.safe_file(work, name).read_bytes() == (package / principles).read_bytes()
                          for name in copies), 'installed runtime principles differ from arm')
    blocks = {}
    for name in ('AGENTS.md', 'CLAUDE.md'):
        path = work / name
        if not path.exists():
            continue
        text = github.safe_file(work, name).read_bytes().replace(b'\r\n', b'\n')
        template = (package / name).read_bytes().replace(b'\r\n', b'\n')
        body = (b'Project-specific instructions outside this managed block take precedence over these defaults.\n\n'
                + template.removesuffix(b'\n') + b'\n')
        block = (b'<!-- devlyn:instructions:begin sha256=' + hashlib.sha256(body).hexdigest().encode()
                 + b' -->\n' + body + b'<!-- devlyn:instructions:end -->\n')
        blocks[name] = text.count(block) == 1
        if not blocks[name]:
            require(name == 'CLAUDE.md' and b'@AGENTS.md' in text and blocks.get('AGENTS.md'),
                    'installed managed instruction differs from arm')
    require(blocks.get('AGENTS.md') is True, 'installed AGENTS.md managed block missing')


def binding(out, runtime, arm):
    out = Path(out)
    name = out.name
    expected = release_identity(runtime, arm)
    plan, baseline = (github.read(out / filename) for filename in ('plan.json', 'baseline.json'))
    require(all(row['arm'] == arm and row['release'] == expected and
                row['prompt_body_sha256'] == prompt_sha256(name) for row in (plan, baseline)),
            'attempt prompt/release binding mismatch')
    raw = prompt_body(arm, name) + b'\nCALLER CONTRACT\n' + (out / 'harness/caller.json').read_bytes()
    require((out / 'prompt.txt').read_bytes() == raw and plan['argv'][-1].encode() == raw and
            baseline['prompt_sha256'] == hashlib.sha256(raw).hexdigest(), 'attempt prompt binding mismatch')
    require(github.digest(out / 'home/.codex/models_cache.json') == runtime['models_cache_sha256'],
            'cell models cache differs from frozen registration copy')
    installed_binding(out, runtime, arm)


def prepare(runtime, name, task, arm, config, **kwargs):
    # rp-d2 preserves the X/Y mount and rp-d1 materializer; rp-d4's helper observer
    # is specific to its reporting experiment and is not part of this smoke.
    if name == 'g06':
        verify_release(runtime)
        local = load('local_only_rpd6_prepare', HERE / 'local_only.py')
        out = local.prepare(runtime, name, task, arm, config, **kwargs)
    else:
        out = legacy.legacy.prepare(runtime, name, task, arm, config, **kwargs)
    for filename in ('plan.json', 'baseline.json'):
        path = out / filename
        github.write(path, dict(github.read(path), arm=arm, release=release_identity(runtime, arm),
                               prompt_body_sha256=prompt_sha256(name)))
    binding(out, runtime, arm)
    return out


# Private path-loaded modules only; no inherited file or other importer changes.
github.url = url
legacy.pack = pack
legacy.legacy.pack = pack
legacy.legacy.verify_release = legacy.legacy.legacy.verify_release = verify_release
# Replace rp-d2's study-specific installed reporting-file check. The final
# rp-d6 binding above checks the three registered instruction surfaces instead.
legacy.legacy.binding = lambda out, runtime, arm: installed_binding(out, runtime, arm)
