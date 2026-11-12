"""Assemble the 0266 control trees (0256's, with the 4.3.31 package and its three one-sentence variants). Never
dispatches models.

control.py <sources> <cache> <out> <image>    build <out> and <out>.manifest.json
control.py compare <B package> <C package> <K>  the qualification comparison of one built C package with B; prints the
                                              files and fields that differ, or refuses

<out>/public                    participant /control: public tools only
<out>/oracle                    evaluator-only files, mounted over /control/autoresearch in check containers
<out>/packages/B/package        the published package (DESIGN "Arms" B), by npm integrity
<out>/packages/K<n>/package     C-K<n>: B's own unpacked tree with the candidate's sentence inserted at the end of its
                                principle's paragraph in the package's principle sources (CLAUDE.md and AGENTS.md),
                                and everything the package derives from them re-derived by the package's own code
                                (bin/release.js buildRelease, run in the cell image without network)
<out>/packages/<P> is mounted read-only at /install in the owner containers of the cells that use package P.

A C package qualifies only when compare() shows exactly what DESIGN "Arms" allows: the sentence inserted once in each
file of PRINCIPLE_FILES, the fields of DERIVED that derive from those files, and no other file, byte, mode or name.
"""
import hashlib
import base64
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import uuid
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
_spec = importlib.util.spec_from_file_location('control0222', HERE.parent / '0222/control.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
PACKAGE_URL = 'https://registry.npmjs.org/devlyn-cli/-/devlyn-cli-4.3.31.tgz'
INTEGRITY = 'sha512-HE0XFeXaS3ySRxpUUO9ZH6v0gUr/X028cGdTG7ryVXCCwXiutmANON5tfGkmzmINbPqJ2SPhWJt99Z5d7Q/MtQ=='
# DESIGN "Candidates": (the principle whose paragraph the sentence ends, the sentence).
CANDIDATES = {
    'K1': (2, 'Handle unspecified failure cases in code you add according to the applicable error contract, without '
              'narrowing specified valid inputs or masking unrelated failures, and report the choice.'),
    'K2': (7, 'Where the request does not say how new code fails on bad input, follow the error contract it does state, '
              'report the choice, and do not reject input the request allows.'),
    'K3': (7, 'Where the request does not say how new code fails on bad input, follow the error contract it does state '
              'and report the choice.'),
}
PACKAGES = ('B', *CANDIDATES)
TARBALL_SHA256 = 'd32da6acaa788d41cb982e8b0a1c8d7ad556fe97c98c4d6801beb1cd0b73691c'
# Each package pinned before the screen (DESIGN "Arms"): its tree_sha256 and its release digest, as this build gave them
# on 2026-11-12 in the cell image; a build that gives anything else is refused.
PINS = {
    'B': ('01df3aade1e34a639a196c4fd0b03fa93d6fce93f443dd80e6beccebed0cd6e5',
          '7be19f082103d694d2c85ab15c7687e43b0e6038903b8b3e997c3744f7ee647e'),
    'K1': ('e369c30e0004fdfa2a19875cc0eaf5aa3306b3e3488098329e51c9f319544292',
           '561f6f9ed714d9f1f1d179557ff3fdb76d2b05005238bc1338b2e7238d02a946'),
    'K2': ('1ffa0a126ba223158cfc9d1cd76d6f4dbe9090b0e1725f8aa33e300a6d0d3794',
           '8c3ddc5c945ac3a31aa4d06d6d645b6e4cf4f50e747840113f55ed4ce9bc6aba'),
    'K3': ('7f7216ca439816f56cbcdca2a5e9323751fd2d8cf3854ea7b6e7bba8729c8fca',
           'd4536fb01862a0baf4652927e7ac355931a4cb4f4f17c59f3a0c93b6ef3e9ec8'),
}
# The package's principle sources (bin/release.js reads both and requires them equal) and the files it derives from
# them (generatedArtifacts: sessionDefaults for the three runtime-principles.md, managedBlock for harness/*).
SOURCES = ('AGENTS.md', 'CLAUDE.md')
PRINCIPLE_FILES = SOURCES + (
    'config/skills/_shared/runtime-principles.md', 'harness/AGENTS.md', 'harness/CLAUDE.md',
    'native/claude/skills/_shared/runtime-principles.md',
    'native/codex/plugins/devlyn/skills/_shared/runtime-principles.md')
MANAGED = ('harness/AGENTS.md', 'harness/CLAUDE.md')
BEGIN, END = '<!-- devlyn:instructions:begin sha256=', '<!-- devlyn:instructions:end -->'
MANAGED_PREFIX = 'Project-specific instructions outside this managed block take precedence over these defaults.\n\n'
# Every field that differs between B and a C package; nothing else may.
DERIVED = tuple(f'{name}: devlyn:instructions:begin sha256' for name in MANAGED) + (
    'release.json: principles.sourceBlockSha256',
    *(f'release.json: files[{name}].sha256' for name in sorted(PRINCIPLE_FILES)), 'release.json: digest.value')
BUILD = "process.stdout.write(JSON.stringify(require('/pkg/bin/release').buildRelease('/pkg')))"
VERIFY = ("process.stdout.write(JSON.stringify(require('/pkg/bin/release').verifyRelease('/pkg', "
          "{ npmInstall: true }).release))")
ORACLE = [name for name in base.TRACKED if name.startswith('autoresearch/experiments/')] + [
    'autoresearch/experiments/0233/oracle.js']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    """bin/release.js canonical(): sorted keys, no whitespace, JSON.stringify scalars."""
    if isinstance(value, list):
        return '[' + ','.join(canonical(item) for item in value) + ']'
    if isinstance(value, dict):
        return '{' + ','.join(json.dumps(key, ensure_ascii=False) + ':' + canonical(value[key])
                              for key in sorted(value)) + '}'
    return json.dumps(value, ensure_ascii=False)


def fetch(cache):
    """Read the frozen npm tarball or fetch it once; cached corruption is always fatal."""
    import urllib.request
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / 'B.tgz'
    if path.exists():
        data = path.read_bytes()
    else:
        with urllib.request.urlopen(PACKAGE_URL, timeout=60) as response:
            data = response.read()
    expected = base64.b64decode(INTEGRITY.removeprefix('sha512-'))
    if hashlib.sha512(data).digest() != expected:
        raise ValueError('B.tgz: npm integrity mismatch')
    if not path.exists():
        path.write_bytes(data)
    return path


def members(path):
    with tarfile.open(path) as archive:
        return {m.name: hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                for m in archive.getmembers() if m.isfile()}


def manifest(tree):
    return {str(p.relative_to(tree)): digest(p) for p in sorted(tree.rglob('*')) if p.is_file()}


def entries(root):
    """Every path under root, never followed: (kind, permission bits, sha256 of the bytes or the link target)."""
    found = {}
    for folder, dirs, files in os.walk(root):
        for name in dirs + files:
            path = Path(folder) / name
            info = path.lstat()
            kind = 'link' if stat.S_ISLNK(info.st_mode) else 'dir' if stat.S_ISDIR(info.st_mode) else (
                'file' if stat.S_ISREG(info.st_mode) else 'other')
            content = (sha256(os.readlink(path).encode()) if kind == 'link' else
                       digest(path) if kind == 'file' else None)
            found[str(path.relative_to(root))] = (kind, stat.S_IMODE(info.st_mode), content)
    return found


def tree_sha256(root):
    """A package tree's pin: the sha256 of its sorted entries (names, kinds, modes, contents)."""
    return sha256(json.dumps(sorted(entries(root).items())).encode())


def insert(text, candidate):
    """The sentence at the end of its principle's paragraph (the one line that starts `<n>. **`)."""
    number, sentence = CANDIDATES[candidate]
    lines = [line for line in text.split('\n') if line.startswith(f'{number}. **')]
    if len(lines) != 1 or text.count(lines[0]) != 1:
        raise ValueError(f'principle {number} is not one line of its own')
    return text.replace(lines[0], f'{lines[0]} {sentence}')


def managed_digest(text):
    """The begin marker's sha256 of a managed block (bin/instructions.js managedBlock): the body between the marker's
    line and the end marker."""
    first, _, rest = text.partition('\n')
    if not first.startswith(BEGIN) or not first.endswith(' -->') or rest.count(END) != 1:
        raise ValueError('not one devlyn managed block')
    return first[len(BEGIN):-len(' -->')], sha256(rest[:rest.index(END)].encode())


def sentence_counts(text):
    return {candidate: text.count(sentence) for candidate, (_, sentence) in CANDIDATES.items()}


def flat(value, path=''):
    """release.json as {field: value}; a files[] entry is named by its path."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield from flat(item, f'{path}.{key}' if path else key)
    elif isinstance(value, list) and value and all(isinstance(item, dict) and 'path' in item for item in value):
        for item in value:
            yield from flat({key: field for key, field in item.items() if key != 'path'}, f'{path}[{item["path"]}]')
    else:
        yield path, value


def release(root):
    """release.json parsed, refused unless its bytes are exactly release.js's own serialization of it."""
    data = (Path(root) / 'release.json').read_bytes()
    parsed = json.loads(data)
    if data != (json.dumps(parsed, indent=2, ensure_ascii=False) + '\n').encode():
        raise ValueError(f'{root}/release.json is not in release.js serialization')
    return parsed


def compare(b_root, c_root, candidate):
    """DESIGN "Arms": C differs from B exactly by the candidate's sentence, once, in each file that carries the
    principles, and by the fields derived from those files, each equal to its re-derived value. Returns the frozen lists
    {files, fields}; refuses (ValueError) on anything else, naming every difference it found."""
    b, c = entries(b_root), entries(c_root)
    problems = [f'{name}: only in {"B" if name in b else "C"}' for name in sorted(set(b) ^ set(c))]
    problems += [f'{name}: kind or mode {b[name][:2]} in B, {c[name][:2]} in C' for name in sorted(set(b) & set(c))
                 if b[name][:2] != c[name][:2]]
    changed = sorted(name for name in set(b) & set(c) if b[name][2] != c[name][2])
    if changed != sorted(PRINCIPLE_FILES + ('release.json',)):
        problems.append(f'contents differ in {changed}, expected exactly {sorted(PRINCIPLE_FILES)} and release.json')
    for name in PRINCIPLE_FILES:
        old, new = ((Path(root) / name).read_text(encoding='utf-8') for root in (b_root, c_root))
        expected = insert(old, candidate)
        if name in MANAGED:
            declared, body = managed_digest(old)
            if declared != body:
                problems.append(f'{name}: B\'s managed block marker {declared} is not its body\'s {body}')
            expected = expected.replace(BEGIN + declared, BEGIN + managed_digest(expected)[1], 1)
        counts = {'B': sentence_counts(old), 'C': sentence_counts(new)}
        if new != expected or counts != {'B': {k: 0 for k in CANDIDATES},
                                         'C': {k: int(k == candidate) for k in CANDIDATES}}:
            problems.append(f'{name}: not B with the {candidate} sentence inserted once (sentence counts {counts})')
    old, new = release(b_root), release(c_root)
    flat_old, flat_new = dict(flat(old)), dict(flat(new))
    fields = sorted(key for key in set(flat_old) | set(flat_new) if flat_old.get(key) != flat_new.get(key))
    allowed = sorted(field.removeprefix('release.json: ') for field in DERIVED if field.startswith('release.json: '))
    if fields != allowed:
        problems.append(f'release.json fields differ in {fields}, expected exactly {allowed}')
    template = (Path(c_root) / 'CLAUDE.md').read_text(encoding='utf-8').replace('\r\n', '\n')
    rederived = {f'files[{name}].sha256': digest(Path(c_root) / name) for name in PRINCIPLE_FILES}
    # bin/instructions.js managedBody: the prefix, then the template with a final newline ensured
    rederived['principles.sourceBlockSha256'] = sha256(
        (MANAGED_PREFIX + template + ('' if template.endswith('\n') else '\n')).encode())
    rederived['digest.value'] = sha256(canonical({k: v for k, v in new.items() if k != 'digest'}).encode())
    problems += [f'release.json {field} is {flat_new.get(field)}, re-derived {value}' for field, value in
                 rederived.items() if flat_new.get(field) != value]
    if any(managed_digest((Path(c_root) / name).read_text(encoding='utf-8'))[0] != rederived[
            'principles.sourceBlockSha256'] for name in MANAGED):
        problems.append('a managed block marker is not release.json principles.sourceBlockSha256')
    if problems:
        raise ValueError(f'C-{candidate} does not differ from B as DESIGN "Arms" allows: ' + '; '.join(problems))
    return dict(files=list(PRINCIPLE_FILES), fields=list(DERIVED))


def node(image, package, script, writable):
    """One node command in a fresh container of the cell image, without network, the package mounted at /pkg."""
    done = subprocess.run(['docker', 'run', '--rm', '--name', f'devlyn-0266-build-{uuid.uuid4().hex}', '--label',
                           'devlyn.task=0266-build', '--network', 'none', '--mount',
                           f'type=bind,src={package},dst=/pkg' + ('' if writable else ',readonly'), '-w', '/pkg',
                           image, 'node', '-e', script], capture_output=True, text=True, timeout=300)
    if done.returncode:
        raise ValueError(f'node in {image} exited {done.returncode}: {done.stderr.strip()[-400:]}')
    return json.loads(done.stdout)


def build_candidate(packages, candidate, image):
    """C-<candidate> from B's unpacked tree: the sentence inserted in the sources, the package's own buildRelease
    re-derives the rest, its own verifyRelease (what `devlyn run` runs on a package) accepts it, and compare() holds."""
    b, c = packages / 'B/package', packages / candidate / 'package'
    shutil.copytree(b, c, symlinks=True)
    for name in SOURCES:
        (c / name).write_text(insert((c / name).read_text(encoding='utf-8'), candidate), encoding='utf-8')
    built = node(image, c, BUILD, writable=True)
    verified = node(image, c, VERIFY, writable=False)
    if verified['digest'] != built['digest'] or release(c)['digest']['value'] != built['digest']:
        raise ValueError(f'C-{candidate}: built release {built["digest"]}, verified {verified["digest"]}')
    comparison = compare(b, c, candidate)
    number, sentence = CANDIDATES[candidate]
    return dict(source='B', principle=number, sentence=sentence, release_digest=built['digest'],
                tree_sha256=tree_sha256(c), comparison=comparison)


def build(sources, cache, out, image):
    out.mkdir(parents=False, exist_ok=False)
    public, oracle = out / 'public', out / 'oracle'
    for name in ORACLE:
        target = oracle / Path(name).relative_to('autoresearch')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target)
    public.mkdir()
    (public / 'autoresearch').mkdir()  # the check containers' mount point for the oracle tree
    with tarfile.open(base.fetch(cache, 'prettier.tgz')) as archive:
        archive.extractall(public / '.prettier', filter='data')
    (public / '.prettier/package').rename(public / 'prettier')
    (public / '.prettier').rmdir()
    with zipfile.ZipFile(base.fetch(cache, 'ruff.whl')) as wheel:
        (public / 'ruff').write_bytes(wheel.read('ruff-0.15.9.data/scripts/ruff'))
    (public / 'ruff').chmod(0o755)
    # Click's tests read its installed metadata. Only the metadata is provided: an installed copy of the code would
    # silently replace the cell's own source whenever `src` is not first on the path.
    with tempfile.TemporaryDirectory() as temp:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', '--no-deps', '--no-compile',
                        '--target', temp, str(sources / 'click')], check=True,
                       env={**os.environ, 'PIP_CACHE_DIR': str(Path(temp) / 'pip-cache')})
        (info,) = Path(temp).glob('click-*.dist-info')
        shutil.copytree(info, public / 'python' / info.name)
    tgz = fetch(cache)
    with tarfile.open(tgz) as archive:
        archive.extractall(out / 'packages/B', filter='data')
    packages = dict(B=dict(url=PACKAGE_URL, integrity=INTEGRITY, sha256=digest(tgz), files=members(tgz),
                           tree_sha256=tree_sha256(out / 'packages/B/package'),
                           release_digest=release(out / 'packages/B/package')['digest']['value']))
    for candidate in CANDIDATES:
        packages[candidate] = build_candidate(out / 'packages', candidate, image)
    for name, (tree, release_digest) in PINS.items():
        if (packages[name]['tree_sha256'], packages[name]['release_digest']) != (tree, release_digest):
            raise ValueError(f'package {name}: tree {packages[name]["tree_sha256"]} release '
                             f'{packages[name]["release_digest"]}, pinned {tree} {release_digest}')
    record = dict(packages=packages, manifests={name: manifest(out / name) for name in ('public', 'oracle', 'packages')})
    (out.parent / (out.name + '.manifest.json')).write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    print(hashlib.sha256(json.dumps(record['manifests'], sort_keys=True).encode()).hexdigest())


if __name__ == '__main__':
    if sys.argv[1:2] == ['compare'] and len(sys.argv) == 5:
        try:
            print(json.dumps(compare(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]), indent=1))
        except ValueError as exc:
            print(f'REFUSED: {exc}', file=sys.stderr)
            sys.exit(1)
    else:
        build(*(Path(arg).resolve() for arg in sys.argv[1:4]), sys.argv[4])
