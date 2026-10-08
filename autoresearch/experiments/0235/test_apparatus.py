"""Model-free, Docker-free contract tests for 0235."""
import importlib.util
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('test_0235_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


control, prepare, locate, diagnostics, decide, calibrate, generate, cell, usage = (load(n) for n in
    ('control', 'prepare', 'locate', 'diagnostics', 'decide', 'calibrate', 'generate_cells', 'cell', 'record_usage'))


class Locator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name); self.anchor = self.out / 'cell/work'
        self.anchor.mkdir(parents=True); (self.out / 'home').mkdir(); (self.out / 'tmp').mkdir()
        self.git('init', '-q', '-b', 'main')
        (self.anchor / 'product.txt').write_text('base\n')
        self.git('add', '.'); self.git('commit', '-q', '-m', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        with tempfile.TemporaryDirectory() as temp:
            files = locate.packet.tree(locate.raw_tree(['git', *locate.SAFE, '-C', str(self.anchor)], self.base, Path(temp)))
        self.baseline = dict(arm='R', allocation_sha=self.base, files=files)

    def git(self, *args):
        return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *args], cwd=self.anchor,
                              check=True, capture_output=True, text=True).stdout.strip()

    def linked(self, name, value):
        folder = self.out / 'cell' / name
        self.git('worktree', 'add', '-q', '-b', name, str(folder), self.base)
        gitdir = self.anchor / '.git/worktrees' / name
        (gitdir / 'gitdir').write_text(f'/cell/{name}/.git\n')
        (folder / '.git').write_text(f'gitdir: /cell/work/.git/worktrees/{name}\n')
        (folder / 'product.txt').write_text(value)

    def receipt(self, name, sha):
        folder = self.anchor / '.git/devlyn-completion' / name
        folder.mkdir(parents=True)
        (folder / 'receipt.json').write_text(json.dumps(dict(task='task', allocation='owned', anchor='/cell/work',
            baseline=self.base, source_sha=sha, worktree='/cell/one',
            acceptance=dict(task='task', kind='direct', source_sha=sha))))

    def test_live_tree_and_ambiguity(self):
        self.assertEqual(locate.select(self.out, self.baseline)['rule'], 'unchanged-anchor')
        self.linked('one', 'linked\n')
        self.assertEqual(locate.select(self.out, self.baseline)['path'], 'cell/one')
        (self.anchor / 'product.txt').write_text('anchor\n')
        with self.assertRaisesRegex(locate.LocatorError, 'more than one changed'):
            locate.select(self.out, self.baseline)

    def test_accepted_receipt_precedence_and_ambiguity(self):
        self.linked('one', 'linked\n')
        (self.anchor / 'product.txt').write_text('anchor\n')
        self.git('add', '.'); self.git('commit', '-q', '-m', 'accepted')
        sha = self.git('rev-parse', 'HEAD')
        self.receipt('one', sha)
        self.assertEqual(locate.select(self.out, self.baseline)['rule'], 'receipt')
        self.receipt('two', sha)
        with self.assertRaisesRegex(locate.LocatorError, 'more than one accepted'):
            locate.select(self.out, self.baseline)


