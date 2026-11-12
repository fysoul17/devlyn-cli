"""Offline tests for the 0266 runtime root and its packages: fakes for Docker, the registry and the control build
(a small synthetic package stands in for devlyn-cli, its derived files re-derived the way release.js derives them);
local Git only."""
import base64
import datetime
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent


def load(name, path=None):
    spec = importlib.util.spec_from_file_location('test_0266_runtime_' + name, path or HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


setup = load('setup_runtime')
control = setup.control
REAL_RUN = subprocess.run
GIT = ['git', '-c', 'user.name=t', '-c', 'user.email=t@localhost', '-c', 'commit.gpgsign=false']
IMAGE_ID = 'sha256:' + 'ab' * 32
ISSUE = 'Issue body — ünïcode, "quotes"\nand a second line\n'


def repo(path, content):
    path.mkdir(parents=True)
    REAL_RUN(GIT + ['init', '-q', str(path)], check=True)
    (path / 'file.txt').write_text(content)
    REAL_RUN(GIT + ['-C', str(path), 'add', '-A'], check=True)
    REAL_RUN(GIT + ['-C', str(path), 'commit', '-qm', 'base'], check=True)
    commit, tree = REAL_RUN(['git', '-C', str(path), 'rev-parse', 'HEAD', 'HEAD^{tree}'],
                            check=True, capture_output=True, text=True).stdout.split()
    return commit, tree


def prompt(context):
    return 'Do the task.\n\nCALLER CONTRACT\n' + json.dumps(dict(request='r', original_context=context), indent=2)


def save_tar(path, image_id):
    data = json.dumps([dict(Config='blobs/sha256/' + image_id.removeprefix('sha256:'), RepoTags=[])]).encode()
    with tarfile.open(path, 'w') as archive:
        info = tarfile.TarInfo('manifest.json')
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))


class FakeDocker:
    """Docker and build.sh stand-ins; Git goes to the real binary."""

    def __init__(self):
        self.image = None
        self.versions = '\n'.join(setup.VERSIONS)
        self.calls = []

    def __call__(self, argv, **kwargs):
        argv = list(argv)
        if argv[0] == 'git':
            return REAL_RUN(argv, **kwargs)
        self.calls.append(argv)
        done = lambda code=0, out='': subprocess.CompletedProcess(argv, code, out, '' if code == 0 else 'error')
        if argv[:3] == ['docker', 'image', 'inspect']:
            return done(0, self.image + '\n') if self.image else done(1)
        if argv[0] == 'bash' and argv[1].endswith('build.sh'):
            self.image = IMAGE_ID
            return done()
        if argv[:2] == ['docker', 'run']:
            return done(0, self.versions + '\n')
        if argv[:2] == ['docker', 'save']:
            save_tar(argv[3], argv[4])
            return done()
        if argv[:2] == ['docker', 'load']:
            with tarfile.open(argv[3]) as archive:
                (entry,) = json.load(archive.extractfile('manifest.json'))
            self.image = 'sha256:' + Path(entry['Config']).name
            return done()
        raise AssertionError(f'unexpected command {argv}')

    def mutations(self):
        return [c for c in self.calls if c[0] == 'bash' or c[:2] in (['docker', 'save'], ['docker', 'load'])]


TEMPLATE = ('# Project Instructions\n\n## Core principles\n\n1. **No workaround** — fix the root cause.\n'
            '2. **No overengineering** — smallest sufficient change.\n7. **Production ready** — errors are visible.\n'
            '\nEach skill is the source of truth.\n')
PREAMBLE = 'The following Devlyn instructions are defaults for this session.\n\n'


