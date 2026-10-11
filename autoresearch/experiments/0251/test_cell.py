"""Synthetic launch parity, refusal and custody checks; no containers or models."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cell = load('cell0251_test', HERE / 'cell.py')
old = load('cell0238_comparison', HERE.parent / '0238/cell-init-v1.py')


class LaunchTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='0251-launch-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.calls = []
        self.native = SimpleNamespace(docker=Mock(side_effect=self.docker),
            preserve_tmp=Mock(), identity=Mock(return_value={'status': 'MATCH'}),
            lines=Mock(return_value=[]), base=SimpleNamespace(final_message=Mock(return_value='done')))
        self.check = Mock(return_value=({'account': ['fixed', 'fixed']}, None))
        self.wait = Mock(return_value=0)

    def prepare(self, name):
        out = self.root / name
        for folder in ('home/.claude', 'home/.codex', 'cell', 'harness', 'tmp', 'auth'):
            (out / folder).mkdir(parents=True)
        (out / 'auth/claude.env').write_text('CLAUDE_CODE_OAUTH_TOKEN=synthetic-secret-sentinel\n')
        # Old launcher's test-only input: the new launcher must never read/mount it.
        (out / 'auth/claude.json').write_text('{"refreshToken":"synthetic-refresh-sentinel"}')
        (out / 'auth/codex.json').write_text('{"synthetic":true}')
        plan = dict(name=name, engine='claude', arm='B', cell=str(out / 'cell'),
            home=str(out / 'home'), harness=str(out / 'harness'), tmp=str(out / 'tmp'),
            control='/registered/public', image='sha256:' + 'a' * 64,
            env={'HOME': '/home/participant', 'CLAUDE_CODE_EFFORT_LEVEL': 'max'},
            argv=['claude', '-p', '--model', 'claude-opus-5-5', '--effort', 'max', 'task'], wall_seconds=5400)
        (out / 'plan.json').write_text(json.dumps(plan))
        return out, dict(auth=str(out / 'auth'), scratch=str(out / 'scratch'))

    def docker(self, *args):
        self.calls.append(args)
        if args[0] == 'create':
            return 'owned-container'
        if args[0] == 'inspect':
            state = dict(Running=False, Pid=0)
            return json.dumps(state if '--format' in args else [dict(State=state)])
        return ''

    def launch(self, argv, *, stdout, stderr):
        self.assertEqual(argv, ['docker', 'start', '-a', 'owned-container'])
        stdout.write(b'{}\n')
        return Mock(wait=self.wait)

    def execute(self, out, runtime):
        with patch.object(cell.subprocess, 'Popen', side_effect=self.launch):
            return cell.run(out, runtime, native=self.native, check_auth=self.check)

    def assert_no_secrets(self, out):
        for path in [out / 'plan.json', *sorted((out / 'run').glob('*'))]:
            self.assertNotIn('synthetic-secret-sentinel', path.read_text())
            self.assertNotIn('synthetic-refresh-sentinel', path.read_text())

    def test_actual_argv_only_changes_auth_transport_and_keeps_evidence_and_watchdog(self):
        current, runtime = self.prepare('current')
        result = self.execute(current, runtime)
        new_argv = list(next(call for call in self.calls if call[0] == 'create'))
        self.assertEqual(new_argv, json.loads((current / 'run/started.json').read_text())['create_argv'])
        self.assertEqual(new_argv, result['create_argv'])
        self.assertEqual(new_argv[new_argv.index('--env-file') + 1], str(current / 'auth/claude.env'))
        self.assertFalse(any('claude.json' in value for value in new_argv))
        self.assertTrue(all('--format' in call for call in self.calls if call[0] == 'inspect'))
        self.wait.assert_called_once_with(timeout=5400)
        self.check.assert_called_once_with(runtime)
        self.native.identity.assert_called_once()
        self.native.preserve_tmp.assert_called_once()
        self.assertEqual((result['owner_status'], result['teardown']), ('EXITED_0', 'CLEAN'))
        self.assertEqual((current / 'home/.claude/.credentials.json').read_bytes(), b'')
        self.assert_no_secrets(current)

        previous, previous_runtime = self.prepare('previous')
        self.calls.clear()
        with patch.object(old, 'docker', side_effect=self.docker), \
                patch.object(old.subprocess, 'Popen', side_effect=self.launch), \
                patch.object(old, 'preserve_tmp'), patch.object(old, 'identity', return_value={'status': 'MATCH'}):
            old.run(previous, previous_runtime)
        old_argv = list(next(call for call in self.calls if call[0] == 'create'))

        def normalized(argv, out):
            values = []
            index = 0
            while index < len(argv):
                key = argv[index]
                if key == '--env-file' or (key == '--mount' and '/.claude/.credentials.json' in argv[index + 1]):
                    index += 2
                    continue
                if key == '--name':
                    values += [key, '<owned-name>']
                    index += 2
                    continue
                value = key.replace(str(out), '<out>')
                if value.startswith('type=volume,src='):
                    value = 'type=volume,src=<owned-volume>,dst=/tmp'
                values.append(value)
                index += 1
            return values

        self.assertEqual(normalized(new_argv, current), normalized(old_argv, previous))

    def test_expiry_during_preparation_refuses_before_any_docker_call(self):
        out, runtime = self.prepare('expired')
        self.check.return_value = (None, 'insufficient lifetime')
        with self.assertRaisesRegex(ValueError, 'insufficient lifetime'):
            self.execute(out, runtime)
        self.native.docker.assert_not_called()
        self.assertFalse((out / 'run').exists())

    def test_competing_plan_auth_refuses(self):
        out, runtime = self.prepare('competing')
        plan = json.loads((out / 'plan.json').read_text())
        plan['env']['ANTHROPIC_API_KEY'] = 'synthetic-alternative'
        (out / 'plan.json').write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValueError, 'competing authentication'):
            self.execute(out, runtime)
        self.native.docker.assert_not_called()

    def test_create_failure_releases_owned_volume_and_retains_record(self):
        out, runtime = self.prepare('create-failure')
        def fail(*args):
            if args[0] == 'create':
                raise RuntimeError('synthetic create failure')
            return self.docker(*args)
        self.native.docker.side_effect = fail
        with self.assertRaisesRegex(RuntimeError, 'synthetic create failure'):
            self.execute(out, runtime)
        record = json.loads((out / 'run/result.json').read_text())
        self.assertEqual(record['teardown'], 'CLEAN')
        self.assertIsNone(record['owner_status'])
        self.assertIn(('volume', 'rm', record['tmp_volume']), self.calls)
        self.native.preserve_tmp.assert_not_called()
        self.assert_no_secrets(out)

    def test_timeout_and_cleanup_failure_remain_visible(self):
        out, runtime = self.prepare('timeout')
        self.wait.side_effect = subprocess.TimeoutExpired('docker start', 5400)
        self.native.preserve_tmp.side_effect = RuntimeError('synthetic preserve failure')
        result = self.execute(out, runtime)
        self.assertEqual((result['owner_status'], result['teardown']), ('HANG_TIMEOUT', 'FAILED'))
        self.assertIn('synthetic preserve failure', result['teardown_error'])
        self.assert_no_secrets(out)


if __name__ == '__main__':
    unittest.main()