class OwnerLaunchedSessions(unittest.TestCase):
    COUNTERS = dict(input_tokens=11, cached_input_tokens=2, cache_write_input_tokens=0,
                    output_tokens=3, reasoning_output_tokens=1)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        for name in ('run', 'cell/trace', 'home/.codex/sessions', 'home/.claude/projects'):
            (self.out / name).mkdir(parents=True)

    def trace(self, thread, model, effort):
        folder = self.out / 'cell/trace' / f'trace-{thread}'
        (folder / 'payloads').mkdir(parents=True)
        (folder / 'manifest.json').write_text(json.dumps(dict(schema_version=1, rollout_id=thread,
            root_thread_id=thread, raw_event_log='trace.jsonl')))
        (folder / 'payloads/config.json').write_text(json.dumps(dict(thread_id=thread, model=model, reasoning_effort=effort)))
        (folder / 'payloads/response.json').write_text(json.dumps(dict(token_usage=self.COUNTERS)))
        events = [dict(type='protocol_event_observed', event_type='session_configured',
                       event_payload=dict(path='payloads/config.json')),
                  dict(type='inference_started', inference_call_id='one', thread_id=thread, model=model),
                  dict(type='inference_completed', inference_call_id='one', response_payload=dict(path='payloads/response.json')),
                  dict(type='rollout_ended', status='completed')]
        (folder / 'trace.jsonl').write_text(''.join(json.dumps(dict(payload=e)) + '\n' for e in events))

    def test_codex_cli_sessions_keep_owner_identity_and_count_usage(self):
        plan = dict(config='codex', engine='codex', model='gpt-6-astra', arm='R')
        (self.out / 'plan.json').write_text(json.dumps(plan))
        (self.out / 'run/stdout').write_text(json.dumps(dict(type='thread.started', thread_id='OWNER')) + '\n')
        self.trace('OWNER', 'gpt-6-astra', 'high')
        for model in ('gpt-6-astra', 'gpt-6-sol'):
            self.trace('CLI-' + model, model, 'low')
        identity = cell.identity(self.out, plan)
        self.assertEqual(identity['status'], 'MATCH')
        self.assertEqual({s['model'] for s in identity['owner_launched_sessions']}, {'gpt-6-astra', 'gpt-6-sol'})
        self.assertTrue(all(s['effort'] == 'low' for s in identity['owner_launched_sessions']))
        measured = usage.record(self.out)
        self.assertEqual(measured['input_tokens'], 33)
        self.assertEqual(measured['output_tokens'], 9)
        self.assertFalse(any('binds to no launch' in gap for gap in measured['gaps']))

    def test_native_codex_child_keeps_registered_child_identity(self):
        plan = dict(config='codex', engine='codex', model='gpt-6-astra', arm='R')
        (self.out / 'run/stdout').write_text(json.dumps(dict(type='thread.started', thread_id='OWNER')) + '\n')
        self.trace('OWNER', 'gpt-6-astra', 'high')
        self.trace('CHILD', 'gpt-6-sol', 'high')
        source = dict(subagent=dict(thread_spawn=dict(parent_thread_id='OWNER')))
        (self.out / 'home/.codex/sessions/child.jsonl').write_text(json.dumps(
            dict(type='session_meta', payload=dict(id='CHILD', source=source))) + '\n')
        identity = cell.identity(self.out, plan)
        self.assertEqual(identity['status'], 'MATCH')
        self.assertEqual(identity['owner_launched_sessions'], [])

    def test_saved_captures_do_not_impose_judge_identity(self):
        """Astra freeze round 2: a saved envelope or plain-mode stderr of an owner-launched session is not a judge."""
        plan = dict(config='claude', engine='claude', model='claude-opus-5-5', arm='B')
        owner = [dict(type='system', subtype='init', session_id='OWNER', model='claude-opus-5-5'),
                 dict(type='result', session_id='OWNER', modelUsage={'claude-opus-5-5': dict(
                     inputTokens=1, cacheReadInputTokens=0, cacheCreationInputTokens=0, outputTokens=1)})]
        (self.out / 'run/stdout').write_text(''.join(json.dumps(e) + '\n' for e in owner))
        transcript = dict(type='assistant', sessionId='CLI', message=dict(id='one', model='claude-sonnet-5',
            usage=dict(input_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0, output_tokens=3)))
        (self.out / 'home/.claude/projects/cli.jsonl').write_text(json.dumps(transcript) + '\n')
        bundle = self.out / 'cell/work/.devlyn/bundle'; bundle.mkdir(parents=True)
        (bundle / 'review.output.json').write_text(json.dumps(dict(type='result', session_id='CLI', modelUsage={
            'claude-sonnet-5': dict(inputTokens=5, cacheReadInputTokens=0, cacheCreationInputTokens=0, outputTokens=3)})))
        self.trace('SOL', 'gpt-6-sol', 'low')
        (bundle / 'review.stderr').write_text('OpenAI Codex v0.156.1\n--------\nworkdir: /cell/work\nmodel: gpt-6-sol\n'
                                              'provider: openai\napproval: never\nsandbox: read-only\n'
                                              'reasoning effort: low\nreasoning summaries: auto\nsession id: SOL\n--------\n')
        identity = cell.identity(self.out, plan)
        self.assertEqual(identity['status'], 'MATCH', identity['violations'])
        self.assertEqual({s['session'] for s in identity['owner_launched_sessions']}, {'SOL', 'CLI'})

    def test_reroute_binds_only_registered_seats(self):
        plan = dict(config='codex', engine='codex', model='gpt-6-astra', arm='R')
        (self.out / 'run/stdout').write_text(json.dumps(dict(type='thread.started', thread_id='OWNER')) + '\n')
        self.trace('OWNER', 'gpt-6-astra', 'high')
        self.trace('CLI', 'gpt-6-sol', 'low')
        reroute = dict(type='event_msg', payload=dict(type='model_reroute'))
        (self.out / 'home/.codex/sessions/cli.jsonl').write_text(
            json.dumps(dict(type='session_meta', payload=dict(id='CLI', source='exec'))) + '\n' + json.dumps(reroute) + '\n')
        self.assertEqual(cell.identity(self.out, plan)['status'], 'MATCH')
        (self.out / 'home/.codex/sessions/owner.jsonl').write_text(
            json.dumps(dict(type='session_meta', payload=dict(id='OWNER', source='exec'))) + '\n' + json.dumps(reroute) + '\n')
        self.assertEqual(cell.identity(self.out, plan)['status'], 'MISMATCH')

    def test_reroute_in_owner_launched_child_is_not_registered(self):
        """Astra freeze round 3: a child of an owner-launched CLI session is not a registered child, traced or not."""
        plan = dict(config='codex', engine='codex', model='gpt-6-astra', arm='B')
        (self.out / 'run/stdout').write_text(json.dumps(dict(type='thread.started', thread_id='OWNER')) + '\n')
        self.trace('OWNER', 'gpt-6-astra', 'high')
        self.trace('CLI', 'gpt-6-sol', 'low')
        reroute = dict(type='event_msg', payload=dict(type='model_reroute'))
        source = dict(subagent=dict(thread_spawn=dict(parent_thread_id='CLI')))
        (self.out / 'home/.codex/sessions/cli-child.jsonl').write_text(
            json.dumps(dict(type='session_meta', payload=dict(id='CLI-CHILD', source=source))) + '\n' + json.dumps(reroute) + '\n')
        self.assertEqual(cell.identity(self.out, plan)['status'], 'MATCH')
        self.trace('CLI-CHILD', 'gpt-6-sol', 'low')
        self.assertEqual(cell.identity(self.out, plan)['status'], 'MATCH')
        owner_child = dict(subagent=dict(thread_spawn=dict(parent_thread_id='OWNER')))
        (self.out / 'home/.codex/sessions/owner-child.jsonl').write_text(
            json.dumps(dict(type='session_meta', payload=dict(id='OWNER-CHILD', source=owner_child))) + '\n'
            + json.dumps(dict(type='turn_context', payload=dict(model='gpt-6-sol', effort='high'))) + '\n' + json.dumps(reroute) + '\n')
        self.assertEqual(cell.identity(self.out, plan)['status'], 'MISMATCH')

    def test_claude_cli_transcript_without_result_is_labeled_lower_bound(self):
        plan = dict(config='claude', engine='claude', model='claude-opus-5-5', arm='R')
        (self.out / 'plan.json').write_text(json.dumps(plan))
        owner = [dict(type='system', subtype='init', session_id='OWNER', model='claude-opus-5-5'),
                 dict(type='result', session_id='OWNER', modelUsage={'claude-opus-5-5': dict(
                     inputTokens=1, cacheReadInputTokens=0, cacheCreationInputTokens=0, outputTokens=1)})]
        (self.out / 'run/stdout').write_text(''.join(json.dumps(e) + '\n' for e in owner))
        transcript = dict(type='assistant', sessionId='CLI', message=dict(id='one', model='claude-sonnet-5',
            usage=dict(input_tokens=5, cache_read_input_tokens=2, cache_creation_input_tokens=1, output_tokens=3)))
        (self.out / 'home/.claude/projects/cli.jsonl').write_text(json.dumps(transcript) + '\n')
        identity = cell.identity(self.out, plan)
        self.assertEqual(identity['status'], 'MATCH')
        self.assertEqual(identity['owner_launched_sessions'], [dict(engine='claude', session='CLI',
            model=['claude-sonnet-5'], effort=None)])
        measured = usage.record(self.out)
        self.assertEqual((measured['input_tokens'], measured['output_tokens']), (9, 4))
        self.assertEqual(measured['completeness'], 'PARTIAL')
        self.assertTrue(any('Claude session CLI has no result' in gap for gap in measured['gaps']))


