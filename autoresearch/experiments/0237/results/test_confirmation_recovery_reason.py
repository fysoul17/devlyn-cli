"""Focused derived-ledger regression; no models, evaluator, or participant writes."""
import json
from pathlib import Path
import runpy
from tempfile import TemporaryDirectory
import unittest

HERE = Path(__file__).resolve().parent
MODULE = runpy.run_path(str(HERE / 'refresh-confirmation-cells.py'))
ORIGINAL = 'f02-CF-CONFIG-claude-C-r1'
REPLACEMENT = ORIGINAL + '-auth1'


class RecoveryReason(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix='confirmation-reason-')
        self.addCleanup(temporary.cleanup)
        self.out = Path(temporary.name)
        self.slot = dict(cell=ORIGINAL, task='CF-CONFIG', config='claude', arm='C')
        self.original_guard = dict(reason='Original token expired before dispatch')
        (self.out / ('not-dispatched-' + ORIGINAL + '.json')).write_text(json.dumps(self.original_guard))

    def state(self, *, finals=None, events=None):
        return MODULE['slot_state'](self.slot, self.out, events or {}, finals or {},
                                    dict(status='MATCH'), {REPLACEMENT: self.slot})

    def assert_original_preserved(self, state):
        self.assertEqual(state['original_attempt']['reason'], self.original_guard)
        self.assertEqual(state['original_attempt']['lifecycle'], 'NOT_DISPATCHED')
        self.assertIsNone(state['original_attempt']['costs'])

    def test_no_replacement_event_retains_original_reason(self):
        state = self.state()
        self.assertEqual(state['reason'], self.original_guard)
        self.assert_original_preserved(state)

    def test_pending_replacement_drops_original_reason(self):
        state = self.state(events={REPLACEMENT: [dict(event='START')]})
        self.assertEqual(state['lifecycle'], 'PENDING_FINAL_VERDICT')
        self.assertNotIn('reason', state)
        self.assertIsNone(state['costs'])
        self.assert_original_preserved(state)

    def test_final_without_reason_drops_original_reason(self):
        final = dict(self.slot, cell=REPLACEMENT, status='PRODUCT_INCOMPLETE')
        state = self.state(finals={REPLACEMENT: final})
        self.assertEqual(state['lifecycle'], 'FINAL_VERDICT')
        self.assertEqual(state['status'], 'PRODUCT_INCOMPLETE')
        self.assertNotIn('reason', state)
        self.assert_original_preserved(state)

    def test_final_with_reason_uses_effective_reason(self):
        final = dict(self.slot, cell=REPLACEMENT, status='STOP', reason='Effective attempt usage missing')
        state = self.state(finals={REPLACEMENT: final})
        self.assertEqual(state['reason'], final['reason'])
        self.assertEqual(state['replacement_attempt']['reason'], final['reason'])
        self.assert_original_preserved(state)

    def test_replacement_guard_uses_its_own_reason(self):
        guard = dict(reason='Replacement blocked by a different preflight condition')
        (self.out / ('not-dispatched-' + REPLACEMENT + '.json')).write_text(json.dumps(guard))
        state = self.state()
        self.assertEqual(state['lifecycle'], 'NOT_DISPATCHED')
        self.assertEqual(state['reason'], guard)
        self.assertIsNone(state['costs'])
        self.assert_original_preserved(state)

    def test_actual_completed_f02_preserves_raw_failure_and_original_guard(self):
        ledger = json.loads((HERE / 'confirmation-cells.json').read_text())
        runtime = json.loads(Path(ledger['runtime']['path']).read_text())
        out = Path(runtime['output'])
        final = json.loads((out / ('verdict-' + REPLACEMENT + '.json')).read_text())
        state = MODULE['slot_state'](self.slot, out, {}, {REPLACEMENT: final},
                                     ledger['authentication_recovery'], {REPLACEMENT: self.slot})
        self.assertEqual(state['effective_cell'], REPLACEMENT)
        self.assertEqual(state['status'], 'PRODUCT_INCOMPLETE')
        self.assertNotIn('reason', state)
        self.assertEqual(state['original_attempt']['reason'],
                         json.loads((out / ('not-dispatched-' + ORIGINAL + '.json')).read_text()))
        self.assertTrue(final['source_check_pass'])
        self.assertFalse(final['delivery_pass'])
        self.assertEqual(final['usage'], 'COMPLETE')


if __name__ == '__main__':
    unittest.main(verbosity=2)
