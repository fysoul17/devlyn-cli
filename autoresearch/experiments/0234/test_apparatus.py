"""Model-free registration and apparatus tests for 0234."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent

def load(name):
    spec = importlib.util.spec_from_file_location('test_0234_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

control, prepare, decide, diagnostics, calibrate, generate, cell, usage, runner = (
    load(name) for name in ('control', 'prepare', 'decide', 'diagnostics', 'calibrate', 'generate_cells',
                           'cell', 'record_usage', 'run_cell'))

class Registration(unittest.TestCase):
    def test_arms_and_pins(self):
        self.assertEqual(set(control.ARMS), {'B', 'H', 'P'})
        self.assertEqual(set(prepare.ARMS), {'A', 'B', 'H', 'P'})
        self.assertEqual(control.ARMS['B'][1], '6f03f5ac2895eaccc22ff12d1644a0fc623baca1eec7d00e877ce3254d33352d')
        self.assertEqual(control.ARMS['H'], ('dc3c4ee60f4750c2460cb821ebc913ec367e8ac9',
                                             'e2d429df04d44476e758e28c9c038f9d38948b850b1564311a4973c95a5e0395'))
        self.assertEqual(control.ARMS['P'], ('276696beee6a5039fbb415c5c7cb3a9a439b722a',
                                             'd297c21f05f6a339688b0d42e316bc4caa463093b23c1328163277a207059200'))
        for commit, digest in control.ARMS.values():
            self.assertEqual((len(commit), len(digest)), (40, 64))
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / 'H.tgz').write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError, 'sha256 mismatch'):
                control.pack(Path(temp), 'H')

    def test_requests_and_hashes(self):
        old = next(t for t in json.loads((HERE.parent / '0222/tasks.json').read_text())['tasks'] if t['id'] == 'I0185')['request']
        i = next(t for t in prepare.TASKS['tasks'] if t['id'] == 'I0185')
        sentence = ' The root research owner handles local-only experimental delivery.'
        self.assertEqual(i['request'], old.replace(sentence, ''))
        self.assertEqual(i['request_sha256_original'], hashlib.sha256(old.encode()).hexdigest())
        self.assertEqual(i['request_sha256_adapted'], hashlib.sha256(i['request'].encode()).hexdigest())
        for task, folder in [('F16', 'F16-cli-quote-tax-rules'), ('F23', 'F23-cli-fulfillment-wave'),
                             ('F25', 'F25-cli-cart-promotion-rules')]:
            with self.subTest(task=task):
                fixture = HERE.parents[2] / 'benchmark/auto-resolve/fixtures' / folder
                spec = (fixture / 'spec.md').read_text()
                requirements = '## Requirements\n' + spec.split('## Requirements\n', 1)[1].split('\n## ', 1)[0].rstrip() + '\n'
                original = (fixture / 'task.txt').read_text()
                adapted = original.rstrip() + '\n\n' + requirements
                row = next(t for t in prepare.TASKS['tasks'] if t['id'] == task)
                self.assertEqual(row['request'], adapted)
                self.assertTrue(row['request'].startswith(original))
                self.assertEqual(row['request_sha256_original'], hashlib.sha256(original.encode()).hexdigest())
                self.assertEqual(row['request_sha256_adapted'], hashlib.sha256(adapted.encode()).hexdigest())
                self.assertNotIn('Solo-headroom', row['request'])

    def test_source_seals_and_routes(self):
        for task in prepare.TASKS['tasks']:
            self.assertEqual(prepare.packet.content(prepare.packet.tree(HERE.parents[2] / task['source_dir'])),
                             task['source_sha256'], task['id'])
        for config, route in prepare.TASKS['routes'].items():
            self.assertEqual(route['peer_routes']['H']['engine'], config)
            self.assertNotEqual(route['peer_routes']['P']['engine'], config)
            self.assertEqual(route['peer_routes']['H']['effort'], 'high')
            self.assertEqual(route['peer_routes']['P']['effort'], 'high')

    def test_cli_defaults_and_s2(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'output').mkdir(); (root / 'sources').mkdir()
            runtime = dict(output=str(root / 'output'), sources=str(root / 'sources'), image='unused',
                           control=str(root / 'control'), auth=str(root / 'auth'))
            out = prepare.prepare(runtime, 'smoke', 'S2', 'A', 'claude')
            self.assertIn('model = "gpt-6-astra"', (out / 'home/.codex/config.toml').read_text())
            self.assertIn('default_subagent_model = "gpt-6-sol"', (out / 'home/.codex/config.toml').read_text())
            self.assertEqual(json.loads((out / 'home/.claude/settings.json').read_text()),
                             {'model': 'claude-opus-5-5', 'effortLevel': 'high'})
            plan = json.loads((out / 'plan.json').read_text())
            self.assertIsNone(plan['peer_route'])
            self.assertEqual(plan['env']['CLAUDE_CODE_EFFORT_LEVEL'], 'high')

    def test_calibration_discovery(self):
        for task in calibrate.NEW:
            spec = next(t for t in prepare.TASKS['tasks'] if t['id'] == task)
            variants = {p.name for p in (HERE / 'calibration' / task).iterdir() if p.is_dir()}
            self.assertTrue(any(v.startswith('good') for v in variants))
            for row in spec['oracle']:
                self.assertTrue(any(v == f'bad-{row}' or v.startswith(f'bad-{row}-') for v in variants), (task, row))

    def test_new_reference_rows(self):
        result = calibrate.run(tasks=('F16', 'F23', 'F25'))
        self.assertEqual(len(result), 17)
        self.assertEqual(result['F16/bad-stock-error-duplicate'], ['stock-error'])
        self.assertEqual(result['F23/bad-priority-rollback'], ['priority-rollback'])
        self.assertEqual(result['F23/good-zero-rows'], [])
        self.assertEqual(result['F16/bad-shipping-base'], ['shipping-base'])
        self.assertEqual(result['F25/bad-shipping-bases-subtotal'], ['shipping-bases'])
        self.assertEqual(result['F25/bad-shipping-bases-post-line'], ['shipping-bases'])
        self.assertEqual(result['F25/bad-exact-success-promotion-order'], ['exact-success'])

    def test_all_slots_frozen(self):
        cells = generate.generate()
        self.assertEqual([len(cells[key]) for key in ('smoke.tsv', 'screening.tsv', 'cells.tsv')], [4, 12, 130])
        self.assertEqual(tuple(generate.POOL), decide.POOL)
        for name, rows in cells.items():
            self.assertEqual((HERE / name).read_text(), generate.render(rows))
        self.assertEqual(generate.DEVELOPMENT_ORDER['claude'][0].index('P'), 3)
        self.assertEqual(generate.DEVELOPMENT_ORDER['claude'][1].index('P'), 0)
        self.assertEqual([r[2] for r in cells['cells.tsv'] if r[1] == 'E1' and r[3] == 'claude' and r[0].startswith('e')], ['B', 'P'])

    def test_development_dispatch_depends_on_eligible_slot(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            Gating().screens(out, {('I0185', 'claude'), ('F23', 'claude'), ('F25', 'codex'), ('F11', 'codex')})
            rows = generate.dispatch_order(out)
            for config, tasks in [('claude', ('I0185', 'F23')), ('codex', ('F25', 'F11'))]:
                for slot, task in enumerate(tasks):
                    arms = ''.join(dict.fromkeys(r[2] for r in rows if r[1] == task and r[3] == config and r[0].startswith('d')))
                    self.assertEqual(arms, generate.DEVELOPMENT_ORDER[config][slot])

class Gating(unittest.TestCase):
    def screens(self, out, eligible):
        for name, task, arm, config, rep in decide.SCREENING:
            status = 'INCOMPLETE' if (task, config) in eligible else 'COMPLETE'
            (out / f'verdict-{name}.json').write_text(json.dumps(dict(status=status, oracle=[{'status': 'PASS'}])))

    def test_first_two_and_next_two_per_config(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            self.screens(out, {('I0185', 'claude'), ('F23', 'claude'), ('F25', 'claude'), ('F10', 'claude'),
                               ('F16', 'codex'), ('F11', 'codex')})
            selected = decide.selected_tasks(out)
            self.assertEqual(selected['claude'], {'development': ['I0185', 'F23'], 'confirmation': ['F25', 'F10']})
            self.assertEqual(selected['codex'], {'development': ['F16', 'F11'], 'confirmation': []})

    def test_screening_adjudication_blocks_gating(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp); self.screens(out, set())
            name = decide.SCREENING[0][0]
            (out / f'verdict-{name}.json').write_text(json.dumps(dict(status='ADJUDICATE',
                oracle=[{'id': 'one', 'status': 'NOT_TRIGGERED'}])))
            with self.assertRaisesRegex(ValueError, 'screening needs root adjudication'):
                decide.selected_tasks(out)
            (out / 'screening-adjudication.json').write_text(json.dumps({name: {'complete': True,
                'rows': {'one': 'PASS'}}}))
            self.assertFalse(decide.eligibility(out)[('I0185', 'claude')])

    def test_not_run_before_preflight(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp); self.screens(out, set())
            runtime = out / 'runtime.json'; runtime.write_text(json.dumps({'output': str(out)}))
            name, task, arm, config, _ = next(r for r in decide.CELLS if r[0].startswith('c'))
            with mock.patch.object(runner, 'preflight', side_effect=AssertionError('must not preflight')):
                self.assertEqual(runner.run(runtime, name, task, arm, config), 0)
            self.assertEqual(json.loads((out / f'verdict-{name}.json').read_text())['status'], 'NOT_RUN')

    def test_i0185_a_reuse_period(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); out = root / 'out'; out.mkdir(); old = root / 'old'; old.mkdir()
            self.screens(out, {('I0185', 'claude')})
            name, task, arm, config, _ = next(r for r in decide.CELLS if r[1:4] == ['I0185', 'A', 'claude'])
            source = decide.REUSED_I0185[(config, 1)]
            (old / source).mkdir()
            (old / f'verdict-{source}.json').write_text(json.dumps({'status': 'COMPLETE', 'oracle': [], 'cell': source}))
            (old / source / 'checks.json').write_text(json.dumps({'public': []}))
            (old / source / 'seal.json').write_text(json.dumps({'sealed_at': '2026-10-07T00:00:00Z'}))
            runtime = root / 'runtime.json'; runtime.write_text(json.dumps({'output': str(out), 'reuse_0233_output': str(old)}))
            with mock.patch.object(runner, 'preflight', side_effect=AssertionError('must reuse')):
                self.assertEqual(runner.run(runtime, name, task, arm, config), 0)
            verdict = json.loads((out / f'verdict-{name}.json').read_text())
            self.assertEqual((verdict['reused_from'], verdict['period']), (source, '2026-10-07T00:00:00Z'))

    def test_i0185_missing_reuse_is_not_dispatched(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp); self.screens(out, {('I0185', 'claude')})
            runtime = out / 'runtime.json'; runtime.write_text(json.dumps({'output': str(out)}))
            name, task, arm, config, _ = next(r for r in decide.CELLS if r[1:4] == ['I0185', 'A', 'claude'])
            self.assertEqual(runner.run(runtime, name, task, arm, config), 3)
            self.assertFalse((out / f'verdict-{name}.json').exists())
            self.assertIn('reuse evidence unavailable', (out / f'not-dispatched-{name}.json').read_text())

class Decision(unittest.TestCase):
    def row(self, task, arm, panel, rep=1, wall=None, complete=True, usage=True, passed=True):
        return dict(name=f'{task}-{arm}-{rep}', task=task, arm=arm, panel=panel, config='codex', replicate=rep,
                    complete=complete, rows={'oracle': passed}, scope=False, false_completion=False, harm=False,
                    reproduced=set(), wall=wall if wall is not None else {'A': 12, 'B': 10, 'H': 9, 'P': 8}[arm],
                    input=100, output=10, usage=usage, reused_from=None, period=None)

    def table(self, confirmation=True):
        rows = [self.row('I0185', arm, 'development') for arm in 'ABHP']
        if confirmation:
            rows += [self.row('F16', arm, 'confirmation', rep) for rep in (1, 2) for arm in 'ABP']
        rows += [self.row('E1', arm, 'easy') for arm in 'BP']
        return {r['name'] + r['panel']: r for r in rows}

    def rule(self, table):
        return decide.config_rule(table, 'codex', {(t, 'codex'): t in ('I0185', 'F16') for t in decide.POOL})

    def test_pass_and_exploratory_comparisons(self):
        result = self.rule(self.table())
        self.assertEqual((result['confirmation'], result['admitted']), ('PASS', 'P'))
        self.assertEqual(list(result['panels']['development']['comparisons']), ['P/B', 'P/A', 'H/B', 'P/H', 'B/A'])

    def test_unconfirmed(self):
        table = self.table()
        for row in table.values():
            if row['panel'] == 'confirmation' and row['arm'] == 'P': row['usage'] = False
        self.assertEqual((self.rule(table)['confirmation'], self.rule(table)['admitted']), ('UNCONFIRMED', 'P-unconfirmed'))

    def test_no_headroom(self):
        result = self.rule(self.table(confirmation=False))
        self.assertEqual((result['confirmation'], result['admitted']), ('NO_HEADROOM', None))

    def test_no_eligible_tasks(self):
        table = {name: row for name, row in self.table().items() if row['panel'] == 'easy'}
        result = self.rule(table)
        self.assertEqual(result['panels']['development']['status'], 'NO_HEADROOM')
        self.assertEqual((result['confirmation'], result['admitted']), ('NO_HEADROOM', None))

    def test_quality_veto(self):
        table = self.table()
        for row in table.values():
            if row['panel'] == 'confirmation' and row['arm'] == 'P': row['rows']['oracle'] = False
        self.assertEqual((self.rule(table)['confirmation'], self.rule(table)['admitted']), ('FAIL', None))

    def test_zero_success_veto(self):
        table = self.table()
        for row in table.values():
            if row['panel'] == 'confirmation' and row['arm'] == 'P': row['complete'] = False
        self.assertEqual((self.rule(table)['confirmation'], self.rule(table)['admitted']), ('FAIL', None))

    def test_development_zero_success_quality_fails_before_no_claim(self):
        rows = [self.row('I0185', arm, 'development') for arm in 'BP']
        rows[1]['complete'] = False; rows[1]['scope'] = True
        self.assertEqual(decide.compare(rows, 'P', 'B', 1, True)['outcome'], 'FAIL')
        rows[1]['scope'] = False
        rows[0]['complete'] = False
        self.assertEqual(decide.compare(rows, 'P', 'B', 1, True)['outcome'], 'NO_CLAIM')

    def test_development_a_second_replicate_is_descriptive_only(self):
        rows = [self.row('I0185', arm, 'development') for arm in 'ABHP']
        second = self.row('I0185', 'A', 'development', 2, complete=False)
        second['reused_from'] = 'old-A-r2'; second['period'] = 'old'
        result = decide.panel_rule(rows + [second], 'development')
        self.assertEqual(result['sums']['A']['S'], 1)
        self.assertEqual(result['descriptive_a_replicate_2'][0]['report']['S'], 0)

    def test_development_failure_blocks_pass(self):
        table = self.table()
        for row in table.values():
            if row['panel'] == 'development' and row['arm'] == 'P': row['wall'] = 100
        self.assertIsNone(self.rule(table)['admitted'])

    def test_easy_tripwire_preserves_each_dimension(self):
        table = self.table()
        for row in table.values():
            if row['panel'] == 'easy' and row['arm'] == 'P':
                row['wall'] = 13; row['usage'] = False
        tripwire = self.rule(table)['panels']['easy']['tripwire']
        self.assertEqual(tripwire['status'], 'TRIGGERED')
        self.assertTrue(tripwire['checks']['wall'])
        self.assertIsNone(tripwire['checks']['input'])

class PeerDiagnostics(unittest.TestCase):
    def test_naming_the_wrapper_is_not_a_launch(self):
        self.assertIsNone(diagnostics.launch_engine('sed -n 1,40p .claude/skills/_shared/codex-monitored.sh'))
        self.assertIsNone(diagnostics.launch_engine('grep -n claude -p README.md'))
        self.assertEqual(diagnostics.launch_engine(
            'CODEX_MONITORED_TIMEOUT_SEC=540 bash /x/codex-monitored.sh --json -s read-only -C . "$(cat t)" > p'), 'codex')
        self.assertEqual(diagnostics.launch_engine('timeout -k 5s 540s claude -p --session-id $U < t > p.json'), 'claude')
        self.assertEqual(diagnostics.launch_engine('timeout -k 5s 540s /usr/local/bin/claude -p < t > p.json'), 'claude')

    def test_heredoc_prose_is_not_a_redirect(self):
        call = {'tool': 'Bash', 'input': {'command': "mkdir -p .devlyn/pair && cat > .devlyn/pair/turn1.md <<'EOF'\n"
                                         "(5, 50, 0) -> 3 and 13.5 -> 14\nEOF\necho done"}, 'output': ''}
        self.assertEqual(diagnostics.paths(call), [])

    def test_redirect_capture_is_not_an_edit(self):
        rows = [dict(type='item.started', item=dict(id='a', type='command_execution',
                    command='claude -p --output-format json > .devlyn/pair/peer1.json')),
                dict(type='item.completed', item=dict(id='a', exit_code=0, aggregated_output=''))]
        self.assertIsNone(diagnostics.summarize(rows, 'codex', 'P')['guide_read']['first_edit_any'])
        rows[0]['item']['command'] = 'codex exec --json > /dev/null'
        self.assertIsNone(diagnostics.summarize(rows, 'codex', 'P')['guide_read']['first_edit_any'])

    def test_guide_read_requires_heading_in_result(self):
        rows = [dict(type='item.started', item=dict(id='a', type='command_execution', command='cat _shared/pair.md')),
                dict(type='item.completed', item=dict(id='a', exit_code=0, aggregated_output='a mention'))]
        self.assertEqual(diagnostics.summarize(rows, 'codex', 'P')['guide_read']['status'], 'mentioned')
        rows[-1]['item']['aggregated_output'] = '# Pair reasoning\n'
        self.assertEqual(diagnostics.summarize(rows, 'codex', 'P')['guide_read']['status'], 'read')
        self.assertEqual(diagnostics.summarize(rows, 'codex', 'B')['guide_read']['status'], 'absent')

    def test_codex_trace_continuity_and_owner_exit(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp); (out / 'run').mkdir(); (out / 'cell/trace/trace-peer/payloads').mkdir(parents=True)
            (out / 'home/.codex/sessions').mkdir(parents=True)
            trace = out / 'cell/trace/trace-peer'
            (trace / 'manifest.json').write_text(json.dumps({'rollout_id': 'PEER', 'root_thread_id': 'PEER', 'raw_event_log': 'trace.jsonl'}))
            (trace / 'payloads/config.json').write_text(json.dumps({'thread_id': 'PEER', 'model': 'gpt-6-astra', 'reasoning_effort': 'high'}))
            (trace / 'trace.jsonl').write_text(json.dumps({'payload': {'type': 'protocol_event_observed', 'event_type': 'session_configured', 'event_payload': {'path': 'payloads/config.json'}}}) + '\n')
            (out / 'run/result.json').write_text(json.dumps({'started_at': 100, 'seconds': 20}))
            calls = [dict(tool='Bash', input={'command': 'bash codex-monitored.sh --json > peer.jsonl'}, output='{"thread_id":"PEER"}',
                          exit_code=0, start='1970-01-01T00:01:45Z', end='1970-01-01T00:01:50Z'),
                     dict(tool='Bash', input={'command': 'bash codex-monitored.sh resume --json PEER'}, output='',
                          exit_code=None, start='1970-01-01T00:01:55Z', end=None)]
            plan = {'engine': 'claude', 'config': 'claude', 'arm': 'P', 'peer_route': {'engine': 'codex', 'model': 'gpt-6-astra', 'effort': 'high'}}
            result = diagnostics.peer_turns(calls, out, plan)
            self.assertEqual([p['session'] for p in result['turns']], ['PEER', 'PEER'])
            self.assertTrue(result['continuity'])
            self.assertTrue(result['owner_ended_while_peer_running'])
            self.assertTrue(result['turns'][0]['route_match'])

    def test_claude_transcript_effort_and_continuity(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp); (out / 'run').mkdir(); (out / 'cell/trace').mkdir(parents=True)
            captures = out / 'cell/work/.devlyn/pair'; captures.mkdir(parents=True)
            for n, tokens in ((1, 2), (2, 4)):
                (captures / f'peer{n}.json').write_text(json.dumps(dict(type='result', session_id='PEER',
                    is_error=False, modelUsage={'claude-opus-5-5': {'inputTokens': tokens,
                    'cacheReadInputTokens': 0, 'cacheCreationInputTokens': 0, 'outputTokens': tokens}})))
            folder = out / 'home/.claude/projects/fixture'; folder.mkdir(parents=True)
            event = {'type': 'assistant', 'sessionId': 'PEER', 'effort': 'high',
                     'message': {'id': 'm1', 'model': 'claude-opus-5-5', 'usage': {'output_tokens': 1}}}
            (folder / 'PEER.jsonl').write_text(json.dumps(event) + '\n')
            (out / 'run/result.json').write_text(json.dumps({'started_at': 100, 'seconds': 20}))
            calls = [dict(tool='Bash', input={'command': 'claude -p --session-id PEER'}, output='result',
                          error=False, exit_code=None, start='1970-01-01T00:01:45Z', end='1970-01-01T00:01:50Z'),
                     dict(tool='Bash', input={'command': 'claude -p --resume PEER'}, output='result',
                          error=False, exit_code=None, start='1970-01-01T00:01:55Z', end='1970-01-01T00:02:00Z')]
            plan = {'engine': 'codex', 'config': 'codex', 'arm': 'P', 'peer_route': {'engine': 'claude', 'model': 'claude-opus-5-5', 'effort': 'high'}}
            result = diagnostics.peer_turns(calls, out, plan)
            self.assertTrue(result['continuity'])
            self.assertTrue(result['turns'][0]['route_match'])
            self.assertEqual(result['completed'], 2)
            self.assertFalse(result['owner_ended_while_peer_running'])
            stream = [dict(type='assistant', message={'content': [{'type': 'tool_use', 'name': 'Bash',
                       'id': 'tool1', 'input': {'command': 'claude -p --session-id PEER'}}]}),
                      dict(type='user', message={'content': [{'type': 'tool_result', 'tool_use_id': 'tool1',
                           'content': 'finished', 'is_error': False}]})]
            untimed = diagnostics.calls(stream, 'claude')
            self.assertTrue(untimed[0]['returned'])
            self.assertIsNone(untimed[0]['end'])
            self.assertTrue(diagnostics.peer_turns(untimed, out, plan)['turns'][0]['completed'])

    def test_background_return_is_not_process_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp); (out / 'run').mkdir(); (out / 'cell/trace').mkdir(parents=True)
            (out / 'run/result.json').write_text(json.dumps({'started_at': 100, 'seconds': 20}))
            calls = [dict(tool='Bash', input={'command': 'claude -p --session-id PEER > .devlyn/pair/peer1.json &'},
                          output='started', error=False, exit_code=None,
                          start='1970-01-01T00:01:45Z', end='1970-01-01T00:01:46Z')]
            plan = {'engine': 'codex', 'config': 'codex', 'arm': 'H', 'peer_route': {'engine': 'claude', 'model': 'claude-opus-5-5', 'effort': 'high'}}
            result = diagnostics.peer_turns(calls, out, plan)
            self.assertFalse(result['turns'][0]['completed'])
            self.assertTrue(result['owner_ended_while_peer_running'])
            calls[0]['input'] = {'command': 'claude -p --session-id PEER', 'run_in_background': True}
            result = diagnostics.peer_turns(calls, out, plan)
            self.assertTrue(result['turns'][0]['background'])
            self.assertTrue(result['owner_ended_while_peer_running'])
            calls[0]['input'] = {'command': 'claude -p --session-id PEER > .devlyn/pair/peer1.json & echo $!'}
            result = diagnostics.peer_turns(calls, out, plan)
            self.assertTrue(result['turns'][0]['background'])

    def test_claude_peer_sidechain_is_not_owner_child(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp); (out / 'run').mkdir(); (out / 'cell/trace').mkdir(parents=True)
            (out / 'run/stdout').write_text(json.dumps({'type': 'system', 'subtype': 'init', 'session_id': 'OWNER',
                                                       'model': 'claude-opus-5-5'}) + '\n')
            folder = out / 'home/.claude/projects/fixture'; folder.mkdir(parents=True)
            events = [dict(type='assistant', sessionId=s, parentSessionId=p, isSidechain=True,
                           message=dict(id=s, model='claude-opus-5-5', usage={'output_tokens': 1}))
                      for s, p in [('CHILD', 'OWNER'), ('PEER', 'INDEPENDENT')]]
            (folder / 'sessions.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))
            from importlib import util
            spec = util.spec_from_file_location('evidence_test', HERE / 'evidence.py')
            evidence = util.module_from_spec(spec); spec.loader.exec_module(evidence)
            inv = evidence.inventory(out, {'engine': 'claude', 'config': 'claude'})
            self.assertEqual(inv['owner_launched_claude'], ['PEER'])

class PeerUsage(unittest.TestCase):
    @staticmethod
    def counters(n):
        return {'inputTokens': n, 'cacheReadInputTokens': 0, 'cacheCreationInputTokens': 0, 'outputTokens': n}

    def test_turn_envelopes_in_linked_tree_and_tmp_count_once(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            paths = [out / 'cell/wt-peer/.devlyn/pair/peer1.json', out / 'tmp/peer2.json']
            for n, path in enumerate(paths, 1):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({'type': 'result', 'session_id': 'PEER', 'modelUsage':
                                 {'claude-opus-5-5': self.counters(n * 2)}, 'is_error': False}))
            from importlib import util
            spec = util.spec_from_file_location('evidence_usage_test', HERE / 'evidence.py')
            evidence = util.module_from_spec(spec); spec.loader.exec_module(evidence)
            envelopes, unreadable = evidence.claude_envelopes(out)
            self.assertEqual((len(envelopes['PEER']), unreadable), (2, []))
            inv = {'claude_owner': {'session': None, 'usage': None}, 'envelopes': envelopes,
                   'transcripts': {}, 'unreadable': [], 'attempted': {'judges': {}}}
            totals, gaps = usage.claude(inv, {'engine': 'codex'})
            self.assertEqual(totals['claude-opus-5-5']['input'], 4)
            self.assertEqual(gaps, [])

    def test_decreasing_snapshot_records_gap_and_lower_bound(self):
        inv = {'claude_owner': {'session': None, 'usage': None}, 'envelopes': {'PEER': [
            {'usage': {'claude-opus-5-5': self.counters(5)}, 'path': 'peer1.json'},
            {'usage': {'claude-opus-5-5': self.counters(2)}, 'path': 'peer2.json'}]},
            'transcripts': {}, 'unreadable': [], 'attempted': {'judges': {}}}
        totals, gaps = usage.claude(inv, {'engine': 'codex'})
        self.assertEqual(totals['claude-opus-5-5']['input'], 5)
        self.assertTrue(any('decreasing' in gap for gap in gaps))

    def test_aggregate_usage_and_transcript_are_one_contribution(self):
        inv = {'claude_owner': {'session': None, 'usage': None}, 'envelopes': {'PEER': [
            {'usage': {'UNKNOWN': self.counters(100)}, 'path': 'peer1.json'}]},
            'transcripts': {'PEER': {'messages': {'m1': {'model': 'claude-opus-5-5', 'usage':
                {'input_tokens': 100, 'cache_read_input_tokens': 0,
                 'cache_creation_input_tokens': 0, 'output_tokens': 100}}}}},
            'unreadable': [], 'attempted': {'judges': {}}}
        totals, gaps = usage.claude(inv, {'engine': 'codex'})
        self.assertEqual(totals['claude-opus-5-5']['input'], 100)
        self.assertNotIn('UNKNOWN', totals)
        self.assertEqual(gaps, [])

    def test_mixed_model_usage_and_aggregate_does_not_double_count(self):
        inv = {'claude_owner': {'session': None, 'usage': None}, 'envelopes': {'PEER': [
            {'usage': {'model-a': self.counters(40)}, 'path': 'peer1.json'},
            {'usage': {'UNKNOWN': self.counters(100)}, 'path': 'peer2.json'}]},
            'transcripts': {'PEER': {'messages': {
                'a': {'model': 'model-a', 'usage': {'input_tokens': 40, 'cache_read_input_tokens': 0,
                      'cache_creation_input_tokens': 0, 'output_tokens': 40}},
                'b': {'model': 'model-b', 'usage': {'input_tokens': 60, 'cache_read_input_tokens': 0,
                      'cache_creation_input_tokens': 0, 'output_tokens': 60}}}}},
            'unreadable': [], 'attempted': {'judges': {}}}
        totals, gaps = usage.claude(inv, {'engine': 'codex'})
        self.assertEqual(sum(row['input'] for row in totals.values()), 100)
        self.assertTrue(any('attribution' in gap for gap in gaps))
        inv['transcripts'] = {}
        totals, gaps = usage.claude(inv, {'engine': 'codex'})
        self.assertEqual(sum(row['input'] for row in totals.values()), 100)
        self.assertTrue(any('attribution' in gap for gap in gaps))

    def test_nonstandard_result_capture_in_linked_worktree(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp); (out / 'run').mkdir()
            command = 'claude -p --output-format json > answer.json'
            event = {'type': 'assistant', 'message': {'content': [
                {'type': 'tool_use', 'name': 'Bash', 'input': {'command': command}}]}}
            (out / 'run/stdout').write_text(json.dumps(event) + '\n')
            path = out / 'cell/wt-peer/answer.json'; path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'type': 'result', 'session_id': 'PEER', 'modelUsage':
                             {'claude-opus-5-5': self.counters(3)}}))
            from importlib import util
            spec = util.spec_from_file_location('evidence_capture_test', HERE / 'evidence.py')
            evidence = util.module_from_spec(spec); spec.loader.exec_module(evidence)
            envelopes, _ = evidence.claude_envelopes(out)
            self.assertEqual(envelopes['PEER'][0]['path'], 'cell/wt-peer/answer.json')

    def test_truncated_claude_capture_is_not_valid(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'answer.json'
            path.write_text('{"type": "result", "session_id": "PE')
            self.assertFalse(usage.valid_claude_result(path))
            path.write_text(json.dumps({'type': 'result', 'session_id': 'PEER', 'modelUsage': {}}))
            self.assertFalse(usage.valid_claude_result(path))
            path.write_text(json.dumps({'type': 'result', 'session_id': 'PEER',
                                        'modelUsage': {'claude-opus-5-5': self.counters(3)}}))
            self.assertTrue(usage.valid_claude_result(path))

    def test_pinned_resume_syntax_binds_session(self):
        pinned = ('CODEX_MONITORED_TIMEOUT_SEC=540 bash /x/codex-monitored.sh resume --json -c sandbox_mode=read-only '
                  '0199aa11-2222-3333-4444-555566667777 "$(cat .devlyn/pair/turn2.md)" > .devlyn/pair/peer2.jsonl')
        self.assertEqual(diagnostics.resume_target(pinned), '0199aa11-2222-3333-4444-555566667777')
        self.assertIsNone(diagnostics.resume_target('bash /x/codex-monitored.sh --json -s read-only -C . "hi"'))

    def test_jsonl_named_claude_capture_enters_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp); (out / 'run').mkdir()
            command = 'claude -p --resume X --output-format json < .devlyn/pair/turn2.md > answer.jsonl'
            event = {'type': 'assistant', 'message': {'content': [
                {'type': 'tool_use', 'name': 'Bash', 'input': {'command': command}}]}}
            (out / 'run/stdout').write_text(json.dumps(event) + '\n')
            path = out / 'cell/work/answer.jsonl'; path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'type': 'result', 'session_id': 'PEER', 'is_error': False,
                                        'modelUsage': {'claude-opus-5-5': self.counters(3)}}))
            (out / 'cell/work/codex-peer.jsonl').write_text('{"type": "thread.started", "thread_id": "T"}\n')
            from importlib import util
            spec = util.spec_from_file_location('evidence_jsonl_test', HERE / 'evidence.py')
            evidence = util.module_from_spec(spec); spec.loader.exec_module(evidence)
            envelopes, unreadable = evidence.claude_envelopes(out)
            self.assertEqual([Path(e['path']).name for e in envelopes['PEER']], ['answer.jsonl'])
            self.assertEqual(unreadable, [])

    def test_codex_each_peer_turn_footer_counted_once_without_trace(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp); folder = out / 'cell/wt-one/.devlyn/pair'; folder.mkdir(parents=True)
            for n in (1, 2):
                events = [{'type': 'thread.started', 'thread_id': 'PEER'},
                          {'type': 'turn.completed', 'usage': {'input_tokens': n * 4,
                           'cached_input_tokens': 0, 'output_tokens': n * 2}}]
                (folder / f'peer{n}.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))
            inv = {'gaps': [], 'inferences': {}, 'owner_launched_codex': ['PEER'], 'rollouts': [],
                   'owner_threads': set(), 'worker_threads': set(), 'headers': {}, 'seated': {},
                   'attempted': {'judges': {}, 'workers': {}}, 'native': {'PEER': {'models': {'gpt-6-astra'}}}}
            totals, gaps = usage.codex(out, inv)
            self.assertEqual(totals['gpt-6-astra']['input_tokens'], 8)
            self.assertEqual(totals['gpt-6-astra']['output_tokens'], 4)
            self.assertTrue(any('no inference trace' in gap for gap in gaps))

if __name__ == '__main__':
    unittest.main()