class Registration(unittest.TestCase):
    def runtime(self, root):
        (root / 'output').mkdir(); (root / 'sources').mkdir()
        return dict(output=str(root / 'output'), sources=str(root / 'sources'), image='devlyn-0231',
                    control=str(root / 'control'), auth=str(root / 'auth'))

    def test_pins_and_refusals(self):
        self.assertEqual(control.ARMS, {
            'B': ('dd4957775337e597f39838fa73acd5c7ec4a5699', '6f03f5ac2895eaccc22ff12d1644a0fc623baca1eec7d00e877ce3254d33352d'),
            'R': ('59ed8a3339316d68290afcf5b74cae0defb84dcf', '90f041bf3f650ca3f028ba6288b4c38bd29a198dd5f76a29163e3e1ce1eb89f7')})
        self.assertEqual(set(prepare.ARMS), {'B', 'R'})
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'B.tgz').write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError, 'sha256 mismatch'):
                control.pack(root, 'B')
            with self.assertRaisesRegex(ValueError, 'arm must be B or R'):
                prepare.prepare(self.runtime(root), 'wrong', 'E1', 'A', 'claude')

    def test_task_entries(self):
        old = json.loads((HERE.parent / '0233/tasks.json').read_text())
        new = prepare.TASKS
        self.assertEqual([t['id'] for t in new['tasks']], ['D3', 'D4', 'E1'])
        self.assertEqual(new['tasks'], [t for t in old['tasks'] if t['id'] in ('D3', 'D4', 'E1')])
        self.assertEqual({k: v for k, v in new.items() if k != 'tasks'},
                         {k: v for k, v in old.items() if k != 'tasks'})

    def test_local_origin_seal_and_vendor(self):
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.object(prepare, 'install'):
                out = prepare.prepare(self.runtime(Path(temp)), 'e1', 'E1', 'R', 'claude')
            work = out / 'cell/work'
            self.assertEqual(prepare.git(work, 'remote', 'get-url', 'origin'), '/harness/mirror.git')
            self.assertNotIn('github.com', (work / '.git/config').read_text().lower())
            baseline = json.loads((out / 'baseline.json').read_text())
            self.assertEqual(prepare.git(work, 'rev-parse', 'origin/HEAD'), baseline['allocation_sha'])
            runner = load('run_cell')
            self.assertTrue(runner.harness_unchanged(out, baseline))
            for name in ('node_modules/express/package.json', 'node_modules/qs/dist/qs.js'):
                self.assertIn(name, prepare.git(work, 'ls-files', name))
            prepare.git(work, 'remote', 'set-url', 'origin', 'https://github.com/other/repo')
            self.assertFalse(runner.harness_unchanged(out, baseline))
        task = next(t for t in prepare.TASKS['tasks'] if t['id'] == 'E1')
        self.assertEqual(prepare.packet.content(prepare.packet.tree(HERE.parents[2] / task['source_dir'])),
                         task['source_sha256'])

    def test_calibration_and_check(self):
        result = calibrate.run()
        self.assertEqual(set(result), {f'E1/{name}' for name in ('good', 'bad-shout', 'bad-name-with-shout', 'bad-default-unchanged')})
        for name, failures in result.items():
            self.assertEqual(failures, [] if name.endswith('/good') else
                             [name.split('/bad-', 1)[1]])
        check = load('check')
        commands = []
        def fake(_runtime, _work, command):
            commands.append(command)
            return dict(argv=command, exit_code=0, timeout=False, stdout='{"pass":true}\n', stderr='')
        with mock.patch.object(check, 'in_image', side_effect=fake):
            rows = check.evaluate(Path('/snapshot'), 'E1', {})['rows']
        self.assertEqual([r['id'] for r in rows], next(t['oracle'] for t in prepare.TASKS['tasks'] if t['id'] == 'E1'))
        self.assertTrue(any('/tmp/public-work' in c[-1] for c in commands if c[0] == 'sh'))
        self.assertTrue(all(c[1] == '/control/autoresearch/experiments/0233/oracle.js' for c in commands if c[0] == 'node'))


