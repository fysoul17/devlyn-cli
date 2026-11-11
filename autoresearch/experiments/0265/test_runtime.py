"""Offline tests for the 0265 runtime root: fakes for Docker, the registry and the control build; local Git only."""
import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent


def load(name, path=None):
    spec = importlib.util.spec_from_file_location('test_0265_runtime_' + name, path or HERE / (name + '.py'))
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


def fake_build(sources, cache, out):
    """control.build's shape: three trees, the package from cache/B.tgz, the manifest beside the tree."""
    out.mkdir(parents=False, exist_ok=False)
    (out / 'public/python').mkdir(parents=True)
    (out / 'public/ruff').write_text('ruff')
    (out / 'oracle/experiments').mkdir(parents=True)
    (out / 'oracle/experiments/oracle.js').write_text('oracle')
    tgz = cache / 'B.tgz'
    with tarfile.open(tgz) as archive:
        archive.extractall(out / 'packages/B', filter='data')
    record = dict(packages=dict(B=dict(url=control.PACKAGE_URL, integrity=control.INTEGRITY,
                                       sha256=control.digest(tgz), files=control.members(tgz))),
                  manifests={name: control.manifest(out / name) for name in ('public', 'oracle', 'packages')})
    (out.parent / (out.name + '.manifest.json')).write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')


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
        package = base / 'pkg'
        (package / 'package/bin').mkdir(parents=True)
        (package / 'package/bin/devlyn.js').write_text('console.log("4.3.30")\n')
        self.tgz = base / 'B.tgz'
        with tarfile.open(self.tgz, 'w:gz') as archive:
            archive.add(package / 'package', arcname='package')
        integrity = 'sha512-' + base64.b64encode(hashlib.sha512(self.tgz.read_bytes()).digest()).decode()
        (self.root / 'cache').mkdir(parents=True)
        (self.root / 'cache/B.tgz').write_bytes(self.tgz.read_bytes())
        self.host_cache = base / 'models_cache.json'
        self.host_cache.write_text(json.dumps(dict(client_version='0.164.0', models=[])))
        self.docker = FakeDocker()
        self.patches = [mock.patch.object(setup, 'SOURCES', sources),
                        mock.patch.object(setup, 'REMOTE', str(base / 'remote') + '/{}'),
                        mock.patch.object(setup, 'OVERRIDE', self.override),
                        mock.patch.object(control, 'INTEGRITY', integrity),
                        mock.patch.object(control, 'build', side_effect=fake_build),
                        mock.patch.object(setup.subprocess, 'run', side_effect=self.docker)]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        self.temp.cleanup()

    def run_setup(self):
        with mock.patch('builtins.print') as printed:
            setup.setup(self.root, self.archive, self.host_cache)
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
              'tasks_override', 'caps', 'account', 'renewal_lock', 'check_lock')

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


class RehearsalParsing(unittest.TestCase):
    def test_memory_sizes_and_step_markers(self):
        rehearse = load('rehearse_memory')
        self.assertEqual(rehearse.size('1.5GiB / 4GiB'), 3 * 2 ** 29)
        self.assertEqual(rehearse.size('837.2MiB / 7.748GiB'), round(837.2 * 2 ** 20))
        self.assertEqual(rehearse.size('0B / 0B'), 0)
        self.assertEqual(rehearse.size('12.5MB / 4GB'), 12_500_000)
        log = 'noise\nQ6-STEP 0 0 100 104\nmore\nQ6-STEP 1 1 104 110\n'
        self.assertEqual(rehearse.steps(['a', 'b', 'c'], log), [
            dict(command='a', exit_code=0, seconds=4), dict(command='b', exit_code=1, seconds=6),
            dict(command='c', exit_code=None, seconds=None)])
        self.assertIn("sh -c 'a b'; code=$?; echo \"Q6-STEP 0 $code", rehearse.script(['a b']))


if __name__ == '__main__':
    unittest.main()
