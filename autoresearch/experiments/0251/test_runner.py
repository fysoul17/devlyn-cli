"""Verify refusal ordering and preserved inherited native evidence wiring."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner0251_test', HERE / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='0251-runner-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        runtime = dict(tasks_file=str(HERE.parent / '0238/tasks-draft.json'),
            image='sha256:' + 'a' * 64, control=str(self.root / 'control'), phase='smoke',
            output=str(self.root / 'out'), auth=str(self.root / 'auth'), sources=str(self.root))
        self.path = self.root / 'runtime.json'
        self.path.write_text(json.dumps(runtime))
        self.app = runner.Runner(self.path)

    def test_initial_refusal_records_no_dispatch_and_never_prepares(self):
        with patch.object(self.app, 'validate'), \
                patch.object(runner.auth, 'preflight', return_value=(None, 'snapshot-changed')) as check, \
                patch.object(self.app, 'prepare') as prepare:
            result = self.app.run('refusal', 'F23', 'B', 'claude')
        self.assertEqual(result, 3)
        check.assert_called_once_with(self.app.runtime)
        prepare.assert_not_called()
        out = self.root / 'out'
        self.assertEqual(sorted(p.name for p in out.iterdir()), ['not-dispatched-refusal.json'])
        self.assertEqual(runner.read(out / 'not-dispatched-refusal.json'), {'reason': 'snapshot-changed'})

    def test_only_owner_launch_and_auth_hooks_change(self):
        previous = runner.legacy.Runner(self.path)
        for name in ('run', 'prepare', 'evaluate', 'unchanged', 'boot_catalogs'):
            self.assertIs(getattr(type(self.app), name), getattr(type(previous), name))
        native = self.app.frame.cell_run
        self.assertIs(native.run.func, runner.cell.run)
        self.assertIs(native.run.keywords['native'], native)
        self.assertIs(native.run.keywords['check_auth'], runner.auth.preflight)
        self.assertIs(native.evidence, self.app.frame.usage.evidence)
        self.assertIs(native.evidence.TASKS, self.app.tasks)

    def test_separate_assessor_fails_explicitly(self):
        with self.assertRaisesRegex(ValueError, 'does not provision separate model assessors'):
            self.app.assess('unused')


if __name__ == '__main__':
    unittest.main()