def derive(package, template):
    """What bin/release.js derives from the principle sources (sessionDefaults, managedBlock, release.json), written
    the way release.js writes it: the stand-in for the package's own buildRelease."""
    body = control.MANAGED_PREFIX + template
    texts = {name: template for name in control.SOURCES} | {
        name: PREAMBLE + template for name in control.PRINCIPLE_FILES if name.endswith('runtime-principles.md')} | {
        name: f'{control.BEGIN}{control.sha256(body.encode())} -->\n{body}{control.END}\n' for name in control.MANAGED}
    for name, text in texts.items():
        (package / name).parent.mkdir(parents=True, exist_ok=True)
        (package / name).write_text(text, encoding='utf-8')
    files = sorted(str(p.relative_to(package)) for p in package.rglob('*') if p.is_file() and p.name != 'release.json')
    manifest = dict(schemaVersion=1, package='devlyn-cli', version='4.3.31',
                    principles=dict(defaults='config/skills/_shared/runtime-principles.md',
                                    sourceBlockSha256=control.sha256(body.encode())),
                    files=[dict(path=name, sha256=control.digest(package / name), executable=False) for name in files])
    manifest['digest'] = dict(algorithm='sha256', value=control.sha256(control.canonical(manifest).encode()))
    (package / 'release.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')


def synthetic_package(folder):
    """A small stand-in for B's unpacked package: one program file and the principle files with their derivations."""
    package = folder / 'package'
    (package / 'bin').mkdir(parents=True)
    (package / 'bin/devlyn.js').write_text('console.log("4.3.31")\n')
    derive(package, TEMPLATE)
    return package


def fake_candidate(packages, candidate, image):
    """control.build_candidate's shape, with derive() for the package's own buildRelease (no Docker here)."""
    b, c = packages / 'B/package', packages / candidate / 'package'
    shutil.copytree(b, c, symlinks=True)
    derive(c, control.insert(TEMPLATE, candidate))
    number, sentence = control.CANDIDATES[candidate]
    return dict(source='B', principle=number, sentence=sentence, release_digest=control.release(c)['digest']['value'],
                tree_sha256=control.tree_sha256(c), comparison=control.compare(b, c, candidate))


