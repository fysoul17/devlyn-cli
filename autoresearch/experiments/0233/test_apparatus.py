"""Model-free, Docker-free contract tests."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('test_0233_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


control, prepare, locate, diagnostics, decide, calibrate, generate, cell, usage = (load(n) for n in
    ('control', 'prepare', 'locate', 'diagnostics', 'decide', 'calibrate', 'generate_cells', 'cell', 'record_usage'))


class Registration(unittest.TestCase):
    def test_pins_arms_and_refusal(self):
        self.assertEqual(set(control.ARMS), {'B', 'C'})
        self.assertEqual(set(prepare.ARMS), {'A', 'B', 'C'})
        for commit, digest in control.ARMS.values():
            self.assertEqual((len(commit), len(digest)), (40, 64))
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / 'B.tgz').write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError, 'sha256 mismatch'):
                control.pack(Path(temp), 'B')

    def test_i0185_sentence_and_fixture_requests(self):
        original = json.loads((HERE.parent / '0222/tasks.json').read_text())
        old = next(t for t in original['tasks'] if t['id'] == 'I0185')['request']
        adapted = next(t for t in prepare.TASKS['tasks'] if t['id'] == 'I0185')
        sentence = ' The root research owner handles local-only experimental delivery.'
        self.assertEqual(old.count(sentence), 1)
        self.assertEqual(adapted['request'], old.replace(sentence, ''))
        self.assertEqual(adapted['request_sha256_original'], hashlib.sha256(old.encode()).hexdigest())
        self.assertEqual(adapted['request_sha256_adapted'], hashlib.sha256(adapted['request'].encode()).hexdigest())
        for task, path in [('B5', 'benchmark/instruction-sensitivity/fixtures/B5-orphan-direction-trap/task.txt'),
                           ('F10', 'benchmark/auto-resolve/fixtures/F10-persist-write-collision/task.txt'),
                           ('F11', 'benchmark/auto-resolve/fixtures/F11-batch-import-all-or-nothing/task.txt')]:
            self.assertEqual(next(t for t in prepare.TASKS['tasks'] if t['id'] == task)['request'],
                             (HERE.parents[2] / path).read_text())

    def runtime(self, root):
        (root / 'output').mkdir(); (root / 'sources').mkdir()
        return dict(output=str(root / 'output'), sources=str(root / 'sources'), image='devlyn-0231',
                    control=str(root / 'control'), auth=str(root / 'auth'))

    def test_local_origin_and_harness_seal(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = self.runtime(Path(temp))
            out = prepare.prepare(runtime, 'test', 'SMOKE', 'A', 'claude')
            work = out / 'cell/work'
            self.assertEqual(prepare.git(work, 'remote', 'get-url', 'origin'), '/harness/mirror.git')
            self.assertNotIn('github.com', (work / '.git/config').read_text().lower())
            self.assertNotIn('insteadOf', (work / '.git/config').read_text())
            baseline = json.loads((out / 'baseline.json').read_text())
            self.assertEqual(prepare.git(work, 'rev-parse', 'origin/HEAD'), baseline['allocation_sha'])
            runner = load('run_cell')
            self.assertTrue(runner.harness_unchanged(out, baseline))
            prepare.git(work, 'remote', 'set-url', 'origin', 'https://github.com/other/repo')
            self.assertFalse(runner.harness_unchanged(out, baseline))

    def test_vendored_dependencies_committed(self):
        with tempfile.TemporaryDirectory() as temp:
            out = prepare.prepare(self.runtime(Path(temp)), 'e1', 'E1', 'A', 'codex')
            self.assertTrue((out / 'cell/work/node_modules/express/package.json').is_file())
            self.assertIn('node_modules/express/package.json',
                          prepare.git(out / 'cell/work', 'ls-files', 'node_modules/express/package.json'))

    def test_all_reference_rows(self):
        result = calibrate.run()
        self.assertEqual((len(result), sum(bool(v) for v in result.values())), (29, 22))
        self.assertEqual(result['F10/bad-concurrent-posts-counter-reset'], ['concurrent-posts'])
        self.assertEqual(result['F10/good-raw-item'], [])
        self.assertEqual(result['F11/bad-mid-batch-invalid-unchanged-qty'], ['mid-batch-invalid-unchanged'])
        self.assertEqual(result['B5/bad-request-only'],
                         ['self-orphan-helper-removed', 'self-orphan-import-removed'])

    def test_every_new_source_seal(self):
        packet = locate.packet
        for task in prepare.TASKS['tasks']:
            if task['id'] in ('B5', 'F10', 'F11', 'E1', 'E2'):
                self.assertEqual(packet.content(packet.tree(HERE.parents[2] / task['source_dir'])),
                                 task['source_sha256'], task['id'])

    def test_new_check_rows_use_writable_public_copies(self):
        check = load('check')
        def fake(_runtime, _work, command):
            if command[0] == 'sh':
                self.assertIn('/tmp/public-work', command[-1])
            return dict(argv=command, exit_code=0, timeout=False, stdout='{"pass":true}\n', stderr='')
        with mock.patch.object(check, 'in_image', side_effect=fake):
            result = check.evaluate(Path('/snapshot'), 'F10', {})
        self.assertEqual([row['id'] for row in result['rows']],
                         ['concurrent-posts', 'invalid-unchanged', 'restart-persists', 'reads-use-store'])
        self.assertTrue(all(row['status'] == 'PASS' for row in result['rows']))


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
        self.baseline = dict(arm='A', allocation_sha=self.base, files=files)

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


class Transcript(unittest.TestCase):
    def test_claude(self):
        def call(id_, name, input_): return dict(type='tool_use', id=id_, name=name, input=input_)
        rows = [dict(type='assistant', message={'content': [
            call('r', 'Read', {'file_path': '_shared/failure-paths.md'}),
            call('d', 'Read', {'file_path': '_shared/task-completion.md'}),
            call('e', 'Edit', {'file_path': 'tests/a.test.js'}),
            call('p', 'Edit', {'file_path': 'server/index.js'}),
            call('c', 'Bash', {'command': 'python3 task-complete.py complete --receipt x'})]}),
            dict(type='user', message={'content': [dict(type='tool_result', tool_use_id='r', content=diagnostics.GUIDE_HEADING),
                                                 dict(type='tool_result', tool_use_id='c', content='Exit code: 0')]})]
        result = diagnostics.summarize(rows, 'claude', 'C')
        self.assertEqual((result['guide_read']['first_edit_any'], result['guide_read']['first_edit_non_test']), (3, 4))
        self.assertTrue(result['guide_read']['before_first_edit_any'])
        self.assertEqual(result['delivery_read']['task_complete'][0]['exit_code'], 0)
        self.assertEqual(diagnostics.summarize(rows, 'claude', 'B')['guide_read']['status'], 'absent')

    def test_codex(self):
        rows = [dict(type='item.started', item=dict(id='r', type='command_execution', command='cat _shared/failure-paths.md')),
                dict(type='item.started', item=dict(id='e', type='apply_patch', patch='*** Update File: bin/cli.js\n')),
                dict(type='item.started', item=dict(id='c', type='command_execution', command='python3 task-complete.py allocate')),
                dict(type='item.completed', item=dict(id='r', exit_code=0, aggregated_output=diagnostics.GUIDE_HEADING)),
                dict(type='item.completed', item=dict(id='c', exit_code=1))]
        result = diagnostics.summarize(rows, 'codex', 'C')
        self.assertTrue(result['guide_read']['before_first_edit_non_test'])
        self.assertEqual(result['delivery_read']['task_complete'][0]['subcommand'], 'allocate')
        self.assertEqual(result['delivery_read']['task_complete'][0]['exit_code'], 1)

    def test_codex_owner_trace_record(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            (out / 'run').mkdir(); (out / 'cell/trace/trace-one/payloads').mkdir(parents=True)
            (out / 'plan.json').write_text(json.dumps(dict(engine='codex', arm='C')))
            (out / 'run/stdout').write_text(json.dumps(dict(type='thread.started', thread_id='root')) + '\n')
            trace = out / 'cell/trace/trace-one'
            (trace / 'manifest.json').write_text(json.dumps(dict(root_thread_id='root', raw_event_log='trace.jsonl')))
            events = []
            for i, item in enumerate((dict(id='r', type='command_execution', command='cat _shared/failure-paths.md'),
                                      dict(id='e', type='apply_patch', patch='*** Update File: bin/cli.js\n'))):
                path = f'payloads/{i}.json'
                (trace / path).write_text(json.dumps(dict(type='item.started', thread_id='root', item=item)))
                events.append(dict(payload=dict(type='protocol_event_observed', event_type='item.started',
                                                event_payload=dict(path=path))))
            (trace / 'payloads/r-done.json').write_text(json.dumps(dict(type='item.completed', thread_id='root',
                item=dict(id='r', exit_code=0, aggregated_output=diagnostics.GUIDE_HEADING))))
            events.append(dict(payload=dict(type='protocol_event_observed', event_type='item.completed',
                                            event_payload=dict(path='payloads/r-done.json'))))
            (trace / 'trace.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))
            self.assertEqual(diagnostics.record(out)['guide_read']['status'], 'read')
            self.assertEqual(json.loads((out / 'diagnostics.json').read_text())['guide_read']['first_edit_any'], 2)


    def test_codex_file_change_is_an_edit(self):
        rows = [dict(type='item.started', item=dict(id='r', type='command_execution', command="sed -n '1,40p' .agents/skills/_shared/failure-paths.md")),
                dict(type='item.started', item=dict(id='e', type='file_change', changes=[dict(path='/cell/work/server/index.js', kind='update')])),
                dict(type='item.completed', item=dict(id='r', exit_code=0, aggregated_output=diagnostics.GUIDE_HEADING))]
        result = diagnostics.summarize(rows, 'codex', 'C')
        self.assertEqual(result['guide_read']['first_edit_non_test'], 2)
        self.assertTrue(result['guide_read']['before_first_edit_non_test'])

    def test_guide_mention_then_successful_read_for_each_engine(self):
        for engine in ('claude', 'codex'):
            with self.subTest(engine=engine):
                if engine == 'claude':
                    rows = [dict(type='assistant', message=dict(content=[
                        dict(type='tool_use', id='m', name='Bash', input={'command': 'test -f _shared/failure-paths.md'}),
                        dict(type='tool_use', id='e', name='Edit', input={'file_path': 'server/index.js'}),
                        dict(type='tool_use', id='r', name='Read', input={'file_path': '_shared/failure-paths.md'})])),
                        dict(type='user', message=dict(content=[
                            dict(type='tool_result', tool_use_id='m', content='Exit code: 0'),
                            dict(type='tool_result', tool_use_id='r', content=diagnostics.GUIDE_HEADING)]))]
                else:
                    rows = [dict(type='item.started', item=dict(id='m', type='command_execution', command='test -f _shared/failure-paths.md')),
                            dict(type='item.started', item=dict(id='e', type='apply_patch', patch='*** Update File: server/index.js')),
                            dict(type='item.started', item=dict(id='r', type='command_execution', command='cat _shared/failure-paths.md')),
                            dict(type='item.completed', item=dict(id='m', exit_code=0, aggregated_output='')),
                            dict(type='item.completed', item=dict(id='r', exit_code=0, aggregated_output=diagnostics.GUIDE_HEADING))]
                result = diagnostics.summarize(rows, engine, 'C')['guide_read']
                self.assertEqual(result['status'], 'read')
                self.assertEqual(result['calls'][0]['position'], 1)
                self.assertFalse(result['before_first_edit_any'])
                if engine == 'claude':
                    rows.pop()
                else:
                    rows.pop()
                mentioned = diagnostics.summarize(rows, engine, 'C')['guide_read']
                self.assertEqual(mentioned['status'], 'mentioned')
                self.assertFalse(mentioned['before_first_edit_any'])


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
        plan = dict(config='codex', engine='codex', model='gpt-6-astra', arm='C')
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
        plan = dict(config='codex', engine='codex', model='gpt-6-astra', arm='C')
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
        plan = dict(config='codex', engine='codex', model='gpt-6-astra', arm='A')
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
        plan = dict(config='claude', engine='claude', model='claude-opus-5-5', arm='C')
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


class Rule(unittest.TestCase):
    def table(self):
        table = {}
        for task in ('D3', 'D4', 'I0185', 'B5', 'E1', 'E2'):
            for config in ('claude', 'codex'):
                for arm in ('A', 'B', 'C'):
                    for rep in ((1,) if task.startswith('E') else (1, 2)):
                        name = f'{task}-{config}-{arm}-{rep}'
                        table[name] = dict(name=name, task=task, arm=arm, config=config, replicate=rep,
                                           complete=True, rows={'oracle': True}, scope=False, false_completion=False,
                                           harm=False, reproduced=set(), wall={'A': 10, 'B': 9, 'C': 8}[arm],
                                           input=100, output=10, usage=arm != 'C' or task != 'D3', methodology=None)
        return table

    def test_token_no_headroom_unknown_usage(self):
        eligibility = {(task, config): False for task in ('F10', 'F11') for config in ('claude', 'codex')}
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp); decisions = out / 'decisions.json'; decisions.write_text('{}')
            with mock.patch.object(decide, 'eligibility', return_value=eligibility), mock.patch.object(decide, 'load', return_value=self.table()):
                result = decide.main(out, decisions)
            self.assertIn('conf:NO_HEADROOM', result['token'])
            self.assertIn('C/B:INCONCLUSIVE', result['token'])
            self.assertIsNone(result['configs']['claude']['panels']['development']['sums']['C']['input'])
            self.assertEqual(json.loads((out / 'decision.json').read_text())['token'], result['token'])

    def confirmation(self, b_wall, c_complete, mutate=None):
        table = {name: dict(cell, usage=True) for name, cell in self.table().items()}
        for task in ('F10', 'F11'):
            for config in ('claude', 'codex'):
                for arm in ('A', 'B', 'C'):
                    for rep in (1, 2):
                        name = f'{task}-{config}-{arm}-{rep}'
                        table[name] = dict(name=name, task=task, arm=arm, config=config, replicate=rep,
                                           complete=c_complete if arm == 'C' else True, rows={'oracle': True},
                                           scope=False, false_completion=False, harm=False, reproduced=set(),
                                           wall={'A': 10, 'B': b_wall, 'C': 8}[arm], input=100, output=10,
                                           usage=True, methodology=None)
        eligibility = {(task, config): True for task in ('F10', 'F11') for config in ('claude', 'codex')}
        if mutate:
            mutate(table)
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp); decisions = out / 'decisions.json'; decisions.write_text('{}')
            with mock.patch.object(decide, 'eligibility', return_value=eligibility), mock.patch.object(decide, 'load', return_value=table):
                return decide.main(out, decisions)['configs']['codex']

    def test_confirmation_gates_on_c_only(self):
        result = self.confirmation(b_wall=11, c_complete=True)
        self.assertEqual(result['panels']['confirmation']['comparisons']['B/A']['outcome'], 'FAIL')
        self.assertEqual(result['confirmation'], 'PASS')
        self.assertEqual(result['admitted'], 'C')

    def test_zero_success_c_fails_confirmation(self):
        result = self.confirmation(b_wall=9, c_complete=False)
        self.assertEqual(result['confirmation'], 'FAIL')
        self.assertIsNone(result['admitted'])

    def test_zero_success_quality_vetoes(self):
        for field, value in (('scope', True), ('false_completion', True), ('harm', True),
                             ('rows', {'oracle': False}), ('reproduced', {'w'})):
            with self.subTest(field=field):
                def change(table):
                    for row in table.values():
                        if row['task'] in ('F10', 'F11'):
                            row['complete'] = False
                    table['F10-codex-C-1'][field] = value
                result = self.confirmation(9, False, change)
                self.assertEqual(result['confirmation'], 'FAIL')
                self.assertIsNone(result['admitted'])

    def test_clean_all_zero_is_unconfirmed(self):
        def change(table):
            for row in table.values():
                if row['task'] in ('F10', 'F11'):
                    row['complete'] = False
        result = self.confirmation(9, False, change)
        self.assertEqual(result['confirmation'], 'UNCONFIRMED')
        self.assertEqual(result['admitted'], 'C-unconfirmed')

    def test_screening_eligibility(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            for name, task, arm, config, rep in decide.SCREENING:
                status = 'FAIL' if (task, arm, config, rep) == ('F10', 'A', 'codex', '1') else 'PASS'
                (out / f'verdict-{name}.json').write_text(json.dumps(dict(status='COMPLETE', oracle=[dict(id='row', status=status)])))
            self.assertTrue(decide.eligibility(out)[('F10', 'codex')])
            self.assertFalse(decide.eligibility(out)[('F10', 'claude')])

    def test_easy_tripwire_threshold(self):
        panel = {'sums': {'B': dict(S=2, wall=100, input=100, output=100),
                          'C': dict(S=2, wall=125, input=125, output=125)}}
        self.assertEqual(decide.easy_tripwire(panel), 'CLEAR')
        panel['sums']['C']['output'] = 126
        self.assertEqual(decide.easy_tripwire(panel), 'TRIGGERED:output')
        panel['sums']['C']['output'] = None
        self.assertEqual(decide.easy_tripwire(panel), 'UNKNOWN:usage')


class Cells(unittest.TestCase):
    def test_ineligible_confirmation_records_not_run_without_preflight(self):
        runner = load('run_cell')
        name, task, arm, config, _ = next(row for row in decide.CELLS if row[1] == 'F10')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / 'runtime.json'
            runtime.write_text(json.dumps({'output': str(root)}))
            with mock.patch.object(runner.decide, 'eligibility', return_value={(task, config): False}), \
                 mock.patch.object(runner, 'preflight', side_effect=AssertionError('dispatched')):
                self.assertEqual(runner.run(runtime, name, task, arm, config), 0)
            self.assertEqual(json.loads((root / f'verdict-{name}.json').read_text())['status'], 'NOT_RUN')

    def test_order_and_counts(self):
        rendered = generate.generate()
        for name, rows in rendered.items():
            self.assertEqual((HERE / name).read_text(), generate.render(rows))
        self.assertEqual((len(rendered['smoke.tsv']), len(rendered['screening.tsv'])), (6, 16))
        self.assertEqual({name: sum(row[1] in tasks for row in rendered['cells.tsv']) for name, tasks in decide.PANELS.items()},
                         {'development': 48, 'easy': 12, 'confirmation': 24})
        for config in ('claude', 'codex'):
            rows = [r for r in rendered['cells.tsv'] if r[1] in decide.PANELS['development'] and r[3] == config]
            self.assertEqual({''.join(r[2] for r in rows[i:i+3]) for i in range(0, len(rows), 3)}, set(generate.ORDERS))


if __name__ == '__main__':
    unittest.main()
