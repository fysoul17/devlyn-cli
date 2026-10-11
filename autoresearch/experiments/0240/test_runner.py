"""Synthetic peer ancestry checks through the unchanged native evidence/accounting gates."""
from pathlib import Path
import unittest
from unittest.mock import patch
import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner0240_tests', HERE / 'runner.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
fixtures = r.load('fixtures0238_single_peer', HERE.parent / '0238/test_runner.py')
fixtures.r = r


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ApparatusTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()

    def test_peer_child_is_protocol_failure_with_all_costs_retained(self):
        f = self.fixture
        f.receipt(); f.codex(child=True)
        before = r.base_policy.check(f.out, f.plan, f.app.tasks, f.app.frame.cell_run.evidence)
        self.assertEqual(before['status'], 'MATCH')
        self.assertEqual(before['protocol_violations'], [])
        result = f.recorded_good_product()
        self.assertEqual(result['status'], 'PRODUCT_INCOMPLETE')
        self.assertEqual(result['peer_policy']['status'], 'MATCH')
        self.assertEqual(result['peer_policy']['protocol_violations'],
                         ['codex peer delegated to native child child'])
        self.assertEqual((result['usage'], result['input_tokens'], result['output_tokens']),
                         ('COMPLETE', 216, 24))

    def test_no_child_fresh_resume_preserve_success_and_full_cost(self):
        f = self.fixture
        f.receipt(); f.codex(child=False)
        f.receipt(turn=2, resume='peer'); f.codex(child=False, turn=2)
        result = f.recorded_good_product()
        self.assertEqual(result['status'], 'CHECKS_PASS')
        self.assertEqual(result['peer_policy']['protocol_violations'], [])
        self.assertEqual((result['usage'], result['input_tokens'], result['output_tokens']),
                         ('COMPLETE', 216, 24))

    def test_native_owner_child_remains_allowed(self):
        self.fixture.test_native_owner_child_is_not_an_independent_peer()
        self.assertEqual(self.fixture.check()['protocol_violations'], [])

    def test_wrong_actual_model_still_stops_before_product_check(self):
        f = self.fixture
        f.receipt(); f.codex(child=False, model='gpt-6-sol', effort='high')
        result = f.recorded_good_product(expected_return=2)
        self.assertEqual(result['status'], 'STOP')
        self.assertIn('model identity', result['reason'])
        self.assertFalse((f.out / 'checks.json').exists())

    def test_unknown_codex_usage_still_stops_with_lower_bound(self):
        f = self.fixture
        f.receipt(); f.codex(child=False, completed=False)
        result = f.recorded_good_product(expected_return=2)
        self.assertEqual(result['status'], 'STOP')
        self.assertEqual(result['usage'], 'PARTIAL')
        self.assertGreater(result['known_usage_lower_bound']['input_tokens'], 0)
        self.assertIsNone(result['input_tokens'])
        self.assertFalse((f.out / 'checks.json').exists())

    def test_base_execution_and_owner_preparation_are_inherited(self):
        for name in ('run', 'prepare', 'evaluate', 'preflight', 'unchanged'):
            self.assertIs(getattr(r.Runner, name), getattr(r.BaseRunner, name))
        self.fixture.test_both_cli_defaults_and_trust_seeded_before_seal()

    def test_new_and_imported_adapters_are_prospective_inputs(self):
        app = self.fixture.app
        paths = [HERE / name for name in ('runner.py', 'peer.py', 'build_packages.py',
                                         'results/stage.py', 'guides/H.md', 'guides/P.md', 'guides/S.md')]
        paths += [HERE.parent / '0238' / name for name in ('runner.py', 'policy.py', 'peer.py',
                    'claude-accounting-v1.py', 'build_packages.py', 'results/stage.py')]
        sealed = app.inputs()
        for path in paths:
            self.assertEqual(sealed[str(path)], r.digest(path))
        original = r.digest
        with patch.object(r, 'digest', side_effect=lambda path: 'changed' if path == HERE / 'peer.py' else original(path)):
            self.assertNotEqual(app.inputs(), sealed)


def load_tests(loader, tests, pattern):
    # Reuse the existing fixtures, with the prospective Runner bound above.
    for name in ('test_unclosed_claude_stream_stops_without_product_failure_or_cost_loss',
                 'test_wrong_resume_effort_and_missing_effort_are_rejected',
                 'test_failed_helper_before_native_trace_does_not_become_zero_peer',
                 'test_source_changed_during_peer_is_visible_product_protocol_failure',
                 'test_zero_peer_is_valid_not_forced_activation',
                 'test_init_owner_keeps_native_owner_effort_check'):
        tests.addTest(fixtures.ApparatusTests(name))
    return tests


if __name__ == '__main__':
    unittest.main(verbosity=2)