def fake_build(sources, cache, out, image):
    """control.build's shape: three trees, B from cache/B.tgz and the three candidates, the manifest beside the tree."""
    out.mkdir(parents=False, exist_ok=False)
    (out / 'public/python').mkdir(parents=True)
    (out / 'public/ruff').write_text('ruff')
    (out / 'oracle/experiments').mkdir(parents=True)
    (out / 'oracle/experiments/oracle.js').write_text('oracle')
    tgz = cache / 'B.tgz'
    with tarfile.open(tgz) as archive:
        archive.extractall(out / 'packages/B', filter='data')
    packages = dict(B=dict(url=control.PACKAGE_URL, integrity=control.INTEGRITY, sha256=control.digest(tgz),
                           files=control.members(tgz), tree_sha256=control.tree_sha256(out / 'packages/B/package'),
                           release_digest=control.release(out / 'packages/B/package')['digest']['value']))
    for candidate in control.CANDIDATES:
        packages[candidate] = fake_candidate(out / 'packages', candidate, image)
    record = dict(packages=packages,
                  manifests={name: control.manifest(out / name) for name in ('public', 'oracle', 'packages')})
    (out.parent / (out.name + '.manifest.json')).write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    return record


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.root = base / 'live'
        sources = {}
        for name, text in (('commander', 'js'), ('click', 'py')):
            commit, tree = repo(base / 'remote' / name, text)
            sources[name] = (name, commit, tree)
        self.archive = base / 'archive'
        hashes = {}
        for task, cell, context in (('D3', 'd001-D3-claude-A-r1', ISSUE), ('D4', 'd005-D4-claude-A-r1', ISSUE + 'D4')):
            (self.archive / cell).mkdir(parents=True)
            (self.archive / cell / 'prompt.txt').write_text(prompt(context), encoding='utf-8')
            hashes[task] = hashlib.sha256(context.encode('utf-8')).hexdigest()
        self.override = base / 'tasks-override.json'
        self.override.write_text(json.dumps({task: dict(issue_snapshot_sha256=value, fetched_at='t', url='u')
                                             for task, value in hashes.items()}))
        package = synthetic_package(base / 'pkg')
        self.tgz = base / 'B.tgz'
        with tarfile.open(self.tgz, 'w:gz') as archive:
            archive.add(package, arcname='package')
        integrity = 'sha512-' + base64.b64encode(hashlib.sha512(self.tgz.read_bytes()).digest()).decode()
        (self.root / 'cache').mkdir(parents=True)
        (self.root / 'cache/B.tgz').write_bytes(self.tgz.read_bytes())
        with mock.patch.object(control, 'INTEGRITY', integrity):  # the pins a build of this stand-in gives
            reference = fake_build(None, self.root / 'cache', base / 'reference', IMAGE_ID)['packages']
        pins = {name: (entry['tree_sha256'], entry['release_digest']) for name, entry in reference.items()}
        self.host_cache = base / 'models_cache.json'
        self.host_cache.write_text(json.dumps(dict(client_version='0.164.0', models=[])))
        self.docker = FakeDocker()
        self.patches = [mock.patch.object(setup, 'SOURCES', sources),
                        mock.patch.object(setup, 'REMOTE', str(base / 'remote') + '/{}'),
                        mock.patch.object(setup, 'OVERRIDE', self.override),
                        mock.patch.object(control, 'INTEGRITY', integrity),
                        mock.patch.object(control, 'PINS', pins),
                        mock.patch.object(control, 'build', side_effect=fake_build),
                        mock.patch.object(setup.subprocess, 'run', side_effect=self.docker)]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        self.temp.cleanup()

    def run_setup(self, codex_auth=None):
        with mock.patch('builtins.print') as printed:
            setup.setup(self.root, self.archive, self.host_cache, codex_auth)
        return [call.args[0] for call in printed.call_args_list]

    def snapshot(self):
        return {str(p.relative_to(self.root)): (p.stat().st_mtime_ns, p.read_bytes())
                for p in sorted(self.root.rglob('*')) if p.is_file() and '.git' not in p.parts}


class IssueSnapshots(Fixture):
    def test_restore_gives_original_context_bytes(self):
        self.assertEqual(setup.restore(prompt(ISSUE)), ISSUE.encode('utf-8'))
        with self.assertRaises(ValueError):
            setup.restore('no caller contract here')

    def test_restored_files_match_override(self):
        (self.root / 'sources').mkdir()
        setup.issues(self.root, self.archive)
        self.assertEqual((self.root / 'sources/D3-issue.json').read_bytes(), ISSUE.encode('utf-8'))
        self.assertEqual((self.root / 'sources/D4-issue.json').read_bytes(), (ISSUE + 'D4').encode('utf-8'))

    def test_wrong_hash_refuses_and_writes_nothing(self):
        (self.root / 'sources').mkdir()
        record = json.loads(self.override.read_text())
        record['D3']['issue_snapshot_sha256'] = '0' * 64
        self.override.write_text(json.dumps(record))
        with self.assertRaisesRegex(setup.Refused, 'restored D3 snapshot sha256'):
            setup.issues(self.root, self.archive)
        self.assertFalse((self.root / 'sources/D3-issue.json').exists())

    def test_existing_snapshot_with_other_bytes_refuses(self):
        (self.root / 'sources').mkdir()
        (self.root / 'sources/D3-issue.json').write_bytes(ISSUE.encode('utf-8') + b' ')
        with self.assertRaisesRegex(setup.Refused, 'D3-issue.json: sha256 differs'):
            setup.issues(self.root, self.archive)


