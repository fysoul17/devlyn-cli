"""Terminal-summary regression through the retained native accounting/STOP gates."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner0244_tests', HERE / 'runner.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
prior = r.load('tests0242_terminal_reused', HERE.parent / '0242/test_runner.py')
prior.r = r
prior.prior.r = r
prior.prior.inherited.r = r
fixtures = prior.fixtures
fixtures.r = r


class TerminalCandidateTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ApparatusTests()
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.evidence = self.f.app.frame.cell_run.evidence
        self.scratch = self.f.out / 'cell/work/.devlyn/pair'
        self.scratch.mkdir(parents=True)
        (self.f.out / 'tmp').mkdir()

    def solo(self):
        self.f.plan['arm'] = 'B'
        r.write(self.f.out / 'plan.json', self.f.plan)

    def output(self, text):
        path = self.f.out / 'run/stdout'
        fixtures.lines(path, self.evidence.lines(path) + [dict(
            type='item.completed', item=dict(id='summary-output',
            type='command_execution', command='python3 inspect_capture.py',
            aggregated_output=text, exit_code=0))])

    def assert_stopped(self, result):
        self.assertEqual(result['status'], 'STOP')
        self.assertIsNone(result['input_tokens'])
        self.assertFalse((self.f.out / 'checks.json').exists())

    def test_exact_observed_summary_file_custody_and_inline_are_not_results(self):
        self.f.receipt(); self.f.codex(child=False)
        source = HERE / 'fixtures/fresh-result-metadata.json'
        expected = json.loads((HERE / 'results/fixture-sources-v1.json').read_text())[0]
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), expected['sha256'])
        summary = self.scratch / 'fresh-result-metadata.json'
        shutil.copyfile(source, summary)
        custody = self.f.out / 'cell/work/.git/devlyn-completion/test/records/.devlyn/pair'
        custody.mkdir(parents=True)
        shutil.copyfile(source, custody / summary.name)
        # The actual summary bytes are retained above; tool output may print
        # the same object on one line, where native envelopes were also found.
        self.output(json.dumps(json.loads(source.read_text())))
        self.assertEqual(self.evidence.claude_envelopes(self.f.out), ({}, []))
        result = self.f.recorded_good_product()
        self.assertEqual((result['status'], result['usage']), ('CHECKS_PASS', 'COMPLETE'))
        self.assertEqual((result['input_tokens'], result['output_tokens']), (116, 14))

    def test_genuine_native_result_missing_both_usage_fields_still_stops(self):
        self.solo()
        source = HERE / 'fixtures/fresh-native-result.json'
        expected = json.loads((HERE / 'results/fixture-sources-v1.json').read_text())[1]
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), expected['sha256'])
        value = json.loads(source.read_text())
        self.assertIn('modelUsage', value)
        self.assertIn('usage', value)
        del value['modelUsage']; del value['usage']
        target = self.f.out / 'tmp/unbound-native-result.json'
        r.write(target, value)
        envelopes, gaps = self.evidence.claude_envelopes(self.f.out)
        self.assertEqual(list(envelopes), [value['session_id']])
        self.assertEqual(gaps, [])
        result = self.f.recorded_good_product(expected_return=2)
        self.assert_stopped(result)
        self.assertTrue(any('without usage' in gap for gap in result['usage_gaps']), result)
        self.assertEqual(result['known_usage_lower_bound'], dict(input_tokens=16, output_tokens=4))

    def test_expected_minimal_counterless_result_bypasses_unbound_filter(self):
        self.f.plan['arm'] = 'H'; r.write(self.f.out / 'plan.json', self.f.plan)
        folder = self.f.receipt(engine='claude'); self.f.claude()
        r.write(folder / 'peer1.json', dict(type='result', session_id='peer'))
        envelopes, gaps = self.evidence.claude_envelopes(self.f.out)
        self.assertEqual(list(envelopes), ['peer'])
        self.assertEqual(gaps, [])
        result = self.f.recorded_good_product(expected_return=2)
        self.assert_stopped(result)
        self.assertTrue(any('without usage' in gap for gap in result['usage_gaps']), result)

    def test_unbound_empty_payload_and_usage_fields_remain_visible_and_stop(self):
        self.solo()
        target = self.f.out / 'tmp/unbound.json'
        cases = [('result', ''), ('result', None), ('errors', []), ('errors', None),
                 ('modelUsage', {}), ('modelUsage', None), ('usage', {}), ('usage', None)]
        for number, (key, value) in enumerate(cases):
            with self.subTest(key=key, value=value):
                r.write(target, dict(type='result', session_id='stranger', **{key: value}))
                envelopes, gaps = self.evidence.claude_envelopes(self.f.out)
                self.assertEqual(list(envelopes), ['stranger'])
                self.assertEqual(gaps, [])
                result = self.f.recorded_good_product(name=f'counterless-{number}', expected_return=2)
                self.assert_stopped(result)
                self.assertTrue(result['usage_gaps'])

    def test_inline_counterless_terminal_payload_is_not_erased_with_summary(self):
        self.solo()
        metadata = json.loads((HERE / 'fixtures/fresh-result-metadata.json').read_text())
        terminal = dict(type='result', session_id='stranger', errors=[])
        self.output(json.dumps(metadata) + '\n' + json.dumps(terminal))
        envelopes, gaps = self.evidence.claude_envelopes(self.f.out)
        self.assertEqual(list(envelopes), ['stranger'])
        self.assertEqual(gaps, [])
        result = self.f.recorded_good_product(expected_return=2)
        self.assert_stopped(result)
        self.assertTrue(any('without usage' in gap for gap in result['usage_gaps']), result)

    def test_new_inventory_is_private_shared_and_sealed_with_inherited_inputs(self):
        app = self.f.app
        self.assertIs(app.frame.usage.evidence, self.evidence)
        self.assertIs(self.evidence.claude_envelopes.func, r.discovery.claude_envelopes)
        historical = r.load('historical_evidence0244_test', HERE.parent / '0234/evidence.py')
        self.assertIsNot(historical, self.evidence)
        self.assertEqual(historical.claude_envelopes.__module__, 'historical_evidence0244_test')
        other = fixtures.ApparatusTests(); other.setUp()
        try:
            self.assertIsNot(other.app.frame.cell_run.evidence, self.evidence)
            self.assertIs(other.app.frame.usage.evidence, other.app.frame.cell_run.evidence)
            before = other.app.frame.cell_run.evidence.claude_envelopes
            with patch.object(self.evidence, 'claude_envelopes', return_value=({}, ['sentinel'])):
                self.assertIs(other.app.frame.cell_run.evidence.claude_envelopes, before)
        finally:
            other.doCleanups()
        paths = app.inputs()
        for path in (HERE / 'runner.py', HERE / 'capture_discovery.py',
                     HERE.parent / '0242/runner.py', HERE.parent / '0242/policy.py',
                     HERE.parent / '0242/peer.py', HERE.parent / '0241/capture_discovery.py'):
            self.assertEqual(paths[str(path)], r.digest(path))
        original = r.digest
        for target in (HERE / 'runner.py', HERE / 'capture_discovery.py'):
            with self.subTest(target=target), patch.object(r, 'digest', side_effect=lambda path:
                    'changed' if path == target else original(path)):
                self.assertNotEqual(app.inputs(), paths)
        frozen = r.load('independent_runner0242_test', HERE.parent / '0242/runner.py')
        previous = frozen.Runner(self.f.runtime)
        self.assertIs(previous.frame.cell_run.evidence.claude_envelopes.func,
                      frozen.discovery.claude_envelopes)
        self.assertIsNot(previous.frame.cell_run.evidence.claude_envelopes.func,
                         self.evidence.claude_envelopes.func)


def load_tests(loader, tests, pattern):
    for name in loader.getTestCaseNames(prior.InvocationTests):
        if name != 'test_new_policy_and_exact_prior_capture_are_wired_and_sealed':
            tests.addTest(prior.InvocationTests(name))
    return prior.load_tests(loader, tests, pattern)


if __name__ == '__main__':
    unittest.main(verbosity=2)
