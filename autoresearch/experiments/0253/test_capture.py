"""Synthetic checks for capture isolation and the one-dispatch boundary."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('probe0253_tests', HERE / 'probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
runner = probe.runner


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        (self.out / 'home/.claude').mkdir(parents=True)
        self.plan = {'env': {'HOME': '/home/participant', 'CLAUDE_CODE_EFFORT_LEVEL': 'max'},
                     'argv': ['claude', '-p', '--effort', 'max', 'original prompt'],
                     'wall_seconds': 5400, 'image': 'original immutable image'}
        runner.write(self.out / 'plan.json', self.plan)
        self.seal = {'inputs': {'original': 'bound'},
                     'prepared': {'plan.json': runner.digest(self.out / 'plan.json'), 'prompt.txt': 'same'}}
        runner.write(self.out / 'seal.json', self.seal)
        self.app = object.__new__(runner.Runner)
        self.checked = []
        self.app.unchanged = self.checked.append

    def prepare(self, config='claude'):
        with patch.object(runner.legacy.Runner, 'prepare', return_value=self.out):
            return self.app.prepare('s01', 'E1', 'B', config)

    def test_capture_keeps_native_launch_and_binds_only_changed_plan(self):
        self.prepare()
        plan = runner.read(self.out / 'plan.json')
        added = {key: plan['env'].pop(key) for key in runner.CAPTURE_ENV}
        self.assertEqual(plan, self.plan)
        self.assertEqual(added, runner.CAPTURE_ENV)
        self.assertEqual({added[key] for key in ('OTEL_LOGS_EXPORTER', 'OTEL_METRICS_EXPORTER',
                                                'OTEL_TRACES_EXPORTER')}, {'none'})
        self.assertEqual((self.out / 'home/.claude/api-bodies').stat().st_mode & 0o777, 0o700)
        seal = runner.read(self.out / 'seal.json')
        self.assertEqual(seal['inputs'], self.seal['inputs'])
        self.assertEqual(seal['prepared']['prompt.txt'], 'same')
        self.assertEqual(seal['prepared']['plan.json'], runner.digest(self.out / 'plan.json'))
        self.assertEqual(self.checked, [self.out])

    def test_codex_is_byte_identical(self):
        before = {p.name: p.read_bytes() for p in self.out.glob('*.json')}
        self.prepare('codex')
        self.assertEqual({p.name: p.read_bytes() for p in self.out.glob('*.json')}, before)
        self.assertFalse((self.out / 'home/.claude/api-bodies').exists())
        self.assertFalse(self.checked)

    def test_competing_telemetry_refuses_instead_of_overwriting(self):
        self.plan['env']['OTEL_EXPORTER_OTLP_ENDPOINT'] = 'https://example.invalid'
        runner.write(self.out / 'plan.json', self.plan)
        with self.assertRaisesRegex(ValueError, 'competing telemetry'):
            self.prepare()
        self.assertEqual(runner.read(self.out / 'plan.json'), self.plan)
        self.assertEqual(runner.read(self.out / 'seal.json'), self.seal)

    def test_existing_body_directory_is_not_adopted(self):
        body = self.out / 'home/.claude/api-bodies'
        body.mkdir()
        retained = body / 'prior.response.json'
        retained.write_text('existing bytes')
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual(retained.read_text(), 'existing bytes')
        self.assertEqual(runner.read(self.out / 'plan.json'), self.plan)

    def test_capture_code_is_a_prospective_input(self):
        with patch.object(runner.legacy.Runner, 'inputs', return_value={'inherited': 'digest'}):
            bound = self.app.inputs()
        self.assertEqual(bound['inherited'], 'digest')
        self.assertEqual(bound[str(HERE / 'runner.py')], runner.digest(HERE / 'runner.py'))

    def test_auth_refusal_is_recorded_and_cannot_be_redispatched(self):
        bindings = self.out / 'bindings.json'
        bindings.write_text(json.dumps({'frozen': 'unchanged'}))
        with patch.object(probe, 'Probe') as constructor, contextlib.redirect_stdout(io.StringIO()):
            app = constructor.return_value
            app.runtime = {'output': str(self.out / 'out')}
            app.inputs.return_value = {'frozen': 'unchanged'}
            app.preflight.return_value = (None, 'fixed-auth-lifetime-refused')
            self.assertEqual(probe.run(self.out / 'runtime.json', bindings), 2)
            app.prepare.assert_not_called()
            result = runner.read(self.out / ('result-' + probe.registration['name'] + '.json'))
            self.assertEqual(result['status'], 'STOP')
            self.assertIn('fixed-auth-lifetime-refused', result['error'])
            with self.assertRaises(FileExistsError):
                probe.run(self.out / 'runtime.json', bindings)
            self.assertEqual(app.preflight.call_count, 1)

    def run_with_gate(self, *, drift=False, quota_fault=False, peer_status='MATCH'):
        bindings = self.out / 'bindings.json'
        bindings.write_text(json.dumps({'frozen': 'unchanged'}))
        (self.out / 'final.txt').write_text('NATIVE_PARENT_READY')
        (self.out / 'home/.claude/api-bodies').mkdir()
        (self.out / 'home/.claude/api-bodies/index.jsonl').write_text('')
        with patch.object(probe, 'Probe') as constructor, \
                patch.object(probe.accounting, 'audit', return_value={'status': 'MATCH'}), \
                patch.object(probe.policy, 'receipts', return_value=([], [])), \
                patch.object(probe.policy, 'check', return_value={'status': peer_status}), \
                contextlib.redirect_stdout(io.StringIO()):
            app = constructor.return_value
            app.runtime = {'output': str(self.out / 'out')}
            app.inputs.return_value = {'frozen': 'unchanged'}
            app.preflight.return_value = ({'identity': 'bound'}, None)
            app.prepare.return_value = self.out
            app.frame.cell_run.run.return_value = {
                'owner_status': 'EXITED_0', 'identity': {'status': 'MATCH'}, 'teardown': 'CLEAN'}
            app.frame.seal_after_teardown.return_value = ('manifest', [])
            app.frame.usage.record.return_value = {'completeness': 'COMPLETE'}
            app.frame.quota.classify.return_value = {'execution': ['auth failure'] if quota_fault else []}
            app.boot_expectation.return_value = {'skills': []}
            app.boot_catalogs.return_value = {'skills': ['unexpected']} if drift else {'skills': []}
            code = probe.run(self.out / 'runtime.json', bindings)
            app.evaluate.assert_not_called()
            app.assess.assert_not_called()
        return code, runner.read(self.out / ('result-' + probe.registration['name'] + '.json'))

    def test_capture_observation_is_still_pending_independent_acceptance(self):
        code, record = self.run_with_gate()
        self.assertEqual(code, 0)
        self.assertEqual(record['status'], 'CAPTURE_OBSERVED')

    def test_catalog_drift_stops_without_product_grading(self):
        code, record = self.run_with_gate(drift=True)
        self.assertEqual(code, 2)
        self.assertFalse(record['checks']['catalog'])
        self.assertEqual(record['status'], 'STOP')

    def test_execution_auth_or_quota_fault_stops_without_product_grading(self):
        code, record = self.run_with_gate(quota_fault=True)
        self.assertEqual(code, 2)
        self.assertFalse(record['checks']['quota'])
        self.assertEqual(record['status'], 'STOP')

    def test_independent_session_policy_fault_stops_without_product_grading(self):
        code, record = self.run_with_gate(peer_status='UNVERIFIED')
        self.assertEqual(code, 2)
        self.assertFalse(record['checks']['peer_policy'])
        self.assertEqual(record['status'], 'STOP')


if __name__ == '__main__':
    unittest.main()
