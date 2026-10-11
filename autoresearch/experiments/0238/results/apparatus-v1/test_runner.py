"""Synthetic native-evidence regressions and real local preparation, without models."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import tomllib
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('runner0238test', HERE / 'runner.py')
r = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r)


def lines(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows))


class ApparatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='0238-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.control = self.root / 'control'
        for name in ('public', 'oracle', 'packages'):
            (self.control / name).mkdir(parents=True)
        self.witness = self.control / 'oracle/experiments/0238/f23_precision.py'
        self.witness.parent.mkdir(parents=True)
        shutil.copyfile(HERE / 'f23_precision.py', self.witness)
        r.write(str(self.control) + '.manifest.json', dict(manifests={
            name: {str(p.relative_to(self.control / name)): r.digest(p)
                   for p in (self.control / name).rglob('*') if p.is_file()}
            for name in ('public', 'oracle', 'packages')}))
        self.runtime = self.root / 'runtime.json'
        r.write(self.runtime, dict(tasks_file=str(HERE / 'tasks-draft.json'),
                image='sha256:' + 'a' * 64, control=str(self.control), phase='smoke',
                output=str(self.root / 'out'), auth=str(self.root / 'auth'), sources=str(self.root)))
        self.app = r.Runner(self.runtime)
        self.out = self.root / 'evidence'
        self.out.mkdir()
        self.plan = dict(config='claude', engine='claude', model='claude-opus-5-5', effort='max', arm='P')
        r.write(self.out / 'plan.json', self.plan)
        self.owner_usage = dict(inputTokens=11, cacheReadInputTokens=3, cacheCreationInputTokens=2, outputTokens=4)
        lines(self.out / 'run/stdout', [dict(type='system', subtype='init', model=self.plan['model'], session_id='owner'),
            dict(type='result', session_id='owner', is_error=False, modelUsage={self.plan['model']: self.owner_usage})])

    def receipt(self, session='peer', engine='codex', turn=1, resume=None):
        folder = self.out / f'cell/work/.devlyn/peer-{turn}'
        folder.mkdir(parents=True)
        route = self.app.tasks['routes']['claude']['peer_routes']['P' if engine == 'codex' else 'H']
        capture = f'peer{turn}.json' + ('l' if engine == 'codex' else '')
        r.write(folder / 'attempt.json', dict(schema='devlyn-peer-v1', engine=engine, model=route['model'],
                effort=route['effort'], started_ns=turn * 10**9, capture=capture,
                resume=resume, source_before={'head': 'stable'}))
        r.write(folder / 'completion.json', dict(schema='devlyn-peer-v1', status='EXITED', exit_code=0,
                ended_ns=turn * 10**9 + 500000000, source_unchanged=True, source_after={'head': 'stable'}))
        if engine == 'codex':
            lines(folder / capture, [dict(type='thread.started', thread_id=session), dict(type='turn.completed',
                  usage=dict(input_tokens=100 * turn, cached_input_tokens=20 * turn, output_tokens=10 * turn))])
        else:
            r.write(folder / capture, dict(type='result', is_error=False, session_id=session,
                    modelUsage={route['model']: {key: value * turn for key, value in self.owner_usage.items()}}))
        return folder

    def codex(self, session='peer', child=True, turn=1, effort='max', model='gpt-6-astra', completed=True):
        trace = self.out / f'cell/trace/trace-{turn}-{session}'
        trace.mkdir(parents=True)
        r.write(trace / 'manifest.json', dict(schema_version=1, rollout_id=session, root_thread_id=session,
                                             started_at_unix_ms=turn * 1000))
        events = []
        members = [(session, model, effort, None)]
        if child:
            members.append(('child', 'gpt-6-sol', 'high', session))
        for thread, selected, level, parent in members:
            name = 'configuration-' + thread + '.json'
            r.write(trace / name, dict(thread_id=thread, model=selected, reasoning_effort=level))
            events += [dict(payload=dict(type='thread_started', thread_id=thread)),
                       dict(payload=dict(type='protocol_event_observed', event_type='session_configured',
                                         event_payload=dict(path=name))),
                       dict(payload=dict(type='inference_started', inference_call_id=thread + str(turn),
                                         thread_id=thread, model=selected))]
            usage = dict(input_tokens=100, cached_input_tokens=20, cache_write_input_tokens=0,
                         output_tokens=10, reasoning_output_tokens=2)
            r.write(trace / ('usage-' + thread + '.json'), dict(token_usage=usage))
            if completed:
                events.append(dict(payload=dict(type='inference_completed', inference_call_id=thread + str(turn),
                                                response_payload=dict(path='usage-' + thread + '.json'))))
            native = self.out / f'home/.codex/sessions/{thread}.jsonl'
            old = self.app.frame.cell_run.evidence.lines(native)
            meta = dict(id=thread, source=dict(subagent=dict(thread_spawn=dict(parent_thread_id=parent)))) if parent else dict(id=thread, source='exec')
            context = dict(type='turn_context', payload=dict(model=selected, effort=level,
                          sandbox_policy=dict(type='read-only'), approval_policy='never'))
            lines(native, (old or [dict(type='session_meta', payload=meta)]) + [context,
                  dict(type='event_msg', payload=dict(type='token_count', info=dict(
                       total_token_usage={key: value * turn for key, value in usage.items()})))])
        events.append(dict(payload=dict(type='rollout_ended', status='completed')))
        lines(trace / 'trace.jsonl', events)
        return trace

    def claude(self, turn=1, effort='max', model='claude-opus-5-5'):
        path = self.out / 'home/.claude/projects/work/peer.jsonl'
        rows = self.app.frame.cell_run.evidence.lines(path)
        rows.append(dict(type='assistant', sessionId='peer', effort=effort,
                         timestamp=f'1970-01-01T00:00:0{turn}.200Z',
                         message=dict(id='message' + str(turn), model=model,
                            content=[dict(type='text', text='review')], usage=dict(input_tokens=11,
                            cache_read_input_tokens=3, cache_creation_input_tokens=2, output_tokens=4))))
        lines(path, rows)

    def check(self):
        return r.policy.check(self.out, self.plan, self.app.tasks, self.app.frame.cell_run.evidence)

    def test_matched_modules_and_registered_routes(self):
        self.assertIs(self.app.frame.cell_run.evidence, self.app.frame.usage.evidence)
        for module in (self.app.frame.prepare, self.app.frame.cell_run.evidence, self.app.frame.check.base):
            self.assertIs(module.TASKS, self.app.tasks)
        self.assertIn(str(HERE.parent / '0234/record_usage.py'), self.app.inputs())
        changed = copy.deepcopy(self.app.tasks)
        changed['routes']['claude']['peer_routes']['H']['effort'] = 'high'
        with self.assertRaisesRegex(ValueError, 'exact owner'):
            r.policy.route_for(changed, 'claude', 'H')

    def test_both_cli_defaults_and_trust_seeded_before_seal(self):
        for config in ('claude', 'codex'):
            with patch.object(self.app, 'validate'):
                out = self.app.prepare('local-' + config, 'S2', 'A', config)
            settings = r.read(out / 'home/.claude/settings.json')
            self.assertEqual(settings['effortLevel'], 'max')
            self.assertFalse(settings['syncClaudeAiSkills'])
            self.assertFalse(settings['syncClaudeAiPlugins'])
            codex = out / 'home/.codex/config.toml'
            conf = tomllib.loads(codex.read_text())
            self.assertEqual(conf['model_reasoning_effort'], 'max')
            self.assertEqual(conf['agents']['default_subagent_reasoning_effort'], 'high')
            self.assertEqual(conf['projects'], {'/cell/work': {'trust_level': 'trusted'}})
            self.assertEqual(r.read(out / 'baseline.json')['tasks_sha256'], r.digest(self.app.tasks_path))
            self.app.unchanged(out)
            codex.write_text(codex.read_text() + '\n')
            with self.assertRaisesRegex(ValueError, 'prepared cell changed'):
                self.app.unchanged(out)

    def test_zero_peer_is_valid_not_forced_activation(self):
        self.assertEqual(self.check()['status'], 'MATCH')
        self.assertFalse(self.check()['activated'])

    def test_codex_peer_child_and_resumed_turn_full_accounting(self):
        self.receipt(); self.codex()
        self.receipt(turn=2, resume='peer'); self.codex(turn=2)
        result = self.check()
        self.assertEqual(result['status'], 'MATCH', result)
        self.assertEqual(result['codex_roles']['child'], ['peer', 'peer'])
        usage = self.app.frame.usage.record(self.out)
        self.assertEqual(usage['completeness'], 'COMPLETE', usage)
        self.assertEqual(usage['input_tokens'], 416)
        self.assertEqual(usage['output_tokens'], 44)

    def test_wrong_resume_effort_and_missing_effort_are_rejected(self):
        self.receipt(); self.codex(child=False)
        self.receipt(turn=2, resume='peer'); self.codex(child=False, turn=2, effort=None)
        self.assertEqual(self.check()['status'], 'MISMATCH')

    def test_wrong_root_model_is_not_hidden_by_allowed_child(self):
        self.receipt(); self.codex(model='gpt-6-sol', effort='high')
        self.assertEqual(self.check()['status'], 'MISMATCH')

    def test_missing_trace_usage_stays_partial_and_lower_bound(self):
        self.receipt(); self.codex(child=False, completed=False)
        usage = self.app.frame.usage.record(self.out)
        self.assertEqual(usage['completeness'], 'PARTIAL', usage)
        self.assertTrue(any('without completed usage' in gap for gap in usage['gaps']))
        self.assertGreater(usage['input_tokens'], 0)

    def test_unreceipted_independent_session_is_unknown(self):
        self.codex(child=False)
        self.assertEqual(self.check()['status'], 'UNVERIFIED')

    def test_failed_helper_before_native_trace_does_not_become_zero_peer(self):
        rows = self.app.frame.cell_run.evidence.lines(self.out / 'run/stdout')
        rows.append(dict(type='assistant', message=dict(content=[dict(type='tool_use', input=dict(
            command='python3 /installed/_shared/peer.py --engine codex --repo missing'))])))
        lines(self.out / 'run/stdout', rows)
        self.assertEqual(self.check()['status'], 'UNVERIFIED')

    def test_native_owner_child_is_not_an_independent_peer(self):
        self.codex(session='owner', child=True)
        self.plan.update(config='codex', engine='codex', model='gpt-6-astra', arm='B')
        lines(self.out / 'run/stdout', [dict(type='thread.started', thread_id='owner')])
        self.assertEqual(self.check()['status'], 'MATCH')
        self.assertEqual(self.check()['codex_roles']['child'], ['owner', 'owner'])

    def test_solo_peer_is_visible_violation(self):
        self.receipt(); self.codex(child=False)
        self.plan['arm'] = 'B'
        self.assertIn('independent peer in solo arm', self.check()['violations'])

    def test_claude_each_resume_requires_own_native_effort_message(self):
        self.plan['arm'] = 'H'
        self.receipt(engine='claude'); self.claude()
        self.receipt(engine='claude', turn=2, resume='peer')
        self.assertEqual(self.check()['status'], 'UNVERIFIED')
        self.claude(turn=2, effort=None)
        self.assertEqual(self.check()['status'], 'MISMATCH')

    def test_source_changed_during_peer_is_visible_product_protocol_failure(self):
        folder = self.receipt(); self.codex(child=False)
        completion = r.read(folder / 'completion.json')
        completion['source_after'] = {'head': 'changed'}
        r.write(folder / 'completion.json', completion)
        result = self.check()
        self.assertEqual(result['status'], 'MATCH')
        self.assertIn('source changed while peer reviewed it', result['protocol_violations'])

    def test_earlier_wrong_native_config_is_not_hidden_by_later_correct(self):
        self.receipt(); trace = self.codex(child=False)
        r.write(trace / 'wrong.json', dict(thread_id='peer', model='gpt-6-astra', reasoning_effort='high'))
        rows = self.app.frame.cell_run.evidence.lines(trace / 'trace.jsonl')
        rows.insert(1, dict(payload=dict(type='protocol_event_observed', event_type='session_configured',
                                         event_payload=dict(path='wrong.json'))))
        lines(trace / 'trace.jsonl', rows)
        self.assertEqual(self.check()['status'], 'MISMATCH')

    def test_f23_preserves_old_rows_and_requires_supplement_exit_contract(self):
        def evaluate(runtime, work, argv):
            value = dict(exit_code=0, argv=argv, timeout=False, stdout='', stderr='')
            if 'python3' in argv:
                value['stdout'] = json.dumps(dict(rows=[dict(id=name, status='PASS') for name in
                                          ('submillisecond-order', 'offset-equivalence')]))
            return value
        with patch.object(self.app.frame.check, 'in_image', side_effect=evaluate):
            result = self.app.evaluate(self.root, 'F23', self.app.runtime)
        self.assertEqual([row['id'] for row in result['rows']],
                         ['priority-rollback', 'single-warehouse-fefo', 'submillisecond-order', 'offset-equivalence'])
        def contradiction(*args):
            value = evaluate(*args)
            if 'python3' in args[-1]:
                value['exit_code'] = 1
            return value
        with patch.object(self.app.frame.check, 'in_image', side_effect=contradiction):
            with self.assertRaisesRegex(ValueError, 'unambiguous verdict'):
                self.app.evaluate(self.root, 'F23', self.app.runtime)


if __name__ == '__main__':
    unittest.main()
