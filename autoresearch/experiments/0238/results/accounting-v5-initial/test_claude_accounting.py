"""Native-accounting closure controls; no models, Docker, or original-cell writes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard = load('closure0238test', HERE / 'claude-accounting-v1.py')
legacy = load('legacyUsage0238test', HERE.parent / '0234/record_usage.py')
MODEL = 'claude-opus-5-5'
LIVE = Path('/Users/aipalm/.local/share/nx01/0239-live/staged-v1')


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + '\n')


def lines(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(value) + '\n' for value in values))


def message(session, identity, *, terminal=True, parent=None):
    event = dict(type='assistant', sessionId=session, requestId='request-' + identity,
                 message=dict(id=identity, model=MODEL, stop_reason='end_turn' if terminal else None,
                              usage=dict(input_tokens=2, cache_read_input_tokens=10,
                                         cache_creation_input_tokens=3, output_tokens=8,
                                         output_tokens_details=dict(thinking_tokens=5))))
    if parent:
        event['parentSessionId'] = parent
    return event


def result(session, count=1, *, failed=False):
    return dict(type='result', session_id=session, is_error=failed, modelUsage={MODEL: dict(
        inputTokens=2*count, cacheReadInputTokens=10*count, cacheCreationInputTokens=3*count,
        outputTokens=8*count, thinkingTokens=5*count)})


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='0238-closure-')
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.native = self.out / 'home/.claude/projects/work/owner.jsonl'
        write(self.out / 'plan.json', dict(engine='claude', config='claude', model=MODEL, arm='B'))
        lines(self.out / 'run/stdout', [dict(type='system', subtype='init', session_id='owner', model=MODEL),
                                      result('owner')])
        lines(self.native, [message('owner', 'one')])

    def audit(self):
        return guard.audit(self.out, legacy.evidence)

    def test_clean_and_provisional_snapshot_are_counted_once(self):
        provisional = message('owner', 'one', terminal=False)
        provisional['message']['usage']['output_tokens'] = 1
        provisional['message']['usage'].pop('output_tokens_details')
        lines(self.native, [provisional, message('owner', 'one')])
        answer = self.audit()
        self.assertEqual(answer['status'], 'MATCH', answer)
        self.assertEqual(answer['terminal_message_count'], 1)

    def test_missing_terminal_or_entire_carrier_is_unknown(self):
        for values in ([message('owner', 'one', terminal=False)], []):
            with self.subTest(values=bool(values)):
                lines(self.native, values)
                answer = self.audit()
                self.assertEqual(answer['status'], 'UNKNOWN', answer)
                self.assertIsNone(answer['unknown_residual']['output_tokens'])
                self.assertEqual(answer['terminal_message_count'], 0)

    def test_unbound_retry_is_unknown_even_if_aggregate_matches(self):
        lines(self.native, [message('owner', 'one'), dict(type='system', subtype='api_error',
              sessionId='owner', error=dict(message='Connection error.'))])
        self.assertEqual(self.audit()['status'], 'UNKNOWN')

    def test_explicitly_bound_terminal_request_can_close_retry(self):
        # Unlike d01's anonymous error, this synthetic error identifies the exact
        # terminal request. A successful different request cannot substitute.
        lines(self.native, [message('owner', 'one'), dict(type='system', subtype='api_error',
              sessionId='owner', requestId='request-one'), message('owner', 'two')])
        lines(self.out / 'run/stdout', [dict(type='system', subtype='api_retry', session_id='owner'),
                                      result('owner', 2)])
        self.assertEqual(self.audit()['status'], 'MATCH')
        values = legacy.evidence.lines(self.native)
        values[1]['requestId'] = 'unclosed-failed-request'
        lines(self.native, values)
        self.assertEqual(self.audit()['status'], 'UNKNOWN')

    def test_stream_only_retry_is_not_closed_by_later_success(self):
        lines(self.out / 'run/stdout', [dict(type='system', subtype='thinking_tokens',
              session_id='owner', estimated_tokens=4150),
              dict(type='system', subtype='api_retry', session_id='owner'), result('owner')])
        answer = self.audit()
        self.assertEqual(answer['status'], 'UNKNOWN')
        self.assertEqual(answer['sessions']['owner'][MODEL]['reported']['output_tokens'], 8)

    def test_peer_failed_complete_turn_then_resume_preserves_cost(self):
        peer = self.out / 'home/.claude/projects/work/peer.jsonl'
        lines(peer, [message('peer', 'first'), message('peer', 'second')])
        write(self.out / 'tmp/peer1.json', result('peer', failed=True))
        write(self.out / 'tmp/peer2.json', result('peer', 2))
        answer = self.audit()
        self.assertEqual(answer['status'], 'MATCH', answer)
        self.assertEqual(answer['sessions']['peer'][MODEL]['reported']['output_tokens'], 16)
        captured = legacy.record(self.out)
        self.assertEqual(captured['completeness'], 'COMPLETE', captured)
        self.assertEqual((captured['input_tokens'], captured['output_tokens']), (45, 24))
        # A missing attempt remains a gap after a successful later resume.
        lines(peer, [message('peer', 'first'), dict(type='system', subtype='api_error',
              sessionId='peer'), message('peer', 'second')])
        self.assertEqual(self.audit()['status'], 'UNKNOWN')

    def test_native_child_same_or_distinct_session_is_in_owner_scope(self):
        child = self.out / 'home/.claude/projects/work/owner/subagents/agent-child.jsonl'
        for session, parent in (('owner', None), ('child', 'owner')):
            with self.subTest(session=session):
                lines(child, [message(session, 'child-one', parent=parent)])
                lines(self.out / 'run/stdout', [result('owner', 2)])
                answer = self.audit()
                self.assertEqual(answer['status'], 'MATCH', answer)
                self.assertEqual(answer['sessions']['owner'][MODEL]['terminal']['output_tokens'], 16)
                lines(child, [message(session, 'child-one', parent=parent),
                      dict(type='system', subtype='api_error', sessionId=session)])
                self.assertEqual(self.audit()['status'], 'UNKNOWN')

    def test_reasoning_counter_must_reconcile_without_double_counting_output(self):
        event = result('owner')
        event['modelUsage'][MODEL]['thinkingTokens'] = 6
        lines(self.out / 'run/stdout', [event])
        answer = self.audit()
        self.assertEqual(answer['status'], 'UNKNOWN')
        self.assertEqual(answer['sessions']['owner'][MODEL]['terminal']['output_tokens'], 8)

    def test_real_retained_short_long_and_d01_are_read_only_controls(self):
        for area, name, expected in [('out-smoke', 's01-claude-b-short', 'MATCH'),
                                     ('out-smoke', 's02-claude-b-long', 'MATCH'),
                                     ('out-development', 'd01-claude-c', 'UNKNOWN')]:
            with self.subTest(name=name):
                original = LIVE / area / name
                self.assertTrue(original.is_dir(), 'required retained control missing: ' + str(original))
                selected = [original / 'plan.json', original / 'run/stdout', original / 'usage.json']
                selected += list((original / 'home/.claude/projects').rglob('*.jsonl'))
                hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in selected}
                with tempfile.TemporaryDirectory(prefix='0238-replay-') as tmp:
                    copied = Path(tmp)
                    for source in selected:
                        target = copied / source.relative_to(original)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(source, target)
                    answer = guard.audit(copied, legacy.evidence)
                    captured = legacy.record(copied)
                    self.assertEqual(answer['status'], expected, answer)
                    retained = json.loads((original / 'usage.json').read_text())
                    self.assertEqual((captured['input_tokens'], captured['output_tokens']),
                                     (retained['input_tokens'], retained['output_tokens']))
                    if name == 'd01-claude-c':
                        self.assertEqual(captured['completeness'], 'COMPLETE')
                        self.assertTrue(any('API error without terminal' in gap for gap in answer['gaps']))
                        self.assertIsNone(answer['unknown_residual']['reasoning_tokens'])
                self.assertEqual(hashes, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in selected})


if __name__ == '__main__':
    unittest.main()