class RuntimeFiles(Fixture):
    SHARED = ('output', 'control', 'sources', 'scratch', 'image', 'image_tarball', 'models_cache', 'renewal_command',
              'tasks_override', 'caps', 'codex_auth', 'renewal_lock', 'check_lock')  # no `account`: nothing reads it

    def test_shared_and_per_lane_fields(self):
        self.run_setup()
        records = {lane: json.loads((self.root / f'runtime-{lane}.json').read_text())
                   for lane in ('smoke', 'claude', 'codex')}
        for lane, record in records.items():
            self.assertEqual(set(record), set(self.SHARED) | {'auth', 'lane'})
            self.assertEqual({key: record[key] for key in self.SHARED},
                             {key: records['smoke'][key] for key in self.SHARED})
            self.assertEqual(record['auth'], str(self.root.resolve() / f'auth-{lane}'))
            self.assertEqual(record['lane'], None if lane == 'smoke' else lane)
        smoke = records['smoke']
        self.assertIsNone(smoke['codex_auth'])  # no --codex-auth: cells use the host's default Codex login
        self.assertEqual(smoke['caps'], {'five_hour': 95, 'seven_day': 95})
        self.assertEqual(smoke['image'], IMAGE_ID)
        self.assertEqual(smoke['renewal_lock'], str(self.root.resolve() / 'renewal.lock'))
        self.assertEqual(smoke['check_lock'], str(self.root.resolve() / 'check.lock'))
        self.assertEqual(smoke['tasks_override'], str(self.override.resolve()))
        for key in ('output', 'control', 'sources', 'scratch', 'image_tarball', 'models_cache', 'tasks_override'):
            self.assertTrue(Path(smoke[key]).is_absolute(), key)
        for key in ('output', 'control', 'sources', 'scratch'):
            self.assertTrue(Path(smoke[key]).is_dir(), key)
        for key in ('image_tarball', 'models_cache'):
            self.assertTrue(Path(smoke[key]).is_file(), key)
        for lane in ('smoke', 'claude', 'codex'):
            auth = self.root / f'auth-{lane}'
            self.assertEqual(oct(auth.stat().st_mode & 0o777), '0o700')
            self.assertEqual(list(auth.iterdir()), [], 'setup never writes into an auth folder')
        self.assertEqual(oct((self.root / 'scratch').stat().st_mode & 0o777), '0o700')

    def login(self, name='auth.json'):
        login = self.root.parent / 'registered' / name
        login.parent.mkdir(exist_ok=True)
        login.write_text('{"made": "up"}')
        return login

    def codex_auth(self):
        return {lane: json.loads((self.root / f'runtime-{lane}.json').read_text())['codex_auth']
                for lane in ('smoke', 'claude', 'codex')}

    def test_codex_auth_option(self):
        """--codex-auth (O15): an absolute path to an existing regular file, by its metadata only, written into all
        three runtime files. The login file here is made up."""
        login = self.login()
        for bad in ('registered/auth.json', str(login.parent), str(login.parent / 'absent.json')):
            with self.subTest(bad=bad), self.assertRaisesRegex(setup.Refused, 'is not an absolute path to an existing '
                                                                               'regular file'):
                self.run_setup(bad)
            self.assertFalse(self.root.joinpath('output').exists())  # refused before any step
        self.run_setup(str(login))
        self.assertEqual(self.codex_auth(), dict.fromkeys(('smoke', 'claude', 'codex'), str(login)))
        self.assertIn('runtime: runtime-codex.json present', self.run_setup(str(login)))
        self.assertIn('runtime: runtime-codex.json present', self.run_setup())  # omitted: kept as it is
        with self.assertRaisesRegex(setup.Refused, 'runtime-smoke.json already names the Codex login'):
            self.run_setup(str(self.login('other.json')))
        self.assertEqual(self.codex_auth(), dict.fromkeys(('smoke', 'claude', 'codex'), str(login)))

    def test_codex_login_named_late_rewrites_that_field_alone(self):
        # README: the root, the seal and the controls are prepared without a login; naming it afterwards changes the
        # runtime files' codex_auth and nothing else, once, before any cell has started.
        self.run_setup()
        self.assertEqual(self.codex_auth(), dict.fromkeys(('smoke', 'claude', 'codex')))
        (self.root / 'instructions.seal.json').write_text('{"sealed": true}')  # stands for the seal and controls
        before = {name: data for name, (_, data) in self.snapshot().items()}
        calls = len(self.docker.mutations())
        login = self.login()
        lines = self.run_setup(str(login))
        after = {name: data for name, (_, data) in self.snapshot().items()}
        self.assertEqual(sorted(name for name in after if after[name] != before.get(name)),
                         ['runtime-claude.json', 'runtime-codex.json', 'runtime-smoke.json'])
        for lane in ('smoke', 'claude', 'codex'):
            self.assertEqual(json.loads(after[f'runtime-{lane}.json']),
                             dict(json.loads(before[f'runtime-{lane}.json']), codex_auth=str(login)))
            self.assertIn(f'runtime: runtime-{lane}.json: codex_auth named {login}', lines)
        self.assertEqual(len(self.docker.mutations()), calls)
        self.assertEqual([line for line in lines if not line.startswith('runtime:')],
                         [line for line in self.run_setup() if not line.startswith('runtime:')])

    def test_codex_login_is_not_named_after_a_cell_started(self):
        self.run_setup()
        (self.root / 'output/smoke-claude-B/run').mkdir(parents=True)
        (self.root / 'output/smoke-claude-B/run/started.json').write_text('{}')
        with self.assertRaisesRegex(setup.Refused, 'a cell has started \\(smoke-claude-B\\)'):
            self.run_setup(str(self.login()))
        self.assertEqual(self.codex_auth(), dict.fromkeys(('smoke', 'claude', 'codex')))

    def test_renewal_command_passes_the_0257_driver_check(self):
        driver = load('driver0257', HERE.parent / '0257/driver.py')
        help_text = '-p --tools --strict-mcp-config --mcp-config'
        self.assertEqual(driver.renewal_command(dict(renewal_command=setup.RENEWAL), help_text), setup.RENEWAL)


