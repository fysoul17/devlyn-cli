"""Temporary local staging and real inherited validation, with Docker inspect mocked."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('stage_rpd1_test', HERE / 'stage.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


class StageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='rp-d1-stage-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.home = self.root / 'host'
        (self.home / '.codex').mkdir(parents=True)
        self.cache = self.home / '.codex/models_cache.json'
        self.cache.write_text('{"models": []}\n')
        self.tarball = self.root / 'release.tgz'
        with tarfile.open(self.tarball, 'w:gz') as archive:
            for name, raw in {'package/package.json': b'{"name":"devlyn-cli","version":"4.2.18"}',
                              'package/bin/devlyn.js': b'// offline installer fixture\n'}.items():
                member = tarfile.TarInfo(name)
                member.size = len(raw)
                archive.addfile(member, io.BytesIO(raw))
        self.auth = self.root / 'auth'
        self.auth.mkdir(mode=0o700)
        files = {'claude.env': b'CLAUDE_CODE_OAUTH_TOKEN=offline\nCLAUDE_CODE_OAUTH_SCOPES=user:profile\n',
                 'codex.json': b'{}'}
        self.account = ['a' * 12, 'b' * 12]
        manifest = dict(schema_version=1, account=self.account, expires_at_ms=(time.time() + 10000) * 1000,
                        files={name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()})
        for name, raw in (files | {'manifest.json': s.auth.encoded(manifest)}).items():
            s.auth.write_private(self.auth, name, raw)
        self.github_auth = self.root / 'github-private'
        self.github_auth.mkdir(mode=0o700)
        # Deliberately not a PAT: stage/check may inspect shape, never parse this value.
        for name in ('hosts.yml', 'config.yml'):
            s.auth.write_private(self.github_auth, name, b'not a credential\n')
        self.args = SimpleNamespace(stage_dir=self.root / 'stage', run_id='offline', release_tarball=self.tarball,
            image='sha256:' + 'a' * 64, auth=self.auth, github_auth=self.github_auth, phase='smoke', smoke_output=None)

    def stage(self):
        with patch.object(Path, 'home', return_value=self.home), \
                patch.object(s.runner.github, 'command', side_effect=AssertionError('GitHub access forbidden')), \
                patch.object(s.runner.cell, 'credential', side_effect=AssertionError('PAT read forbidden')), \
                patch.object(subprocess, 'run', side_effect=AssertionError('staging subprocess forbidden')):
            return s.stage(self.args)

    def check(self, runtime):
        def inspect(argv, **kwargs):
            self.assertEqual(argv, ['docker', 'image', 'inspect', self.args.image, '--format', '{{.Id}}'])
            return self.args.image + '\n'
        with patch.object(subprocess, 'check_output', side_effect=inspect) as docker, \
                patch.object(s.runner.github, 'command', side_effect=AssertionError('GitHub access forbidden')), \
                patch.object(s.runner.cell, 'credential', side_effect=AssertionError('PAT read forbidden')), \
                patch.object(s.runner.Runner, 'run', side_effect=AssertionError('model dispatch forbidden')), \
                patch.object(s.auth, 'profile', side_effect=AssertionError('profile access forbidden')):
            s.check(runtime)
        docker.assert_called_once()

    def smoke_receipts(self):
        output = self.args.stage_dir / 'smoke-output'
        catalogs = dict(skills=['devlyn-ideate', 'devlyn-engines'], plugins=[], mcp_servers=[])
        s.write(output / 'verdict-smoke-claude.json', dict(boot_catalogs=catalogs))
        for name, _, _ in s.runner.SMOKE:
            (output / name).mkdir()
            s.write(output / name / 'rp-verdict.json', dict(status='ADJUDICATE', repository_cleanup=dict(
                repository=f'fysoul17/rpd1-offline-{name}', status='DELETED', http_status=404,
                archive_manifest_sha256='a' * 64)))
        return catalogs

    def test_smoke_stages_all_required_mounts_and_passes_real_validation(self):
        runtime_path = self.stage()
        runtime = s.read(runtime_path)
        self.check(runtime_path)
        self.assertEqual(runtime['account'], self.account)
        self.assertEqual(runtime['auth_manifest_sha256'], s.digest(self.auth / 'manifest.json'))
        self.assertEqual(runtime['models_cache_sha256'], s.digest(self.cache))
        self.assertEqual(Path(runtime['models_cache']).read_bytes(), self.cache.read_bytes())
        self.assertEqual(runtime['release']['sha256'], s.digest(self.tarball))
        self.assertEqual(runtime['tasks_file'], str(HERE / 'smoke-tasks.json'))
        for key in ('output', 'smoke_output', 'scratch', 'sources', 'control'):
            self.assertTrue(Path(runtime[key]).is_relative_to(self.args.stage_dir))
            self.assertTrue(Path(runtime[key]).is_dir())
        control = Path(runtime['control'])
        self.assertTrue((control / 'public/python').is_dir())
        self.assertTrue((control / 'public/autoresearch').is_dir())
        hidden = control / 'oracle/experiments/rp-d1-delivery-cost'
        self.assertEqual(s.digest(hidden / 'oracle.py'), s.digest(HERE / 'oracle.py'))
        for task in ('SM', 'BV', 'Z0'):
            self.assertEqual((hidden / 'fixtures' / task / '.user-state/draft.txt').read_bytes(),
                             (HERE / 'fixtures' / task / '.user-state/draft.txt').read_bytes())
        self.assertFalse(any(path.name in ('hosts.yml', 'config.yml', 'claude.env', 'codex.json')
                             for path in self.args.stage_dir.rglob('*')))

    def test_measured_copies_recorded_catalogs_and_keeps_smoke_inputs_frozen(self):
        smoke = self.stage()
        catalogs = self.smoke_receipts()
        frozen = {path: path.read_bytes() for path in self.args.stage_dir.rglob('*') if path.is_file()}
        self.cache.write_text('host cache changed after smoke')
        self.args.phase = 'measured'
        self.args.smoke_output = self.args.stage_dir / 'smoke-output'
        measured = self.stage()
        runtime = s.read(measured)
        self.assertEqual(runtime['boot_catalogs'], {'claude': {'B': catalogs}})
        self.assertEqual(runtime['tasks_file'], str(HERE / 'tasks.json'))
        self.check(measured)
        self.assertNotEqual(smoke, measured)
        for path, raw in frozen.items():
            self.assertEqual(path.read_bytes(), raw, str(path))

    def test_measured_refuses_absent_or_malformed_recorded_catalogs(self):
        self.stage()
        self.args.phase = 'measured'
        record = self.args.stage_dir / 'smoke-output/verdict-smoke-claude.json'
        for value in (None, {}, {'boot_catalogs': {}}, {'boot_catalogs': {'skills': []}}):
            if value is not None:
                s.write(record, value)
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, 'recorded boot catalogs'):
                self.stage()
        self.assertFalse((self.args.stage_dir / 'runtime-measured.json').exists())

    def test_measured_check_requires_smoke_deletion_receipts_and_matching_catalogs(self):
        self.stage()
        self.smoke_receipts()
        self.args.phase = 'measured'
        measured = self.stage()
        runtime = s.read(measured)
        runtime['boot_catalogs']['claude']['B']['skills'] = []
        s.write(measured, runtime)
        with self.assertRaisesRegex(RuntimeError, 'differ from smoke'):
            self.check(measured)
        runtime['boot_catalogs']['claude']['B'] = s.smoke_catalogs(Path(runtime['smoke_output']))
        s.write(measured, runtime)
        receipt = Path(runtime['smoke_output']) / 'smoke-codex/rp-verdict.json'
        receipt.unlink()
        with self.assertRaises(FileNotFoundError):
            self.check(measured)

    def test_check_refuses_missing_image(self):
        runtime = self.stage()
        with patch.object(subprocess, 'check_output', side_effect=subprocess.CalledProcessError(1, ['docker'])):
            with self.assertRaises(subprocess.CalledProcessError):
                s.check(runtime)

    def test_check_refuses_wrong_image_identity(self):
        runtime = self.stage()
        with patch.object(subprocess, 'check_output', return_value='sha256:' + 'b' * 64):
            with self.assertRaisesRegex(ValueError, 'image identity mismatch'):
                s.check(runtime)

    def test_check_refuses_missing_nested_oracle_mountpoint(self):
        runtime = self.stage()
        (self.args.stage_dir / 'control/public/autoresearch').rmdir()
        with self.assertRaisesRegex(RuntimeError, 'public check mount missing'):
            self.check(runtime)

    def test_check_rejects_changed_cache_release_and_controls(self):
        runtime = self.stage()
        paths = [('models_cache.json', 'models cache changed'), ('release.tgz', 'SHA-256 mismatch'),
                 ('control/packages/B/package/bin/devlyn.js', 'extracted release'),
                 ('control/oracle/experiments/rp-d1-delivery-cost/oracle.py', 'hidden oracle changed')]
        for name, reason in paths:
            path = self.args.stage_dir / name
            original = path.read_bytes()
            path.write_bytes(original + b'changed')
            with self.subTest(name=name), self.assertRaisesRegex(RuntimeError, reason):
                self.check(runtime)
            path.write_bytes(original)

    def test_check_refuses_changed_auth_binding_and_credential_shape(self):
        runtime = self.stage()
        original = s.read(runtime)
        s.write(runtime, dict(original, auth_manifest_sha256='b' * 64))
        with self.assertRaisesRegex(RuntimeError, 'binding mismatch'):
            self.check(runtime)
        s.write(runtime, original)
        (self.github_auth / 'hosts.yml').chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'private regular'):
            self.check(runtime)

    def test_stage_refuses_overlapping_smoke_output_before_writing(self):
        for name in ('control/public', 'Control/public', 'control', 'output', 'output/nested', 'scratch', 'scratch/nested'):
            with self.subTest(name=name):
                self.args.stage_dir = self.root / name.replace('/', '-')
                self.args.smoke_output = self.args.stage_dir / name
                with self.assertRaisesRegex(RuntimeError, 'disjoint'):
                    self.stage()
                self.assertFalse(self.args.stage_dir.exists())

    def test_stage_refuses_paths_resolving_inside_or_around_control(self):
        for name in ('output', 'scratch', 'smoke-output'):
            for target in ('control', 'control/public', '.'):
                with self.subTest(name=name, target=target):
                    self.args.stage_dir = self.root / (name + '-' + target.replace('/', '-'))
                    self.args.stage_dir.mkdir()
                    (self.args.stage_dir / name).symlink_to(target, target_is_directory=True)
                    with self.assertRaisesRegex(RuntimeError, 'disjoint|under the stage directory'):
                        self.stage()
                    self.assertEqual(list(self.args.stage_dir.iterdir()), [self.args.stage_dir / name])

    def test_cli_refuses_smoke_output_in_control_before_writing(self):
        with redirect_stdout(io.StringIO()) as output:
            code = s.main([str(self.args.stage_dir), '--run-id', self.args.run_id,
                '--release-tarball', str(self.tarball), '--image', self.args.image, '--auth', str(self.auth),
                '--github-auth', str(self.github_auth), '--phase', 'smoke',
                '--smoke-output', str(self.args.stage_dir / 'control/public')])
        self.assertEqual(code, 2)
        self.assertIn('STOP', output.getvalue())
        self.assertFalse(self.args.stage_dir.exists())

    def test_stage_refuses_missing_host_cache_and_preserves_failed_stage(self):
        self.cache.unlink()
        with self.assertRaises(FileNotFoundError):
            self.stage()
        self.assertFalse((self.args.stage_dir / 'runtime-smoke.json').exists())
        self.assertTrue(self.args.stage_dir.exists())

    def test_stage_refuses_overwrite_and_unpinned_image(self):
        self.args.image = 'latest'
        with self.assertRaisesRegex(RuntimeError, 'exact sha256'):
            self.stage()
        self.assertFalse(self.args.stage_dir.exists())
        self.args.image = 'sha256:' + 'a' * 64
        self.stage()
        with self.assertRaisesRegex(RuntimeError, 'already staged'):
            self.stage()

    def test_cli_stage_and_check_print_fixed_summary(self):
        with patch.object(Path, 'home', return_value=self.home), redirect_stdout(io.StringIO()) as output:
            code = s.main([str(self.args.stage_dir), '--run-id', self.args.run_id,
                '--release-tarball', str(self.tarball), '--image', self.args.image, '--auth', str(self.auth),
                '--github-auth', str(self.github_auth), '--phase', 'smoke'])
        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue().strip(), str(self.args.stage_dir / 'runtime-smoke.json'))
        with patch.object(subprocess, 'check_output', return_value=self.args.image), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(s.main(['--check', str(self.args.stage_dir / 'runtime-smoke.json')]), 0)
        self.assertEqual(output.getvalue(),
                         'rp-d1 stage check: PASS (inputs, release, credential shape, boot catalogs, image)\n')


if __name__ == '__main__':
    unittest.main()
