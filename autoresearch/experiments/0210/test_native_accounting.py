"""Regressions for the native copied-context counterexample observed in 0210."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '0208'))
from test_accounting import event, meta, usage
from native_accounting import AccountingError, Rollouts


class NativeForkTests(unittest.TestCase):
    def rows(self):
        parent = [meta('owner'), event('task_started', turn_id='p'), usage(40, 4),
                  event('task_complete', turn_id='p')]
        child_meta = meta('child', 'owner')
        child_meta['payload'].update(forked_from_id='owner', parent_thread_id='owner')
        child = [child_meta, copy.deepcopy(parent[0]), copy.deepcopy(parent[1]),
                 {'type': 'turn_context', 'payload': {'turn_id': 'p'}},
                 event('thread_settings_applied', thread_id='child'),
                 event('task_started', turn_id='c'), usage(100, 10),
                 event('task_complete', turn_id='c')]
        return parent, child

    def run_rows(self, parent, child):
        with tempfile.TemporaryDirectory() as tmp:
            for name, rows in [('owner', parent), ('child', child)]:
                (Path(tmp)/(name+'.jsonl')).write_text(''.join(json.dumps(row)+'\n' for row in rows))
            meter = Rollouts(tmp, 'owner', input_limit=1000, output_limit=100,
                             dispatch_limit=5, stale_seconds=float('inf'), started=time.monotonic())
            return meter.finish(time.monotonic())

    def test_native_copy_does_not_duplicate_parent_dispatch_or_tokens(self):
        result = self.run_rows(*self.rows())
        self.assertEqual((result['dispatches'], result['totals']['input_tokens'],
                          result['totals']['output_tokens']), (2, 140, 14))

    def test_wrong_boundary_thread(self):
        p, c = self.rows(); c[4]['payload']['thread_id'] = 'owner'
        with self.assertRaises(AccountingError): self.run_rows(p, c)

    def test_unknown_inherited_turn(self):
        p, c = self.rows(); c[3]['payload']['turn_id'] = 'unaccounted'
        with self.assertRaises(AccountingError): self.run_rows(p, c)

    def test_never_discard_inherited_usage(self):
        p, c = self.rows(); c.insert(4, usage(5, 1))
        with self.assertRaises(AccountingError): self.run_rows(p, c)

    def test_missing_child_usage(self):
        p, c = self.rows(); del c[6]
        with self.assertRaises(AccountingError): self.run_rows(p, c)

    def test_child_total_cannot_silently_include_parent(self):
        p, c = self.rows(); c[6]['payload']['info']['total_token_usage']['input_tokens'] += 40
        c[6]['payload']['info']['total_token_usage']['total_tokens'] += 40
        with self.assertRaises(AccountingError): self.run_rows(p, c)

    def test_missing_fork_boundary(self):
        p, c = self.rows(); del c[4]
        with self.assertRaises(AccountingError): self.run_rows(p, c)


if __name__ == '__main__': unittest.main()
