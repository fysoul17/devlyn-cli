"""The rp-d4 X artifact and byte-identical common prompt, under rp-d5 names."""
import importlib.util
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare_rpd4_rpd5', HERE.parent / 'rp-d4-helper-report/prepare.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
load, PRIOR, github, require = legacy.load, legacy.PRIOR, legacy.github, legacy.require
pack = load('pack_rpd5_prepare', HERE / 'pack.py')
PROMPT_SHA256 = {'X': legacy.PROMPT_SHA256['X']}
prompt_body, native_prompt, release_identity = legacy.prompt_body, legacy.native_prompt, legacy.release_identity


def url(repository):
    require(isinstance(repository, str) and re.fullmatch(
        r'fysoul17/rpd5-[A-Za-z0-9][A-Za-z0-9-]*-(?:smoke2?-claude|c0[1-4])', repository),
        'unregistered rp-d5 repository name')
    return 'https://github.com/' + repository + '.git'


def verify_release(runtime):
    path = Path(runtime['arms_file'])
    release = pack.verify_arms(path)['X']
    tarball = path.parent / release['tarball']
    require(runtime['releases'] == {'X': dict(release, tarball=str(tarball))}, 'runtime/release binding mismatch')
    package = Path(runtime['control']) / 'packages/X/package'
    require(not package.is_symlink() and pack.tree_manifest(package) == pack.archive_manifest(tarball),
            'extracted release differs from verified tarball')


# These modules are private path-loaded instances; inherited files stay immutable.
legacy.pack = pack
legacy.PROMPT_SHA256 = PROMPT_SHA256
legacy.verify_release = verify_release
legacy.legacy.pack = pack
legacy.legacy.verify_release = legacy.legacy.legacy.verify_release = verify_release
github.url = url
binding, prepare = legacy.binding, legacy.prepare