class Idempotence(Fixture):
    def test_second_run_performs_no_step(self):
        first = self.run_setup()
        self.assertIn('created', first[0])
        self.assertEqual(len(self.docker.mutations()), 2)  # build.sh, docker save
        before = self.snapshot()
        second = self.run_setup()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(self.docker.mutations()), 2)
        self.assertEqual(len(second), len(first))
        for line in second:
            self.assertIn('present', line)
            self.assertNotRegex(line, r'created|cloned|restored|downloaded|built|saved|loaded|copied|written')

    def test_missing_image_is_loaded_from_its_tarball_not_rebuilt(self):
        self.run_setup()
        self.docker.image = None
        calls = len(self.docker.calls)
        lines = self.run_setup()
        self.assertEqual([c[:2] for c in self.docker.calls[calls:] if c[0] == 'bash' or c[1] in ('save', 'load')],
                         [['docker', 'load']])
        self.assertIn('image: loaded from image.tar', '\n'.join(lines))


class PinMismatch(Fixture):
    def assert_refused(self, pattern):
        with self.assertRaisesRegex(setup.Refused, pattern):
            self.run_setup()

    def test_clone_tree_mismatch_refuses(self):
        name, commit, _ = setup.SOURCES['click']
        with mock.patch.dict(setup.SOURCES, click=(name, commit, '0' * 40)):
            self.assert_refused('click: expected HEAD .* with tree 0{40}')

    def test_clone_moved_off_base_refuses(self):
        self.run_setup()
        REAL_RUN(GIT + ['-C', str(self.root / 'sources/click'), 'commit', '-q', '--allow-empty', '-m', 'later'],
                 check=True)
        self.assert_refused('click: expected HEAD')

    def test_package_integrity_mismatch_refuses(self):
        (self.root / 'cache/B.tgz').write_bytes(self.tgz.read_bytes() + b'\0')
        self.assert_refused('B.tgz: npm integrity mismatch')

    def test_image_with_other_cli_versions_refuses(self):
        self.docker.versions = '2.1.281 (Claude Code)\ncodex-cli 0.156.1'
        self.assert_refused(r'reports \[.2\.1\.281')

    def test_tarball_of_another_image_refuses(self):
        self.run_setup()
        save_tar(self.root / 'image.tar', 'sha256:' + 'cd' * 32)
        self.assert_refused('image.tar holds sha256:cdcd')

    def test_control_tree_change_refuses(self):
        self.run_setup()
        (self.root / 'control/public/ruff').write_text('other')
        self.assert_refused('public differs from control.manifest.json')

    def test_host_models_cache_of_another_codex_refuses(self):
        self.host_cache.write_text(json.dumps(dict(client_version='0.167.1', models=[])))
        self.assert_refused('not a Codex 0.164.0 models cache')
        self.assertFalse((self.root / 'models_cache.json').exists())

    def test_existing_models_cache_of_another_codex_refuses(self):
        self.run_setup()
        (self.root / 'models_cache.json').write_text(json.dumps(dict(client_version='0.163.0')))
        self.assert_refused('client_version 0.163.0, expected 0.164.0')

    def test_runtime_file_changed_refuses(self):
        self.run_setup()
        path = self.root / 'runtime-codex.json'
        record = json.loads(path.read_text())
        record['caps'] = {'five_hour': 70, 'seven_day': 85}
        path.write_text(json.dumps(record))
        self.assert_refused('runtime-codex.json differs')

    def test_auth_folder_mode_refuses(self):
        self.run_setup()
        (self.root / 'auth-claude').chmod(0o755)
        self.assert_refused('auth-claude has mode 755, expected 700')


