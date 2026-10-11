#!/usr/bin/env python3
"""0247 LF/startup regressions: retained fixtures and fake CLIs, no native models.

BaselineRegressionTests deliberately asserts the new invariant against the old
implementation; run it explicitly to retain the expected red evidence.
"""
from contextlib import ExitStack
from copy import deepcopy
from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import sys

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / 'fixtures'
CATALOGS = ('skills', 'plugins', 'mcp_servers')
UNICODE = 'answer\u2028line separator\u2029paragraph separator\u0085next line'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache
def candidate():
    return load('runner0247_focused_tests', HERE / 'runner.py')


@lru_cache
def custody():
    module = load('custody0245_reused0247', HERE.parent / '0245/test_peer.py')
    module.fixture.HERE = HERE
    return module


def rows(path):
    return [json.loads(line) for line in path.read_bytes().split(b'\n') if line.strip()]


def emit(path, values, separator='\n'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((separator.join(json.dumps(v, ensure_ascii=False) for v in values)
                      + separator).encode('utf-8'))


def terminal(answer=UNICODE):
    return [dict(type='item.completed', item=dict(type='agent_message', text=answer)),
            dict(type='turn.completed', usage=dict(input_tokens=3, output_tokens=5))]


def canonical(value):
    return {key: sorted(value[key], key=lambda v: json.dumps(v, sort_keys=True))
            for key in CATALOGS}


class Scratch(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='0247-fake-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)


class BaselineRegressionTests(Scratch):
    def test_old_helper_accepts_retained_unicode_command(self):
        old = load('peer0245_baseline_red', HERE.parent / '0245/peer.py')
        capture = self.root / 'peer.jsonl'
        emit(capture, terminal('valid answer'))
        capture.write_bytes((FIXTURES / 'd05-unicode-command.jsonl').read_bytes() + capture.read_bytes())
        self.assertEqual(old.answer('codex', capture), 'valid answer')

    def test_old_inventory_keeps_retained_unicode_command(self):
        old = load('evidence0234_baseline_red', HERE.parent / '0234/evidence.py')
        self.assertEqual(old.lines(FIXTURES / 'd05-unicode-command.jsonl'),
                         rows(FIXTURES / 'd05-unicode-command.jsonl'))

    def test_old_startup_accepts_retained_consistent_pair(self):
        old = load('runner0245_baseline_red', HERE.parent / '0245/runner.py')
        app = old.Runner.__new__(old.Runner)
        app.frame = SimpleNamespace(cell_run=SimpleNamespace(lines=rows))
        inits = rows(FIXTURES / 'd05-init-pair.jsonl')
        emit(self.root / 'run/stdout', inits)
        self.assertEqual(app.boot_catalogs(self.root, 'claude'), canonical(inits[0]))


class PeerFramingTests(Scratch):
    def setUp(self):
        super().setUp()
        self.peer = load('peer0247_focused', HERE / 'peer.py')
        self.capture = self.root / 'peer.jsonl'

    def test_exact_fixture_provenance_and_source_hashes(self):
        provenance = json.loads((FIXTURES / 'provenance.json').read_text())
        for source in provenance['sources']:
            with self.subTest(fixture=source['fixture']):
                self.assertEqual(hashlib.sha256(Path(source['path']).read_bytes()).hexdigest(), source['sha256'])
                self.assertEqual(hashlib.sha256((FIXTURES / source['fixture']).read_bytes()).hexdigest(), source['fixture_sha256'])
        raw = (FIXTURES / 'd05-unicode-command.jsonl').read_bytes()
        self.assertEqual(len(raw.split(b'\n')), 2)
        self.assertIn(b'\xe2\x80\xa8', raw)
        source = provenance['sources'][0]
        self.assertEqual(raw[:-1], Path(source['path']).read_bytes().split(b'\n')[source['lf_record'] - 1])

    def test_lf_crlf_payload_matrix_preserves_capture_bytes(self):
        command = rows(FIXTURES / 'd05-unicode-command.jsonl')
        for separator in ('\n', '\r\n'):
            for answer in ('ordinary answer', 'a\u2028b', 'a\u2029b', 'a\u0085b', UNICODE):
                with self.subTest(separator=repr(separator), answer=repr(answer)):
                    emit(self.capture, command + terminal(answer), separator)
                    before = self.capture.read_bytes()
                    self.assertEqual(self.peer.answer('codex', self.capture), answer)
                    self.assertEqual(self.capture.read_bytes(), before)

    def test_byte_exact_retained_command_is_accepted_without_reencoding(self):
        emit(self.capture, terminal())
        self.capture.write_bytes((FIXTURES / 'd05-unicode-command.jsonl').read_bytes() + self.capture.read_bytes())
        before = self.capture.read_bytes()
        self.assertEqual(self.peer.answer('codex', self.capture), UNICODE)
        self.assertEqual(self.capture.read_bytes(), before)

    def test_invalid_json_failed_error_missing_duplicate_terminal_and_answer_reject(self):
        cases = {
            'invalid-json': b'{"unfinished":\n',
            'failed': terminal() + [dict(type='turn.failed')],
            'error': terminal() + [dict(type='error')],
            'missing-completed': terminal()[:-1],
            'duplicate-completed': terminal() + [terminal()[-1]],
            'missing-answer': terminal()[-1:],
            'blank-answer': terminal(' \t '),
        }
        for name, values in cases.items():
            with self.subTest(case=name):
                if isinstance(values, bytes):
                    self.capture.write_bytes(values)
                else:
                    emit(self.capture, values)
                before = self.capture.read_bytes()
                with self.assertRaises(ValueError):
                    self.peer.answer('codex', self.capture)
                self.assertEqual(self.capture.read_bytes(), before)

    def test_claude_terminal_failure_and_missing_answer_still_reject(self):
        for value in (dict(type='result', is_error=True, result=UNICODE),
                      dict(type='result', is_error=False),
                      dict(type='result', is_error=False, result=' ')):
            with self.subTest(value=value):
                self.capture.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    self.peer.answer('claude', self.capture)


class InstalledUnicodeTests(unittest.TestCase):
    def test_installed_fake_capture_and_answer_survive_for_both_engines(self):
        reused = custody()
        fixture = reused.CustodyTests()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        fake = reused.fixture.FAKE.format(python=sys.executable, answer=UNICODE,
                                         stderr=reused.NATIVE_STDERR)
        for engine in ('claude', 'codex'):
            (fixture.bin / engine).write_text(fake)
        before = fixture.peer['source_identity'](fixture.repo)
        for engine in ('claude', 'codex'):
            with self.subTest(engine=engine):
                result = fixture.invoke(engine)
                self.assertEqual(result.returncode, 0, result.stderr)
                summary = json.loads(result.stdout)
                out = Path(summary['receipt'])
                attempt, completion = fixture.receipt(out)
                self.assertEqual(out.parent, fixture.repo / '.devlyn/pair')
                self.assertEqual((out / attempt['capture']).read_bytes(), fixture.expected.read_bytes())
                self.assertEqual(Path(summary['final_answer']).read_text().strip(), UNICODE)
                self.assertEqual(completion['status'], 'EXITED')
                self.assertEqual(completion['exit_code'], 0)
                self.assertTrue(completion['source_unchanged'])
                self.assertEqual(completion['source_after'], before)
                fixture.assert_native_flags(engine, attempt, None)
        self.assertEqual(fixture.peer['source_identity'](fixture.repo), before)


class RunnerTests(Scratch):
    def setUp(self):
        super().setUp()
        self.r = candidate()
        runtime = self.root / 'runtime.json'
        self.r.write(runtime, dict(tasks_file=str(HERE.parent / '0245/tasks-smoke.json'),
                                  phase='smoke', output=str(self.root / 'verdicts')))
        # Construct the real Runner and its private imported modules. No init mocks.
        self.app = self.r.Runner(runtime)
        self.out = self.root / 'evidence'
        self.out.mkdir()
        self.evidence = self.app.frame.cell_run.evidence
        self.inits = rows(FIXTURES / 'd05-init-pair.jsonl')

    def boot(self, values):
        emit(self.out / 'run/stdout', values)
        return self.app.boot_catalogs(self.out, 'claude')

    def test_actual_private_inventory_cell_identity_and_usage_reader_bindings(self):
        frame = self.app.frame
        self.assertIs(frame.usage.evidence, self.evidence)
        self.assertIs(self.evidence.lines, self.r.lines)
        self.assertIs(frame.cell_run.lines, self.r.cell_lines)
        self.assertIs(frame.cell_run.identity.__globals__['lines'], self.r.cell_lines)
        self.assertIs(frame.usage.base.events, self.r.events)
        self.assertIs(self.evidence.claude_envelopes.func, self.r.discovery.claude_envelopes)
        source = FIXTURES / 'd05-unicode-command.jsonl'
        for reader in (self.evidence.lines, frame.cell_run.lines,
                       frame.cell_run.identity.__globals__['lines'], frame.usage.base.events):
            self.assertEqual(reader(source), rows(source))
        other = self.r.Runner(self.app.runtime_path)
        self.assertIsNot(other.frame.cell_run.evidence, self.evidence)
        with patch.object(self.evidence, 'lines', return_value=[{'sentinel': True}]):
            self.assertEqual(other.frame.cell_run.evidence.lines(source), rows(source))

    def test_tolerant_dict_rows_and_original_missing_path_semantics(self):
        path = self.out / 'mixed.jsonl'
        path.write_bytes(b'not json\n[]\nnull\n42\n' + (FIXTURES / 'd05-unicode-command.jsonl').read_bytes())
        for reader in (self.r.lines, self.r.cell_lines, self.r.events):
            self.assertEqual(reader(path), rows(FIXTURES / 'd05-unicode-command.jsonl'))
        absent = self.out / 'absent'
        self.assertEqual(self.r.lines(absent), [])
        self.assertEqual(self.r.cell_lines(absent), [])
        with self.assertRaises(FileNotFoundError):
            self.r.events(absent)
        self.assertEqual(self.r.lines(self.out), [])
        for reader in (self.r.cell_lines, self.r.events):
            with self.assertRaises(IsADirectoryError):
                reader(self.out)

    def test_all_101_retained_rollout_records_survive_every_actual_reader(self):
        provenance = json.loads((FIXTURES / 'provenance.json').read_text())
        source = next(item for item in provenance['sources'] if item.get('valid_lf_records') == 101)
        path = Path(source['path'])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source['sha256'])
        expected = rows(path)
        self.assertEqual(len(expected), 101)
        for reader in (self.evidence.lines, self.app.frame.cell_run.lines,
                       self.app.frame.cell_run.identity.__globals__['lines'],
                       self.app.frame.usage.base.events):
            self.assertEqual(reader(path), expected)
        for row in rows(FIXTURES / source['fixture']):
            self.assertIn(row, expected)

    def test_bound_inventory_consumes_retained_command(self):
        source = FIXTURES / 'd05-unicode-command.jsonl'
        (self.out / 'run').mkdir()
        (self.out / 'run/stdout').write_bytes(source.read_bytes())
        with patch.object(self.evidence, 'lines', wraps=self.evidence.lines) as reader:
            inv = self.evidence.inventory(self.out, dict(engine='codex', config='codex'))
        self.assertIn(unittest.mock.call(self.out / 'run/stdout'), reader.call_args_list)
        self.assertEqual(self.evidence.lines(self.out / 'run/stdout'), rows(source))
        self.assertEqual(inv['owner_threads'], set())

    def test_identity_rejects_unicode_reroute_through_actual_alias(self):
        route = self.app.tasks['routes']['codex']['owner']
        plan = dict(engine='codex', config='codex', model=route['model'], effort=route['effort'])
        emit(self.out / 'run/stdout', [dict(type='thread.started', thread_id='owner')])
        path = self.out / 'home/.codex/sessions/owner.jsonl'
        native = [dict(type='session_meta', payload=dict(id='owner', source='exec')),
                  dict(type='turn_context', payload=dict(model=route['model'], effort=route['effort']))]
        emit(path, native)
        self.assertEqual(self.app.frame.cell_run.identity(self.out, plan)['status'], 'MATCH')
        emit(path, native + [dict(type='event_msg', payload=dict(type='model_reroute', reason=UNICODE))])
        result = self.app.frame.cell_run.identity(self.out, plan)
        self.assertEqual(result['status'], 'MISMATCH')
        self.assertIn('model_reroute in owner.jsonl', result['violations'])

    def test_rollout_counter_reader_keeps_unicode_payload_and_counts_once(self):
        sessions = self.out / 'home/.codex/sessions'
        counters = dict(input_tokens=100, cached_input_tokens=70, cache_write_input_tokens=0,
                        output_tokens=12, reasoning_output_tokens=8)
        emit(sessions / 'owner.jsonl', [dict(type='session_meta', payload=dict(id='owner')),
             dict(type='event_msg', payload=dict(type='token_count', text=UNICODE,
                  info=dict(total_token_usage=counters)))])
        self.assertEqual(self.app.frame.usage.rollout_counters(sessions), {'owner': counters})

    def inline(self, value, *, copied=False):
        text = json.dumps(value, ensure_ascii=False)
        emit(self.out / 'run/stdout', [dict(type='item.completed', item=dict(
             type='command_execution', command='python3 inspect_capture.py',
             aggregated_output=text + '\n' + text, exit_code=0))])
        if copied:
            path = self.out / 'tmp/captured-result.json'
            path.parent.mkdir(exist_ok=True)
            path.write_text(text)
        envelopes, unreadable = self.evidence.claude_envelopes(self.out)
        inv = dict(envelopes=envelopes, unreadable=unreadable, transcripts={},
                   claude_owner={}, attempted=dict(judges={}))
        return envelopes, self.app.frame.usage.claude(inv, dict(engine='codex'))

    def envelope(self):
        return dict(type='result', session_id='unicode-peer', is_error=False, result=UNICODE,
                    modelUsage={'claude-opus-5-5': dict(inputTokens=11, cacheReadInputTokens=3,
                    cacheCreationInputTokens=2, outputTokens=7, reasoningOutputTokens=5)})

    def test_inline_unicode_result_usage_survives_and_deduplicates_stored_copy(self):
        for copied in (False, True):
            with self.subTest(copied=copied):
                envelopes, (totals, gaps) = self.inline(self.envelope(), copied=copied)
                self.assertEqual(len(envelopes['unicode-peer']), 1)
                self.assertEqual(gaps, [])
                self.assertEqual(totals, {'claude-opus-5-5': dict(input=11, cache_read=3, cache_write=2, output=7)})

    def test_inline_missing_and_invalid_counters_remain_gaps(self):
        variants = [None, {}, dict(inputTokens=11, outputTokens=7),
                    dict(inputTokens=True, cacheReadInputTokens=3, cacheCreationInputTokens=2, outputTokens=7),
                    dict(inputTokens=11, cacheReadInputTokens=3, cacheCreationInputTokens=2, outputTokens=-1)]
        for counters in variants:
            with self.subTest(counters=counters):
                value = self.envelope()
                if counters is None:
                    del value['modelUsage']
                else:
                    value['modelUsage'] = {'claude-opus-5-5': counters}
                envelopes, (_, gaps) = self.inline(value)
                self.assertEqual(list(envelopes), ['unicode-peer'])
                self.assertTrue(gaps)

    def test_single_and_retained_pair_have_exact_same_catalog(self):
        expected = canonical(self.inits[0])
        self.assertEqual(self.boot(self.inits[:1]), expected)
        self.assertEqual(self.boot(self.inits[1:]), expected)
        self.assertEqual(self.boot(self.inits), expected)

    def test_normalized_catalog_order_and_unrelated_init_fields_do_not_conflict(self):
        pair = deepcopy(self.inits)
        for key in CATALOGS:
            pair[0][key] += [{'name': 'synthetic-catalog-item'}]
            pair[1][key] = list(reversed(pair[0][key]))
        pair[0].update(cwd='/work', uuid='first')
        pair[1].update(cwd='/elsewhere', uuid='second')
        self.assertEqual(self.boot(pair), canonical(pair[0]))

    def test_missing_or_malformed_catalog_on_any_init_rejects(self):
        for key in CATALOGS:
            for invalid in (None, '[]', {}, 1):
                with self.subTest(key=key, invalid=invalid):
                    pair = deepcopy(self.inits); pair[1][key] = invalid
                    with self.assertRaisesRegex(ValueError, 'missing or malformed'):
                        self.boot(pair)
            pair = deepcopy(self.inits); del pair[1][key]
            with self.assertRaisesRegex(ValueError, 'missing or malformed'):
                self.boot(pair)

    def test_missing_blank_or_malformed_identity_on_any_init_rejects(self):
        for key in ('session_id', 'model'):
            for index in (0, 1):
                for invalid in (None, '', ' \t', 1, []):
                    with self.subTest(key=key, index=index, invalid=invalid):
                        pair = deepcopy(self.inits); pair[index][key] = invalid
                        with self.assertRaisesRegex(ValueError, 'missing or malformed'):
                            self.boot(pair)
                pair = deepcopy(self.inits); del pair[index][key]
                with self.assertRaisesRegex(ValueError, 'missing or malformed'):
                    self.boot(pair)

    def test_conflicting_identity_catalog_and_later_third_row_reject(self):
        for key in ('session_id', 'model') + CATALOGS:
            with self.subTest(key=key):
                pair = deepcopy(self.inits)
                pair[1][key] = ['different'] if key in CATALOGS else 'different'
                with self.assertRaisesRegex(ValueError, 'conflict'):
                    self.boot(pair)
        values = deepcopy(self.inits) + [dict(type='system', subtype='init')]
        with self.assertRaisesRegex(ValueError, 'missing or malformed'):
            self.boot(values)

    def test_no_init_rejects_and_codex_config_none_ignores_claude_catalog(self):
        with self.assertRaisesRegex(ValueError, 'missing or malformed'):
            self.boot([])
        self.assertIsNone(self.app.boot_catalogs(self.out, 'codex'))

    def test_real_inherited_expected_catalog_gate_rejects_drift_before_grading(self):
        self.boot(self.inits)
        expected = canonical(self.inits[0]); expected['skills'] += ['not-installed']
        self.app.runtime['boot_catalogs'] = dict(claude=dict(P=expected))
        self.r.write(self.out / 'plan.json', dict(config='claude', engine='claude', arm='P'))
        run_globals = self.app.run.__func__.__globals__
        with ExitStack() as stack:
            for target, name, value in (
                (self.app, 'validate', None), (self.app, 'preflight', ({}, None)),
                (self.app, 'prepare', self.out),
                (self.app.frame.cell_run, 'run', dict(owner_status='EXITED_0', seconds=0,
                     identity=dict(status='MATCH'), teardown='CLEAN')),
                (self.app.frame, 'seal_after_teardown', ('fake-seal', [])),
                (self.app.frame.usage, 'record', dict(completeness='COMPLETE', gaps=[], input_tokens=1, output_tokens=1)),
                (run_globals['policy'], 'receipts', ({}, [])),
                (run_globals['policy'], 'check', dict(status='MATCH', gaps=[], protocol_violations=[])),
                (run_globals['accounting'], 'audit', dict(gaps=[]))):
                stack.enter_context(patch.object(target, name, return_value=value))
            grading = stack.enter_context(patch.object(self.app.frame.check, 'check'))
            self.assertEqual(self.app.run('synthetic-drift', 'unused', 'P', 'claude'), 2)
            grading.assert_not_called()
        verdict = self.r.read(Path(self.app.runtime['output']) / 'verdict-synthetic-drift.json')
        self.assertEqual(verdict['status'], 'STOP')
        self.assertEqual(verdict['reason'], 'ValueError: boot catalog contamination or drift')
        self.assertEqual(verdict['usage'], 'COMPLETE')


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    for case in (PeerFramingTests, InstalledUnicodeTests, RunnerTests, custody().CustodyTests):
        suite.addTests(loader.loadTestsFromTestCase(case))
    return suite


if __name__ == '__main__':
    unittest.main(verbosity=2)
