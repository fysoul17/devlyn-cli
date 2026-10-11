"""Synthetic fixed-auth regressions. All host and profile operations are mocked."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('auth0251_test', HERE / 'auth.py')
auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth)


class FixedAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / 'home'
        (self.home / '.codex').mkdir(parents=True)
        self.codex = b'{"tokens":{"access_token":"synthetic-codex","refresh_token":"synthetic-codex-refresh"}}\n'
        (self.home / '.codex/auth.json').write_bytes(self.codex)
        self.now = 1000000
        self.oauth = {'accessToken': 'synthetic-claude-token', 'refreshToken': 'synthetic-claude-refresh',
                      'expiresAt': (self.now + 10000) * 1000,
                      'scopes': ['user:inference', 'user:profile'],
                      'subscriptionType': 'max', 'rateLimitTier': 'default_claude_max_5x'}
        self.identity = [auth.digest(item.encode())[:12] for item in ('account-fixture', 'org-fixture')]
        self.destination = self.root / 'frozen'
        self.enterContext(patch.dict(auth.os.environ, {}, clear=True))
        self.clock = self.enterContext(patch.object(auth.time, 'time', return_value=self.now))
        self.host = self.enterContext(patch.object(auth.subprocess, 'run', side_effect=self.read_host))
        self.enterContext(patch.object(auth.Path, 'home', return_value=self.home))
        self.profile = self.enterContext(patch.object(auth.urllib.request, 'urlopen', side_effect=self.read_profile))

    def read_host(self, argv, **kwargs):
        self.assertEqual(argv, ['security', 'find-generic-password', '-s', 'Claude Code-credentials', '-w'])
        self.assertEqual(kwargs, {'capture_output': True, 'check': True, 'timeout': 20})
        return subprocess.CompletedProcess(argv, 0, json.dumps({'claudeAiOauth': self.oauth}).encode())

    def read_profile(self, request, **kwargs):
        self.assertEqual(request.full_url, auth.PROFILE_URL)
        self.assertEqual(request.get_header('Authorization'), 'Bearer synthetic-claude-token')
        self.assertEqual(kwargs, {'timeout': 20})
        return io.BytesIO(json.dumps({'account': {'uuid': 'account-fixture'},
                                     'organization': {'uuid': 'org-fixture'}}).encode())

    def bootstrap(self):
        manifest = auth.bootstrap(self.destination)
        return {'auth': str(self.destination), 'auth_manifest_sha256': auth.digest(auth.encoded(manifest)),
                'account': self.identity}, manifest

    def replace(self, name, raw):
        path = self.destination / name
        path.chmod(0o600)
        path.write_bytes(raw)
        path.chmod(0o400)

    def test_bootstrap_reads_once_and_preflight_never_reads_changed_host(self):
        original_read = Path.read_bytes
        reads = []
        def recorded_read(path):
            if path == self.home / '.codex/auth.json':
                reads.append(str(path))
            return original_read(path)
        with patch.object(Path, 'read_bytes', recorded_read):
            runtime, manifest = self.bootstrap()
            self.oauth['accessToken'] = 'different-live-account'
            (self.home / '.codex/auth.json').write_bytes(b'changed-host-codex')
            self.host.side_effect = AssertionError('host reread forbidden')
            for _ in range(2):
                venue, refused = auth.preflight(runtime)
                self.assertIsNone(refused)
                self.assertEqual(venue, {'account': self.identity, 'token_seconds_left': 10000})
        self.assertEqual(self.host.call_count, 1)
        self.assertEqual(len(reads), 1)
        self.assertEqual(self.profile.call_count, 3)
        self.assertEqual((self.destination / 'codex.json').read_bytes(), self.codex)
        self.assertEqual(manifest['account'], self.identity)

    def test_private_access_only_snapshot_preserves_supported_metadata(self):
        runtime, manifest = self.bootstrap()
        env = (self.destination / 'claude.env').read_text()
        self.assertEqual(env, 'CLAUDE_CODE_OAUTH_TOKEN=synthetic-claude-token\n'
                         'CLAUDE_CODE_OAUTH_SCOPES=user:inference user:profile\n'
                         'CLAUDE_CODE_SUBSCRIPTION_TYPE=max\n'
                         'CLAUDE_CODE_RATE_LIMIT_TIER=default_claude_max_5x\n')
        self.assertEqual(self.destination.stat().st_mode & 0o777, 0o700)
        self.assertEqual({p.name for p in self.destination.iterdir()}, {'claude.env', 'codex.json', 'manifest.json'})
        for path in self.destination.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o400)
            self.assertNotIn(b'synthetic-claude-refresh', path.read_bytes())
        self.assertNotIn('synthetic-claude-token', json.dumps(manifest))
        self.assertEqual(auth.digest((self.destination / 'manifest.json').read_bytes()), runtime['auth_manifest_sha256'])

    def test_existing_destination_refuses_before_any_host_read(self):
        self.destination.mkdir()
        marker = self.destination / 'keep'; marker.write_bytes(b'unchanged')
        with self.assertRaises(FileExistsError):
            auth.bootstrap(self.destination)
        self.host.assert_not_called()
        self.assertEqual(marker.read_bytes(), b'unchanged')

    def test_host_source_overrides_refuse_before_reads_or_creation(self):
        for name in auth.HOST_OVERRIDES:
            with self.subTest(name=name), patch.dict(auth.os.environ, {name: 'synthetic-override'}):
                with self.assertRaisesRegex(auth.AuthError, 'requires-default-host-sources'):
                    auth.bootstrap(self.destination)
                self.host.assert_not_called()
                self.assertFalse(self.destination.exists())

    def test_expiry_boundary_and_elapsed_profile_time_fail_closed(self):
        runtime, _ = self.bootstrap()
        self.clock.return_value = self.now + 3700
        self.assertEqual(auth.preflight(runtime)[0]['token_seconds_left'], 6300)
        self.clock.return_value = self.now + 3701
        before = self.profile.call_count
        self.assertEqual(auth.preflight(runtime), (None, 'frozen-auth-lifetime-below-6300-seconds'))
        self.assertEqual(self.profile.call_count, before)
        self.clock.side_effect = [self.now + 3700, self.now + 3701]
        self.assertEqual(auth.preflight(runtime), (None, 'frozen-auth-lifetime-below-6300-seconds'))

    def test_missing_snapshot_or_binding_never_falls_back(self):
        self.host.side_effect = AssertionError('host fallback forbidden')
        runtime = {'auth': str(self.destination), 'auth_manifest_sha256': '0' * 64, 'account': self.identity}
        self.assertIsNone(auth.preflight(runtime)[0])
        self.host.assert_not_called()
        self.host.side_effect = self.read_host
        runtime, _ = self.bootstrap()
        runtime.pop('auth_manifest_sha256')
        self.assertIsNone(auth.preflight(runtime)[0])
        self.assertEqual(self.host.call_count, 1)

    def test_manifest_and_each_frozen_file_are_bound(self):
        runtime, _ = self.bootstrap()
        for name in ('manifest.json', 'claude.env', 'codex.json'):
            with self.subTest(name=name):
                before = (self.destination / name).read_bytes()
                self.replace(name, before + b' ')
                self.assertIsNone(auth.preflight(runtime)[0])
                self.replace(name, before)
        wrong = {**runtime, 'account': ['0' * 12, '1' * 12]}
        self.assertEqual(auth.preflight(wrong), (None, 'auth-account-binding-mismatch'))
        self.profile.side_effect = lambda *a, **k: io.BytesIO(b'{"account":{"uuid":"different"},"organization":{"uuid":"org-fixture"}}')
        self.assertEqual(auth.preflight(runtime), (None, 'auth-account-profile-mismatch'))

    def test_permissions_owners_links_and_extra_files_refuse(self):
        runtime, _ = self.bootstrap()
        for name in ('manifest.json', 'claude.env', 'codex.json'):
            with self.subTest(name=name):
                path = self.destination / name
                path.chmod(0o644)
                self.assertIsNone(auth.preflight(runtime)[0])
                path.chmod(0o400)
                saved = path.read_bytes(); path.unlink(); path.symlink_to(self.home / '.codex/auth.json')
                self.assertIsNone(auth.preflight(runtime)[0])
                path.unlink(); auth.write_private(self.destination, name, saved)
        self.destination.chmod(0o755)
        self.assertIsNone(auth.preflight(runtime)[0])
        self.destination.chmod(0o700)
        with patch.object(auth.os, 'getuid', return_value=os.getuid() + 1):
            self.assertIsNone(auth.preflight(runtime)[0])
        alias = self.root / 'alias'; alias.symlink_to(self.destination, target_is_directory=True)
        self.assertIsNone(auth.preflight({**runtime, 'auth': str(alias)})[0])
        extra = self.destination / 'extra'; extra.write_bytes(b'not adopted')
        self.assertIsNone(auth.preflight(runtime)[0])

    def test_nonregular_and_hardlinked_snapshot_files_refuse_without_blocking(self):
        runtime, _ = self.bootstrap()
        path = self.destination / 'claude.env'
        saved = path.read_bytes(); path.unlink()
        os.mkfifo(path, 0o400)
        self.assertEqual(auth.preflight(runtime), (None, 'auth-file-not-private-regular'))
        path.unlink(); auth.write_private(self.destination, 'claude.env', saved)
        os.link(path, self.root / 'linked-secret')
        self.assertEqual(auth.preflight(runtime), (None, 'auth-file-not-private-regular'))

    def test_bootstrap_rejects_unsafe_env_and_expiry_without_persisting_secret(self):
        for field, item in (('accessToken', 'bad\nvalue'), ('subscriptionType', 'bad\0value'),
                            ('rateLimitTier', 'bad\rvalue'), ('scopes', ['bad\nscope']),
                            ('expiresAt', float('nan')), ('expiresAt', (self.now + 6299) * 1000)):
            with self.subTest(field=field, item=item):
                self.destination = self.root / ('bad-' + str(self.host.call_count))
                before = self.oauth[field]; self.oauth[field] = item
                with self.assertRaises(auth.AuthError):
                    auth.bootstrap(self.destination)
                self.assertEqual(list(self.destination.iterdir()), [])
                self.oauth[field] = before

    def test_profile_and_cli_failures_do_not_echo_secrets(self):
        self.profile.side_effect = OSError('synthetic-claude-token synthetic-claude-refresh')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(auth.main([str(self.destination)]), 3)
        self.assertEqual(json.loads(output.getvalue()), {'status': 'BLOCKED', 'reason': 'frozen-auth-profile-unavailable'})
        self.assertNotIn('synthetic-', output.getvalue())
        self.destination = self.root / 'host-failure'
        self.host.side_effect = subprocess.CalledProcessError(1, 'security', output=b'synthetic-claude-token')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(auth.main([str(self.destination)]), 3)
        self.assertEqual(json.loads(output.getvalue()), {'status': 'BLOCKED', 'reason': 'auth-bootstrap-failed'})

    def test_http_and_json_profile_failures_are_masked_in_preflight(self):
        runtime, _ = self.bootstrap()
        error = urllib.error.HTTPError(auth.PROFILE_URL, 401, 'synthetic-claude-token', {}, None)
        self.profile.side_effect = error
        self.assertEqual(auth.preflight(runtime), (None, 'frozen-auth-profile-unavailable'))
        self.assertTrue(error.closed)
        self.profile.side_effect = lambda *a, **k: io.BytesIO(b'synthetic-claude-token')
        self.assertEqual(auth.preflight(runtime), (None, 'frozen-auth-profile-unavailable'))

    def test_partial_write_failure_is_explicit_private_and_never_readopted(self):
        write = auth.write_private
        def fail_manifest(root, name, raw):
            if name == 'manifest.json':
                raise OSError('synthetic-claude-token')
            return write(root, name, raw)
        output = io.StringIO()
        with patch.object(auth, 'write_private', side_effect=fail_manifest), contextlib.redirect_stdout(output):
            self.assertEqual(auth.main([str(self.destination)]), 3)
        self.assertEqual(json.loads(output.getvalue()), {'status': 'BLOCKED',
                         'reason': 'auth-write-failed-private-destination-retained'})
        self.assertEqual(self.destination.stat().st_mode & 0o777, 0o700)
        for path in self.destination.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o400)
        with self.assertRaises(FileExistsError):
            auth.bootstrap(self.destination)
        self.assertEqual(self.host.call_count, 1)
        runtime = {'auth': str(self.destination), 'auth_manifest_sha256': '0' * 64, 'account': self.identity}
        self.assertEqual(auth.preflight(runtime), (None, 'auth-snapshot-file-set-mismatch'))

    def test_cli_success_prints_only_nonsecret_binding(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(auth.main([str(self.destination)]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result['manifest']['account'], self.identity)
        self.assertNotIn('synthetic-', output.getvalue())
        self.assertEqual(result['auth_manifest_sha256'], auth.digest((self.destination / 'manifest.json').read_bytes()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
