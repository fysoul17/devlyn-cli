"""Model-free tests of the 0232 apparatus: python3 -B -m unittest discover -s autoresearch/experiments/0232 -p 'test_*.py'.

Container cases need APPARATUS_IMAGE (the devlyn-0231 image id) and APPARATUS_CONTROL (the built 0232 control tree, which
needs the frozen I package). obligations.py is byte-identical to 0231's; its fixtures build real runs with the 0231
bundle package and stay in 0231's suite.
"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name + 'test0232', HERE / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


traces, usage, locate, decide, quota, compliance = (
    load(n) for n in ('trace_usage', 'record_usage', 'locate', 'decide', 'quota', 'compliance'))
USAGE = dict(input_tokens=100, cached_input_tokens=40, cache_write_input_tokens=0, output_tokens=7, reasoning_output_tokens=2)


def claude_usage(input_=10, cache_read=200, cache_write=30, output=3):
    """A Claude modelUsage entry; its processed input is input + cache reads + cache writes (240 by default)."""
    return dict(inputTokens=input_, cacheReadInputTokens=cache_read, cacheCreationInputTokens=cache_write, outputTokens=output)


def review(out, name, engine, events, meta=None):
    """A review launcher record as the fixed interface lays it out: home/.devlyn/reviews/<UTC timestamp>-<engine>/."""
    folder = out / 'home/.devlyn/reviews' / f'{name}-{engine}'
    folder.mkdir(parents=True)
    (folder / 'prompt.txt').write_text('review request\n')
    (folder / 'stdout').write_text(''.join(json.dumps(e) + '\n' for e in events))
    (folder / 'stderr').write_text('')
    if meta is not None:
        (folder / 'meta.json').write_text(json.dumps(meta))
    return folder


def claude_review(session, entry, text='No findings.', is_error=False, model='claude-opus-5-5'):
    """A Claude reviewer's stream-json: its init and final result."""
    return [dict(type='system', subtype='init', model=model, session_id=session),
            dict(type='result', session_id=session, is_error=is_error, result=text, modelUsage={model: entry})]


def codex_review(thread, text='No findings.'):
    """A Codex reviewer's JSONL events: its thread and final agent message."""
    return [dict(type='thread.started', thread_id=thread), dict(type='item.completed', item=dict(type='agent_message', text=text))]


def write_trace(root, rollout, events, payloads, *, manifest=True):
    folder = root / f'trace-t-{rollout}'
    (folder / 'payloads').mkdir(parents=True)
    if manifest:
        (folder / 'manifest.json').write_text(json.dumps(dict(schema_version=1, rollout_id=rollout, root_thread_id=rollout,
                                                               raw_event_log='trace.jsonl', payloads_dir='payloads')))
    for name, value in payloads.items():
        (folder / 'payloads' / name).write_text(json.dumps(value))
    (folder / 'trace.jsonl').write_text(''.join(line if isinstance(line, str) else json.dumps(dict(payload=line)) + '\n'
                                                for line in events))
    return folder


def ref(name):
    return dict(path=f'payloads/{name}')


def inference(call, thread, model='gpt-6-astra', response='r.json'):
    return [dict(type='inference_started', inference_call_id=call, thread_id=thread, model=model),
            dict(type='inference_completed', inference_call_id=call, response_payload=ref(response))]


class Traces(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)

    def test_complete_rollout_counts_once_and_reproduces_the_footer(self):
        write_trace(self.root, 'R', [dict(type='thread_started', thread_id='R', agent_path='/root', metadata_payload=ref('m.json')),
                                     *inference('c1', 'R'), dict(type='rollout_ended', status='completed')],
                    {'m.json': dict(model='gpt-6-astra'), 'r.json': dict(token_usage=USAGE)})
        measured = traces.usage(self.root)
        self.assertEqual(measured['gaps'], [])
        self.assertEqual(measured['totals']['gpt-6-astra']['output_tokens'], 7)
        self.assertEqual(measured['rollouts'][0]['footer_tokens'], 100 - 40 + 7)

    def test_child_thread_models_and_usage_are_attributed(self):
        write_trace(self.root, 'R', [*inference('c1', 'R'), *inference('c2', 'K', model='gpt-6-sol', response='k.json'),
                                     dict(type='rollout_ended', status='completed')],
                    {'r.json': dict(token_usage=USAGE), 'k.json': dict(token_usage=USAGE)})
        self.assertEqual(traces.models(self.root), {'R': {'gpt-6-astra'}, 'K': {'gpt-6-sol'}})
        self.assertEqual(set(traces.usage(self.root)['totals']), {'gpt-6-astra', 'gpt-6-sol'})

    def test_interrupted_torn_and_missing_evidence_are_named_gaps_never_zero(self):
        write_trace(self.root, 'R', [*inference('c1', 'R'),
                                     dict(type='inference_started', inference_call_id='c2', thread_id='R', model='gpt-6-astra'),
                                     *inference('c3', 'R', response='absent.json'), '{"torn\n'],
                    {'r.json': dict(token_usage=USAGE)})
        measured = traces.usage(self.root)
        gaps = ' | '.join(measured['gaps'])
        for expected in ('c2 started without completed usage', 'c3 completed without usage', 'torn line', 'rollout did not end'):
            self.assertIn(expected, gaps)
        self.assertEqual(measured['totals']['gpt-6-astra']['output_tokens'], 7)  # the known inference still counts
        self.assertIsNone(measured['rollouts'][0]['footer_tokens'])

    def test_a_compaction_request_is_a_named_gap(self):  # shape of the 2026-10-04 compaction probe
        write_trace(self.root, 'R', [*inference('c1', 'R'),
                                     dict(type='compaction_request_started', compaction_request_id='compaction_request:1', thread_id='R', model='gpt-6-astra'),
                                     dict(type='compaction_request_completed', compaction_request_id='compaction_request:1', response_payload=ref('cr.json')),
                                     dict(type='rollout_ended', status='completed')],
                    {'r.json': dict(token_usage=USAGE), 'cr.json': dict(output_items=[])})
        self.assertIn('compaction request compaction_request:1 has no native usage', ' | '.join(traces.usage(self.root)['gaps']))

    def test_an_unfinished_compaction_request_is_a_named_gap(self):
        write_trace(self.root, 'R', [*inference('c1', 'R'),
                                     dict(type='compaction_request_started', compaction_request_id='compaction_request:9', thread_id='R'),
                                     dict(type='rollout_ended', status='completed')], {'r.json': dict(token_usage=USAGE)})
        self.assertIn('compaction request compaction_request:9 has no native usage', ' | '.join(traces.usage(self.root)['gaps']))

    def test_host_git_never_fetches_lazily_or_follows_replacements(self):
        self.assertEqual((locate.ENV.get('GIT_NO_LAZY_FETCH'), locate.ENV.get('GIT_NO_REPLACE_OBJECTS')), ('1', '1'))

    def test_missing_manifest_is_a_gap(self):
        write_trace(self.root, 'R', [], {}, manifest=False)
        self.assertIn('missing or unreadable manifest', traces.usage(self.root)['gaps'][0])


