"""Regression checks for pre-draw review findings; no native model calls."""
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('native0197_test', HERE / 'native.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class NativeOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='0197-runner-test-', dir=native.SCRATCH)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'home'
        (self.home / 'sessions').mkdir(parents=True)
        self.old = self.home / 'sessions/old.jsonl'
        self.old.write_text(json.dumps({'type': 'turn_context', 'payload': {'model': 'gpt-6-astra', 'effort': 'high', 'sandbox_policy': {'type': 'danger-full-access'}}}) + '\n')
        self.calls = 0
        self.exit_code = 0
        self.message = ''
        self.tool = False
        self.sandbox = 'read-only'
        self.patches = [patch.object(native, 'E', self.root / 'evidence'), patch.object(native.controller, 'execute', self.execute)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def execute(self, plan, out):
        self.calls += 1
        context = {'type': 'turn_context', 'payload': {'model': 'gpt-6-astra', 'effort': 'high', 'sandbox_policy': {'type': self.sandbox}}}
        with self.old.open('a') as stream:
            stream.write(json.dumps(context) + '\n')
        events = [{'type': 'thread.started', 'thread_id': 'same-thread'}]
        if self.message:
            events.append({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': self.message}})
        if self.tool:
            events.append({'type': 'item.completed', 'item': {'type': 'command_execution', 'command': 'forbidden'}})
        (out / 'stdout').write_text('\n'.join(json.dumps(e) for e in events))
        return dict(wrapper_return_seconds=1, exit_code=self.exit_code, owned_writers_quiescent=True, error=None)

    def invoke(self):
        return native.invoke('test-call', 'same packet', self.root, home=self.home, resume='same-thread', review=True, budget=600)

    def test_only_new_context_and_cached_empty_result(self):
        answer, meta = self.invoke()
        self.assertEqual(answer, '')
        self.assertEqual(len(meta['contexts']), 1)
        self.assertFalse(meta['infrastructure_failure'])
        self.invoke()
        self.assertEqual(self.calls, 1)

    def test_budget_is_scored_and_not_retried(self):
        self.exit_code = 124
        _, meta = self.invoke()
        self.assertTrue(meta['budget_exhausted'])
        self.invoke()
        self.assertEqual(self.calls, 1)

    def test_tool_attempt_is_retained_fidelity_failure(self):
        self.tool = True
        _, meta = self.invoke()
        self.assertFalse(meta['no_tool_fidelity'])
        self.assertEqual(meta['tool_events'], 1)

    def test_transport_failure_is_retained_and_never_retried(self):
        self.exit_code = 1
        with self.assertRaises(RuntimeError):
            self.invoke()
        with self.assertRaises(RuntimeError):
            self.invoke()
        self.assertEqual(self.calls, 1)

    def test_wrong_effective_sandbox_blocks(self):
        self.sandbox = 'danger-full-access'
        with self.assertRaises(RuntimeError):
            self.invoke()

    def test_incomplete_stage_does_not_relaunch(self):
        (native.E / 'runs/test-call').mkdir(parents=True)
        with self.assertRaises(RuntimeError):
            self.invoke()
        self.assertEqual(self.calls, 0)


if __name__ == '__main__':
    unittest.main()
