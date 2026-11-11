"""Offline tests for the 0265 runtime root: fakes for Docker, the registry and the control build; local Git only."""
import base64
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time
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
              'tasks_override', 'caps', 'account', 'codex_auth', 'renewal_lock', 'check_lock')

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

    def test_codex_auth_option(self):
        """--codex-auth (O15): an absolute path to an existing regular file, by its metadata only, written into all
        three runtime files and pinned like the rest. The login file here is made up."""
        login = self.root.parent / 'registered/auth.json'
        login.parent.mkdir()
        login.write_text('{"made": "up"}')
        for bad in ('registered/auth.json', str(login.parent), str(login.parent / 'absent.json')):
            with self.subTest(bad=bad), self.assertRaisesRegex(setup.Refused, 'is not an absolute path to an existing '
                                                                               'regular file'):
                self.run_setup(bad)
            self.assertFalse(self.root.joinpath('output').exists())  # refused before any step
        self.run_setup(str(login))
        self.assertEqual({lane: json.loads((self.root / f'runtime-{lane}.json').read_text())['codex_auth']
                          for lane in ('smoke', 'claude', 'codex')}, dict.fromkeys(('smoke', 'claude', 'codex'),
                                                                                   str(login)))
        self.assertIn('runtime: runtime-codex.json present', self.run_setup(str(login)))
        other = login.with_name('other.json')
        other.write_text('{"made": "up"}')
        for value in (str(other), None):  # another login, or none, than the files hold
            with self.subTest(value=value), self.assertRaisesRegex(setup.Refused, 'runtime-smoke.json differs'):
                self.run_setup(value)
        self.assertEqual(json.loads((self.root / 'runtime-codex.json').read_text())['codex_auth'], str(login))

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


rehearse = load('rehearse_memory')
GIB, MIB = 2 ** 30, 2 ** 20
OWNER_1, OWNER_2, ASSESSOR = 'devlyn-0231-' + 'a' * 32, 'devlyn-0231-' + 'b' * 32, 'devlyn-0231-assess-' + 'c' * 32


class FakeSamplerDocker:
    """`docker` for the sampler: per `docker stats` call, the containers it lists (None: the call fails) and the VM's
    MemAvailable in bytes; the until-file appears during the call `stop_at` (1-based), or `interrupt_at` raises."""

    def __init__(self, until, ticks, stop_at=None, interrupt_at=None):
        self.until, self.ticks, self.stop_at, self.interrupt_at = until, ticks, stop_at, interrupt_at
        self.calls, self.sampler, self.stats_calls = [], None, 0

    def __call__(self, argv, **kwargs):
        argv = list(argv)
        self.calls.append(argv)
        done = lambda out='': subprocess.CompletedProcess(argv, 0, out, '')  # noqa: E731
        if argv[:2] == ['docker', 'info']:
            return done('8319369216\n')
        if argv[:3] == ['docker', 'run', '-d']:
            self.sampler = argv[argv.index('--name') + 1]
            return done('cid\n')
        if argv[:2] == ['docker', 'stats']:
            self.stats_calls += 1
            if self.stats_calls == self.interrupt_at:
                raise KeyboardInterrupt
            if self.stats_calls == self.stop_at:
                self.until.touch()
            listed = self.ticks[self.stats_calls - 1][0]
            if listed is None:
                raise subprocess.CalledProcessError(1, argv, '', 'Cannot connect to the Docker daemon')
            return done('\n'.join(json.dumps(dict(Name=name, MemUsage=f'{used / MIB:.1f}MiB / 7.748GiB'))
                                  for name, used in (listed | {self.sampler: MIB}).items()) + '\n')
        if argv[:2] == ['docker', 'exec']:
            available = self.ticks[self.stats_calls - 1][1]
            return done(f'MemTotal:        8124384 kB\nMemAvailable:   {available // 1024} kB\n')
        if argv[:3] == ['docker', 'rm', '-f']:
            return done()
        raise AssertionError(f'unexpected command {argv}')


