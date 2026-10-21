"""Offline contract tests for 0256's registration, accounting and dispatch rules."""
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
    spec = importlib.util.spec_from_file_location('test_0256_' + name, HERE / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


control, prepare, generate, decide, usage, run_cell, driver, snapshots, models = (
    load(n) for n in ('control', 'prepare', 'generate_cells', 'decide', 'record_usage',
                       'run_cell', 'driver', 'snapshot_issues', 'models_cache'))


class Registration(unittest.TestCase):
    def committed_modes_fixture(self, root):
        work = root / 'work'
        work.mkdir()
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(work)], check=True)
        for key, value in [('user.name', 'Test'), ('user.email', 'test@localhost')]:
            subprocess.run(['git', '-C', str(work), 'config', key, value], check=True)
        private = work / 'private.txt'
        private.write_text('original')
        private.chmod(0o600)
        executable = work / 'run.sh'
        executable.write_text('#!/bin/sh\n')
        executable.chmod(0o755)
        subprocess.run(['git', '-C', str(work), 'add', 'private.txt', 'run.sh'], check=True)
        subprocess.run(['git', '-C', str(work), 'commit', '-qm', 'fixture'], check=True)
        return work, private, executable

    def test_committed_modes_match_prepared_work_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            work, private, executable = self.committed_modes_fixture(Path(temp))
            committed = prepare.committed_tree(work, prepare.git(work, 'rev-parse', 'HEAD'))
            self.assertEqual(committed['private.txt'].split(':')[-1], '644')
            self.assertEqual(committed['run.sh'].split(':')[-1], '755')
            self.assertNotEqual(prepare.packet.tree(work)['private.txt'], committed['private.txt'])
            prepare.match_committed_tree(work, committed)
            self.assertEqual(private.stat().st_mode & 0o777, 0o644)
            self.assertEqual(executable.stat().st_mode & 0o777, 0o755)
            self.assertEqual(prepare.packet.tree(work), committed)

    def test_committed_tree_refuses_tracked_content_difference(self):
        with tempfile.TemporaryDirectory() as temp:
            work, private, _ = self.committed_modes_fixture(Path(temp))
            committed = prepare.committed_tree(work, prepare.git(work, 'rev-parse', 'HEAD'))
            private.write_text('changed')
            with self.assertRaisesRegex(ValueError, 'committed tree'):
                prepare.match_committed_tree(work, committed)

    def test_install_records_empty_commit_when_output_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work, _, _ = self.committed_modes_fixture(root)
            (work / '.gitignore').write_text('.agents/\n')
            prepare.git(work, 'add', '.gitignore')
            prepare.git(work, 'commit', '-qm', 'ignore install target')
            parent = prepare.git(work, 'rev-parse', 'HEAD')
            tree = prepare.git(work, 'rev-parse', 'HEAD^{tree}')
            installed = work / '.agents/skills/devlyn-ideate/SKILL.md'
            run = subprocess.run

            def fake_docker(argv, **kwargs):
                if argv[0] == 'docker':
                    installed.parent.mkdir(parents=True)
                    installed.write_text('installed')
                    return subprocess.CompletedProcess(argv, 0)
                return run(argv, **kwargs)

            with mock.patch.object(prepare.subprocess, 'run', side_effect=fake_docker):
                prepare.install(dict(control=str(root), image='frozen'), work, root / 'home', 'codex', 'B')

            self.assertTrue(installed.is_file())
            self.assertEqual(prepare.git(work, 'rev-parse', 'HEAD^'), parent)
            self.assertEqual(prepare.git(work, 'log', '-1', '--format=%s'), 'install B')
            self.assertEqual(prepare.git(work, 'rev-parse', 'HEAD^{tree}'), tree)
            self.assertEqual(prepare.git(work, 'status', '--porcelain', '--untracked-files=all'), '')

    def test_cells_and_orders(self):
        generated = generate.generate()
        self.assertEqual(set(generated), {'cells.tsv', 'smoke.tsv'})
        self.assertEqual(tuple(map(len, generated.values())), (56, 4))
        self.assertEqual([row[1] for row in generated['cells.tsv'][:4]], ['D3'] * 4)
        for prefix, tasks, reps in [('d', ('D3', 'D4', 'I0185', 'B5'), 2),
                                    ('e', ('E1', 'E2'), 1), ('c', ('F10', 'F11'), 2)]:
            rows = [row for row in generated['cells.tsv'] if row[0].startswith(prefix)]
            blocks = [rows[i:i + 2] for i in range(0, len(rows), 2)]
            self.assertEqual(len(blocks), len(tasks) * 2 * reps)
            for rep in range(1, reps + 1):
                part = blocks[(rep - 1) * len(tasks) * 2:rep * len(tasks) * 2]
                expected = [(task, config, t, ci) for t, task in enumerate(tasks)
                            for ci, config in enumerate(('claude', 'codex'))]
                if rep == 2:
                    expected.reverse()
                for block, (task, config, t, ci) in zip(part, expected):
                    self.assertEqual({tuple(row[1:4:2]) for row in block}, {(task, config)})
                    arms = 'AB' if (t + ci) % 2 == 0 else 'BA'
                    if rep == 2:
                        arms = arms[::-1]
                    self.assertEqual(''.join(row[2] for row in block), arms)
        self.assertEqual(generate.render(generated['cells.tsv']), (HERE / 'cells.tsv').read_text())

    def test_package_integrity_refuses_cached_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp)
            (cache / 'B.tgz').write_bytes(b'wrong')
            with mock.patch.object(control, 'urllib', create=True):
                with self.assertRaisesRegex(ValueError, 'integrity mismatch'):
                    control.fetch(cache)
            self.assertEqual((cache / 'B.tgz').read_bytes(), b'wrong')

    def test_override_refusals(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'override.json'
            with self.assertRaises(FileNotFoundError):
                prepare.override_tasks(path)
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'exactly'):
                prepare.override_tasks(path)
            entries = {key: dict(issue_snapshot_sha256='0' * 64, fetched_at='2026-10-21T00:00:00+00:00',
                                 url=url) for key, url in [('D3', 'https://api.github.com/repos/tj/commander.js/issues/2530'),
                                                           ('D4', 'https://api.github.com/repos/pallets/click/issues/2645')]}
            path.write_text(json.dumps(entries))
            tasks = prepare.override_tasks(path)
            self.assertEqual([t['issue_snapshot_sha256'] for t in tasks['tasks'] if t['id'] in entries], ['0' * 64] * 2)
            entries['D3']['url'] = 'wrong'
            path.write_text(json.dumps(entries))
            with self.assertRaisesRegex(ValueError, 'malformed'):
                prepare.override_tasks(path)

    def test_prepared_exclusions_and_digests(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            override = root / 'override.json'
            override.write_text(json.dumps({key: dict(issue_snapshot_sha256='0' * 64,
                fetched_at='2026-10-21T00:00:00+00:00', url=url) for key, url in
                [('D3', 'https://api.github.com/repos/tj/commander.js/issues/2530'),
                 ('D4', 'https://api.github.com/repos/pallets/click/issues/2645')]}))
            runtime = dict(output=str(root), sources=str(root), image='frozen', control=str(root),
                           auth=str(root), tasks_override=str(override))
            for config in ('claude', 'codex'):
                out = prepare.prepare(runtime, config, 'SMOKE', 'A', config)
                plan = json.loads((out / 'plan.json').read_text())
                baseline = json.loads((out / 'baseline.json').read_text())
                self.assertEqual(json.loads((out / 'home/.claude/settings.json').read_text()),
                                 dict(syncClaudeAiSkills=False, syncClaudeAiPlugins=False))
                self.assertEqual(plan['env']['ENABLE_CLAUDEAI_MCP_SERVERS'], 'false')
                self.assertEqual(baseline['prepared']['plan.json'], hashlib.sha256((out / 'plan.json').read_bytes()).hexdigest())
                if config == 'claude':
                    self.assertEqual(plan['argv'][1:4], ['--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}'])
                else:
                    self.assertIn('[projects."/cell/work"]', (out / 'home/.codex/config.toml').read_text())

    def test_issue_snapshot_uses_raw_bytes_once(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = [b'{"number":2530}\n', b'{"number":2645}\n']
            with mock.patch.object(snapshots.subprocess, 'run', side_effect=[mock.Mock(stdout=x) for x in raw]) as call:
                snapshots.snapshot(root, root / 'override.json')
            self.assertEqual(call.call_count, 2)
            self.assertEqual((root / 'D3-issue.json').read_bytes(), raw[0])
            self.assertEqual(json.loads((root / 'override.json').read_text())['D4']['issue_snapshot_sha256'],
                             hashlib.sha256(raw[1]).hexdigest())
            with self.assertRaises(FileExistsError):
                snapshots.snapshot(root, root / 'override.json')

    def test_models_cache_argv_and_refusal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'auth').mkdir()
            (root / 'auth/codex.json').write_text('{}')
            runtime = dict(scratch=str(root), auth=str(root / 'auth'), image='sha256:frozen')
            argv = models.command(runtime, root)
            self.assertIn('sha256:frozen', argv)
            self.assertEqual(argv[argv.index('codex') + 1], 'exec')
            with mock.patch.object(models.subprocess, 'run'):
                with mock.patch.object(models, 'reap'):
                    with self.assertRaisesRegex(RuntimeError, 'no models cache'):
                        models.generate(runtime, root / 'out')

    def test_models_cache_timeout_reaps_container(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'auth').mkdir()
            (root / 'auth/codex.json').write_text('{}')
            runtime = dict(scratch=str(root), auth=str(root / 'auth'), image='sha256:frozen')
            with mock.patch.object(models.subprocess, 'run', side_effect=subprocess.TimeoutExpired('docker', 180)):
                with mock.patch.object(models, 'reap', create=True) as reap:
                    with self.assertRaises(subprocess.TimeoutExpired):
                        models.generate(runtime, root / 'out')
            reap.assert_called_once()
            self.assertTrue(reap.call_args.args[0].startswith('devlyn-0256-cache-'))


class Decisions(unittest.TestCase):
    def cell(self, arm, *, complete=True, row=True, safe=True, false=False, severe=False,
             wall=10, tokens=10, known=True):
        return dict(task='D3', arm=arm, replicate=1, complete=complete, rows={'r': row},
                    scope=not safe, false_completion=false, harm=False,
                    reproduced={'w'} if severe else set(), wall=wall, input=tokens, output=tokens,
                    usage=known)

    def reading(self, a, b):
        return decide.panel_rule([a, b], 'development')['reading']

    def test_all_readings_and_dominance(self):
        a = self.cell('A')
        self.assertEqual(self.reading(a, self.cell('B', complete=False)), 'NO_CLAIM')
        self.assertEqual(self.reading(a, self.cell('B', row=False)), 'PACKAGE_LOWERS_QUALITY')
        self.assertEqual(self.reading(a, self.cell('B', severe=True)), 'PACKAGE_LOWERS_QUALITY')
        self.assertEqual(self.reading(a, self.cell('B', false=True)), 'PACKAGE_UNSAFE')
        self.assertEqual(self.reading(a, self.cell('B', wall=11)), 'PACKAGE_COSTS_MORE')
        self.assertEqual(self.reading(a, self.cell('B', known=False)), 'COST_UNKNOWN')
        self.assertEqual(self.reading(self.cell('A', known=False), self.cell('B')), 'COST_UNKNOWN')
        self.assertEqual(self.reading(a, self.cell('B')), 'NO_STRICT_GAIN')
        self.assertEqual(self.reading(a, self.cell('B', wall=9)), 'DEVELOPMENT_PASS')
        zero = self.cell('A', complete=False)
        self.assertEqual(self.reading(zero, self.cell('B')), 'DEVELOPMENT_PASS')
        self.assertEqual(decide.at_most(decide.sums([self.cell('B')]), decide.sums([zero]), 'input'), True)

    def test_missing_verdicts_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            decisions = root / 'decisions.json'
            decisions.write_text('{}')
            outcome = decide.main(root, decisions)
            self.assertIn('NOT_FINISHED', outcome['token'])
            self.assertTrue(any('missing verdict' in x for x in outcome['configs']['claude']['development']['conditions']))
            self.assertTrue((root / 'decision.json').exists())

    def test_product_incomplete_verdict_loads(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name, task, arm, config, _ = decide.CELLS[0]
            (root / name).mkdir()
            (root / name / 'checks.json').write_text(json.dumps(dict(public=[dict(exit_code=1)])))
            (root / f'verdict-{name}.json').write_text(json.dumps(dict(
                status='PRODUCT_INCOMPLETE', cell=name, oracle=[], assessments=[], scope_violations=[],
                owner_status='DONE', owner_seconds=1, usage='COMPLETE')))
            table, gaps = decide.load(root, dict.fromkeys(decide.JUDGMENTS, {}))
            self.assertIn(name, table)
            self.assertFalse(table[name]['complete'])
            self.assertFalse(any(name + ': unresolved' in gap for gap in gaps[(config, 'development')]))
            verdict = json.loads((root / f'verdict-{name}.json').read_text())
            verdict['status'] = 'INCOMPLETE'
            (root / f'verdict-{name}.json').write_text(json.dumps(verdict))
            table, gaps = decide.load(root, dict.fromkeys(decide.JUDGMENTS, {}))
            self.assertNotIn(name, table)
            self.assertTrue(any(name + ': unresolved INCOMPLETE' in gap for gap in gaps[(config, 'development')]))

    def test_unreadable_decisions_are_named_gaps_for_every_panel(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for path in (root / 'missing.json', root):
                outcome = decide.main(root, path)
                for panels in outcome['configs'].values():
                    for result in panels.values():
                        self.assertEqual(result['reading'], 'NOT_FINISHED')
                        self.assertTrue(any('decisions' in gap for gap in result['conditions']))

    def test_strict_gain_condition_in_every_reading(self):
        a = self.cell('A')
        for b, expected in ((self.cell('B', wall=11), 'strict_gain'),
                            (self.cell('B', known=False), 'strict_gain')):
            result = decide.panel_rule([a, b], 'development')
            self.assertIn(expected, result['conditions'])

    def test_reproduced_witness_requires_explicit_paired_result(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pair = [row for row in decide.CELLS if row[1] == 'D3' and row[3] == 'claude' and row[4] == '1']
            names = {row[2]: row[0] for row in pair}
            for name, task, arm, config, replicate in decide.CELLS:
                (root / name).mkdir()
                (root / name / 'checks.json').write_text(json.dumps(dict(public=[dict(exit_code=0)])))
                (root / f'verdict-{name}.json').write_text(json.dumps(dict(
                    status='COMPLETE', cell=name, oracle=[], assessments=[], scope_violations=[],
                    owner_status='DONE', owner_seconds=1, usage='COMPLETE')))
            decisions = dict(audited=[row[0] for row in decide.CELLS], false_completion=[], user_data_harm=[],
                             adjudicated={}, severe={}, witnesses={})
            decision_path = root / 'decisions.json'
            for reproducing, paired in ((names['B'], names['A']), (names['A'], names['B'])):
                decisions['witnesses'] = {'w': {reproducing: True}}
                decision_path.write_text(json.dumps(decisions))
                outcome = decide.main(root, decision_path)
                result = outcome['configs']['claude']['development']
                self.assertEqual(result['reading'], 'NOT_FINISHED')
                self.assertTrue(any(paired in gap and 'w' in gap for gap in result['conditions']))
                decisions['witnesses']['w'][paired] = False
                _, gaps = decide.load(root, decisions)
                self.assertFalse(any('paired' in gap for gap in gaps[('claude', 'development')]))


class Accounting(unittest.TestCase):
    def inv(self, amount):
        return dict(claude_owner=dict(session='s', usage={'m': dict(inputTokens=amount, cacheReadInputTokens=0,
                          cacheCreationInputTokens=0, outputTokens=2)}), envelopes={}, unreadable=[],
                    attempted={'judges': {}}, transcripts={})

    def transcript(self, root, messages, stdout=()):
        directory = root / 'home/.claude/projects/x'
        directory.mkdir(parents=True)
        (directory / 's.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in messages))
        (root / 'run').mkdir()
        (root / 'run/stdout').write_text(''.join(json.dumps(row) + '\n' for row in stdout))

    def message(self, ident='m1', *, usage=True, amount=3):
        return dict(type='assistant', sessionId='s', message=dict(id=ident, model='m', stop_reason='end_turn',
                    usage=dict(input_tokens=amount, cache_read_input_tokens=0,
                               cache_creation_input_tokens=0, output_tokens=2) if usage else None))

    def test_reconciliation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.transcript(root, [self.message(), self.message()])
            totals, gaps = usage.claude(root, self.inv(3), dict(engine='claude'))
            self.assertEqual((totals['m']['input'], gaps), (3, []))

    def test_interrupted_retry_is_unknown_with_terminal_lower_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.transcript(root, [self.message()], [dict(type='system', subtype='api_retry', session_id='s')])
            totals, gaps = usage.claude(root, self.inv(4), dict(engine='claude'))
            self.assertEqual(totals['m']['input'], 3)
            self.assertTrue(any('envelope differs' in gap for gap in gaps))
            self.assertTrue(any('unbound retry' in gap for gap in gaps))

    def test_missing_terminal_and_conflicting_copies(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.transcript(root, [dict(type='assistant', sessionId='s', message=dict(id='m1', model='m'))])
            _, gaps = usage.claude(root, self.inv(3), dict(engine='claude'))
            self.assertTrue(any('no terminal usage' in gap for gap in gaps))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.transcript(root, [self.message(), self.message(amount=4)])
            _, gaps = usage.claude(root, self.inv(3), dict(engine='claude'))
            self.assertTrue(any('terminal copies disagree' in gap for gap in gaps))

    def test_stream_progress_requires_terminal_message(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stream = [dict(type='system', subtype='init', session_id='s'),
                      dict(type='stream_event', event=dict(type='message_start', message=dict(id='m1'))),
                      dict(type='stream_event', event=dict(type='content_block_delta'))]
            self.transcript(root, [self.message()], stream)
            _, gaps = usage.claude(root, self.inv(3), dict(engine='claude'))
            self.assertEqual(gaps, [])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.transcript(root, [self.message()], [dict(type='system', subtype='init', session_id='s'),
                                                   dict(type='stream_event', event=dict(type='content_block_delta'))])
            _, gaps = usage.claude(root, self.inv(3), dict(engine='claude'))
            self.assertTrue(any('unbound progress' in gap for gap in gaps))

    def test_synthetic_and_unbound_hook_progress_are_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            synthetic = dict(type='assistant', sessionId='s', message=dict(id='synthetic', model='<synthetic>'))
            synthetic_error = dict(synthetic, isApiErrorMessage=True)
            self.transcript(root, [self.message(), synthetic, synthetic_error, dict(type='progress', sessionId='s'),
                                   dict(type='error', sessionId='s')],
                            [dict(type='progress', session_id='s'), dict(type='error', session_id='s')])
            totals, gaps = usage.claude(root, self.inv(3), dict(engine='claude'))
            self.assertEqual(totals['m']['input'], 3)
            self.assertEqual(gaps, [])

    def test_id_free_api_error_and_abort_remain_unknown(self):
        for subtype in ('api_retry', 'api_error', 'abort'):
            with self.subTest(subtype=subtype), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.transcript(root, [self.message(), dict(type='progress', sessionId='s', subtype=subtype)])
                _, gaps = usage.claude(root, self.inv(3), dict(engine='claude'))
                self.assertTrue(any('unbound retry' in gap for gap in gaps))

    def test_bound_retry_before_assistant_takes_model(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.transcript(root, [dict(type='progress', subtype='api_retry', sessionId='s', message_id='m1'),
                                   self.message()])
            totals, gaps = usage.claude(root, self.inv(3), dict(engine='claude'))
            self.assertEqual((totals['m']['input'], gaps), (3, []))

    def test_native_subagent_sessions_reconcile_to_owner(self):
        for separate in (False, True):
            with self.subTest(separate=separate), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                child = self.message('child', amount=2)
                child['isSidechain'] = True
                child['parentSessionId'] = 's'
                if separate:
                    child['sessionId'] = 'child-session'
                self.transcript(root, [self.message(amount=3), child])
                inventory = self.inv(5)
                inventory['claude_owner']['usage']['m']['outputTokens'] = 4
                totals, gaps = usage.claude(root, inventory, dict(engine='claude'))
                self.assertEqual((totals['m']['input'], gaps), (5, []))
                (root / 'plan.json').write_text(json.dumps(dict(engine='claude')))
                with mock.patch.object(usage.evidence, 'inventory', return_value=inventory), \
                     mock.patch.object(usage, 'codex', return_value=({}, [])):
                    self.assertEqual(usage.record(root)['completeness'], 'COMPLETE')

    def test_folded_conflicting_terminal_copies_use_counter_minima(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            parent = self.message(amount=9)
            child = self.message(amount=2)
            child.update(sessionId='child-session', parentSessionId='s')
            self.transcript(root, [parent, child])
            inventory = self.inv(9)
            totals, gaps = usage.claude(root, inventory, dict(engine='claude'))
            self.assertEqual(totals['m']['input'], 2)
            self.assertTrue(any('terminal copies disagree' in gap for gap in gaps))
            (root / 'plan.json').write_text(json.dumps(dict(engine='claude')))
            with mock.patch.object(usage.evidence, 'inventory', return_value=inventory), \
                 mock.patch.object(usage, 'codex', return_value=({}, [])):
                recorded = usage.record(root)
            self.assertEqual((recorded['input_tokens'], recorded['completeness']), (2, 'UNKNOWN'))

    def test_folded_conflict_uses_minimum_for_each_counter(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            parent = self.message(amount=9)
            child = self.message(amount=2)
            child.update(sessionId='child-session', parentSessionId='s')
            parent['message']['usage'].update(cache_read_input_tokens=1, cache_creation_input_tokens=5,
                                              output_tokens=8)
            child['message']['usage'].update(cache_read_input_tokens=4, cache_creation_input_tokens=2,
                                             output_tokens=3)
            self.transcript(root, [parent, child])
            totals, gaps = usage.claude(root, self.inv(9), dict(engine='claude'))
            self.assertEqual(totals['m'], dict(input=2, cache_read=1, cache_write=2, output=3))
            self.assertTrue(any('terminal copies disagree' in gap for gap in gaps))

    def test_folded_child_fills_owner_event_placeholder_model(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            child = self.message(amount=2)
            child.update(sessionId='child-session', parentSessionId='s')
            self.transcript(root, [dict(type='progress', sessionId='s', message_id='m1'), child])
            totals, gaps = usage.claude(root, self.inv(2), dict(engine='claude'))
            self.assertEqual((totals['m']['input'], gaps), (2, []))

    def test_unenveloped_independent_session_remains_gap(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            other = self.message('other')
            other['sessionId'] = 'independent'
            self.transcript(root, [self.message(), other])
            _, gaps = usage.claude(root, self.inv(3), dict(engine='claude'))
            self.assertTrue(any('independent has no result envelope' in gap for gap in gaps))


class Operations(unittest.TestCase):
    def test_image_check(self):
        with mock.patch.object(run_cell.subprocess, 'check_output', return_value='sha256:a\n'):
            self.assertTrue(run_cell.image_identity(dict(image='sha256:a')))
            self.assertFalse(run_cell.image_identity(dict(image='sha256:b')))

    def test_image_mismatch_is_not_dispatched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / 'runtime.json'
            runtime.write_text(json.dumps(dict(output=str(root), image='sha256:expected')))
            with mock.patch.object(run_cell, 'image_identity', return_value=False):
                self.assertEqual(run_cell.run(runtime, 'n', 'D3', 'A', 'claude'), 3)
            self.assertFalse((root / 'verdict-n.json').exists())
            self.assertIn('image', json.loads((root / 'not-dispatched-n.json').read_text())['reason'])

    def test_assessment_snapshot_1500_second_cutoff(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'auth').mkdir()
            runtime = dict(auth=str(root / 'auth'), account=['a', 'b'])
            venue = dict(account=['a', 'b'])
            response = mock.MagicMock()
            response.__enter__.return_value = response
            response.read.return_value = json.dumps(dict(account=dict(uuid='owner'),
                                                         organization=dict(uuid='org'))).encode()
            with mock.patch.object(run_cell.time, 'time', return_value=1000):
                with mock.patch.object(run_cell.subprocess, 'run') as security:
                    with mock.patch.object(run_cell.urllib.request, 'urlopen', return_value=response) as http:
                        with mock.patch.object(run_cell.base, 'fingerprint', side_effect=['a', 'b']):
                            security.return_value.stdout = json.dumps(dict(claudeAiOauth=dict(
                                accessToken='new', expiresAt=2499 * 1000)))
                            self.assertIsNone(run_cell.assessment_snapshot(runtime, venue)[0])
                            http.assert_not_called()
                            security.return_value.stdout = json.dumps(dict(claudeAiOauth=dict(
                                accessToken='new', expiresAt=2501 * 1000)))
                            fresh, blocked = run_cell.assessment_snapshot(runtime, venue)
            self.assertIsNone(blocked)
            self.assertEqual(fresh['token_seconds_left'], 1501)
            self.assertTrue(http.called)

    def test_after_grading_telemetry_error_keeps_verdict(self):
        with mock.patch.object(run_cell, 'assessment_snapshot', return_value=(dict(account=['a', 'b']), None)):
            with mock.patch.object(run_cell.assess, 'assess', return_value=[dict(complete=True, severe=False)]):
                with mock.patch.object(run_cell.base, 'unassessed', return_value=[]):
                    with mock.patch.object(run_cell.base, 'verdict', return_value='COMPLETE'):
                        with mock.patch.object(run_cell, 'claude_limits', side_effect=TimeoutError('timed out')):
                            result = run_cell.grade(Path('/tmp/unused'), {}, dict(cell='n'), dict(
                                product_check_pass=True, oracle=[], scope_violations=[]), dict(account=['a', 'b']))
        self.assertEqual(result['status'], 'COMPLETE')
        self.assertIn('timed out', result['claude_limits_after_error'])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'verdict-n.json'
            self.assertEqual(run_cell.write_verdict(path, result), 0)
            self.assertEqual(json.loads(path.read_text())['status'], 'COMPLETE')

    def test_regrade_replaces_inherited_claude_telemetry(self):
        old = {'five_hour': dict(used=10, resets='old')}
        record = dict(cell='n', claude_limits_after=old, claude_limits_after_error='old error')
        checks = dict(product_check_pass=True, oracle=[], scope_violations=[])
        with mock.patch.object(run_cell, 'assessment_snapshot', return_value=(dict(account=['a', 'b']), None)), \
             mock.patch.object(run_cell.assess, 'assess', return_value=[]), \
             mock.patch.object(run_cell.base, 'unassessed', return_value=[]), \
             mock.patch.object(run_cell.base, 'verdict', return_value='COMPLETE'):
            with mock.patch.object(run_cell, 'claude_limits', side_effect=TimeoutError('new timeout')):
                failed = run_cell.grade(Path('/tmp/unused'), {}, record.copy(), checks, dict(account=['a', 'b']))
            self.assertNotIn('claude_limits_after', failed)
            self.assertEqual(failed['claude_limits_after_error'], 'new timeout')
            fresh = {'five_hour': dict(used=20, resets='new')}
            with mock.patch.object(run_cell, 'claude_limits', return_value=fresh):
                succeeded = run_cell.grade(Path('/tmp/unused'), {}, record.copy(), checks, dict(account=['a', 'b']))
            self.assertEqual(succeeded['claude_limits_after'], fresh)
            self.assertNotIn('claude_limits_after_error', succeeded)

    def test_preflight_profile_timeout_is_not_dispatched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime_path = root / 'runtime.json'
            (root / 'auth').mkdir()
            (root / '.codex').mkdir()
            (root / '.codex/auth.json').write_text('{}')
            runtime_path.write_text(json.dumps(dict(output=str(root), auth=str(root / 'auth'),
                                                    image='sha256:expected')))
            raw = json.dumps(dict(claudeAiOauth=dict(accessToken='fresh',
                                                      expiresAt=(run_cell.time.time() + 10000) * 1000)))
            with mock.patch.object(run_cell, 'image_identity', return_value=True), \
                 mock.patch.object(run_cell.shutil, 'disk_usage', return_value=mock.Mock(free=run_cell.HEADROOM_BYTES)), \
                 mock.patch.object(run_cell.base.subprocess, 'run', return_value=mock.Mock(stdout=raw)), \
                 mock.patch.object(run_cell.base.Path, 'home', return_value=root), \
                 mock.patch.object(run_cell.urllib.request, 'urlopen', side_effect=TimeoutError('profile timed out')):
                self.assertEqual(run_cell.run(runtime_path, 'n', 'D3', 'A', 'claude'), 3)
            self.assertIn('profile timed out', json.loads((root / 'not-dispatched-n.json').read_text())['reason'])

    def test_preflight_usage_and_codex_query_oserrors_are_not_dispatched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            auth = root / 'auth'
            auth.mkdir()
            (auth / 'claude.json').write_text(json.dumps(dict(claudeAiOauth=dict(accessToken='fresh'))))
            runtime_path = root / 'runtime.json'
            runtime_path.write_text(json.dumps(dict(output=str(root), auth=str(auth), image='sha256:expected')))
            with mock.patch.object(run_cell, 'image_identity', return_value=True), \
                 mock.patch.object(run_cell.shutil, 'disk_usage', return_value=mock.Mock(free=run_cell.HEADROOM_BYTES)), \
                 mock.patch.object(run_cell.base, 'snapshot_auth', return_value=({}, None)):
                with mock.patch.object(run_cell.urllib.request, 'urlopen', side_effect=TimeoutError('usage timed out')):
                    self.assertEqual(run_cell.run(runtime_path, 'usage', 'D3', 'A', 'claude'), 3)
                self.assertIn('usage timed out', json.loads((root / 'not-dispatched-usage.json').read_text())['reason'])
                with mock.patch.object(run_cell, 'claude_limits', return_value={'five_hour': dict(used=1)}), \
                     mock.patch.object(run_cell, 'codex_limits', side_effect=OSError('Codex unavailable')):
                    self.assertEqual(run_cell.run(runtime_path, 'codex', 'D3', 'A', 'claude'), 3)
                self.assertIn('Codex unavailable', json.loads((root / 'not-dispatched-codex.json').read_text())['reason'])

    def test_usage_attribute_error_is_recorded_not_raised(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'n'
            out.mkdir()
            (out / 'baseline.json').write_text('{}')
            (root / 'control.manifest.json').write_text(json.dumps(dict(packages=dict(B=dict(sha256='hash')))))
            runtime = root / 'runtime.json'
            runtime.write_text(json.dumps(dict(output=str(root), control=str(root / 'control'),
                                               models_cache=str(root / 'cache'), image='sha256:expected')))
            owner = dict(owner_status='DONE', seconds=1, teardown='CLEAN', identity=dict(status='MATCH'))
            with mock.patch.object(run_cell, 'image_identity', return_value=True), \
                 mock.patch.object(run_cell, 'preflight', return_value=(dict(claude_limits={}), None)), \
                 mock.patch.object(run_cell, 'control_unchanged', return_value=True), \
                 mock.patch.object(run_cell.prepare, 'prepare', return_value=out), \
                 mock.patch.object(run_cell, 'digest', return_value='hash'), \
                 mock.patch.object(run_cell.subprocess, 'check_output', return_value='commit'), \
                 mock.patch.object(run_cell.cell_run, 'run', return_value=owner), \
                 mock.patch.object(run_cell, 'seal_after_teardown', return_value=('hash', [])), \
                 mock.patch.object(run_cell.usage, 'record', side_effect=AttributeError('bad usage row')), \
                 mock.patch.object(run_cell.quota, 'classify', return_value=dict(execution=[])), \
                 mock.patch.object(run_cell.diagnostics, 'record', return_value={}), \
                 mock.patch.object(run_cell, 'harness_unchanged', return_value=False):
                self.assertEqual(run_cell.run(runtime, 'n', 'D3', 'A', 'claude'), 2)
            verdict = json.loads((root / 'verdict-n.json').read_text())
            self.assertIn('AttributeError', verdict['usage'])
            self.assertEqual(verdict['reason'], 'harness changed')

    def test_assessment_hold_and_regrade_reason(self):
        with mock.patch.object(run_cell, 'assessment_snapshot', return_value=(None, 'token short')):
            result = run_cell.grade(Path('/tmp/absent'), {}, dict(cell='x'), {}, dict(account=['a', 'b']))
        self.assertEqual(result['reason'], 'assessment held: token short')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / 'runtime.json'
            runtime.write_text(json.dumps(dict(output=str(root))))
            out = root / 'n'
            out.mkdir()
            (out / 'seal.json').write_text(json.dumps(dict(venue=dict(account=['a', 'b']))))
            (out / 'checks.json').write_text('{}')
            (root / 'verdict-n.json').write_text(json.dumps(dict(cell='n', status='STOP', reason='assessment held: token short')))
            with mock.patch.object(run_cell, 'assessment_snapshot', return_value=(dict(account=['a', 'b']), None)):
                with mock.patch.object(run_cell, 'grade', return_value=dict(cell='n', status='COMPLETE')):
                    self.assertEqual(run_cell.regrade(runtime, 'n'), 0)
            self.assertTrue((root / 'verdict-n.stop-1.json').exists())
            self.assertEqual(json.loads((root / 'verdict-n.json').read_text())['status'], 'COMPLETE')

    def test_window_estimates_and_resets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before = {w: dict(used=10, resets='2026-10-21T09:00:00+00:00') for w in driver.WINDOWS}
            after = {w: dict(used=14, resets='2026-10-21T09:00:00+00:00') for w in driver.WINDOWS}
            (root / 'verdict-smoke.json').write_text(json.dumps(dict(status='COMPLETE', config='claude',
                   task='SMOKE', claude_limits_before=before, claude_limits_after=after)))
            estimate = driver.estimates(root, 'claude', 'development')
            self.assertEqual(estimate, driver.FLOORS)
            (root / 'verdict-dev.json').write_text(json.dumps(dict(status='COMPLETE', config='claude',
                   task='D3', claude_limits_before=before, claude_limits_after=after)))
            self.assertEqual(driver.estimates(root, 'claude', 'development'), dict.fromkeys(driver.WINDOWS, 4))
            after['seven_day']['resets'] = '2026-10-21T10:00:00+00:00'
            self.assertIsNone(driver.delta(before, after, 'seven_day'))
            self.assertFalse(driver.fits(before, dict.fromkeys(driver.WINDOWS, 30), estimate, 3))

    def test_window_jitter_and_reset_crossing_estimates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before = {w: dict(used=10, resets='2026-10-21T08:59:59.541426+00:00') for w in driver.WINDOWS}
            after = {w: dict(used=14, resets='2026-10-21T09:00:00.323437+00:00') for w in driver.WINDOWS}
            self.assertEqual(driver.delta(before, after, 'five_hour'), 4)
            (root / 'verdict-dev.json').write_text(json.dumps(dict(status='COMPLETE', config='claude',
                task='D3', claude_limits_before=before, claude_limits_after=after)))
            self.assertEqual(driver.estimates(root, 'claude', 'development'), dict.fromkeys(driver.WINDOWS, 4))
            after['five_hour']['resets'] = '2026-10-21T10:00:00+00:00'
            (root / 'verdict-dev.json').write_text(json.dumps(dict(status='COMPLETE', config='claude',
                task='D3', claude_limits_before=before, claude_limits_after=after)))
            self.assertIsNone(driver.delta(before, after, 'five_hour'))
            self.assertEqual(driver.estimates(root, 'claude', 'development'),
                             dict(seven_day=4, five_hour=driver.FLOORS['five_hour']))
            self.assertTrue(driver.same_window('2026-10-21T09:00:00+00:00',
                                               '2026-10-21T09:09:59.999999+00:00'))
            self.assertFalse(driver.same_window('2026-10-21T09:00:00+00:00',
                                                '2026-10-21T09:10:00+00:00'))

    def test_estimates_exclude_reset_crossing_sample(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before = {w: dict(used=10, resets='2026-10-21T09:00:00+00:00') for w in driver.WINDOWS}
            after = {w: dict(used=90, resets='2026-10-21T10:00:00+00:00') for w in driver.WINDOWS}
            (root / 'verdict-dev.json').write_text(json.dumps(dict(status='COMPLETE', config='claude',
                task='D3', claude_limits_before=before, claude_limits_after=after)))
            self.assertEqual(driver.estimates(root, 'claude', 'development'), driver.FLOORS)

    def test_renewal_command_flags(self):
        command = ['claude', '-p', '--tools', '', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', 'OK']
        help_text = '-p --tools --strict-mcp-config --mcp-config'
        self.assertEqual(driver.renewal_command(dict(renewal_command=command), help_text), command)
        with self.assertRaisesRegex(ValueError, 'missing'):
            driver.renewal_command(dict(renewal_command=command), '-p --tools')

    def test_renewal_once_per_expiry_and_account(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            command = ['claude', '-p', '--tools', '', '--strict-mcp-config', '--mcp-config',
                       '{"mcpServers":{}}', 'OK']
            runtime_path = root / 'runtime.json'
            runtime_path.write_text(json.dumps(dict(output=str(root), caps=dict(seven_day=85, five_hour=70),
                                                    account=['a', 'b'], renewal_command=command)))
            d = driver.Driver(runtime_path, [])
            old = dict(expires=driver.time.time() + 200, account=['a', 'b'])
            same = dict(expires=old['expires'], account=['a', 'b'])
            fake = mock.Mock(stdout='-p --tools --strict-mcp-config --mcp-config')
            with mock.patch.object(driver, 'credential', side_effect=[old, same, old]) as credentials:
                with mock.patch.object(driver.subprocess, 'run', return_value=fake) as calls:
                    self.assertFalse(d.ready('claude', 'development', 2))
                    self.assertFalse(d.ready('claude', 'development', 2))
            self.assertEqual(credentials.call_count, 3)
            self.assertEqual(calls.call_count, 2)
            self.assertEqual(d.state['renewed_expiries'], [old['expires']])

    def test_renewal_threshold_and_fresh_window_token(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'auth').mkdir()
            (root / 'auth/claude.json').write_text(json.dumps(dict(claudeAiOauth=dict(accessToken='old'))))
            command = ['claude', '-p', '--tools', '', '--strict-mcp-config', '--mcp-config',
                       '{"mcpServers":{}}', 'OK']
            runtime_path = root / 'runtime.json'
            runtime_path.write_text(json.dumps(dict(output=str(root), auth=str(root / 'auth'),
                image='sha256:expected', caps=dict(seven_day=85, five_hour=70),
                account=['a', 'b'], renewal_command=command)))
            d = driver.Driver(runtime_path, [])
            windows = {w: dict(used=0, resets='2026-10-21T09:00:00+00:00') for w in driver.WINDOWS}
            with mock.patch.object(driver.time, 'time', return_value=1000):
                with mock.patch.object(driver, 'credential', return_value=dict(
                        expires=1400, account=['a', 'b'], access_token='old')):
                    with mock.patch.object(driver.subprocess, 'run') as process:
                        self.assertFalse(d.ready('claude', 'development', 2))
                        process.assert_not_called()
                with mock.patch.object(driver, 'credential', side_effect=[
                        dict(expires=1300, account=['a', 'b'], access_token='old'),
                        dict(expires=9000, account=['a', 'b'], access_token='new')]):
                    with mock.patch.object(driver.subprocess, 'run', return_value=mock.Mock(
                            stdout='-p --tools --strict-mcp-config --mcp-config')) as process:
                        with mock.patch.object(driver.cell, 'claude_limits', return_value=windows) as limits:
                            with mock.patch.object(d, 'image', return_value=True):
                                self.assertTrue(d.ready('claude', 'development', 2))
                        limits.assert_called_once_with(d.runtime, 'new')
                        self.assertEqual(process.call_count, 2)
            self.assertEqual(json.loads((root / 'auth/claude.json').read_text())['claudeAiOauth']['accessToken'], 'old')

    def test_expired_and_expiring_tokens_skip_old_profile_before_renewal(self):
        for expiry in (900, 1300):
            with self.subTest(expiry=expiry), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                command = ['claude', '-p', '--tools', '', '--strict-mcp-config', '--mcp-config',
                           '{"mcpServers":{}}', 'OK']
                runtime = root / 'runtime.json'
                runtime.write_text(json.dumps(dict(output=str(root), caps=dict(seven_day=85, five_hour=70),
                                                     account=['a', 'b'], renewal_command=command)))
                d = driver.Driver(runtime, [])
                profile = mock.MagicMock()
                profile.__enter__.return_value = profile
                profile.read.return_value = json.dumps(dict(account=dict(uuid='owner'),
                                                             organization=dict(uuid='org'))).encode()
                def process(argv, **kwargs):
                    if argv[0] == 'security':
                        token = 'new' if d.state['renewed_expiries'] else 'old'
                        end = 9000 if token == 'new' else expiry
                        return mock.Mock(stdout=json.dumps(dict(claudeAiOauth=dict(
                            accessToken=token, expiresAt=end * 1000))))
                    return mock.Mock(stdout='-p --tools --strict-mcp-config --mcp-config')
                def urlopen(request, timeout):
                    if request.get_header('Authorization') == 'Bearer old':
                        raise driver.cell.urllib.error.HTTPError(request.full_url, 401, 'expired', {}, None)
                    return profile
                windows = {w: dict(used=0, resets='2026-10-21T09:00:00+00:00') for w in driver.WINDOWS}
                with mock.patch.object(driver.time, 'time', return_value=1000), \
                     mock.patch.object(driver.subprocess, 'run', side_effect=process), \
                     mock.patch.object(driver.cell.urllib.request, 'urlopen', side_effect=urlopen) as http, \
                     mock.patch.object(driver.cell.base, 'fingerprint', side_effect=['a', 'b']), \
                     mock.patch.object(driver.cell, 'claude_limits', return_value=windows), \
                     mock.patch.object(d, 'image', return_value=True):
                    self.assertTrue(d.ready('claude', 'development', 2))
                self.assertEqual(http.call_count, 1)
                self.assertEqual(http.call_args.args[0].get_header('Authorization'), 'Bearer new')

    def test_renewal_command_fault_rechecks_keychain_and_holds_only_if_needed(self):
        command = ['claude', '-p', '--tools', '', '--strict-mcp-config', '--mcp-config',
                   '{"mcpServers":{}}', 'OK']
        for fault in (subprocess.TimeoutExpired(command, 180), OSError('renewal unavailable')):
            for renewed in (True, False):
                with self.subTest(fault=type(fault).__name__, renewed=renewed), tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    runtime = root / 'runtime.json'
                    runtime.write_text(json.dumps(dict(output=str(root), caps=dict(seven_day=85, five_hour=70),
                                                         account=['a', 'b'], renewal_command=command)))
                    d = driver.Driver(runtime, [])
                    old = dict(expires=1200, account=['a', 'b'], access_token='old')
                    new = dict(expires=9000 if renewed else 1200, account=['a', 'b'], access_token='new')
                    windows = {w: dict(used=0, resets='2026-10-21T09:00:00+00:00') for w in driver.WINDOWS}
                    def process(argv, **kwargs):
                        if argv == ['claude', '--help']:
                            return mock.Mock(stdout='-p --tools --strict-mcp-config --mcp-config')
                        raise fault
                    with mock.patch.object(driver.time, 'time', return_value=1000), \
                         mock.patch.object(driver, 'credential', side_effect=[old, new]) as credentials, \
                         mock.patch.object(driver.subprocess, 'run', side_effect=process), \
                         mock.patch.object(driver.cell, 'claude_limits', return_value=windows), \
                         mock.patch.object(d, 'image', return_value=True):
                        self.assertEqual(d.ready('claude', 'development', 2), renewed)
                    self.assertEqual(credentials.call_count, 2)
                    self.assertEqual(d.state['renewed_expiries'], [1200])
                    if not renewed:
                        self.assertEqual(d.state['current']['reason'],
                                         'renewal did not preserve account and advance expiry')

    def test_driver_profile_and_window_timeouts_are_holds(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / 'runtime.json'
            runtime.write_text(json.dumps(dict(output=str(root), caps=dict(seven_day=85, five_hour=70),
                                                 account=['a', 'b'])))
            d = driver.Driver(runtime, [])
            raw = json.dumps(dict(claudeAiOauth=dict(accessToken='fresh', expiresAt=9000 * 1000)))
            with mock.patch.object(driver.time, 'time', return_value=1000), \
                 mock.patch.object(driver.subprocess, 'run', return_value=mock.Mock(stdout=raw)), \
                 mock.patch.object(driver.cell.urllib.request, 'urlopen', side_effect=TimeoutError('profile timed out')):
                self.assertFalse(d.ready('claude', 'development', 2))
            self.assertIn('profile timed out', d.state['current']['reason'])
            with mock.patch.object(driver.time, 'time', return_value=1000), \
                 mock.patch.object(driver, 'credential', return_value=dict(
                    expires=9000, account=['a', 'b'], access_token='fresh')), \
                 mock.patch.object(driver.cell, 'claude_limits', side_effect=TimeoutError('usage timed out')):
                self.assertFalse(d.ready('claude', 'development', 2))
            self.assertIn('usage timed out', d.state['current']['reason'])

    def test_claude_limits_accepts_access_token(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(dict(five_hour=dict(
            utilization=12, resets_at='2026-10-21T09:00:00+00:00'))).encode()
        with mock.patch.object(run_cell.urllib.request, 'urlopen', return_value=response):
            with mock.patch.object(run_cell.urllib.request, 'Request', wraps=run_cell.urllib.request.Request) as request:
                self.assertEqual(run_cell.claude_limits({}, 'new')['five_hour']['used'], 12)
        self.assertEqual(request.call_args.kwargs['headers']['Authorization'], 'Bearer new')

    def test_credential_snapshot_carries_window_token(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(dict(account=dict(uuid='owner'),
                                                     organization=dict(uuid='org'))).encode()
        raw = json.dumps(dict(claudeAiOauth=dict(accessToken='fresh', expiresAt=9000 * 1000)))
        with mock.patch.object(driver.time, 'time', return_value=1000):
            with mock.patch.object(driver.subprocess, 'run', return_value=mock.Mock(stdout=raw)):
                with mock.patch.object(driver.cell.urllib.request, 'urlopen', return_value=response):
                    with mock.patch.object(driver.cell.base, 'fingerprint', side_effect=['a', 'b']):
                        self.assertEqual(driver.credential({}), dict(expires=9000, account=['a', 'b'],
                                                                      access_token='fresh'))

    def test_finished_slot_never_redispatched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime_path = root / 'runtime.json'
            runtime_path.write_text(json.dumps(dict(output=str(root), caps=dict(seven_day=85, five_hour=70))))
            d = driver.Driver(runtime_path, [['n', 'D3', 'A', 'claude', '1']])
            (root / 'verdict-n.json').write_text(json.dumps(dict(status='COMPLETE')))
            with mock.patch.object(d, 'ready', side_effect=AssertionError('ready called')):
                with mock.patch.object(driver.cell, 'run', side_effect=AssertionError('redispatched')):
                    d.run()
            self.assertIn('complete', (root / 'driver.log').read_text())

    def test_quota_stop_archived_before_redispatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime_path = root / 'runtime.json'
            runtime_path.write_text(json.dumps(dict(output=str(root), caps=dict(seven_day=85, five_hour=70))))
            d = driver.Driver(runtime_path, [])
            (root / 'verdict-n.json').write_text(json.dumps(dict(status='STOP', reason='shared account fault during execution: quota')))
            (root / 'n').mkdir()
            with mock.patch.object(driver.cell, 'run', return_value=0) as call:
                self.assertTrue(d.dispatch(['n', 'D3', 'B', 'claude', '1']))
            call.assert_called_once()
            self.assertTrue((root / 'verdict-n.stop-1.json').exists())
            self.assertTrue((root / 'n.stop-1').exists())

    def test_split_arm_waits_for_reset_even_if_estimate_falls(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime_path = root / 'runtime.json'
            runtime_path.write_text(json.dumps(dict(output=str(root), caps=dict(seven_day=85, five_hour=70),
                                                    account=['a', 'b'])))
            slots = [['first', 'D3', 'A', 'claude', '1'], ['second', 'D3', 'B', 'claude', '1']]
            d = driver.Driver(runtime_path, slots)
            windows = {'seven_day': dict(used=80, resets='2026-10-21T09:00:00+00:00'),
                       'five_hour': dict(used=40, resets='2026-10-21T09:00:00+00:00')}
            with mock.patch.object(driver, 'credential', return_value=dict(
                    expires=driver.time.time() + 7000, account=['a', 'b'], access_token='fresh')):
                with mock.patch.object(driver.cell, 'claude_limits', return_value=windows):
                    with mock.patch.object(driver, 'estimates', return_value=dict(seven_day=10, five_hour=25)):
                        self.assertFalse(d.ready('claude', 'development', 1, slot='second', previous='first'))
                    self.assertEqual(d.state['split_wait']['second'], {'seven_day': '2026-10-21T09:00:00+00:00'})
                    with mock.patch.object(driver, 'estimates', return_value=dict(seven_day=1, five_hour=1)):
                        self.assertFalse(d.ready('claude', 'development', 1, slot='second', previous='first'))
                    windows['seven_day']['resets'] = '2026-10-21T10:00:00+00:00'
                    with mock.patch.object(driver, 'estimates', return_value=dict(seven_day=1, five_hour=1)):
                        with mock.patch.object(d, 'image', return_value=True):
                            self.assertTrue(d.ready('claude', 'development', 1, slot='second', previous='first'))

    def test_split_wait_ignores_reset_jitter_but_releases_on_real_reset(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / 'runtime.json'
            runtime.write_text(json.dumps(dict(output=str(root), caps=dict(seven_day=85, five_hour=70),
                                                account=['a', 'b'])))
            d = driver.Driver(runtime, [])
            d.state['split_wait']['second'] = {'five_hour': '2026-10-21T08:59:59.541426+00:00'}
            windows = {w: dict(used=0, resets='2026-10-21T09:00:00.323437+00:00') for w in driver.WINDOWS}
            with mock.patch.object(driver, 'credential', return_value=dict(
                    expires=driver.time.time() + 7000, account=['a', 'b'], access_token='fresh')):
                with mock.patch.object(driver.cell, 'claude_limits', return_value=windows):
                    with mock.patch.object(d, 'image', return_value=True):
                        self.assertFalse(d.ready('claude', 'development', 1, slot='second'))
                    windows['five_hour']['resets'] = '2026-10-21T10:00:00+00:00'
                    with mock.patch.object(d, 'image', return_value=True):
                        self.assertTrue(d.ready('claude', 'development', 1, slot='second'))


if __name__ == '__main__':
    unittest.main()
