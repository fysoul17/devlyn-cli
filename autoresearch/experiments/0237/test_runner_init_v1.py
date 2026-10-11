"""Offline regression checks; every process boundary is mocked."""
import ast
from contextlib import ExitStack
import importlib.util
import inspect
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner_init_test', HERE / 'runner-init-v1.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class InitRunnerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='0237-init-mock-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.runtime = self.root / 'runtime.json'
        control = self.root / 'control'
        Path(str(control) + '.manifest.json').write_text('{}')
        self.runtime.write_text(json.dumps(dict(control=str(control), phase='smoke')))
        self.app = runner.Runner(self.runtime)
        self.owner = self.app.frame.cell_run
        # A missed mock must fail before starting any executable.
        guard = patch.object(subprocess, 'run', side_effect=AssertionError('real subprocess forbidden'))
        guard.start()
        self.addCleanup(guard.stop)

    def test_only_owner_creation_argument_changes(self):
        original = ast.parse(inspect.getsource(self.owner.legacy.run))
        current = ast.parse(inspect.getsource(self.owner.run))
        argv = next(node.value for node in ast.walk(current)
                    if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'argv' for target in node.targets))
        self.assertEqual(argv.elts[1].value, '--init')
        del argv.elts[1]
        self.assertEqual(ast.dump(current), ast.dump(original))
        for name in ('identity', 'preserve_tmp', 'lines', 'docker', 'evidence', 'base'):
            self.assertIs(getattr(self.owner, name), getattr(self.owner.legacy, name))

    def test_inputs_bind_new_owner_without_changing_legacy_inputs_or_routes(self):
        old = runner.frozen.Runner(self.runtime)
        new_inputs = self.app.inputs()
        self.assertEqual({key: value for key, value in new_inputs.items() if key in old.inputs()}, old.inputs())
        self.assertEqual(set(new_inputs) - set(old.inputs()),
                         {str(HERE / 'runner-init-v1.py'), str(HERE / 'cell-init-v1.py')})
        for path in ('runner-init-v1.py', 'cell-init-v1.py'):
            self.assertEqual(new_inputs[str(HERE / path)], runner.frozen.digest(HERE / path))
        self.assertEqual(self.app.tasks, old.tasks)
        self.assertIs(self.owner.evidence.TASKS, self.app.tasks)
        for name in ('run', 'prepare', 'preflight', 'unchanged', 'assess', 'boot_catalogs'):
            self.assertIs(getattr(type(self.app), name), getattr(runner.frozen.Runner, name))
        with patch.object(runner.frozen, 'digest', side_effect=lambda path: 'changed' if Path(path).name == 'cell-init-v1.py' else new_inputs[str(path)]):
            self.assertNotEqual(self.app.inputs(), new_inputs)

    def run_owner(self, case, code=0, timeout=False, survivor=False, bad_identity=False):
        out = self.root / case
        home = out / 'home'
        for path in (home / '.claude', home / '.codex', out / 'cell', out / 'harness', out / 'tmp', out / 'auth'):
            path.mkdir(parents=True)
        (out / 'auth/claude.json').write_text('{"synthetic_fixture":true}')
        (out / 'auth/codex.json').write_text('{"synthetic_fixture":true}')
        plan = dict(name=case, engine='claude', home=str(home), cell=str(out / 'cell'),
                    harness=str(out / 'harness'), tmp=str(out / 'tmp'), control=str(out / 'control'),
                    image='sha256:' + 'a' * 64, env={'HOME': '/home/participant'},
                    argv=['claude', '-p', '--model', 'registered-model', '--effort', 'max', 'fixture'],
                    wall_seconds=5400)
        (out / 'plan.json').write_text(json.dumps(plan))
        runtime = dict(auth=str(out / 'auth'), scratch=str(out / 'scratch'))
        calls = []
        killed = False

        def docker(*args, **kwargs):
            nonlocal killed
            calls.append(args)
            if args[0] == 'create':
                return 'fixture-container'
            if args[0] == 'inspect':
                running = survivor or (timeout and not killed)
                return json.dumps([{'State': {'Running': running, 'Pid': 1 if running else 0}}])
            if args[0] == 'kill':
                killed = True
            return ''

        wait = Mock(side_effect=subprocess.TimeoutExpired('docker start', 5400) if timeout else None,
                    return_value=code)

        def launch(argv, *, stdout, stderr):
            self.assertEqual(argv, ['docker', 'start', '-a', 'fixture-container'])
            stdout.write(b'{"type":"result","result":"fixture final"}\n')
            return SimpleNamespace(wait=wait)

        expected_identity = dict(status='MATCH', marker='inherited native identity')
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.owner, 'docker', side_effect=docker))
            stack.enter_context(patch.object(self.owner.subprocess, 'Popen', side_effect=launch))
            preserve = stack.enter_context(patch.object(self.owner, 'preserve_tmp'))
            identity = stack.enter_context(patch.object(self.owner, 'identity', return_value=expected_identity,
                                                        side_effect=ValueError('identity gap') if bad_identity else None))
            result = self.owner.run(out, runtime)
        wait.assert_called_once_with(timeout=5400)
        actual = list(next(args for args in calls if args[0] == 'create'))
        started = json.loads((out / 'run/started.json').read_text())
        saved = json.loads((out / 'run/result.json').read_text())
        self.assertEqual(actual, started['create_argv'])
        self.assertEqual(actual, saved['create_argv'])
        self.assertEqual(actual.count('--init'), 1)
        for flag, value in (('--pids-limit', '256'), ('--memory', '4g'), ('--cpus', '2'), ('--network', 'bridge')):
            self.assertEqual(actual[actual.index(flag) + 1], value)
        self.assertEqual(actual[actual.index(plan['image']) + 1:], plan['argv'])
        self.assertEqual(started['source_sha256'], runner.frozen.digest(HERE / 'cell-init-v1.py'))
        self.assertFalse((out / 'scratch/credentials' / case).exists())
        identity.assert_called_once_with(out, plan)
        self.assertEqual(result['identity']['status'], 'UNVERIFIED' if bad_identity else 'MATCH')
        self.assertEqual((out / 'final.txt').read_text(), 'fixture final')
        if survivor:
            preserve.assert_not_called()
            self.assertEqual(result['teardown'], 'FAILED')
        else:
            preserve.assert_called_once_with(result['tmp_volume'], out / 'tmp', plan['image'])
            self.assertEqual(result['teardown'], 'CLEAN')
        return result

    def test_recorded_argv_exit_timeout_and_teardown_are_preserved(self):
        for name, kwargs, expected in (
                ('success', {}, 'EXITED_0'),
                ('nonzero', {'code': 7}, 'EXITED_NONZERO'),
                ('timeout', {'timeout': True}, 'HANG_TIMEOUT'),
                ('survivor', {'survivor': True}, 'EXITED_0')):
            with self.subTest(case=name):
                self.assertEqual(self.run_owner(name, **kwargs)['owner_status'], expected)

    def test_identity_gap_stays_visible(self):
        result = self.run_owner('identity-gap', bad_identity=True)
        self.assertEqual(result['identity']['violations'], ['identity check failed: identity gap'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