class Binding(unittest.TestCase):
    """Usage on the shared inventory: bound once, attempted calls inventoried, every disagreement a named gap."""

    def setUp(self):
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)
        for name in ('cell/trace', 'cell/work/.devlyn', 'home/.codex/sessions', 'home/.claude/projects', 'tmp', 'run'):
            (self.out / name).mkdir(parents=True)
        init = dict(type='system', subtype='init', model='claude-opus-5-5', session_id='OWNER')
        result = dict(type='result', session_id='OWNER', modelUsage={'claude-opus-5-5': claude_usage()})
        (self.out / 'run/stdout').write_text(json.dumps(init) + '\n' + json.dumps(result) + '\n')
        (self.out / 'plan.json').write_text(json.dumps(dict(engine='claude', config='claude', model='claude-opus-5-5', arm='I')))

    def judge(self, session, footer, round_=0):
        header = ('OpenAI Codex v0.156.1\n--------\nworkdir: /cell/work\nmodel: gpt-6-astra\nprovider: openai\n'
                  f'approval: never\nsandbox: read-only\nreasoning effort: high\nsession id: {session}\n--------\nuser\nVERIFY\n')
        (self.out / f'cell/work/.devlyn/codex-judge.r{round_}.stderr').write_text(header + f'codex\nPASS\ntokens used\n{footer}\n')

    def trace(self, rollout, folder=None):
        write_trace(self.out / 'cell/trace' / (folder or ''), rollout,
                    [dict(type='thread_started', thread_id=rollout, agent_path='/root', metadata_payload=ref('m.json')),
                     *inference('c1', rollout), dict(type='rollout_ended', status='completed')],
                    {'m.json': dict(model='gpt-6-astra'), 'r.json': dict(token_usage=USAGE)})

    def gaps(self):
        return ' | '.join(usage.record(self.out)['gaps'])

    def test_plain_root_with_matching_footer_is_complete(self):
        self.judge('S1', '67')
        self.trace('S1')
        recorded = usage.record(self.out)
        self.assertEqual((recorded['completeness'], recorded['input_tokens'], recorded['output_tokens']),
                         ('COMPLETE', 240 + 100, 3 + 7), recorded['gaps'])

    def test_footer_mismatch_unexplained_trace_and_untraced_launch_are_gaps(self):
        self.judge('S1', '68')
        self.trace('S1')
        self.trace('ORPHAN')
        (self.out / 'cell/work/.devlyn/implement.worker-session.0.jsonl').write_text(
            json.dumps(dict(type='thread.started', thread_id='W0')) + '\n')
        gaps = self.gaps()
        for expected in ('plain root S1: footer 68 vs trace 67', 'trace ORPHAN binds to no launch evidence', 'launch W0 has no trace'):
            self.assertIn(expected, gaps)

    def test_a_duplicated_trace_counts_once(self):
        self.judge('S1', '67')
        self.trace('S1')
        self.trace('S1', folder='copy')
        recorded = usage.record(self.out)
        self.assertEqual((recorded['completeness'], recorded['output_tokens']), ('COMPLETE', 10), recorded['gaps'])

    def test_a_dispatched_judge_whose_result_vanished_is_a_gap_and_its_transcript_counts(self):
        (self.out / 'cell/work/.devlyn/verify-judge.r0.dispatch.json').write_text(json.dumps(dict(roles=dict(
            primary_judge=dict(decision='dispatch', engine='claude')))))
        (self.out / 'home/.claude/projects/x').mkdir()
        (self.out / 'home/.claude/projects/x/judge.jsonl').write_text(json.dumps(dict(type='assistant', sessionId='JUDGE', message=dict(
            id='m1', model='claude-opus-5-5', usage=dict(input_tokens=1, cache_read_input_tokens=2, cache_creation_input_tokens=3,
                                                         output_tokens=7)))) + '\n')
        recorded = usage.record(self.out)
        self.assertEqual((recorded['completeness'], recorded['input_tokens'], recorded['output_tokens']), ('PARTIAL', 240 + 6, 3 + 7))
        self.assertIn('dispatched claude primary_judge r0 left no result', ' | '.join(recorded['gaps']))

    def test_an_older_run_does_not_mask_a_newer_runs_missing_result(self):
        devlyn = self.out / 'cell/work/.devlyn'
        older = devlyn / 'runs/R1'
        older.mkdir(parents=True)
        for folder, run in ((older, 'R1'), (devlyn, 'R2')):
            (folder / 'pipeline.state.json').write_text(json.dumps(dict(run_id=run)))
            (folder / 'verify-judge.r0.dispatch.json').write_text(json.dumps(dict(roles=dict(
                primary_judge=dict(decision='dispatch', engine='claude')))))
        (older / 'claude-judge.r0.output.json').write_text(json.dumps(dict(type='result', session_id='J1',
                                                                           modelUsage={'claude-opus-5-5': claude_usage(output=7)})))
        gaps = self.gaps()
        self.assertIn('run R2: dispatched claude primary_judge r0 left no result', gaps)
        self.assertNotIn('run R1', gaps)

    def test_surviving_copies_are_reconciled_in_any_order(self):
        for names in (('a-live', 'b-custody'), ('b-live', 'a-custody')):
            devlyn = self.out / 'cell' / names[0] / '.devlyn'
            custody = self.out / 'cell' / names[1] / '.devlyn'
            for folder in (devlyn, custody):
                folder.mkdir(parents=True)
                (folder / 'pipeline.state.json').write_text(json.dumps(dict(run_id='R1')))
                (folder / 'verify-judge.r0.dispatch.json').write_text(json.dumps(dict(roles=dict(
                    primary_judge=dict(decision='dispatch', engine='claude')))))
            (custody / 'claude-judge.r0.output.json').write_text(json.dumps(dict(type='result', session_id='J1',
                                                                                 modelUsage={'claude-opus-5-5': claude_usage(output=7)})))
            self.assertNotIn('left no result', self.gaps(), names)
            shutil.rmtree(self.out / 'cell' / names[0])
            shutil.rmtree(self.out / 'cell' / names[1])

    def test_rollout_counters_must_all_agree(self):
        self.judge('S1', '67')
        self.trace('S1')
        rollout = self.out / 'home/.codex/sessions/r.jsonl'
        rollout.write_text(json.dumps(dict(type='session_meta', payload=dict(id='S1'))) + '\n' + json.dumps(dict(
            type='event_msg', payload=dict(type='token_count', info=dict(total_token_usage=dict(USAGE, input_tokens=999))))) + '\n')
        self.assertIn('thread S1: rollout counters', self.gaps())

    def test_an_inference_on_an_undeclared_thread_is_a_gap(self):
        self.judge('S1', '67')
        write_trace(self.out / 'cell/trace', 'S1', [dict(type='thread_started', thread_id='S1', agent_path='/root', metadata_payload=ref('m.json')),
                                                    *inference('c1', 'GHOST'), dict(type='rollout_ended', status='completed')],
                    {'m.json': dict(model='gpt-6-astra'), 'r.json': dict(token_usage=USAGE)})
        self.assertIn('undeclared thread GHOST', self.gaps())

    def test_claude_input_and_cache_counters_are_each_counted_once(self):
        (self.out / 'cell/work/.devlyn/claude-judge.r0.output.json').write_text(json.dumps(dict(
            type='result', session_id='J1', modelUsage={'claude-opus-5-5[1m]': claude_usage(1, 2, 3, 4)})))
        review(self.out, '2026-10-05T01-02-03Z', 'claude', claude_review('R1', claude_usage(5, 50, 7, 6)))
        (self.out / 'home/.claude/projects/x').mkdir()  # the review's own transcript: covered by its result, never added
        (self.out / 'home/.claude/projects/x/r1.jsonl').write_text(json.dumps(dict(type='assistant', sessionId='R1', message=dict(
            id='m1', model='claude-opus-5-5', usage=dict(input_tokens=5, cache_read_input_tokens=50, cache_creation_input_tokens=7,
                                                         output_tokens=6)))) + '\n')
        recorded = usage.record(self.out)
        self.assertEqual((recorded['completeness'], recorded['input_tokens'], recorded['output_tokens']),
                         ('COMPLETE', 240 + 6 + 62, 3 + 4 + 6), recorded['gaps'])
        self.assertEqual(recorded['claude']['claude-opus-5-5'], dict(input=16, cache_read=252, cache_write=40, output=13))

    def test_a_missing_claude_counter_is_a_named_gap_never_zero(self):
        result = dict(type='result', session_id='OWNER', modelUsage={'claude-opus-5-5': dict(inputTokens=10, outputTokens=3)})
        (self.out / 'run/stdout').write_text(json.dumps(result) + '\n')
        recorded = usage.record(self.out)
        self.assertIn('owner result: claude-opus-5-5 usage lacks a counter', recorded['gaps'])
        self.assertEqual(recorded['completeness'], 'UNKNOWN')

    def test_a_codex_review_call_is_bound_to_its_trace_and_counted(self):
        review(self.out, '2026-10-05T01-02-03Z', 'codex', codex_review('RV'), meta=dict(engine='codex', exit_code=0))
        self.trace('RV')
        recorded = usage.record(self.out)
        self.assertEqual((recorded['completeness'], recorded['input_tokens'], recorded['output_tokens']),
                         ('COMPLETE', 240 + 100, 3 + 7), recorded['gaps'])

    def test_review_calls_without_their_session_evidence_are_named_gaps(self):
        review(self.out, '2026-10-05T01-02-03Z', 'codex', codex_review('RV'))
        review(self.out, '2026-10-05T01-09-00Z', 'claude', claude_review('CR', claude_usage())[:1])  # killed before its result
        (self.out / 'home/.claude/projects/x').mkdir()
        (self.out / 'home/.claude/projects/x/cr.jsonl').write_text(json.dumps(dict(type='assistant', sessionId='CR', message=dict(
            id='m1', model='claude-opus-5-5', usage=dict(input_tokens=1, cache_read_input_tokens=0, cache_creation_input_tokens=0,
                                                         output_tokens=2)))) + '\n')
        recorded = usage.record(self.out)
        gaps = ' | '.join(recorded['gaps'])
        for expected in ('launch RV has no trace', 'reviews/2026-10-05T01-02-03Z-codex: codex call has no traced session',
                         'reviews/2026-10-05T01-09-00Z-claude: claude call left no result with usage',
                         'Claude session CR has no result; its transcript usage is a lower bound'):
            self.assertIn(expected, gaps)
        self.assertEqual((recorded['completeness'], recorded['input_tokens'], recorded['output_tokens']), ('PARTIAL', 240 + 1, 3 + 2))


