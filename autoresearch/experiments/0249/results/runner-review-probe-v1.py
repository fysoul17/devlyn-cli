"""Review-only mocked evaluator probes. Blocks subprocess execution globally."""
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('review_tests0249', HERE / 'test_runner.py')
tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tests)


class EdgeTests(tests.RoutingTests):
    def setUp(self):
        super().setUp()
        fixture = tests.runner.read(HERE / 'fixtures/OR2/task.json')
        self.subject.tasks['tasks'].append(dict(fixture, eq3_dir='unused-by-review'))

    def evaluate_record(self, task_id, public_exit=0, oracle_exit=0, timeout=False):
        subject = self.subject
        expected = subject.task(task_id)['oracle']
        def execute(runtime, work, argv):
            public = argv[0] == 'sh'
            return dict(argv=argv, exit_code=public_exit if public else oracle_exit,
                        timeout=timeout, stderr='review-full-diagnostic-' + 'x' * 3000,
                        stdout=json.dumps({'manifestations': [dict(id=row, passed=i != 0)
                                                             for i, row in enumerate(expected)]}))
        module = subject.orphan if task_id == 'B5' else subject.frame.check
        with patch.object(module, 'in_image', execute):
            return subject.evaluate(self.work, task_id, self.runtime)

    def test_public_failure_is_preserved(self):
        for task_id in ('B5', 'OR1', 'OR2'):
            for exit_code in (1, 124):
                with self.subTest(task=task_id, exit_code=exit_code):
                    result = self.evaluate_record(task_id, public_exit=exit_code)
                    self.assertTrue(result['public'])
                    self.assertTrue(all(row['exit_code'] == exit_code for row in result['public']))
                    self.assertEqual(len(result['rows']), len(self.subject.task(task_id)['oracle']))

    def test_fixture_timeout_and_nonzero_preserve_full_raw(self):
        for task_id in ('OR1', 'OR2'):
            for exit_code in (1, 124, None):
                with self.subTest(task=task_id, exit_code=exit_code):
                    with self.assertRaises(ValueError) as caught:
                        self.evaluate_record(task_id, oracle_exit=exit_code, timeout=exit_code != 1)
                    result = json.loads(str(caught.exception).split(': ', 1)[1])
                    self.assertEqual(result['raw'][0]['stderr'], 'review-full-diagnostic-' + 'x' * 3000)
                    self.assertEqual(result['raw'][0]['exit_code'], exit_code)
                    self.assertEqual(result['raw'][0]['timeout'], exit_code != 1)
                    self.assertTrue(result['raw'][0]['stdout'])

    def test_b5_timeout_preserves_inherited_failed_row(self):
        result = self.evaluate_record('B5', oracle_exit=124, timeout=True)
        self.assertEqual([row['status'] for row in result['rows']], ['FAIL'] * 5)
        self.assertTrue(all(row['timeout'] for row in result['raw']))

    def test_or2_valid_product_failure_and_startup_stop(self):
        result = self.evaluate_record('OR2')
        self.assertEqual([row['status'] for row in result['rows']],
                         ['FAIL'] + ['PASS'] * (len(result['rows']) - 1))
        for task_id in ('B5', 'OR1', 'OR2'):
            for exit_code in (125, 126, 127):
                error = self.subject.orphan.NoVerdict if task_id == 'B5' else self.subject.frame.check.NoVerdict
                with self.subTest(task=task_id, exit_code=exit_code), self.assertRaises(error):
                    self.evaluate_record(task_id, oracle_exit=exit_code)

    def test_instance_globals_and_cli_entry(self):
        second_path = self.subject.tasks_path.parent / 'second-tasks.json'
        second_tasks = json.loads(json.dumps(self.subject.tasks))
        second_tasks['watchdog_seconds']['evaluator'] += 1
        tests.runner.write(second_path, second_tasks)
        second = tests.runner.Runner(self.subject.runtime_path, second_path)
        self.assertIsNot(self.subject.orphan, second.orphan)
        self.assertIsNot(self.subject.orphan.base, second.orphan.base)
        self.assertIsNot(self.subject.frame.check, second.frame.check)
        self.assertIs(self.subject.orphan.TASKS, self.subject.tasks)
        self.assertIs(self.subject.orphan.base.TASKS, self.subject.tasks)
        self.assertEqual(second.orphan.SECONDS, self.subject.orphan.SECONDS + 1)
        self.assertEqual(second.orphan.base.SECONDS, second.orphan.SECONDS)
        self.assertEqual(self.subject.orphan.ROWS['B5'], self.subject.task('B5')['oracle'])
        entry = tests.runner.legacy.legacy.legacy.legacy.legacy.legacy.legacy
        self.assertEqual(Path(entry.__file__).parent.name, '0238')
        self.assertIs(self.subject.frame.check.evaluate.__self__, self.subject)
        self.assertIs(second.frame.check.evaluate.__self__, second)
        for name in ('run', 'preflight', 'boot_catalogs'):
            self.assertIs(getattr(tests.runner.Runner, name), getattr(tests.runner.legacy.Runner, name))


if __name__ == '__main__':
    with patch.object(subprocess, 'run', side_effect=AssertionError('External process forbidden in review')):
        unittest.main(verbosity=2)
