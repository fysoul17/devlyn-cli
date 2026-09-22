"""Non-model controls for fresh native-shaped rollout observation."""
import json
from pathlib import Path
import tempfile
import unittest

from accounting import AccountingError, Rollouts


def meta(sid, parent=None):
    source = 'exec' if parent is None else {'subagent': {'thread_spawn': {'parent_thread_id': parent}}}
    return dict(type='session_meta', payload=dict(id=sid, source=source))


def event(kind, **fields):
    return dict(type='event_msg', payload=dict(type=kind, **fields))


def tokens(i, o):
    return dict(input_tokens=i, cached_input_tokens=i // 2, cache_write_input_tokens=0,
                output_tokens=o, reasoning_output_tokens=o // 2, total_tokens=i + o)


def usage(i, o, previous=None):
    total = tokens(i, o)
    last = {k: v - (previous or {}).get(k, 0) for k, v in total.items()}
    return event('token_count', info=dict(total_token_usage=total, last_token_usage=last))


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.meter = Rollouts(self.root, 'owner', input_limit=1000, output_limit=100,
                             dispatch_limit=5, stale_seconds=2, started=0)

    def append(self, sid, *events):
        with (self.root / (sid + '.jsonl')).open('a') as stream:
            for row in events:
                stream.write(json.dumps(row) + '\n')

    def start(self, sid='owner', parent=None):
        self.append(sid, meta(sid, parent), event('task_started', turn_id=sid + '-1'))

    def test_interleaved_tree_deduplicates_and_reports_subsets(self):
        self.start(); self.start('child', 'owner'); self.start('grandchild', 'child')
        for sid in ('owner', 'child', 'grandchild'):
            self.append(sid, usage(100, 10))
        first = self.meter.poll(.1)
        self.assertEqual(first['totals'], tokens(300, 30))
        self.assertEqual(first['dispatches'], 3)
        for sid in ('owner', 'child', 'grandchild'):
            self.append(sid, usage(100, 10), usage(200, 20, tokens(100, 10)),
                        event('task_complete', turn_id=sid + '-1'))
        final = self.meter.finish(.2)
        self.assertEqual(final['totals'], tokens(600, 60))
        self.assertFalse(final['exceeded'])

    def test_redispatch_counts_again_without_recounting_history(self):
        self.start()
        self.append('owner', usage(100, 10), event('task_complete', turn_id='owner-1'),
                    event('task_started', turn_id='owner-2'), usage(200, 20, tokens(100, 10)),
                    event('task_complete', turn_id='owner-2'))
        result = self.meter.finish(.1)
        self.assertEqual(result['dispatches'], 2)
        self.assertEqual(result['totals'], tokens(200, 20))

    def test_partial_line_waits_but_blocks_finish(self):
        self.start(); self.append('owner', usage(100, 10))
        path = self.root / 'owner.jsonl'
        raw = json.dumps(event('task_complete', turn_id='owner-1'))
        with path.open('a') as f: f.write(raw[:10])
        self.meter.poll(.1)
        with path.open('a') as f: f.write(raw[10:] + '\n')
        self.assertEqual(self.meter.finish(.2)['dispatches'], 1)
        with path.open('a') as f: f.write('{')
        with self.assertRaisesRegex(AccountingError, 'incomplete'): self.meter.finish(.3)

    def test_duplicate_does_not_extend_staleness(self):
        self.start(); self.append('owner', usage(100, 10)); self.meter.poll(.1)
        self.append('owner', usage(100, 10)); self.meter.poll(1.9)
        with self.assertRaisesRegex(AccountingError, 'stale'): self.meter.poll(2.1)

    def test_same_total_with_changed_last_is_not_a_duplicate(self):
        self.start(); self.append('owner', usage(100, 10)); self.meter.poll(.1)
        row = usage(100, 10)
        row['payload']['info']['last_token_usage'] = tokens(50, 5)
        self.append('owner', row)
        with self.assertRaisesRegex(AccountingError, 'inconsistent duplicate'): self.meter.poll(.2)

    def test_silent_owner(self):
        with self.assertRaisesRegex(AccountingError, 'missing owner'): self.meter.poll(2)

    def test_silent_active_session(self):
        self.start(); self.meter.poll(.1)
        with self.assertRaisesRegex(AccountingError, 'stale'): self.meter.poll(2.1)

    def test_metadata_without_dispatch_becomes_stale(self):
        self.append('owner', meta('owner')); self.meter.poll(.1)
        with self.assertRaisesRegex(AccountingError, 'stale'): self.meter.poll(2.1)

    def test_empty_dispatch_cannot_finish(self):
        for turn in ('', None, 0, False):
            with self.subTest(turn=turn):
                path = self.root / 'owner.jsonl'; path.unlink(missing_ok=True)
                self.append('owner', meta('owner'), event('task_started', turn_id=turn))
                meter = Rollouts(self.root, 'owner', input_limit=1000, output_limit=100,
                                 dispatch_limit=5, stale_seconds=2, started=0)
                with self.assertRaisesRegex(AccountingError, 'dispatch id'): meter.finish(.1)

    def test_non_integer_last_usage(self):
        self.start(); row = usage(100, 10)
        row['payload']['info']['last_token_usage']['input_tokens'] = 100.0
        self.append('owner', row)
        with self.assertRaisesRegex(AccountingError, 'last usage'): self.meter.poll(.1)

    def test_aborted_turn_keeps_measured_usage_in_nested_directory(self):
        self.start(); self.append('owner', usage(100, 10), event('turn_aborted', turn_id='owner-1'))
        nested = self.root / '2026/09/22'; nested.mkdir(parents=True)
        (self.root / 'owner.jsonl').rename(nested / 'owner.jsonl')
        self.assertEqual(self.meter.finish(.1)['totals'], tokens(100, 10))

    def test_late_usage_after_terminal_blocks(self):
        self.start(); self.append('owner', usage(100, 10), event('task_complete', turn_id='owner-1'),
                                 usage(200, 20, tokens(100, 10)))
        with self.assertRaisesRegex(AccountingError, 'without active'): self.meter.poll(.1)

    def test_counter_subset_semantics(self):
        for key, value in [('cached_input_tokens', 101), ('reasoning_output_tokens', 11), ('total_tokens', 0)]:
            with self.subTest(key=key):
                (self.root / 'owner.jsonl').unlink(missing_ok=True)
                self.start(); row = usage(100, 10)
                row['payload']['info']['total_token_usage'][key] = value
                self.append('owner', row)
                meter = Rollouts(self.root, 'owner', input_limit=1000, output_limit=100,
                                 dispatch_limit=5, stale_seconds=2, started=0)
                with self.assertRaisesRegex(AccountingError, 'semantics'): meter.poll(.1)

    def test_missing_lineage_and_cycle(self):
        for parent in ('absent', 'child'):
            with self.subTest(parent=parent):
                (self.root / 'child.jsonl').unlink(missing_ok=True)
                self.append('child', meta('child', parent))
                meter = Rollouts(self.root, 'owner', input_limit=1000, output_limit=100,
                                 dispatch_limit=5, stale_seconds=2, started=0)
                with self.assertRaises(AccountingError): meter.poll(.1)

    def test_inherited_baseline_is_unknown(self):
        self.start(); self.append('owner', usage(200, 20, tokens(100, 10)))
        with self.assertRaisesRegex(AccountingError, 'baseline'): self.meter.poll(.1)

    def test_counter_regression_is_sticky(self):
        self.start(); self.append('owner', usage(100, 10)); self.meter.poll(.1)
        self.append('owner', usage(50, 5))
        with self.assertRaisesRegex(AccountingError, 'regression'): self.meter.poll(.2)
        with self.assertRaisesRegex(AccountingError, 'regression'): self.meter.poll(.3)

    def test_replacement_and_truncation(self):
        for replace in (False, True):
            with self.subTest(replace=replace), tempfile.TemporaryDirectory() as root:
                path = Path(root) / 'owner.jsonl'
                path.write_text(json.dumps(meta('owner')) + '\n')
                meter = Rollouts(root, 'owner', input_limit=1000, output_limit=100,
                                 dispatch_limit=5, stale_seconds=2, started=0)
                meter.poll(.1)
                if replace:
                    new = Path(root) / 'new'; new.write_text(path.read_text()); new.replace(path)
                else: path.write_text('')
                with self.assertRaisesRegex(AccountingError, 'replaced or truncated'): meter.poll(.2)

    def test_token_and_dispatch_breaches_report_actual_overshoot(self):
        for i, o in ((1001, 100), (1000, 101)):
            with self.subTest(i=i, o=o):
                (self.root / 'owner.jsonl').unlink(missing_ok=True)
                self.start(); self.append('owner', usage(i, o))
                meter = Rollouts(self.root, 'owner', input_limit=1000, output_limit=100,
                                 dispatch_limit=5, stale_seconds=2, started=0)
                result = meter.poll(.1)
                self.assertTrue(result['exceeded'])
                self.assertEqual(result['overshoot']['input_tokens'], max(0, i - 1000))
                self.assertEqual(result['overshoot']['output_tokens'], max(0, o - 100))
        (self.root / 'owner.jsonl').unlink()
        self.start()
        for n in range(5): self.start('c' + str(n), 'owner')
        self.assertEqual(self.meter.poll(.1)['overshoot']['dispatches'], 1)

    def test_exact_ceiling_is_allowed(self):
        self.start(); self.append('owner', usage(1000, 100), event('task_complete', turn_id='owner-1'))
        self.assertFalse(self.meter.finish(.1)['exceeded'])

    def test_unmeasured_and_unfinished_dispatches_block(self):
        self.start(); self.append('owner', event('task_complete', turn_id='owner-1'))
        with self.assertRaisesRegex(AccountingError, 'terminal without measured'): self.meter.finish(.1)

    def test_empty_rollout_blocks_terminal(self):
        self.start(); self.append('owner', usage(100, 10), event('task_complete', turn_id='owner-1'))
        (self.root / 'child.jsonl').touch()
        with self.assertRaisesRegex(AccountingError, 'incomplete'): self.meter.finish(.1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
