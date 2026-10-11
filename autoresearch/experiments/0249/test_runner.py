"""Focused dispatch and verdict-contract checks; no model or container calls."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner0249_test', HERE / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        tasks = runner.read(HERE.parent / '0247/tasks-smoke.json')
        previous = runner.read(HERE.parent / '0237/tasks.json')
        for task_id in ('B5', 'E1'):
            tasks['tasks'] = [t for t in tasks['tasks'] if t['id'] != task_id]
            tasks['tasks'].append(next(t for t in previous['tasks'] if t['id'] == task_id))
        fixture = runner.read(HERE / 'fixtures/OR1/task.json')
        tasks['tasks'].append(dict(fixture, eq3_dir='unused-by-readonly-dispatch-test'))
        runner.write(root / 'tasks.json', tasks)
        runtime = runner.read('/Users/aipalm/.local/share/nx01/0248-live/runtime-measured.json')
        runtime['tasks_file'] = str(root / 'tasks.json')
        runner.write(root / 'runtime.json', runtime)
        self.subject = runner.Runner(root / 'runtime.json')
        self.runtime = runtime
        self.work = root / 'work'

    def test_b5_uses_original_five_orphan_rows_and_retains_source_failure(self):
        calls = []
        def execute(runtime, work, argv):
            calls.append(argv)
            failed = 'legacy-removed' in argv
            return dict(argv=argv, exit_code=int(failed), timeout=False, stdout='{}', stderr='')
        with patch.object(self.subject.orphan, 'in_image', execute):
            result = self.subject.evaluate(self.work, 'B5', self.runtime)
        expected = self.subject.task('B5')['oracle']
        self.assertEqual([r['id'] for r in result['rows']], expected)
        self.assertEqual([r['status'] for r in result['rows']], ['FAIL'] + ['PASS'] * 4)
        self.assertEqual([c[1:4] for c in calls[1:]],
                         [['/control/autoresearch/experiments/0233/oracle.js', 'B5', row] for row in expected])

    def test_existing_e1_route_stays_on_0234(self):
        calls = []
        def execute(runtime, work, argv):
            calls.append(argv)
            return dict(argv=argv, exit_code=0, timeout=False, stdout='{}', stderr='')
        with patch.object(self.subject.frame.check, 'in_image', execute):
            result = self.subject.evaluate(self.work, 'E1', self.runtime)
        self.assertEqual([r['id'] for r in result['rows']], self.subject.task('E1')['oracle'])
        self.assertTrue(all(c[1] == '/control/autoresearch/experiments/0234/oracle.js' for c in calls[1:]))

    def fixture_result(self, exit_code):
        rows = [dict(id=name, passed=index != 0) for index, name in enumerate(self.subject.task('OR1')['oracle'])]
        def execute(runtime, work, argv):
            oracle = argv[0] == 'python3'
            return dict(argv=argv, exit_code=exit_code if oracle else 0, timeout=False,
                        stdout=json.dumps(dict(manifestations=rows)) if oracle else '{}',
                        stderr='oracle-diagnostic-marker' if oracle else '')
        with patch.object(self.subject.frame.check, 'in_image', execute):
            return self.subject.evaluate(self.work, 'OR1', self.runtime)

    def test_valid_fixture_failure_keeps_per_obligation_verdict(self):
        result = self.fixture_result(0)
        self.assertEqual([r['status'] for r in result['rows']], ['FAIL'] + ['PASS'] * 9)

    def test_incomplete_fixture_exit_stops_and_preserves_raw_diagnostics(self):
        with self.assertRaisesRegex(ValueError, 'oracle-diagnostic-marker') as caught:
            self.fixture_result(1)
        self.assertIn('recursive-ownership-boundaries', str(caught.exception))
        self.assertIn('"exit_code": 1', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