class RehearsalParsing(unittest.TestCase):
    def test_memory_sizes_and_step_markers(self):
        self.assertEqual(rehearse.size('1.5GiB / 4GiB'), 3 * 2 ** 29)
        self.assertEqual(rehearse.size('837.2MiB / 7.748GiB'), round(837.2 * 2 ** 20))
        self.assertEqual(rehearse.size('0B / 0B'), 0)
        self.assertEqual(rehearse.size('12.5MB / 4GB'), 12_500_000)
        log = 'noise\nQ6-STEP 0 0 100 104\nmore\nQ6-STEP 1 1 104 110\n'
        self.assertEqual(rehearse.steps(['a', 'b', 'c'], log), [
            dict(command='a', exit_code=0, seconds=4), dict(command='b', exit_code=1, seconds=6),
            dict(command='c', exit_code=None, seconds=None)])
        self.assertIn("sh -c 'a b'; code=$?; echo \"Q6-STEP 0 $code", rehearse.script(['a b']))
        self.assertEqual([rehearse.prefix(n) for n in (OWNER_1, ASSESSOR, 'a9-mysql', 'devlyn-0231-abc')],
                         ['devlyn-0231', 'devlyn-0231-assess', 'a9-mysql', 'devlyn-0231-abc'])


class MemorySampler(unittest.TestCase):
    """DESIGN Q8 (b): rehearse_memory.py sample, with a fake docker."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'runtime-smoke.json').write_text(json.dumps(dict(image=IMAGE_ID)))
        self.out, self.until = self.root / 'q8-sample.json', self.root / 'rehearsal.done'

    def tearDown(self):
        self.temp.cleanup()

    def watch(self, fake):
        with mock.patch.object(rehearse.subprocess, 'run', side_effect=fake), \
                mock.patch.object(rehearse.time, 'sleep') as sleep:
            result = rehearse.watch(self.root, self.out, self.until, interval=2)
        self.assertEqual(sleep.call_count, len(result['samples']))
        return result

    def test_samples_until_the_file_appears_then_summarises(self):
        ticks = [({OWNER_1: GIB, ASSESSOR: 300 * MIB, 'a9-mysql': 500 * MIB}, 3 * GIB),
                 ({OWNER_1: 1200 * MIB, OWNER_2: 800 * MIB, 'a9-mysql': 500 * MIB}, 2 * GIB),
                 (None, 5 * GIB // 2)]  # a failed `docker stats` is a recorded gap, not the end
        fake = FakeSamplerDocker(self.until, ticks, stop_at=3)
        result = self.watch(fake)
        self.assertEqual(json.loads(self.out.read_text()), result)
        self.assertEqual((result['sample_count'], result['samples_without_stats'], result['samples_without_available']),
                         (3, 1, 0))
        self.assertEqual(result['stopped'], 'until-file')
        self.assertEqual(result['min_vm_available'], 2 * GIB)
        self.assertEqual(result['running_at_min'], ticks[1][0] | {fake.sampler: MIB})
        self.assertEqual(result['peak_by_prefix'], {
            'a9-mysql': dict(peak=500 * MIB, largest=500 * MIB),
            'devlyn-0231': dict(peak=2000 * MIB, largest=1200 * MIB),  # both lanes' owners in one sample
            'devlyn-0231-assess': dict(peak=300 * MIB, largest=300 * MIB),
            'devlyn-0265-q8-sampler': dict(peak=MIB, largest=MIB)})
        self.assertIn('Cannot connect', ''.join(s.get('stats_error', '') for s in result['samples']))
        # The sampler is ours, small, offline and removed; memory is read only inside it, never another container.
        run = next(c for c in fake.calls if c[:3] == ['docker', 'run', '-d'])
        for flag, value in (('--network', 'none'), ('--memory', '64m'), ('--label', 'devlyn.task=0265-q8')):
            self.assertEqual(run[run.index(flag) + 1], value)
        self.assertEqual(run[-3:], [IMAGE_ID, 'sleep', 'infinity'])
        self.assertEqual({c[2] for c in fake.calls if c[:2] == ['docker', 'exec']}, {fake.sampler})
        self.assertEqual(fake.calls[-1], ['docker', 'rm', '-f', fake.sampler])
        self.assertFalse([c for c in fake.calls if c[:2] in (['docker', 'kill'], ['docker', 'stop'])
                          or (c[:2] == ['docker', 'rm'] and fake.sampler not in c)])

    def test_an_interrupted_run_keeps_its_samples_and_removes_the_sampler(self):
        fake = FakeSamplerDocker(self.until, [({OWNER_1: GIB}, 3 * GIB)] * 3, interrupt_at=2)
        with mock.patch.object(rehearse.subprocess, 'run', side_effect=fake), \
                mock.patch.object(rehearse.time, 'sleep'), self.assertRaises(KeyboardInterrupt):
            rehearse.watch(self.root, self.out, self.until)
        record = json.loads(self.out.read_text())
        self.assertEqual((record['sample_count'], record['stopped']), (1, 'KeyboardInterrupt: '))
        self.assertEqual(fake.calls[-1], ['docker', 'rm', '-f', fake.sampler])

    def test_refuses_to_overwrite_or_to_start_already_stopped(self):
        fake = FakeSamplerDocker(self.until, [({}, GIB)], stop_at=1)
        self.watch(fake)  # allowed: a new file, written once
        calls = len(fake.calls)
        with mock.patch.object(rehearse.subprocess, 'run', side_effect=fake), self.assertRaises(FileExistsError):
            rehearse.watch(self.root, self.out, self.root / 'other.done')
        self.out.unlink()
        with mock.patch.object(rehearse.subprocess, 'run', side_effect=fake), self.assertRaises(FileExistsError):
            rehearse.watch(self.root, self.out, self.until)  # the until-file is already there
        self.assertEqual(len(fake.calls), calls)  # neither refusal touched docker
        self.assertFalse(self.out.exists())


class Rehearsal(unittest.TestCase):
    """DESIGN Q8 (b): rehearsal.tsv, the SMOKE task once more per lane, outside every sum."""

    def test_rehearsal_rows(self):
        generate = load('generate_cells')
        rows = generate.rehearsal()
        self.assertEqual(rows, [(f'rehearsal-{config}-{arm}', 'SMOKE', arm, config)
                                for config in ('claude', 'codex') for arm in 'AB'])
        self.assertEqual((HERE / 'rehearsal.tsv').read_text(), generate.render(rows))
        others = {row[0] for name in ('cells.tsv', 'smoke.tsv') for row in generate.generate()[name]}
        self.assertFalse(others & {row[0] for row in rows})
        self.assertFalse([row for row in rows if row[0].startswith('smoke-')])  # the driver's SMOKE start glob
        for config in ('claude', 'codex'):  # each lane driver runs its own two rows (row[3] is the config)
            self.assertEqual([row[2] for row in rows if row[3] == config], ['A', 'B'])
        cells = (HERE / 'cells.tsv').read_text()
        self.assertNotIn('rehearsal', cells)  # decide.py and the grading scripts read cells.tsv only


strict = load('strict_config_check')
SECRET = 'fake-refresh-token-0265'


class StrictConfigExec(unittest.TestCase):
    """DESIGN Q3 (O1): strict_config_check.py --run-exec with a fake runner and a fake credential snapshot."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = self.root = Path(self.temp.name)
        for folder in ('output', 'scratch/strict-config-exec-old1/allowed/.codex', 'scratch/strict-config-exec-old2',
                       'auth-smoke'):
            (root / folder).mkdir(parents=True)
        (root / 'models.json').write_text('{}')
        self.runtime = root / 'runtime-smoke.json'
        self.runtime.write_text(json.dumps(dict(image=IMAGE_ID, output=str(root / 'output'),
                                                scratch=str(root / 'scratch'), auth=str(root / 'auth-smoke'),
                                                models_cache=str(root / 'models.json'))))
        self.snapshots, self.calls = 0, []

    def tearDown(self):
        self.temp.cleanup()

    def snapshot(self, runtime):
        self.snapshots += 1
        (Path(runtime['auth']) / 'codex.json').write_text(json.dumps(dict(tokens=dict(refresh_token=SECRET))))
        return dict(account=['a', 'o'], token_seconds_left=7200), None

    def runner(self, answers):
        """answers: label -> (code, stdout, stderr, files written under the home)."""
        def run(argv):
            self.calls.append(argv)
            if argv[:2] == ['docker', 'rm']:
                return 0, '', ''
            label = next(label for label in strict.LABELS if f'devlyn-0265-strict-{label}-' in ' '.join(argv))
            home = Path(next(v for v in argv if v.endswith(',dst=/home/probe')).split('src=')[1].split(',dst=')[0])
            code, stdout, stderr, files = answers[label]
            for file in files:
                (home / file).parent.mkdir(parents=True, exist_ok=True)
                (home / file).write_text('x')
            return code, stdout, stderr
        return run

    def run_exec(self, allowed=None, violating=None, snapshot=None):
        answers = dict(allowed=allowed or (0, '{"type":"thread.started","thread_id":"t"}\n{"type":"turn.completed"}\n',
                                           'session log', ['trace/t/1.jsonl', '.codex/sessions/2026/r.jsonl']),
                       violating=violating or (1, '', 'Error: unknown field `zz_unknown_top_0265`', []))
        with mock.patch('sys.stdout', new=io.StringIO()) as printed:
            code = strict.run_exec(self.runtime, self.runner(answers), snapshot or self.snapshot)
        target = self.root / 'q3-strict-config.json'
        return code, json.loads(target.read_text()) if target.exists() else None, printed.getvalue()

    def test_pass_records_no_credential_and_removes_every_config_home(self):
        code, record, printed = self.run_exec()
        self.assertEqual((code, record['status']), (0, 'PASS'))
        self.assertTrue(printed.startswith('PASS'))
        self.assertEqual(record['runs']['allowed'], dict(exit_code=0, events=['thread.started', 'turn.completed'],
                                                          trace_and_session_files=['.codex/sessions/2026/r.jsonl',
                                                                                   'trace/t/1.jsonl'], named_keys=[]))
        self.assertEqual(record['runs']['violating'], dict(exit_code=1, events=[], trace_and_session_files=[],
                                                            named_keys=['zz_unknown_top_0265'],
                                                            error_text='Error: unknown field `zz_unknown_top_0265`'))
        self.assertNotIn(SECRET, (self.root / 'q3-strict-config.json').read_text())
        self.assertEqual(list((self.root / 'scratch').iterdir()), [])  # its own homes and the two earlier ones
        self.assertEqual(self.snapshots, 1)
        self.assertEqual(len(self.calls), 2)
        for argv, text in zip(self.calls, strict.configs()):
            self.assertEqual(argv[-6:], ['codex', 'exec', '--strict-config', '--json', '--skip-git-repo-check',
                                         'Reply OK.'])
            self.assertEqual(argv[argv.index('--network') + 1], 'bridge')
            self.assertIn(f'type=bind,src={self.root / "auth-smoke/codex.json"},dst=/home/probe/.codex/auth.json,'
                          'readonly', argv)
            self.assertIn('CODEX_ROLLOUT_TRACE_ROOT=/home/probe/trace', argv)

    def test_violating_run_must_fail_at_config_load_without_a_model_request(self):
        for violating, why in (
                ((0, '{"type":"turn.completed"}\n', '', []), 'did not fail at config load'),
                ((1, '{"type":"thread.started","thread_id":"t"}\n', 'zz_unknown_top_0265 later', []),
                 'past config load'),
                ((1, '', 'Error: unknown field `zz_unknown_top_0265`', ['trace/t/1.jsonl']), 'past config load'),
                ((1, '', 'error sending request: network unreachable', []), 'for another reason'),
                ((None, '', 'timed out after 180 s', []), 'did not fail at config load')):
            with self.subTest(why=why, violating=violating[:2]):
                (self.root / 'q3-strict-config.json').unlink(missing_ok=True)
                code, record, _ = self.run_exec(violating=violating)
                self.assertEqual((code, record['status']), (1, 'FAIL'))
                self.assertIn(why, record['why'])
        self.assertEqual(self.calls[-1][:3], ['docker', 'rm', '-f'])  # the timed-out run is removed

    def test_an_error_event_alone_is_not_a_session(self):
        code, record, _ = self.run_exec(violating=(1, '{"type":"error","message":"unknown field `zz_unknown_top_0265`"}'
                                                      '\n', '', []))
        self.assertEqual((code, record['status'], record['runs']['violating']['events']), (0, 'PASS', ['error']))

    def test_allowed_run_must_exit_0(self):
        code, record, _ = self.run_exec(allowed=(1, '', 'Error: unknown field `rollout_budget`', []))
        self.assertEqual((code, record['status']), (1, 'FAIL'))
        self.assertIn('did not exit 0', record['why'])
        self.assertEqual(record['runs']['allowed']['error_text'], 'Error: unknown field `rollout_budget`')

    def test_nothing_runs_without_a_fresh_snapshot_or_over_a_record(self):
        held = lambda runtime: (None, 'Claude login token expires in 1200s; refresh the host login first')  # noqa: E731

        def broken(runtime):
            raise subprocess.CalledProcessError(44, ['security', 'find-generic-password'])
        for snapshot in (held, broken):
            code, record, printed = self.run_exec(snapshot=snapshot)
            self.assertEqual((code, record, self.calls), (3, None, []))
            self.assertTrue(printed.startswith('UNDECIDED: not run'))
        self.assertEqual(len(list((self.root / 'scratch').iterdir())), 2)  # nothing made, nothing removed yet
        self.run_exec()
        self.calls.clear()
        with mock.patch('sys.stderr', new=io.StringIO()):
            code, _, _ = self.run_exec()
        self.assertEqual((code, self.snapshots, self.calls), (3, 1, []))  # Q3 is recorded once

    def test_an_old_codex_login_holds_the_exec_runs(self):
        """O15, through the real run_cell.snapshot_auth: a Codex login renewed 7.5 days ago leaves Q3 undecided with
        the reason, no copy and no run (violating); a 2-day-old one is copied and both runs go (allowed). The logins
        are made-up files."""
        real = strict.run_cell()
        raw = json.dumps({'claudeAiOauth': {'expiresAt': (time.time() + 5400) * 1000, 'accessToken': 'fake'}})
        profile = json.dumps({'account': {'uuid': 'a'}, 'organization': {'uuid': 'o'}})
        record = json.loads(self.runtime.read_text())
        for days, held in ((7.5, True), (2, False)):
            with self.subTest(days=days):
                login = self.root / f'login-{days}.json'
                refreshed = datetime.datetime.fromtimestamp(time.time() - days * 86400, datetime.timezone.utc)
                login.write_text(json.dumps(dict(tokens=dict(account_id='fake-account-id', refresh_token=SECRET),
                                                 last_refresh=refreshed.isoformat().replace('+00:00', 'Z'))))
                self.runtime.write_text(json.dumps(dict(record, codex_auth=str(login))))
                with mock.patch.object(real.subprocess, 'run',
                                       return_value=subprocess.CompletedProcess([], 0, stdout=raw)), \
                        mock.patch.object(real.urllib.request, 'urlopen', side_effect=lambda *_a, **_k: io.StringIO(profile)):
                    code, result, printed = self.run_exec(snapshot=real.snapshot_auth)
                copied = self.root / 'auth-smoke/codex.json'
                if held:
                    self.assertEqual((code, result, self.calls), (3, None, []))
                    self.assertEqual(printed, 'UNDECIDED: not run: Codex login (codex_auth) last renewed 7.5 days ago; '
                                              'limit 7 days\n')
                    self.assertFalse(copied.exists())
                else:
                    self.assertEqual((code, result['status'], len(self.calls)), (0, 'PASS', 2))
                    self.assertEqual(copied.read_bytes(), login.read_bytes())
                    self.assertNotIn(SECRET, (self.root / 'q3-strict-config.json').read_text())


if __name__ == '__main__':
    unittest.main()