class Identity(unittest.TestCase):
    """Each seat's native model and Codex effort against the route; usage-only loss never makes identity UNVERIFIED."""

    def setUp(self):
        self.cell = load('cell')
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)
        for name in ('cell/trace', 'cell/work/.devlyn', 'home/.codex/sessions', 'home/.claude/projects', 'tmp', 'run'):
            (self.out / name).mkdir(parents=True)

    def configured(self, rollout, thread, model, effort, path='/root'):
        return [dict(type='thread_started', thread_id=thread, agent_path=path, metadata_payload=ref(f'{thread}.json')),
                dict(type='protocol_event_observed', event_type='session_configured', event_payload=ref(f'{thread}-c.json'))], {
            f'{thread}.json': dict(model=model), f'{thread}-c.json': dict(thread_id=thread, model=model, reasoning_effort=effort)}

    def codex_cell(self, worker_model, worker_effort):
        (self.out / 'run/stdout').write_text(json.dumps(dict(type='thread.started', thread_id='OWN')) + '\n')
        events, payloads = self.configured('OWN', 'OWN', 'gpt-6-astra', 'high')
        write_trace(self.out / 'cell/trace', 'OWN', [*events, dict(type='rollout_ended', status='completed')], payloads)
        events, payloads = self.configured('WRK', 'WRK', worker_model, worker_effort)
        write_trace(self.out / 'cell/trace', 'WRK', [*events, dict(type='rollout_ended', status='completed')], payloads)
        (self.out / 'cell/work/.devlyn/implement.worker-session.0.jsonl').write_text(json.dumps(dict(type='thread.started', thread_id='WRK')) + '\n')
        return dict(config='codex', engine='codex', model='gpt-6-astra', arm='I')

    def test_the_registered_worker_matches_and_a_seat_swap_does_not(self):
        self.assertEqual(self.cell.identity(self.out, self.codex_cell('gpt-6-sol', 'high'))['status'], 'MATCH')
        shutil.rmtree(self.out / 'cell/trace')
        (self.out / 'cell/trace').mkdir()
        result = self.cell.identity(self.out, self.codex_cell('gpt-6-astra', 'low'))
        self.assertEqual(result['status'], 'MISMATCH')
        self.assertTrue(any(v.startswith('worker WRK ran gpt-6-astra/low') for v in result['violations']), result['violations'])

    def test_an_inference_on_another_model_is_a_mismatch(self):
        plan = self.codex_cell('gpt-6-sol', 'high')
        shutil.rmtree(self.out / 'cell/trace')
        (self.out / 'cell/trace').mkdir()
        events, payloads = self.configured('OWN', 'OWN', 'gpt-6-astra', 'high')
        write_trace(self.out / 'cell/trace', 'OWN', [*events, *inference('c1', 'OWN', model='gpt-6-sol')],
                    dict(payloads, **{'r.json': dict(token_usage=USAGE)}))
        events, payloads = self.configured('WRK', 'WRK', 'gpt-6-sol', 'high')
        write_trace(self.out / 'cell/trace', 'WRK', events, payloads)
        self.assertTrue(any('owner inference c1 ran gpt-6-sol' in v for v in self.cell.identity(self.out, plan)['violations']))

    def test_a_lost_owner_trace_falls_back_to_its_rollout(self):
        plan = self.codex_cell('gpt-6-sol', 'high')
        shutil.rmtree(self.out / 'cell/trace/trace-t-OWN')
        (self.out / 'home/.codex/sessions/own.jsonl').write_text(json.dumps(dict(type='session_meta', payload=dict(id='OWN'))) + '\n'
            + json.dumps(dict(type='turn_context', payload=dict(model='gpt-6-astra', effort='high'))) + '\n')
        self.assertEqual(self.cell.identity(self.out, plan)['status'], 'MATCH')

    def test_untraced_native_children_are_validated_by_ancestry(self):
        plan = self.codex_cell('gpt-6-sol', 'high')
        shutil.rmtree(self.out / 'cell/trace/trace-t-OWN')
        sessions = self.out / 'home/.codex/sessions'
        (sessions / 'own.jsonl').write_text(json.dumps(dict(type='session_meta', payload=dict(id='OWN'))) + '\n'
            + json.dumps(dict(type='turn_context', payload=dict(model='gpt-6-astra', effort='high'))) + '\n')
        source = dict(subagent=dict(thread_spawn=dict(parent_thread_id='OWN')))
        (sessions / 'kid.jsonl').write_text(json.dumps(dict(type='session_meta', payload=dict(id='KID', source=source))) + '\n'
            + json.dumps(dict(type='turn_context', payload=dict(model='gpt-6-astra', effort='low'))) + '\n')
        result = self.cell.identity(self.out, plan)
        self.assertEqual(result['status'], 'MISMATCH')
        self.assertTrue(any(v.startswith('native child KID') for v in result['violations']), result['violations'])

    def test_an_incomplete_trace_identity_uses_the_bound_rollout(self):
        plan = self.codex_cell('gpt-6-sol', 'high')
        own = self.out / 'cell/trace/trace-t-OWN/payloads'
        for name in ('OWN.json', 'OWN-c.json'):
            (own / name).unlink()
        (self.out / 'home/.codex/sessions/own.jsonl').write_text(json.dumps(dict(type='session_meta', payload=dict(id='OWN'))) + '\n'
            + json.dumps(dict(type='turn_context', payload=dict(model='gpt-6-astra', effort='high'))) + '\n')
        self.assertEqual(self.cell.identity(self.out, plan)['status'], 'MATCH')

    def test_a_surviving_child_does_not_hide_the_owners_own_identity(self):
        plan = self.codex_cell('gpt-6-sol', 'high')
        shutil.rmtree(self.out / 'cell/trace/trace-t-OWN')
        events, payloads = self.configured('OWN', 'KID', 'gpt-6-sol', 'high', path='/root/child')
        write_trace(self.out / 'cell/trace', 'OWN', events, payloads)
        (self.out / 'home/.codex/sessions/own.jsonl').write_text(json.dumps(dict(type='session_meta', payload=dict(id='OWN'))) + '\n'
            + json.dumps(dict(type='turn_context', payload=dict(model='gpt-6-astra', effort='low'))) + '\n')
        self.assertEqual(self.cell.identity(self.out, plan)['status'], 'MISMATCH')

    def test_effort_lost_from_the_trace_is_recovered_from_the_rollout(self):
        plan = self.codex_cell('gpt-6-sol', 'high')
        (self.out / 'cell/trace/trace-t-OWN/payloads/OWN-c.json').unlink()
        (self.out / 'home/.codex/sessions/own.jsonl').write_text(json.dumps(dict(type='session_meta', payload=dict(id='OWN'))) + '\n'
            + json.dumps(dict(type='turn_context', payload=dict(model='gpt-6-astra', effort='high'))) + '\n')
        self.assertEqual(self.cell.identity(self.out, plan)['status'], 'MATCH')

    def test_a_forked_childs_inherited_context_is_not_its_own(self):
        plan = self.codex_cell('gpt-6-sol', 'high')
        shutil.rmtree(self.out / 'cell/trace/trace-t-OWN')
        sessions = self.out / 'home/.codex/sessions'
        (sessions / 'own.jsonl').write_text(json.dumps(dict(type='session_meta', payload=dict(id='OWN'))) + '\n'
            + json.dumps(dict(type='turn_context', payload=dict(model='gpt-6-astra', effort='high'))) + '\n')
        source = dict(subagent=dict(thread_spawn=dict(parent_thread_id='OWN')))
        (sessions / 'kid.jsonl').write_text('\n'.join(json.dumps(e) for e in (
            dict(type='session_meta', payload=dict(id='KID', source=source, forked_from_id='OWN')),
            dict(type='turn_context', payload=dict(model='gpt-6-astra', effort='high')),
            dict(type='event_msg', payload=dict(type='thread_settings_applied', thread_id='KID')),
            dict(type='turn_context', payload=dict(model='gpt-6-sol', effort='high')))) + '\n')
        self.assertEqual(self.cell.identity(self.out, plan)['status'], 'MATCH')

    def test_mixed_native_efforts_are_a_mismatch(self):
        plan = self.codex_cell('gpt-6-sol', 'high')
        (self.out / 'home/.codex/sessions/own.jsonl').write_text('\n'.join(json.dumps(e) for e in (
            dict(type='session_meta', payload=dict(id='OWN')),
            dict(type='turn_context', payload=dict(model='gpt-6-astra', effort='low')),
            dict(type='turn_context', payload=dict(model='gpt-6-astra', effort='high')))) + '\n')
        self.assertEqual(self.cell.identity(self.out, plan)['status'], 'MISMATCH')

    def test_an_unbound_codex_process_is_a_mismatch(self):
        plan = self.codex_cell('gpt-6-sol', 'high')
        events, payloads = self.configured('STRAY', 'STRAY', 'gpt-6-sol', 'high')
        write_trace(self.out / 'cell/trace', 'STRAY', events, payloads)
        self.assertIn('unbound Codex process STRAY', self.cell.identity(self.out, plan)['violations'])

    def test_an_empty_judge_capture_with_a_routed_transcript_stays_verified(self):
        init = dict(type='system', subtype='init', model='claude-opus-5-5', session_id='OWNER')
        (self.out / 'run/stdout').write_text(json.dumps(init) + '\n' + json.dumps(dict(type='result', session_id='OWNER', modelUsage={'claude-opus-5-5': {}})) + '\n')
        (self.out / 'cell/work/.devlyn/claude-judge.r0.output.json').write_text('')
        (self.out / 'home/.claude/projects/x').mkdir()
        (self.out / 'home/.claude/projects/x/j.jsonl').write_text(json.dumps(dict(type='assistant', sessionId='J', message=dict(
            id='m', model='claude-opus-5-5', usage=dict(output_tokens=1)))) + '\n')
        self.assertEqual(self.cell.identity(self.out, dict(config='claude', engine='claude', model='claude-opus-5-5', arm='F'))['status'], 'MATCH')

    def test_an_owner_without_any_evidence_is_unknown(self):
        (self.out / 'run/stdout').write_text('')
        self.assertEqual(self.cell.identity(self.out, dict(config='claude', engine='claude', model='claude-opus-5-5', arm='A'))['status'], 'UNKNOWN')

    def test_a_codex_review_is_bound_and_runs_its_registered_pin(self):
        init = dict(type='system', subtype='init', model='claude-opus-5-5', session_id='OWNER')
        (self.out / 'run/stdout').write_text(json.dumps(init) + '\n' + json.dumps(dict(
            type='result', session_id='OWNER', modelUsage={'claude-opus-5-5': claude_usage()})) + '\n')
        plan = dict(config='claude', engine='claude', model='claude-opus-5-5', arm='I')
        review(self.out, '2026-10-05T01-02-03Z', 'codex', codex_review('RV'))
        for model, status in (('gpt-6-astra', 'MATCH'), ('gpt-6-sol', 'MISMATCH')):
            shutil.rmtree(self.out / 'cell/trace')
            (self.out / 'cell/trace').mkdir()
            events, payloads = self.configured('RV', 'RV', model, 'high')
            write_trace(self.out / 'cell/trace', 'RV', [*events, dict(type='rollout_ended', status='completed')], payloads)
            result = self.cell.identity(self.out, plan)
            self.assertEqual(result['status'], status, result['violations'])
        self.assertTrue(any(v.startswith('reviewer RV ran gpt-6-sol/high') for v in result['violations']), result['violations'])

    def test_a_review_without_its_trace_is_checked_on_its_rollout(self):
        init = dict(type='system', subtype='init', model='claude-opus-5-5', session_id='OWNER')
        (self.out / 'run/stdout').write_text(json.dumps(init) + '\n')
        plan = dict(config='claude', engine='claude', model='claude-opus-5-5', arm='I')
        review(self.out, '2026-10-05T01-02-03Z', 'codex', codex_review('RV'))
        self.assertEqual(self.cell.identity(self.out, plan)['status'], 'UNVERIFIED')
        rollout = self.out / 'home/.codex/sessions/rv.jsonl'
        for model, status in (('gpt-6-astra', 'MATCH'), ('gpt-6-sol', 'MISMATCH')):
            rollout.write_text(json.dumps(dict(type='session_meta', payload=dict(id='RV'))) + '\n'
                               + json.dumps(dict(type='turn_context', payload=dict(model=model, effort='high'))) + '\n')
            self.assertEqual(self.cell.identity(self.out, plan)['status'], status)

    def test_a_claude_review_on_an_unregistered_model_is_a_mismatch(self):
        plan = self.codex_cell('gpt-6-sol', 'high')
        review(self.out, '2026-10-05T01-02-03Z', 'claude', claude_review('CR', claude_usage()))
        self.assertEqual(self.cell.identity(self.out, plan)['status'], 'MATCH')
        shutil.rmtree(self.out / 'home/.devlyn')
        review(self.out, '2026-10-05T01-02-03Z', 'claude', claude_review('CR', claude_usage(), model='claude-sonnet-5'))
        self.assertIn('claude result CR ran claude-sonnet-5', self.cell.identity(self.out, plan)['violations'])