class Packages(Fixture):
    def test_every_package_is_checked_and_its_comparison_printed(self):
        lines = '\n'.join(self.run_setup())
        for name in control.PACKAGES:
            self.assertIn(f'package: {name} present: tree {control.PINS[name][0]}', lines)
        self.assertIn('differs from B in exactly 7 files', lines)
        self.assertIn('and 11 derived fields', lines)

    def test_a_package_off_its_pin_refuses(self):
        self.run_setup()
        with mock.patch.dict(control.PINS, K2=('0' * 64, control.PINS['K2'][1])):
            with self.assertRaisesRegex(setup.Refused, 'package K2: tree'):
                self.run_setup()

    def test_a_tampered_package_refuses(self):
        self.run_setup()
        (self.root / 'control/packages/K3/package/bin/devlyn.js').write_text('changed\n')
        with self.assertRaisesRegex(setup.Refused, 'packages differs from control.manifest.json'):
            self.run_setup()


class Comparison(unittest.TestCase):
    """control.compare, DESIGN "Arms": exactly the sentence once in the 7 principle files and the 11 derived fields."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.packages = Path(self.temp.name)
        synthetic_package(self.packages / 'B')
        self.b = self.packages / 'B/package'
        self.c = {k: self.packages / k / 'package' for k in control.CANDIDATES}
        for candidate in control.CANDIDATES:
            fake_candidate(self.packages, candidate, IMAGE_ID)

    def tearDown(self):
        self.temp.cleanup()

    def test_the_frozen_lists(self):
        for candidate, folder in self.c.items():
            result = control.compare(self.b, folder, candidate)
            self.assertEqual(result, dict(files=list(control.PRINCIPLE_FILES), fields=list(control.DERIVED)))
        self.assertEqual(len(control.PRINCIPLE_FILES), 7)
        self.assertEqual(len(control.DERIVED), 11)
        text = (self.c['K1'] / 'CLAUDE.md').read_text()
        self.assertEqual(control.sentence_counts(text), dict(K1=1, K2=0, K3=0))
        self.assertIn('2. **No overengineering** — smallest sufficient change. ' + control.CANDIDATES['K1'][1], text)
        self.assertEqual(control.sentence_counts((self.c['K3'] / 'harness/AGENTS.md').read_text()),
                         dict(K1=0, K2=0, K3=1))

    def refused(self, pattern, candidate='K3', folder=None):
        with self.assertRaisesRegex(ValueError, pattern):
            control.compare(self.b, folder or self.c[candidate], candidate)

    def test_another_byte_refuses(self):
        (self.c['K3'] / 'bin/devlyn.js').write_text('console.log("4.3.31") \n')
        self.refused(r"contents differ in \[.*'bin/devlyn.js'")

    def test_a_mode_refuses(self):
        os.chmod(self.c['K3'] / 'bin/devlyn.js', 0o755)
        self.refused('bin/devlyn.js: kind or mode')

    def test_a_name_refuses(self):
        (self.c['K3'] / 'bin/extra.js').write_text('')
        self.refused('bin/extra.js: only in C')
        (self.c['K3'] / 'bin/extra.js').unlink()
        (self.c['K3'] / 'bin/devlyn.js').rename(self.c['K3'] / 'bin/devlyn2.js')
        self.refused('bin/devlyn.js: only in B')

    def test_the_sentence_twice_or_another_candidate_refuses(self):
        derive(self.c['K3'], control.insert(control.insert(TEMPLATE, 'K3'), 'K3'))
        self.refused('not B with the K3 sentence inserted once')
        self.refused('not B with the K3 sentence inserted once', folder=self.c['K1'])
        self.refused('not B with the K1 sentence inserted once', candidate='K1', folder=self.c['K2'])

    def test_a_derived_field_not_re_derived_refuses(self):
        harness = self.c['K3'] / 'harness/CLAUDE.md'
        old = (self.b / 'harness/CLAUDE.md').read_text().split('\n', 1)[0]
        new_text = harness.read_text()
        harness.write_text(old + '\n' + new_text.split('\n', 1)[1])  # the stale marker of B
        self.refused('harness/CLAUDE.md: not B with the K3 sentence')

    def test_another_release_field_refuses(self):
        path = self.c['K3'] / 'release.json'
        manifest = json.loads(path.read_text())
        manifest['version'] = '4.3.32'
        manifest['digest']['value'] = control.sha256(control.canonical(
            {k: v for k, v in manifest.items() if k != 'digest'}).encode())
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
        self.refused(r"release.json fields differ in \[.*'version'")
        manifest['version'] = '4.3.31'
        path.write_text(json.dumps(manifest, indent=1) + '\n')
        self.refused('not in release.js serialization')

    def test_a_wrong_derived_value_refuses(self):
        path = self.c['K3'] / 'release.json'
        manifest = json.loads(path.read_text())
        manifest['principles']['sourceBlockSha256'] = '0' * 64
        manifest['digest']['value'] = control.sha256(control.canonical(
            {k: v for k, v in manifest.items() if k != 'digest'}).encode())
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
        self.refused('release.json principles.sourceBlockSha256 is 0{64}, re-derived')

    def test_insert_needs_one_line_of_its_own(self):
        with self.assertRaisesRegex(ValueError, 'principle 7 is not one line of its own'):
            control.insert(TEMPLATE.replace('7. **Production ready**', '8. **Production ready**'), 'K3')
        with self.assertRaisesRegex(ValueError, 'principle 2 is not one line of its own'):
            control.insert(TEMPLATE + TEMPLATE, 'K1')

    def test_the_cli_prints_the_lists_or_refuses(self):
        done = REAL_RUN([sys.executable, str(HERE / 'control.py'), 'compare', str(self.b), str(self.c['K2']), 'K2'],
                        capture_output=True, text=True)
        self.assertEqual((done.returncode, json.loads(done.stdout)['files']), (0, list(control.PRINCIPLE_FILES)))
        done = REAL_RUN([sys.executable, str(HERE / 'control.py'), 'compare', str(self.b), str(self.c['K2']), 'K3'],
                        capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        self.assertIn('REFUSED: C-K3 does not differ from B', done.stderr)