class Transcript(unittest.TestCase):
    def test_delivery_for_both_engines(self):
        claude = [dict(type='assistant', message=dict(content=[
            dict(type='tool_use', id='r', name='Read', input={'file_path': '_shared/task-completion.md'}),
            dict(type='tool_use', id='c', name='Bash', input={'command': 'python3 task-complete.py complete --receipt x'})])),
            dict(type='user', message=dict(content=[dict(type='tool_result', tool_use_id='c', content='Exit code: 0')]))]
        codex = [dict(type='item.started', item=dict(id='r', type='command_execution', command='cat _shared/task-completion.md')),
                 dict(type='item.started', item=dict(id='c', type='command_execution', command='python3 task-complete.py allocate')),
                 dict(type='item.completed', item=dict(id='c', exit_code=1))]
        for engine, events, subcommand, code in (('claude', claude, 'complete', 0), ('codex', codex, 'allocate', 1)):
            with self.subTest(engine=engine):
                result = diagnostics.summarize(events, engine)
                self.assertNotIn('guide_read', result)
                self.assertTrue(result['delivery_read']['read'])
                self.assertEqual(result['delivery_read']['task_complete'][0]['subcommand'], subcommand)
                self.assertEqual(result['delivery_read']['task_complete'][0]['exit_code'], code)

    def test_codex_owner_trace_record(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            (out / 'run').mkdir(); (out / 'cell/trace/trace-one/payloads').mkdir(parents=True)
            (out / 'plan.json').write_text(json.dumps(dict(engine='codex', arm='R')))
            (out / 'run/stdout').write_text(json.dumps(dict(type='thread.started', thread_id='root')) + '\n')
            trace = out / 'cell/trace/trace-one'
            (trace / 'manifest.json').write_text(json.dumps(dict(root_thread_id='root', raw_event_log='trace.jsonl')))
            events = []
            for i, item in enumerate((dict(id='r', type='command_execution', command='cat _shared/task-completion.md'),
                                      dict(id='c', type='command_execution', command='python3 task-complete.py accept'))):
                path = f'payloads/{i}.json'
                (trace / path).write_text(json.dumps(dict(type='item.started', thread_id='root', item=item)))
                events.append(dict(payload=dict(type='protocol_event_observed', event_type='item.started', event_payload=dict(path=path))))
            (trace / 'payloads/done.json').write_text(json.dumps(dict(type='item.completed', thread_id='root', item=dict(id='c', exit_code=2))))
            events.append(dict(payload=dict(type='protocol_event_observed', event_type='item.completed', event_payload=dict(path='payloads/done.json'))))
            (trace / 'trace.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))
            result = diagnostics.record(out)
            self.assertNotIn('guide_read', result)
            self.assertTrue(result['delivery_read']['read'])
            self.assertEqual(result['delivery_read']['task_complete'][0]['subcommand'], 'accept')
            self.assertEqual(result['delivery_read']['task_complete'][0]['exit_code'], 2)

class Rule(unittest.TestCase):
    def table(self, b_success=('r01-D3-claude-B-r1',)):
        return {name: dict(name=name, task=task, arm=arm, config=config, replicate=int(rep),
                           complete=(arm == 'R' or name in b_success), rows={'oracle': True},
                           scope=False, false_completion=False, harm=False, reproduced=set(),
                           wall=10, input=100, output=10, usage=True)
                for name, task, arm, config, rep in decide.CELLS}

    def outcome(self, table, expected, final_report=None):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp); path = out / 'decisions.json'
            path.write_text(json.dumps({'final_report': final_report or {}}))
            with mock.patch.object(decide, 'load', return_value=table), contextlib.redirect_stdout(io.StringIO()):
                result = decide.main(out, path)
            self.assertEqual(result['outcome'], expected)
            self.assertEqual(result['token'], '0235:claude=R/B:' + expected)
            self.assertEqual(json.loads((out / 'decision.json').read_text()), result)
            self.assertEqual(result['final_report'], final_report or {})
            return result

    def test_advance_and_costs(self):
        table = self.table()
        result = self.outcome(table, 'ADVANCE', {'r02-D3-claude-R-r1': {'verified': True}})
        self.assertEqual(result['completions']['B'], {'D3': 1, 'D4': 0})
        for key in ('wall', 'input'):
            with self.subTest(key=key):
                changed = self.table()
                changed['r02-D3-claude-R-r1'][key] = 131 if key == 'wall' else 1301
                self.assertEqual(self.outcome(changed, 'INCONCLUSIVE')['advance']['cost'], False)
        changed = self.table()
        changed['r02-D3-claude-R-r1']['usage'] = False
        self.assertIsNone(self.outcome(changed, 'INCONCLUSIVE')['advance']['cost'])
        changed = self.table()
        changed['r04-D4-claude-B-r1']['usage'] = False
        self.assertIsNone(self.outcome(changed, 'INCONCLUSIVE')['advance']['cost'])

    def test_completion_and_witness_thresholds(self):
        names = {arm: [n for n, t, a, _, _ in decide.CELLS if a == arm] for arm in ('B', 'R')}
        changed = self.table(b_success=names['B'][:3])
        self.outcome(changed, 'INCONCLUSIVE')
        changed = self.table(b_success=[n for n in names['B'] if '-D3-' in n])
        self.outcome(changed, 'INCONCLUSIVE')
        changed = self.table()
        changed[names['R'][0]]['reproduced'] = {'w'}
        self.assertFalse(self.outcome(changed, 'INCONCLUSIVE')['advance']['witnessed'])
        changed = self.table()
        changed[names['R'][0]]['complete'] = False
        self.outcome(changed, 'INCONCLUSIVE')
        changed = self.table(b_success=names['B'])
        self.outcome(changed, 'REJECT')

    def test_zero_success_raw_cost(self):
        for ratio, expected in ((1.25, 'ADVANCE'), (1.26, 'INCONCLUSIVE')):
            table = self.table(b_success=())
            for row in table.values():
                if row['arm'] == 'R':
                    row.update(wall=10*ratio, input=100*ratio, output=10*ratio)
            self.outcome(table, expected)
        table = self.table(b_success=())
        table['r02-D3-claude-R-r1']['usage'] = False
        self.assertIsNone(self.outcome(table, 'INCONCLUSIVE')['advance']['cost'])
        table = self.table(b_success=())
        table['r04-D4-claude-B-r1']['usage'] = False
        self.assertIsNone(self.outcome(table, 'INCONCLUSIVE')['advance']['cost'])

    def test_safety_rejects_even_four_completions(self):
        for key in ('scope', 'false_completion', 'harm'):
            with self.subTest(key=key):
                table = self.table()
                table['r02-D3-claude-R-r1'][key] = True
                self.outcome(table, 'REJECT')

    def test_missing_judgments_and_missing_verdict(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            with self.assertRaises(FileNotFoundError):
                decide.load(out, {})
            for name, *_ in decide.CELLS:
                (out / name).mkdir()
                (out / name / 'checks.json').write_text(json.dumps({'public': []}))
                (out / f'verdict-{name}.json').write_text(json.dumps(dict(cell=name, status='COMPLETE', oracle=[],
                    assessments=[], scope_violations=[], owner_status='DONE', owner_seconds=1, usage='COMPLETE')))
            with self.assertRaisesRegex(ValueError, 'mandatory judgments are missing'):
                decide.load(out, {})


class Cells(unittest.TestCase):
    def test_order_and_replicates(self):
        rendered = generate.generate()
        self.assertEqual(set(rendered), {'cells.tsv', 'smoke.tsv'})
        for name, rows in rendered.items():
            self.assertEqual((HERE / name).read_text(), generate.render(rows))
        self.assertEqual([row[0] for row in rendered['cells.tsv']], [
            'r01-D3-claude-B-r1', 'r02-D3-claude-R-r1', 'r03-D4-claude-R-r1', 'r04-D4-claude-B-r1',
            'r05-D3-claude-R-r2', 'r06-D3-claude-B-r2', 'r07-D4-claude-B-r2', 'r08-D4-claude-R-r2'])
        for task in ('D3', 'D4'):
            for arm in ('B', 'R'):
                self.assertEqual({row[4] for row in rendered['cells.tsv'] if row[1:3] == (task, arm)}, {1, 2})
            self.assertEqual({next(row[2] for row in rendered['cells.tsv'] if row[1] == task and row[4] == rep)
                              for rep in (1, 2)}, {'B', 'R'})
        self.assertEqual(rendered['smoke.tsv'], (('s01-E1-claude-R', 'E1', 'R', 'claude'),))

    def test_preflight_refusal(self):
        runner = load('run_cell')
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp); runtime = out / 'runtime.json'
            runtime.write_text(json.dumps({'output': str(out)}))
            with mock.patch.object(runner, 'preflight', return_value=(None, 'blocked')):
                self.assertEqual(runner.run(runtime, 'r01-D3-claude-B-r1', 'D3', 'B', 'claude'), 3)
            self.assertEqual(json.loads((out / 'not-dispatched-r01-D3-claude-B-r1.json').read_text()),
                             {'reason': 'blocked'})
            self.assertFalse((out / 'verdict-r01-D3-claude-B-r1.json').exists())


if __name__ == '__main__':
    unittest.main()