class Locator(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)
        anchor = self.out / 'cell/work'
        anchor.mkdir(parents=True)
        (self.out / 'tmp').mkdir()
        self.git = lambda *a, cwd=anchor: subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=cwd,
                                                         check=True, capture_output=True, text=True).stdout.strip()
        self.git('init', '-q', '-b', 'main')
        (anchor / '.gitignore').write_text('ignored.log\n')
        (anchor / 'product.txt').write_text('base\n')
        self.git('add', '.')
        self.git('commit', '-q', '-m', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        with tempfile.TemporaryDirectory() as temp:  # what prepare records: the allocation commit's product
            files = locate.packet.tree(locate.raw_tree(['git', *locate.SAFE, '-C', str(anchor)], self.base, Path(temp)))
        (anchor / 'product.txt').write_text('anchor edit\n')
        (anchor / 'ignored.log').write_text('noise\n')
        (self.out / 'baseline.json').write_text(json.dumps(dict(arm='I', allocation_sha=self.base, files=files)))

    def as_arm(self, arm):
        (self.out / 'baseline.json').write_text(json.dumps(dict(self.baseline(), arm=arm)))

    def linked(self, container_path, edit):
        """A worktree as a container leaves it: registered, with container paths in both Git links."""
        worktree = locate.host(self.out, container_path)
        self.git('worktree', 'add', '-q', '-b', 'task/' + worktree.name, str(worktree), self.base)
        (gitdir,) = [d for d in (self.out / 'cell/work/.git/worktrees').iterdir()
                     if Path((d / 'gitdir').read_text().strip()).resolve() == (worktree / '.git').resolve()]
        (gitdir / 'gitdir').write_text(container_path + '/.git\n')
        (worktree / '.git').write_text(f'gitdir: /cell/work/.git/worktrees/{gitdir.name}\n')
        (worktree / 'product.txt').write_text(edit)
        (worktree / 'ignored.log').write_text('noise\n')
        return worktree

    def receipt(self, key, **fields):
        folder = self.out / 'cell/work/.git/devlyn-completion' / key
        folder.mkdir(parents=True)
        (folder / 'receipt.json').write_text(json.dumps(dict(task='t', allocation='owned', **fields)))
        return folder

    def baseline(self):
        return json.loads((self.out / 'baseline.json').read_text())

    def test_anchor_only_when_nothing_was_allocated_and_ignored_files_stay_out(self):
        self.as_arm('F')
        selection = locate.locate(self.out)
        self.assertEqual(selection['kind'], 'anchor')
        self.assertEqual(sorted(p.name for p in (self.out / 'snapshot').iterdir()), ['.gitignore', 'product.txt'])

    def test_a_receipt_less_F_run_is_its_anchor_as_in_0231(self):
        self.as_arm('F')
        (self.out / 'cell/work/product.txt').write_text('base\n')
        self.linked('/cell/one', 'one\n')
        self.assertEqual(locate.select(self.out, self.baseline()), dict(kind='anchor', path='cell/work', candidates=[]))
        self.linked('/tmp/two', 'two\n')  # never the native STOP
        self.assertEqual(locate.select(self.out, self.baseline())['kind'], 'anchor')

    def test_a_nested_repository_is_copied_as_a_tree_with_its_symlinks(self):
        nested = self.out / 'cell/work/tests/fixture-repo'
        nested.mkdir(parents=True)
        self.git('init', '-q', cwd=nested)
        (nested / 'data.txt').write_text('fixture\n')
        (nested / 'link').symlink_to('data.txt')
        locate.locate(self.out)
        copied = self.out / 'snapshot/tests/fixture-repo'
        self.assertEqual(((copied / 'data.txt').read_text(), (copied / 'link').readlink()), ('fixture\n', Path('data.txt')))

    def test_a_file_that_cannot_be_copied_is_a_locator_stop(self):
        unreadable = self.out / 'cell/work/secret.txt'
        unreadable.write_text('x\n')
        unreadable.chmod(0)
        with self.assertRaisesRegex(locate.LocatorError, 'secret.txt'):
            locate.locate(self.out)

    def test_worktree_tree_when_local_only_completion_bound_no_acceptance(self):
        self.as_arm('F')
        self.linked('/tmp/task', 'linked edit\n')
        self.receipt('a', worktree='/tmp/task', local_only=True)
        selection = locate.locate(self.out)
        self.assertEqual((selection['kind'], selection['path']), ('worktree', 'tmp/task'))
        self.assertEqual((self.out / 'snapshot/product.txt').read_text(), 'linked edit\n')
        self.assertFalse((self.out / 'snapshot/ignored.log').exists())

    def accepted_run(self, worktree, sha, *, seal_head=None, root=None):
        runs = (root or worktree) / '.devlyn/runs/R1'
        runs.mkdir(parents=True)
        (runs / 'pipeline.state.json').write_text(json.dumps(dict(run_id='R1')))
        (runs / 'source-seal.json').write_text(json.dumps(dict(seal=dict(head=seal_head or sha))))

    def test_acceptance_needs_its_run_and_seal_and_survives_cleanup_through_custody(self):
        self.as_arm('F')
        worktree = self.linked('/cell/task', 'accepted\n')
        sha = self.git('commit-tree', self.git('write-tree'), '-p', self.base, '-m', 'accepted')
        acceptance = dict(task='t', source_sha=sha, kind='pipeline', run_id='R1')
        self.accepted_run(worktree, sha, seal_head=self.base)  # a seal of another commit binds nothing
        self.receipt('a', worktree='/cell/task', acceptance=acceptance)
        self.assertEqual(locate.select(self.out, self.baseline())['kind'], 'worktree')
        shutil.rmtree(worktree / '.devlyn')
        shutil.rmtree(self.out / 'cell/work/.git/devlyn-completion')
        folder = self.receipt('b', worktree='/cell/task', acceptance=acceptance)
        self.accepted_run(None, sha, root=folder / 'custody')  # cleanup kept the archive in custody
        self.assertEqual(locate.select(self.out, self.baseline())['sha'], sha)

    def test_owned_allocation_without_a_preserved_tree_stops(self):
        self.as_arm('F')
        self.receipt('a', worktree='/var/lost')
        with self.assertRaises(locate.LocatorError):
            locate.select(self.out, self.baseline())

    def test_a_native_run_keeps_its_changed_anchor_beside_a_baseline_witness_worktree(self):
        self.linked('/tmp/witness', 'baseline witness\n')
        selection = locate.locate(self.out)
        self.assertEqual((selection['kind'], selection['changed']), ('anchor', ['cell/work', 'tmp/witness']))
        self.assertEqual((self.out / 'snapshot/product.txt').read_text(), 'anchor edit\n')

    def test_a_native_run_in_an_unchanged_anchor_selects_its_one_changed_worktree(self):
        (self.out / 'cell/work/product.txt').write_text('base\n')
        self.linked('/cell/task', 'linked edit\n')
        selection = locate.locate(self.out)
        self.assertEqual((selection['kind'], selection['path'], selection['changed']), ('worktree', 'cell/task', ['cell/task']))
        self.assertEqual((self.out / 'snapshot/product.txt').read_text(), 'linked edit\n')
        self.assertFalse((self.out / 'snapshot/ignored.log').exists())

    def test_an_unchanged_native_run_is_its_anchor_and_two_changed_worktrees_stop(self):
        (self.out / 'cell/work/product.txt').write_text('base\n')
        self.assertEqual((locate.select(self.out, self.baseline())['kind'], locate.select(self.out, self.baseline())['changed']),
                         ('anchor', []))
        self.linked('/cell/one', 'one\n')
        self.linked('/tmp/two', 'two\n')
        with self.assertRaises(locate.LocatorError):
            locate.select(self.out, self.baseline())

    def test_participant_git_configuration_never_executes_during_native_selection(self):
        self.linked('/tmp/witness', 'baseline witness\n')
        marker = self.out / 'fsmonitor-ran'
        self.git('config', 'core.fsmonitor', f'touch {marker}; echo')
        locate.locate(self.out)
        self.assertFalse(marker.exists())


class Decision(unittest.TestCase):
    """The O4 rule per configuration: six cells per arm, per-success costs, quality per task, no claim at S = 0."""

    def setUp(self):
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)

    def write(self, wall=None, tokens=None, done=lambda name, arm: True, usage=lambda name, arm: 'COMPLETE', **judgments):
        """wall and tokens give each cell's value by (arm, config) or by arm (defaults 100 s and 1000 input, output a
        tenth of input); done and usage take (cell, arm). Extra keywords replace recorded judgments."""
        value = lambda table, arm, config, default: (table or {}).get((arm, config), (table or {}).get(arm, default))
        for name, task, arm, config, replicate in decide.CELLS:
            (self.out / name).mkdir(exist_ok=True)
            (self.out / name / 'checks.json').write_text(json.dumps(dict(public=[dict(exit_code=0)])))
            complete, spent = done(name, arm), value(tokens, arm, config, 1000)
            (self.out / f'verdict-{name}.json').write_text(json.dumps(dict(
                cell=name, status='COMPLETE' if complete else 'PRODUCT_INCOMPLETE',
                oracle=[dict(id='row', status='PASS' if complete else 'FAIL')], scope_violations=[], assessments=[],
                owner_status='EXITED_0', owner_seconds=value(wall, arm, config, 100), usage=usage(name, arm),
                input_tokens=spent, output_tokens=spent // 10)))
        decisions = dict(audited=[c[0] for c in decide.CELLS], false_completion=[], user_data_harm=[], adjudicated={},
                         severe={}, witnesses={})
        (self.out / 'decisions.json').write_text(json.dumps(dict(decisions, **judgments)))
        return self.decide()

    def decide(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return decide.main(self.out, self.out / 'decisions.json')

    def test_admission_needs_a_strict_improvement_and_a_tie_earns_none(self):
        claude = self.write(wall=dict(I=90))['configs']['claude']
        self.assertEqual((claude['admitted'], claude['admission']['outcome'], claude['admission']['strictly_better']), ('I', 'PASS', True))
        self.assertEqual(claude['admission']['tests'], dict(wall=True, input=True, output=True))
        codex = self.write()['configs']['codex']
        self.assertEqual((codex['admitted'], codex['admission']['outcome'], codex['admission']['strictly_better']), ('A', 'FAIL', False))

    def test_more_completions_at_tied_per_success_costs_qualify(self):
        half = lambda name, arm: arm != 'A' or name.endswith('r1')  # A completes 3 cells, I all 6
        admission = self.write(wall=dict(A=50, I=100), tokens=dict(A=1000, I=2000), done=half)['configs']['claude']['admission']
        self.assertEqual((admission['tests'], admission['strictly_better'], admission['outcome']),
                         (dict(wall=True, input=True, output=True), True, 'PASS'))

    def test_a_hung_owner_counts_the_5400_second_wall(self):
        self.write()
        path = self.out / 'verdict-m02-D4-claude-I-r1.json'
        path.write_text(json.dumps(dict(json.loads(path.read_text()), owner_status='HANG_TIMEOUT', owner_seconds=7)))
        self.assertEqual(self.decide()['configs']['claude']['sums']['I']['wall'], 5 * 100 + 5400)

    def test_cost_is_per_completed_cell_with_failures_in_the_sums(self):
        half = lambda name, arm: arm != 'A' or name.endswith('r1')  # A completes only its replicate-1 cells
        claude = self.write(wall=dict(A=50, I=90), done=half)['configs']['claude']
        sums = claude['sums']
        self.assertEqual((sums['A']['S'], sums['A']['wall'], sums['A']['per_success']['wall']), (3, 300.0, 100.0))
        self.assertEqual((sums['I']['S'], sums['I']['wall'], sums['I']['per_success']['wall']), (6, 540.0, 90.0))
        self.assertEqual((sums['A']['input'], sums['A']['per_success']['input']), (6000, 2000.0))
        self.assertEqual(claude['admission']['outcome'], 'PASS')  # higher raw sums, lower cost per success

    def test_zero_successes_earn_no_claim_and_A_stays_admitted(self):
        claude = self.write(wall=dict(I=10), done=lambda name, arm: arm != 'I')['configs']['claude']
        self.assertEqual((claude['admission']['outcome'], claude['replacement']['outcome'], claude['admitted']),
                         ('NO_CLAIM', 'NO_CLAIM', 'A'))
        self.assertIsNone(claude['sums']['I']['per_success']['wall'])

    def test_missing_candidate_usage_is_inconclusive_and_a_partial_reference_bound_only_proves(self):
        report = self.write(wall=dict(I=90), usage=lambda name, arm: 'PARTIAL' if name == 'm02-D4-claude-I-r1' else 'COMPLETE')
        self.assertEqual(report['configs']['claude']['admission']['tests'], dict(wall=True, input=None, output=None))
        self.assertEqual(report['configs']['claude']['admission']['outcome'], 'INCONCLUSIVE')
        self.assertEqual(report['configs']['codex']['admission']['outcome'], 'PASS')
        partial_a = lambda name, arm: 'PARTIAL' if arm == 'A' else 'COMPLETE'
        admission = self.write(wall=dict(I=90), tokens=dict(I=900), usage=partial_a)['configs']['claude']['admission']
        self.assertEqual(admission['outcome'], 'PASS')
        admission = self.write(wall=dict(I=90), tokens=dict(I=1100), usage=partial_a)['configs']['claude']['admission']
        self.assertEqual((admission['tests']['input'], admission['outcome']), (None, 'INCONCLUSIVE'))

    def test_replacement_needs_seventy_percent_of_F_wall_per_success_and_no_more_tokens(self):
        self.assertEqual(self.write(wall=dict(I=70))['configs']['claude']['replacement']['outcome'], 'PASS')  # inclusive
        self.assertEqual(self.write(wall=dict(I=71))['configs']['claude']['replacement']['outcome'], 'FAIL')
        replacement = self.write(wall=dict(I=70), tokens=dict(I=1010))['configs']['claude']['replacement']
        self.assertEqual((replacement['tests'], replacement['outcome']), (dict(wall=True, input=False, output=False), 'FAIL'))

    def test_replacement_needs_admission_and_reports_both(self):
        report = self.write(wall=dict(A=50, I=60, F=100))  # within 0.70 x F's wall, but slower than A
        replacement = report['configs']['claude']['replacement']
        self.assertEqual((replacement['admission'], replacement['comparison'], replacement['outcome']), ('FAIL', 'PASS', 'FAIL'))
        self.assertEqual(report['token'], 'LIVE:claude=admitted:A,replaces_F:FAIL;codex=admitted:A,replaces_F:FAIL')
        replacement = self.write(wall=dict(A=50, I=40, F=100))['configs']['claude']['replacement']
        self.assertEqual((replacement['admission'], replacement['comparison'], replacement['outcome']), ('PASS', 'PASS', 'PASS'))

    def test_an_incumbent_without_successes_is_dominated_but_quality_still_applies(self):
        no_f = lambda name, arm: arm != 'F'
        report = self.write(wall=dict(A=600, I=500), done=no_f)['configs']['codex']
        replacement = report['replacement']
        self.assertEqual((replacement['outcome'], replacement['reason'], replacement['tests']),
                         ('PASS', 'dominance over a zero-success incumbent', dict(wall=True, input=True, output=True)))
        self.assertEqual((report['sums']['F']['per_success'], 'reason' in report['admission']),
                         (dict(wall=None, input=None, output=None), False))  # no ratio exists to report
        replacement = self.write(wall=dict(A=600, I=500), done=no_f, false_completion=['m06-I0185-codex-I-r1'])['configs']['codex']['replacement']
        self.assertEqual((replacement['outcome'], replacement['quality']['I0185']['safe']), ('FAIL', False))

    def test_quality_is_per_task_and_a_reproduced_defect_must_reproduce_on_the_reference(self):
        loss = lambda name, arm: name != 'm09-D3-claude-I-r1'
        quality = self.write(wall=dict(I=50), done=loss)['configs']['claude']['admission']['quality']
        self.assertEqual((quality['D3']['completion'], quality['D3']['rows'], quality['D4']['completion']), (False, False, True))
        admission = self.write(wall=dict(I=50), user_data_harm=['m02-D4-claude-I-r1'])['configs']['claude']['admission']
        self.assertEqual((admission['outcome'], admission['quality']['D4']['safe']), ('FAIL', False))
        for trees, outcome in (({'m02-D4-claude-I-r1': True}, 'FAIL'), ({'m02-D4-claude-I-r1': True, 'm01-D4-claude-A-r1': False}, 'FAIL'),
                               ({'m02-D4-claude-I-r1': True, 'm01-D4-claude-A-r1': True}, 'PASS')):
            self.assertEqual(self.write(wall=dict(I=50), witnesses={'W1': trees})['configs']['claude']['admission']['outcome'], outcome, trees)

    def test_configs_decide_separately(self):
        report = self.write(wall={('I', 'claude'): 90, ('I', 'codex'): 110})
        self.assertEqual(report['token'], 'LIVE:claude=admitted:I,replaces_F:FAIL;codex=admitted:A,replaces_F:FAIL')

    def test_methodology_is_reported_beside_the_rule_never_in_it(self):
        self.write(wall=dict(I=90))
        for name, task, arm, config, replicate in decide.CELLS:
            path = self.out / f'verdict-{name}.json'
            record = dict(I=dict(compliance=dict(compliant=False)), F=dict(obligations=dict(satisfied=True))).get(arm, {})
            path.write_text(json.dumps(dict(json.loads(path.read_text()), **record)))
        claude = self.decide()['configs']['claude']
        self.assertEqual(claude['admitted'], 'I')
        self.assertEqual({arm: set(claude['sums'][arm]['methodology'].values()) for arm in 'AIF'},
                         dict(A={None}, I={False}, F={True}))

    def test_missing_judgments_and_stop_rows_block_the_computation(self):
        self.write()
        decisions = json.loads((self.out / 'decisions.json').read_text())
        for key in ('user_data_harm', 'false_completion', 'audited'):
            (self.out / 'decisions.json').write_text(json.dumps({k: v for k, v in decisions.items() if k != key}))
            with self.assertRaises(ValueError, msg=key):
                self.decide()
        (self.out / 'decisions.json').write_text(json.dumps(decisions))
        first = self.out / f'verdict-{decide.CELLS[0][0]}.json'
        verdict = json.loads(first.read_text())
        first.write_text(json.dumps(dict(verdict, assessments=[dict(route=dict(engine='codex'), complete=True, severe=1,
                                                                    severe_findings=[dict(severity='HIGH')])])))
        with self.assertRaises(ValueError):  # a severe finding without a recorded disposition
            self.decide()
        first.write_text(json.dumps(dict(verdict, status='STOP')))
        with self.assertRaises(ValueError):
            self.decide()


class Quota(unittest.TestCase):
    def test_only_explicit_native_shapes_count(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        prose = root / 'prose.jsonl'
        prose.write_text(json.dumps(dict(type='item.completed', item=dict(type='agent_message', text='the reviewer hit a rate limit (429)'))) + '\n'
                         + json.dumps(dict(type='item.completed', item=dict(type='error', message='upstream gateway responded HTTP 429'))) + '\n')
        native = root / 'native.jsonl'
        native.write_text(json.dumps(dict(type='result', is_error=True, api_error_status=429, result="You've hit your weekly limit")) + '\n'
                          + json.dumps(dict(type='item.completed', item=dict(type='error', message="You've hit your usage limit"))) + '\n'
                          + json.dumps(dict(type='result', is_error=True, api_error_status=401, result='OAuth token expired')) + '\n')
        stderr = root / 'codex-judge.r0.stderr'
        stderr.write_text("OpenAI Codex v0.156.1\nERROR: You've hit your usage limit. Try again later.\n")
        self.assertEqual(quota.scan([prose], root), [])
        self.assertEqual([(h['fault'], h['kind']) for h in quota.scan([native, stderr], root)],
                         [('limit', 'claude limit result'), ('limit', 'codex usage limit'), ('auth', 'claude authentication result'),
                          ('limit', 'codex usage limit (stderr)')])

    def test_review_launcher_records_are_execution_evidence(self):
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out)
        review(out, '2026-10-05T01-02-03Z', 'claude', [dict(type='result', is_error=True, api_error_status=429,
                                                              result="You've hit your session limit")])
        folder = review(out, '2026-10-05T01-03-00Z', 'codex', [])
        (folder / 'stderr').write_text("ERROR: You've hit your usage limit. Try again later.\n")
        self.assertEqual(sorted((h['fault'], h['kind']) for h in quota.classify(out)['execution']),
                         [('limit', 'claude limit result'), ('limit', 'codex usage limit (stderr)')])


class Assessor(unittest.TestCase):
    def test_an_invalid_answer_is_no_verdict(self):
        assess = load('assess')
        for answer in ('{}', '{"complete": true}', '{"complete": "unknown"}', '{"complete": true, "findings": "none"}', 'no json'):
            self.assertIsNone(assess.valid(answer), answer)
        self.assertEqual(assess.valid('{"complete": false, "findings": [{"severity": "HIGH"}]}')['complete'], False)


    def test_uncertain_container_teardown_raises(self):
        assess = load('assess')
        daemon_down = subprocess.CompletedProcess([], 1, '', 'Cannot connect to the Docker daemon')
        original = assess.subprocess.run
        assess.subprocess.run = lambda *a, **k: daemon_down
        try:
            with self.assertRaises(RuntimeError):
                assess.reap('devlyn-0231-assess-x')
        finally:
            assess.subprocess.run = original


class Venue(unittest.TestCase):
    """Preflight and evidence collection fail closed and visibly."""

    def setUp(self):
        self.run_cell = load('run_cell')
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        (self.root / 'auth').mkdir()
        (self.root / 'auth/codex.json').write_text('{}')

    def test_a_timed_out_limit_probe_is_unavailable_evidence_and_is_reaped(self):
        reaped, original_run, original_reap = [], self.run_cell.subprocess.run, self.run_cell.assess.reap
        def timeout(*a, **k):
            raise subprocess.TimeoutExpired(a[0], 180)
        self.run_cell.subprocess.run, self.run_cell.assess.reap = timeout, reaped.append
        try:
            limits = self.run_cell.codex_limits(dict(auth=str(self.root / 'auth'), scratch=str(self.root), image='x'))
        finally:
            self.run_cell.subprocess.run, self.run_cell.assess.reap = original_run, original_reap
        self.assertEqual((limits, len(reaped)), ({}, 1))

    def test_a_sealing_failure_stops_before_any_other_evidence_reader(self):
        rc, out = self.run_cell, self.root / 'out'
        out.mkdir()
        cell = out / 'c1'
        (cell / 'run').mkdir(parents=True)
        runtime = dict(output=str(out), control=str(self.root / 'control'), image='devlyn-0231')
        saved = (rc.preflight, rc.control_unchanged, rc.prepare.prepare, rc.cell_run.run, rc.seal_after_teardown,
                 rc.usage.record, rc.quota.classify)
        def forbidden(*a, **k):
            raise AssertionError('an evidence reader ran after a sealing failure')
        (rc.preflight, rc.control_unchanged) = (lambda runtime: (dict(), None)), (lambda runtime: True)
        rc.prepare.prepare = lambda *a: (cell / 'plan.json').write_text('{}') and cell or cell
        rc.cell_run.run = lambda out, runtime: dict(owner_status='EXITED_0', teardown='CLEAN', seconds=1, identity={})
        rc.seal_after_teardown = lambda out: (None, ['owner log unreadable'])
        rc.usage.record, rc.quota.classify = forbidden, forbidden
        (self.root / 'runtime.json').write_text(json.dumps(runtime))
        try:
            (cell / 'baseline.json').write_text('{}')
            (cell / 'prompt.txt').write_text('')
            original_digest = rc.digest
            rc.digest = lambda path: 'x'
            code = rc.run(str(self.root / 'runtime.json'), 'c1', 'SMOKE', 'F', 'claude')
        finally:
            rc.digest = original_digest
            (rc.preflight, rc.control_unchanged, rc.prepare.prepare, rc.cell_run.run, rc.seal_after_teardown,
             rc.usage.record, rc.quota.classify) = saved
        verdict = json.loads((out / 'verdict-c1.json').read_text())
        self.assertEqual((code, verdict['status']), (2, 'STOP'))
        self.assertIn('evidence collection failed', verdict['reason'])

    def test_compliance_is_attached_to_I_verdicts_and_obligations_only_to_F(self):
        rc, out = self.run_cell, self.root / 'out'
        out.mkdir()
        (self.root / 'runtime.json').write_text(json.dumps(dict(output=str(out), control=str(self.root / 'control'), image='x')))

        def prepared(runtime, name, task, arm, config):
            cell = out / name
            (cell / 'cell/trace').mkdir(parents=True)
            for file in ('plan.json', 'prompt.txt', 'baseline.json'):
                (cell / file).write_text('{}')
            return cell

        def patch(owner, **values):
            for name, value in values.items():
                self.addCleanup(setattr, owner, name, getattr(owner, name))
                setattr(owner, name, value)
        patch(rc, preflight=lambda runtime: (dict(), None), control_unchanged=lambda runtime: True, digest=lambda path: 'x',
              seal_after_teardown=lambda out: ('sealed', []), harness_unchanged=lambda out, baseline: True)
        patch(rc.prepare, prepare=prepared)
        patch(rc.cell_run, run=lambda out, runtime: dict(owner_status='EXITED_0', teardown='CLEAN', seconds=1,
                                                         identity=dict(status='MATCH')))
        patch(rc.usage, record=lambda out: dict(completeness='COMPLETE', input_tokens=1, output_tokens=1))
        patch(rc.quota, classify=lambda out: dict(execution=[], assessment=[]))
        patch(rc.locate, locate=lambda out: dict(kind='anchor', path='cell/work'))
        patch(rc.check, check=lambda out, runtime: dict(product_check_pass=True, oracle=[], scope_violations=[]))
        patch(rc.assess, assess=lambda out, runtime: [dict(complete=True)])
        patch(rc.base, verdict=lambda checks, assessments: 'COMPLETE', unassessed=lambda assessments: [])
        patch(rc.obligations, meter=lambda out: dict(satisfied=True))
        patch(rc.compliance, read=lambda out: dict(compliant=True))
        for arm in 'AIF':
            self.assertEqual(rc.run(str(self.root / 'runtime.json'), 'c-' + arm, 'SMOKE', arm, 'claude'), 0)
            verdict = json.loads((out / f'verdict-c-{arm}.json').read_text())
            self.assertEqual((verdict.get('compliance'), verdict.get('obligations')),
                             (dict(compliant=True) if arm == 'I' else None, dict(satisfied=True) if arm == 'F' else None), arm)

    def test_collection_and_verdict_write_failures_are_explicit(self):
        out = self.root / 'cell-out'
        for name in ('run', 'cell', 'tmp', 'home'):
            (out / name).mkdir(parents=True)
        (out / 'evidence.manifest.json').mkdir()  # the manifest cannot be written
        sealed, failures = self.run_cell.seal_after_teardown(out)
        self.assertIsNone(sealed)
        self.assertTrue(failures)
        self.assertEqual(self.run_cell.write_verdict(self.root / 'missing-dir/verdict.json', dict(status='COMPLETE')), 2)


class Compliance(unittest.TestCase):
    """I's methodology: a successful review by the registered other engine of exactly the submitted source."""

    def setUp(self):
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)
        self.work = self.out / 'cell/work'
        self.work.mkdir(parents=True)
        (self.out / 'home').mkdir()
        self.git('init', '-q', '-b', 'main')
        (self.work / 'src.py').write_text('base\n')
        (self.work / 'helper.py').write_text('helper\n')
        self.git('add', '.')
        self.git('commit', '-q', '-m', 'allocation')
        self.base = self.git('rev-parse', 'HEAD')
        (self.out / 'baseline.json').write_text(json.dumps(dict(allocation_sha=self.base)))
        (self.out / 'snapshot.json').write_text(json.dumps(dict(kind='anchor', path='cell/work')))
        self.config('claude')  # its registered reviewer is codex
        (self.work / 'src.py').write_text('fixed\n')  # the agent's change
        (self.work / 'repro.py').write_text('debug\n')  # a file the agent created
        self.calls = 0

    def git(self, *args, cwd=None, env=None):
        return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *args], cwd=cwd or self.work, check=True,
                              capture_output=True, text=True, env=env).stdout.strip()

    def config(self, config):
        (self.out / 'plan.json').write_text(json.dumps(dict(config=config, arm='I')))

    def reviewed_tree(self, cwd=None):
        """What the launcher records, by the shared algorithm as the cell runs it (cell environment, own hooks path)."""
        with tempfile.TemporaryDirectory() as temp:
            env = {k: v for k, v in os.environ.items() if k != 'XDG_CONFIG_HOME'} | dict(
                HOME=str(self.out / 'home'), GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1', GIT_INDEX_FILE=temp + '/index')
            for args in (('read-tree', 'HEAD'), ('add', '-A', '--', '.')):
                self.git('-c', 'core.hooksPath=/nonexistent', *args, cwd=cwd, env=env)
            return self.git('-c', 'core.hooksPath=/nonexistent', 'write-tree', cwd=cwd, env=env)

    def call(self, engine, exit_code=0, meta=None, **answer):
        """A review launcher call of the current source against the allocation commit, unless meta says otherwise."""
        self.calls += 1
        events = codex_review('T', **answer) if engine == 'codex' else claude_review('S', claude_usage(), **answer)
        return review(self.out, f'2026{self.calls:02d}', engine, events, meta=dict(dict(
            engine=engine, exit_code=exit_code, base=self.base, head=self.git('rev-parse', 'HEAD'),
            reviewed_tree=self.reviewed_tree()), **(meta or {})))

    def test_a_review_of_exactly_the_submitted_source_complies(self):
        self.call('codex')
        result = compliance.read(self.out)
        self.assertEqual((result['compliant'], result['reasons'], result['reviewer_engine'], result['final_tree']),
                         (True, [], 'codex', self.reviewed_tree()))

    def test_a_revert_a_deletion_or_a_mode_change_after_the_review_is_a_tree_mismatch(self):
        (self.work / 'helper.py').write_text('touched\n')
        helper, repro, src = (self.work / n for n in ('helper.py', 'repro.py', 'src.py'))
        for change, undo in ((lambda: helper.write_text('helper\n'), lambda: helper.write_text('touched\n')),  # baseline bytes
                             (repro.unlink, lambda: repro.write_text('debug\n')),  # the agent-created file removed
                             (lambda: src.chmod(0o755), lambda: src.chmod(0o644))):
            shutil.rmtree(self.out / 'home/.devlyn', ignore_errors=True)
            self.call('codex')
            change()
            result = compliance.read(self.out)
            self.assertEqual((result['compliant'], result['reasons']), (False, ['tree mismatch']))
            undo()
            self.assertTrue(compliance.read(self.out)['compliant'])  # the same review covers the source again

    def test_a_linked_worktree_run_location_is_read_through_its_registered_git_directory(self):
        worktree = self.out / 'tmp/task'
        self.git('worktree', 'add', '-q', '-b', 'task', str(worktree), self.base)
        (gitdir,) = (self.work / '.git/worktrees').iterdir()
        (worktree / 'src.py').write_text('fixed in the worktree\n')
        tree = self.reviewed_tree(cwd=worktree)
        (gitdir / 'gitdir').write_text('/tmp/task/.git\n')  # the container paths a cell leaves in both links
        (worktree / '.git').write_text(f'gitdir: /cell/work/.git/worktrees/{gitdir.name}\n')
        (self.out / 'snapshot.json').write_text(json.dumps(dict(kind='worktree', path='tmp/task')))
        self.call('codex', meta=dict(reviewed_tree=tree))
        self.assertEqual(compliance.read(self.out)['reasons'], [])
        (worktree / 'src.py').write_text('changed after the review\n')
        self.assertEqual(compliance.read(self.out)['reasons'], ['tree mismatch'])

    def test_a_review_against_a_later_base_saw_only_part_of_the_change(self):
        self.git('commit', '-q', '-am', 'part of the change')
        self.call('codex', meta=dict(base=self.git('rev-parse', 'HEAD')))
        self.assertEqual(compliance.read(self.out)['reasons'], ['partial base'])
        self.call('codex')
        self.assertTrue(compliance.read(self.out)['compliant'])

    def test_no_review_a_wrong_engine_and_failed_reviews_are_named(self):
        self.assertEqual(compliance.read(self.out)['reasons'], ['no review'])
        self.call('claude')
        self.call('codex', exit_code=1)
        self.call('codex', text='')
        (self.call('codex') / 'meta.json').unlink()
        result = compliance.read(self.out)
        self.assertEqual([c['reasons'] for c in result['calls']], [
            ['wrong engine'], ['failed review'], ['failed review'], ['failed review', 'tree mismatch', 'partial base']])
        self.assertEqual((result['compliant'], result['reasons']),
                         (False, ['failed review', 'partial base', 'tree mismatch', 'wrong engine']))
        self.config('codex')  # there the registered reviewer is claude
        self.assertTrue(compliance.read(self.out)['compliant'])

    def test_a_claude_answer_needs_is_error_false_and_codex_answers_with_its_last_message(self):
        self.config('codex')  # the registered reviewer is claude
        folder = self.call('claude')
        init, result = [json.loads(line) for line in (folder / 'stdout').read_text().splitlines()]
        del result['is_error']
        (folder / 'stdout').write_text(json.dumps(init) + '\n' + json.dumps(result) + '\n')
        self.assertEqual(compliance.read(self.out)['calls'][0]['reasons'], ['failed review'])
        self.config('claude')  # the registered reviewer is codex
        shutil.rmtree(self.out / 'home/.devlyn')
        folder = self.call('codex')
        message = lambda text: dict(type='item.completed', item=dict(type='agent_message', text=text))
        for texts, answered in ((['Reading the diff.', ''], False), (['', 'No findings.'], True)):
            (folder / 'stdout').write_text(''.join(json.dumps(e) + '\n' for e in [
                dict(type='thread.started', thread_id='T'), *map(message, texts)]))
            self.assertEqual(compliance.read(self.out)['calls'][0]['answered'], answered, texts)

    def test_the_host_computation_runs_no_participant_filter_and_writes_no_evidence(self):
        marker = self.out / 'filter-ran'
        self.git('config', 'filter.probe.clean', f'touch {marker}; cat')
        self.git('config', 'filter.probe.required', 'true')
        (self.work / '.gitattributes').write_text('*.py filter=probe\n')
        evidence = lambda: {p: p.read_bytes() for p in (self.work / '.git').rglob('*') if p.is_file()}  # no object holds the edits yet
        before = evidence()
        result = compliance.read(self.out)
        self.assertEqual((result['final_tree_error'], marker.exists(), evidence() == before), (None, False, True))
        self.call('codex')  # the cell runs its own filter (an identity here): the same tree
        marker.unlink()
        self.assertEqual((compliance.read(self.out)['compliant'], marker.exists()), (True, False))

    def test_host_user_ignore_files_never_hide_cell_files(self):
        self.call('codex')
        user = self.out / 'host-user'
        (user / '.config/git').mkdir(parents=True)
        (user / '.config/git/ignore').write_text('repro.py\n')
        for key, value in (('HOME', user), ('XDG_CONFIG_HOME', user / '.config')):
            original = compliance.locate.ENV
            compliance.locate.ENV = dict(original, **{key: str(value)})
            try:
                self.assertTrue(compliance.read(self.out)['compliant'], key)
            finally:
                compliance.locate.ENV = original

    def test_a_tracked_submodule_is_refused_before_git_could_run_status_inside_it(self):
        nested = self.work / 'sub'
        nested.mkdir()
        self.git('init', '-q', '-b', 'main', cwd=nested)
        (nested / 'n.txt').write_text('n\n')
        self.git('add', '.', cwd=nested)
        self.git('commit', '-q', '-m', 'n', cwd=nested)
        self.git('add', 'sub')
        self.git('commit', '-q', '-m', 'track the nested repository')
        marker = self.out / 'status-filter-ran'
        self.git('config', 'filter.probe.clean', f'touch {marker}; cat', cwd=nested)
        (nested / '.git/info').mkdir(exist_ok=True)
        (nested / '.git/info/attributes').write_text('* filter=probe\n')
        os.utime(nested / 'n.txt', (1_900_000_000, 1_900_000_000))  # a stale index entry: `git status` there would re-read it
        result = compliance.read(self.out)
        self.assertEqual((result['final_tree'], marker.exists()), (None, False))
        self.assertIn('submodule: sub', result['final_tree_error'])


INSTALLER = '''const fs = require('fs'), path = require('path');
fs.writeFileSync('INSTALLED-{arm}.md', process.argv.slice(2).join(' ') + '\\n');
if ({launcher}) {{
  fs.mkdirSync(path.join(process.env.HOME, '.devlyn'), {{recursive: true}});
  fs.writeFileSync(path.join(process.env.HOME, '.devlyn/review.js'), '// review launcher\\n');
}}
'''


@unittest.skipUnless(shutil.which('node'), 'the fake package installers need node')
class Prepare(unittest.TestCase):
    """Arm preparation with fake packages and no Docker: the install container is replaced by running the package's own
    installer on the host with the container's mounts; everything else is the real preparation."""

    def setUp(self):
        self.prepare = load('prepare')
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        (self.root / 'control/public').mkdir(parents=True)
        self.package('F', launcher=False)
        self.package('I', launcher=True)
        self.runtime = dict(output=str(self.root / 'out'), control=str(self.root / 'control'), image='fake-image',
                            sources=str(self.root), auth=str(self.root / 'auth'))
        self.installs, real = [], subprocess.run

        def run(argv, *args, **kwargs):
            if list(argv[:2]) != ['docker', 'run']:
                return real(argv, *args, **kwargs)
            mounts = {}
            for index, value in enumerate(argv):
                if value == '--mount':
                    fields = dict(f.split('=', 1) for f in argv[index + 1].split(',') if '=' in f)
                    mounts[fields['dst']] = (fields['src'], argv[index + 1].endswith(',readonly'))
            self.installs.append(dict(argv=list(argv), mounts=mounts))
            script = argv.index('/install/package/bin/devlyn.js')
            return real(['node', mounts['/install'][0] + '/package/bin/devlyn.js', *argv[script + 1:]], cwd=mounts['/work'][0],
                        env=dict(os.environ, HOME=mounts['/home/participant'][0]), check=True, capture_output=True, timeout=60)
        self.prepare.subprocess.run = run
        self.addCleanup(setattr, self.prepare.subprocess, 'run', real)

    @staticmethod
    def prompt0231(config):
        spec = importlib.util.spec_from_file_location('prepare0231t', HERE.parent / '0231/prepare.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.prompt_text(config)

    def package(self, arm, launcher):
        folder = self.root / 'control/packages' / arm / 'package/bin'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'devlyn.js').write_text(INSTALLER.format(arm=arm, launcher='true' if launcher else 'false'))

    def test_each_arm_prepares_its_own_treatment_in_both_configs(self):
        common = (HERE / 'common.txt').read_text()
        for config in ('claude', 'codex'):
            for arm in ('A', 'I', 'F'):
                count = len(self.installs)
                out = self.prepare.prepare(self.runtime, f'{config}-{arm}', 'SMOKE', arm, config)
                installs, prompt = self.installs[count:], (out / 'prompt.txt').read_text()
                baseline = json.loads((out / 'baseline.json').read_text())
                tracked = subprocess.run(['git', '-C', str(out / 'cell/work'), 'ls-files'], capture_output=True, text=True,
                                         check=True).stdout.split()
                self.assertEqual(json.loads((out / 'plan.json').read_text())['argv'][-1], prompt)
                if arm == 'A':
                    self.assertEqual((installs, [n for n in tracked if n.startswith('INSTALLED')]), ([], []))
                else:
                    (install,) = installs
                    self.assertEqual(install['mounts']['/install'], (str(self.root / 'control/packages' / arm), True))
                    self.assertEqual(install['argv'][install['argv'].index('--network') + 1], 'none')
                    self.assertEqual((out / f'cell/work/INSTALLED-{arm}.md').read_text().split(), self.prepare.INSTALL[config])
                    self.assertIn(f'INSTALLED-{arm}.md', tracked)  # the installer's output is the committed baseline
                if arm == 'F':  # 0231's control prompt and committed goal, unchanged
                    self.assertEqual(prompt, self.prompt0231(config))
                    self.assertEqual(('.task/goal.txt' in tracked, baseline['goal_sha256'] is not None), (True, True))
                else:  # A and I share the native prompt: the task frame plus this cell's caller contract
                    self.assertEqual(prompt, common + '\nCALLER CONTRACT\n' + (out / 'harness/caller.json').read_text())
                    self.assertEqual(('.task/goal.txt' in tracked, baseline['goal_sha256']), (False, None))
                self.assertEqual(((out / 'home/.devlyn/review.js').is_file(), baseline['review_sha256'] is not None),
                                 (arm == 'I', arm == 'I'))

    def test_every_arm_records_origin_HEAD_at_the_allocation_commit_through_the_transport(self):
        for arm in ('A', 'I', 'F'):
            out = self.prepare.prepare(self.runtime, 'origin-' + arm, 'SMOKE', arm, 'codex')
            git = lambda *a: subprocess.run(['git', '-C', str(out / 'cell/work'), *a], capture_output=True, text=True,
                                            check=True).stdout.strip()
            allocation = json.loads((out / 'baseline.json').read_text())['allocation_sha']
            self.assertEqual((git('symbolic-ref', 'refs/remotes/origin/HEAD'), git('merge-base', 'HEAD', 'refs/remotes/origin/HEAD')),
                             ('refs/remotes/origin/main', allocation), arm)
            self.assertIn("branch 'main' of github.com:fysoul17/devlyn-cli", (out / 'cell/work/.git/FETCH_HEAD').read_text())
            self.assertEqual(git('config', 'core.sshCommand'), '/harness/git-ssh')  # the participant's transport, unchanged

    def test_an_I_package_without_its_launcher_and_the_0231_arms_are_refused(self):
        self.package('I', launcher=False)
        with self.assertRaisesRegex(ValueError, 'review launcher'):
            self.prepare.prepare(self.runtime, 'no-launcher', 'SMOKE', 'I', 'claude')
        for arm in ('control', 'candidate'):
            with self.assertRaises(ValueError):
                self.prepare.prepare(self.runtime, 'old-' + arm, 'SMOKE', arm, 'claude')


class Control(unittest.TestCase):
    def test_F_is_pinned_and_an_unfrozen_I_is_never_packed(self):
        control = load('control')
        self.assertEqual((sorted(control.ARMS), control.ARMS['F']), (['F', 'I'], (
            '4056ebe24cba16c03bc447a8fbd4bb92cbf21edb', '48d21558e717a8b833b619d7ea696d07512cb78b6f29d13b0ccfb063ac263806')))
        with tempfile.TemporaryDirectory() as cache, self.assertRaisesRegex(ValueError, 'placeholder'):
            control.pack(Path(cache), 'I')


class Order(unittest.TestCase):
    def test_cells_are_balanced_per_config_and_replicate_two_reverses_the_order(self):
        cells = decide.CELLS
        self.assertEqual((len(cells), len({tuple(c[1:]) for c in cells})), (36, 36))
        self.assertEqual([c[0] for c in cells], [f'm{i:02d}-{t}-{cfg}-{a}-r{r}' for i, (_, t, a, cfg, r) in enumerate(cells, 1)])
        groups = [cells[i:i + 3] for i in range(0, 36, 3)]
        orders = {}
        for group in groups:  # each (task, config, replicate) runs its three arms back to back
            self.assertEqual((len({(c[1], c[3], c[4]) for c in group}), sorted(c[2] for c in group)), (1, ['A', 'F', 'I']))
            orders[group[0][1], group[0][3], group[0][4]] = ''.join(c[2] for c in group)
        for config in ('claude', 'codex'):
            for replicate in '12':
                square = [o for (task, c, r), o in orders.items() if (c, r) == (config, replicate)]
                self.assertTrue(all(sorted(o[i] for o in square) == ['A', 'F', 'I'] for i in range(3)), square)
            self.assertEqual(len({o for (task, c, r), o in orders.items() if c == config}), 6)
        for (task, config, replicate), order in orders.items():
            self.assertEqual(orders[task, config, '2' if replicate == '1' else '1'], order[::-1])
        sequence = [(g[0][1], g[0][3]) for g in groups]
        self.assertEqual(sequence[6:], sequence[:6][::-1])

    def test_smoke_runs_every_arm_in_both_configs(self):
        smoke = [line.split() for line in (HERE / 'smoke.tsv').read_text().splitlines() if line and not line.startswith('#')]
        self.assertEqual(sorted((s[1], s[2], s[3]) for s in smoke), sorted(('SMOKE', a, c) for a in 'AIF' for c in ('claude', 'codex')))


@unittest.skipUnless(os.environ.get('APPARATUS_IMAGE') and os.environ.get('APPARATUS_CONTROL'), 'container cases need the image and control tree')
class Cells(unittest.TestCase):
    """Prepared cells for each arm and config, then probes inside the cell container (no model call, no network)."""

    @classmethod
    def setUpClass(cls):
        cls.prepare = load('prepare')
        cls.root = Path(tempfile.mkdtemp(prefix='0232-cells-'))
        cls.runtime = dict(sources=str(HERE.parents[2] / '.devlyn/0206'), control=os.environ['APPARATUS_CONTROL'],
                           image=os.environ['APPARATUS_IMAGE'], output=str(cls.root / 'out'), scratch=str(cls.root),
                           auth=str(cls.root / 'auth'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root)

    def probe(self, out, script):
        control = Path(self.runtime['control'])
        argv = ['docker', 'run', '--rm', '--network', 'none', '--read-only', '--cap-drop', 'ALL', '--security-opt',
                'no-new-privileges', '--user', '501:501', '--mount', f'type=bind,src={out / "cell"},dst=/cell',
                '--mount', f'type=bind,src={out / "tmp"},dst=/tmp', '--mount', f'type=bind,src={out / "home"},dst=/home/participant',
                '--mount', f'type=bind,src={control / "public"},dst=/control,readonly',
                '--mount', f'type=bind,src={out / "harness"},dst=/harness,readonly']
        for key, value in json.loads((out / 'plan.json').read_text())['env'].items():
            argv += ['-e', f'{key}={value}']
        done = subprocess.run([*argv, '-w', '/cell/work', self.runtime['image'], 'bash', '-c', script],
                              capture_output=True, text=True, timeout=600)
        return done.returncode, done.stdout + done.stderr

    def test_each_arm_and_config_prepares_its_treatment_and_fetches_only_from_the_mirror(self):
        for config, skills in (('claude', '.claude/skills'), ('codex', '.agents/skills')):
            for arm in ('A', 'I', 'F'):
                out = self.prepare.prepare(self.runtime, f'smoke-{config}-{arm}', 'SMOKE', arm, config)
                baseline = json.loads((out / 'baseline.json').read_text())
                if arm == 'F':  # 0231's control arm: resolve allocates its task tree from the mirror
                    self.assertTrue((out / 'cell/work' / skills / 'devlyn-resolve/SKILL.md').is_file())
                    self.assertEqual((out / 'cell/work/.task/goal.txt').read_text().count('/harness/caller.json'), 1)
                    steps = f'''S={skills}/_shared
python3 $S/task-complete.py allocate --repo . --task t --branch task/t --worktree /cell/task-t --repository fysoul17/devlyn-cli --remote origin --base main >/dev/null
test "$(git -C /cell/task-t rev-parse HEAD)" = {baseline["allocation_sha"]}
cmp -s .task/goal.txt /cell/task-t/.task/goal.txt
cd /cell/task-t && python3 $S/resolve-bootstrap.py --goal-file .task/goal.txt --role-config /harness/roles.json --max-rounds 4 >/dev/null'''
                else:  # native: the contract is readable and the origin serves only the mirror's allocation commit
                    steps = f'''test -r /harness/caller.json
git fetch -q origin main && test "$(git rev-parse FETCH_HEAD)" = {baseline["allocation_sha"]}
{'test -f "$HOME/.devlyn/review.js"' if arm == 'I' else 'test ! -e "$HOME/.devlyn"'}'''
                code, text = self.probe(out, f'''set -e
if git push origin HEAD:refs/heads/x 2>/dev/null; then echo PUSHED; exit 1; fi
if git ls-remote git@github.com:other/repo.git 2>/dev/null; then echo FOREIGN; exit 1; fi
test -z "$(ls -A /control/autoresearch)" && test ! -e /install && test ! -e /control/packages
{steps}
echo OK''')
                self.assertEqual((code, text.strip().splitlines()[-1] if text.strip() else ''), (0, 'OK'), f'{config}/{arm}: {text}')

    def test_declared_checkers_read_the_linked_task_source(self):
        cases = (('D4', 'claude', '.claude/skills', 'pallets/click', '''cd /cell/task-t
python3 -c "import click; assert click.__file__.startswith('/cell/task-t/src/')"
if (cd /tmp && python3 -c "import click" 2>/dev/null); then echo SHADOW; exit 1; fi
mypy >/dev/null && pyright --ignoreexternal --verifytypes click >/dev/null
echo 'x_planted: int = "s"' >> src/click/core.py
if mypy >/dev/null 2>&1; then echo MYPY-MISSED; exit 1; fi
if pyright src/click/core.py >/dev/null 2>&1; then echo PYRIGHT-MISSED; exit 1; fi'''),
                 ('D3', 'codex', '.agents/skills', 'tj/commander.js', '''cd /cell/task-t
npm run -s check:type >/dev/null && eslint . >/dev/null
echo 'const planted: number = "s";' > lib/planted.ts
if npm run -s check:type >/dev/null 2>&1; then echo TSC-MISSED; exit 1; fi'''))
        for task, config, skills, repository, script in cases:
            out = self.prepare.prepare(self.runtime, f'tools-{task}', task, 'F', config)
            code, text = self.probe(out, f'''set -e
python3 {skills}/_shared/task-complete.py allocate --repo . --task t --branch task/t --worktree /cell/task-t --repository {repository} --remote origin --base main >/dev/null
{script}
echo OK''')
            self.assertEqual((code, text.strip().splitlines()[-1] if text.strip() else ''), (0, 'OK'), f'{task}: {text}')

    def test_an_unchanged_allocation_after_checker_runs_has_no_scope_violations(self):  # Astra apparatus #1
        locate_module, packet = load('locate'), load('check').packet
        for task, config, skills, repository, script in (
                ('D4', 'claude', '.claude/skills', 'pallets/click', 'python3 -m pytest tests/test_basic.py -q >/dev/null && mypy >/dev/null'),
                ('D3', 'codex', '.agents/skills', 'tj/commander.js', 'npm run -s check:type >/dev/null && env -u NO_COLOR node --test >/dev/null')):
            out = self.prepare.prepare(self.runtime, f'scope-{task}', task, 'F', config)
            code, text = self.probe(out, f'''set -e
python3 {skills}/_shared/task-complete.py allocate --repo . --task t --branch task/t --worktree /tmp/task-t --repository {repository} --remote origin --base main >/dev/null
cd /tmp/task-t && {script}
echo OK''')
            self.assertEqual(text.strip().splitlines()[-1] if text.strip() else '', 'OK', text)
            sealed, failures = load('run_cell').seal_after_teardown(out)  # the full post-teardown sequence
            self.assertTrue(sealed and not failures, failures)
            selection = locate_module.locate(out)
            baseline = json.loads((out / 'baseline.json').read_text())
            current = packet.tree(out / 'snapshot')
            changed = sorted(n for n in baseline['files'].keys() | current.keys() if baseline['files'].get(n) != current.get(n))
            self.assertEqual((selection['kind'], changed), ('worktree', []), task)

    def test_wrong_arm_is_refused(self):
        with self.assertRaises(ValueError):
            self.prepare.prepare(self.runtime, 'bad', 'SMOKE', 'control', 'claude')


if __name__ == '__main__':
    unittest.main()
