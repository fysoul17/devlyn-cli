"""Model-free, Docker-free contract tests for 0236."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import stat
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
REGISTRATION = HERE.parent.parent / 'iterations/0236-review-findings-repair.md'
SOURCE_OUTPUT = Path.home() / '.local/share/nx01/0235-live/out'
IMAGE = 'sha256:image'
SID = 'session-1'


def load(name):
    spec = importlib.util.spec_from_file_location('test_0236_' + name.replace('/', '_').replace('-', '_'),
                                                  HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


messages, cont, decide, d4 = load('messages'), load('run_continuation'), load('decide'), load('witnesses/d4-writer-strict')


def jsonl(*events):
    return ''.join(json.dumps(e) + '\n' for e in events)


def model_usage(i, r, w, o):
    return {'claude-opus-5-5': dict(inputTokens=i, cacheReadInputTokens=r, cacheCreationInputTokens=w, outputTokens=o)}


def assistant(message_id, i, r, w, o, session=SID):
    return dict(type='assistant', sessionId=session, message=dict(id=message_id, model='claude-opus-5-5', usage=dict(
        input_tokens=i, cache_read_input_tokens=r, cache_creation_input_tokens=w, output_tokens=o)))


def source_cell(root, name='r01-D3-claude-B-r1', status='PRODUCT_INCOMPLETE'):
    """A sealed 0235-shaped cell: evidence manifest, verdict, seal, init stream, transcript with cost-state."""
    src = root / name
    files = {
        'run/stdout': jsonl(dict(type='system', subtype='init', session_id=SID, model='claude-opus-5-5', tools=['Bash'],
                                 mcp_servers=[dict(name='docs', status='pending')]),
                            dict(type='result', session_id=SID, modelUsage=model_usage(1, 10, 5, 4))),
        'cell/work/product.txt': 'product\n', 'cell/work/.git/index': 'index\n', 'tmp/scratch.txt': 'tmp\n',
        f'home/.claude/projects/-cell-work/{SID}.jsonl': jsonl(
            assistant('m1', 1, 10, 5, 4), dict(type='cost-state', sessionId=SID, modelUsage=model_usage(1, 10, 5, 4))),
        'baseline.json': '{}', 'prompt.txt': 'prompt', 'plan.json': json.dumps(dict(
            name=name, task='D3', config='claude', model='claude-opus-5-5', effort='high', image=IMAGE, argv=['claude'])),
        'harness/caller.json': '{}', 'seal.json': json.dumps(dict(image=IMAGE)),
    }
    for engine, complete in (('claude', True), ('codex', False)):
        files[f'assessment/{engine}/result.json'] = json.dumps(dict(seconds=60, usage='UNKNOWN', exit_code=0, complete=complete))
    for relative, text in files.items():
        (src / relative).parent.mkdir(parents=True, exist_ok=True)
        (src / relative).write_text(text)
    manifest = {str(p.relative_to(src)): hashlib.sha256(p.read_bytes()).hexdigest()
                for n in ('run', 'cell', 'tmp', 'home') for p in sorted((src / n).rglob('*')) if p.is_file()}
    (src / 'evidence.manifest.json').write_text(json.dumps(dict(files=manifest, failures=[])))
    (root / f'verdict-{name}.json').write_text(json.dumps(dict(
        status=status, evidence_manifest_sha256=hashlib.sha256((src / 'evidence.manifest.json').read_bytes()).hexdigest(),
        owner_status='EXITED_0', owner_seconds=200.0, usage='COMPLETE', input_tokens=16, output_tokens=4)))
    return src


class Messages(unittest.TestCase):
    def test_generic_text_is_the_registered_text(self):
        self.assertIn(f'**G (generic):** "{messages.GENERIC}"', REGISTRATION.read_text())
        self.assertEqual(messages.ENGINES, ('claude', 'codex'))

    def test_findings_are_cut_verbatim_with_their_code(self):
        findings = ('[\n    {"severity": "medium", "witness": {"code": "x = \\"findings\\": [1]"}},\n'
                    '    {"severity":"low"}\n  ]')
        answer = '```json\n{\n  "complete": false,\n  "findings": ' + findings + ',\n  "limitations": []\n}\n```'
        self.assertEqual(messages.findings_text(answer), findings)
        with self.assertRaisesRegex(ValueError, 'not a valid'):
            messages.findings_text('{"complete": "no", "findings": []}')

    def test_f_message_appends_both_reviewers_in_assessor_order(self):
        with tempfile.TemporaryDirectory() as temp:
            unit = Path(temp) / 'u'
            for engine, event in (
                    ('claude', dict(type='result', result='{"complete": true, "findings": [{"severity": "low"}]}')),
                    ('codex', dict(type='item.completed', item=dict(type='agent_message',
                                                                   text='{"complete": false, "findings": []}')))):
                (unit / 'assessment' / engine).mkdir(parents=True)
                (unit / 'assessment' / engine / 'stdout').write_text(jsonl(event))
            self.assertEqual(messages.message(temp, 'u', 'F'), messages.GENERIC + "\n\nThe reviewers' findings:\n\n"
                             'Reviewer 1:\n[{"severity": "low"}]\n\nReviewer 2:\n[]')
            self.assertEqual(messages.message(temp, 'u', 'G'), messages.GENERIC)

    @unittest.skipUnless(SOURCE_OUTPUT.is_dir(), '0235 live output not present')
    def test_frozen_messages_regenerate_from_the_sources(self):
        for name, text in messages.generate(SOURCE_OUTPUT).items():
            self.assertEqual((HERE / 'messages' / name).read_text(), text, name)
        self.assertEqual(sorted(p.name for p in (HERE / 'messages').iterdir()),
                         sorted(['G.txt'] + [f'{u}-F.txt' for u in messages.UNITS]))


class Cells(unittest.TestCase):
    def test_registered_order(self):
        order = [('r01', 'F', 'G'), ('r03', 'G', 'F'), ('r04', 'F', 'G'), ('r08', 'G', 'F')]
        expected = [(u, a, 1) for u, *arms in order for a in arms] + [(u, a, 2) for u, *arms in order for a in arms[::-1]]
        rows = [line.split() for line in (HERE / 'cells.tsv').read_text().splitlines() if not line.startswith('#')]
        self.assertEqual([(unit[:3], arm, int(rep)) for _, unit, arm, rep in rows], expected)
        self.assertEqual([name for name, *_ in rows],
                         [f'c{i:02d}-{u}-{a}-{r}' for i, (u, a, r) in enumerate(expected, 1)])
        self.assertTrue(all(name[4:7] == unit[:3] for name, unit, *_ in rows))
        self.assertEqual({unit for _, unit, *_ in rows}, set(messages.UNITS))
        smoke = [line.split() for line in (HERE / 'smoke.tsv').read_text().splitlines() if not line.startswith('#')]
        self.assertEqual(smoke, [['s01-r06-G', 'r06-D3-claude-B-r2', 'G']])
        self.assertEqual(cont.FIRST, {'r01-D3-claude-B-r1': 'c01-r01-F-1', 'r03-D4-claude-R-r1': 'c03-r03-G-1',
                                      'r04-D4-claude-B-r1': 'c05-r04-F-1', 'r08-D4-claude-R-r2': 'c07-r08-G-1'})
        self.assertFalse((HERE / 'environment.json').exists())  # no single global reference (§5)


class Source(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_index_drift_alone_is_allowed_and_recorded(self):
        src = source_cell(self.root)
        (src / 'cell/work/.git/index').write_text('refreshed\n')
        origin = cont.verify_source(src, IMAGE)
        self.assertEqual(origin['manifest_drift'], ['cell/work/.git/index'])
        self.assertEqual((origin['session'], origin['cost_state']), (SID, model_usage(1, 10, 5, 4)))
        self.assertEqual(origin['init']['tools'], ['Bash'])

    def test_other_drift_stop_and_image_refuse(self):
        src = source_cell(self.root)
        (src / 'tmp/scratch.txt').write_text('changed\n')
        with self.assertRaisesRegex(cont.SourceError, 'evidence changed'):
            cont.verify_source(src, IMAGE)
        src = source_cell(self.root, 'r02')
        with self.assertRaisesRegex(cont.SourceError, 'image'):
            cont.verify_source(src, 'sha256:other')
        src = source_cell(self.root, 'r03', status='STOP')
        with self.assertRaisesRegex(cont.SourceError, 'STOP'):
            cont.verify_source(src, IMAGE)

    def test_build_copies_and_writes_the_resume_plan(self):
        src = source_cell(self.root)
        os.mkfifo(src / 'tmp/pipe', 0o600)  # left by a FIFO test; not a sealed regular file
        origin = cont.verify_source(src, IMAGE)
        out = self.root / 'new' / 'c01'
        out.parent.mkdir()
        plan = cont.build(src, out, origin, 'repair message')
        self.assertEqual(plan['argv'], ['claude', '-p', '--resume', SID, '--model', 'claude-opus-5-5', '--effort', 'high',
                                        '--permission-mode', 'bypassPermissions', '--output-format', 'stream-json',
                                        '--verbose', 'repair message'])
        self.assertEqual((plan['name'], plan['tmp']), ('c01', str(out / 'tmp')))
        self.assertEqual((out / 'tmp.seed/scratch.txt').read_text(), 'tmp\n')
        self.assertTrue(stat.S_ISFIFO(os.lstat(out / 'tmp.seed/pipe').st_mode))
        self.assertEqual(list((out / 'tmp').iterdir()), [])
        self.assertFalse((out / 'run').exists() or (out / 'snapshot').exists())
        self.assertEqual(out.stat().st_mode & 0o777, 0o700)

    def test_build_refuses_a_harness_copy_that_differs(self):
        src = source_cell(self.root)
        origin, real = cont.verify_source(src, IMAGE), shutil.copytree
        def corrupt(source, target, *args, **kwargs):  # shutil.copytree recurses through the patched name
            result = real(source, target, *args, **kwargs)
            if Path(source).name == 'harness' and Path(source).parent == src:
                (Path(target) / 'caller.json').write_text('{"changed": true}')
            return result
        with mock.patch.object(cont.shutil, 'copytree', corrupt), self.assertRaisesRegex(cont.SourceError, 'copy differs'):
            cont.build(src, self.root / 'c02', origin, 'repair message')


class Resume(unittest.TestCase):
    """The continuation's session ancestry and its own turn usage."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = source_cell(self.root)
        self.origin = cont.verify_source(self.src, IMAGE)
        self.out = self.root / 'c01'
        (self.out / 'run').mkdir(parents=True)
        self.transcript = self.out / self.origin['transcript']
        self.transcript.parent.mkdir(parents=True)

    def resume(self, session=SID, appended=(), final=model_usage(3, 30, 9, 10), model='claude-opus-5-5'):
        self.transcript.write_bytes((self.src / self.origin['transcript']).read_bytes() + jsonl(*appended).encode())
        (self.out / 'run/stdout').write_text(jsonl(
            dict(type='system', subtype='init', session_id=session, model=model, tools=['Bash'],
                 mcp_servers=[dict(name='docs', status='pending')]),
            dict(type='result', session_id=session, modelUsage=final)))

    def session(self, final=(3, 30, 9, 10)):
        return dict(completeness='COMPLETE', input_tokens=sum(final[:3]), output_tokens=final[3])

    def test_session_must_be_the_source_and_extend_its_transcript(self):
        self.resume(appended=[assistant('m2', 2, 20, 4, 6)])
        env, reason = cont.session_check(self.out, self.origin)
        self.assertIsNone(reason)
        self.assertTrue(env['same_as_source'])
        self.assertEqual(env['route_differences'], {})
        self.assertEqual(env['compared']['compared'], dict(mcp_servers=['docs'], skills=[], tools=['Bash']))
        self.resume(session='other', appended=[assistant('m2', 2, 20, 4, 6)])
        self.assertIn('not the source session', cont.session_check(self.out, self.origin)[1])
        self.resume()
        self.assertIn('prefix', cont.session_check(self.out, self.origin)[1])
        self.transcript.write_text(jsonl(assistant('m2', 2, 20, 4, 6)))
        self.assertIn('prefix', cont.session_check(self.out, self.origin)[1])

    def test_the_route_must_equal_the_source_route(self):
        self.resume(appended=[assistant('m2', 2, 20, 4, 6)], model='claude-sonnet-5-5')
        env, reason = cont.session_check(self.out, self.origin)
        self.assertIsNone(reason)  # a route difference is a STOP of its own, before grading
        self.assertEqual(env['route_differences'], dict(model=dict(source='claude-opus-5-5', continuation='claude-sonnet-5-5')))
        self.assertEqual(cont.route_differences(dict(agents=['a'], plugins=['p'], tools=['Bash']),
                                                dict(agents=['a'], plugins=[], tools=['Read'])),
                         dict(plugins=dict(source=['p'], continuation=[])))  # tools are no route field

    def test_turn_is_the_result_minus_the_source_and_matches_new_messages(self):
        self.resume(appended=[assistant('m2', 1, 5, 4, 1), assistant('m3', 1, 15, 0, 5), assistant('m3', 1, 15, 0, 5)])
        turn = cont.turn_usage(self.out, self.origin, self.session())
        self.assertEqual(turn['completeness'], 'COMPLETE', turn['gaps'])
        self.assertEqual((turn['input_tokens'], turn['output_tokens']), (26, 6))
        self.assertEqual((turn['uncached_input_tokens'], turn['cache_read_tokens'], turn['cache_write_tokens']), (2, 20, 4))

    def test_disagreement_restated_history_and_outside_usage_leave_turn_unknown(self):
        self.resume(appended=[assistant('m2', 2, 20, 4, 5)])  # one output token short of the result difference
        turn = cont.turn_usage(self.out, self.origin, self.session())
        self.assertEqual((turn['completeness'], turn['input_tokens']), ('UNKNOWN', None))
        self.assertTrue(any('disagrees' in gap for gap in turn['gaps']))
        self.resume(appended=[assistant('m2', 2, 20, 4, 6)], final=model_usage(2, 20, 4, 6))  # no cost-state restore
        self.assertTrue(any('fell from' in gap for gap in cont.turn_usage(self.out, self.origin, self.session((2, 20, 4, 6)))['gaps']))
        self.resume(appended=[assistant('m1', 1, 10, 5, 4), assistant('m2', 2, 20, 4, 6)])
        self.assertTrue(any('written again' in gap for gap in cont.turn_usage(self.out, self.origin, self.session())['gaps']))
        self.resume(appended=[assistant('m2', 2, 20, 4, 6)])
        outside = dict(self.session(), input_tokens=99)
        self.assertIn('usage outside the owner session', cont.turn_usage(self.out, self.origin, outside)['gaps'])
        self.assertEqual(cont.turn_usage(self.out, self.origin, self.session())['completeness'], 'COMPLETE')


class Environment(unittest.TestCase):
    """Every continuation of a unit must match the reference its first measured continuation recorded (§5)."""
    INIT = dict(type='system', subtype='init', session_id=SID, tools=['Bash', 'Read', 'mcp__docs__a'],
                skills=['debug', 'review'], mcp_servers=[dict(name='docs', status='pending')])

    def test_skills_server_names_and_non_mcp_tools_are_compared(self):
        reference = cont.reference_environment(self.INIT)
        self.assertEqual(reference['compared'], dict(mcp_servers=['docs'], skills=['debug', 'review'], tools=['Bash', 'Read']))
        self.assertEqual(reference['recorded'], dict(mcp_tools=['mcp__docs__a'], synced_skills=[],
                                                     mcp_status=[['docs', 'pending']], account_servers=[]))
        account = cont.reference_environment(dict(self.INIT, mcp_servers=[
            dict(name='docs', status='pending'), dict(name='claude.ai Docs', status='connected', source='claudeai')]))
        self.assertEqual(cont.environment_differences(account, reference), {})  # Amendment 1: account connectors
        self.assertEqual(account['recorded']['account_servers'], ['claude.ai Docs'])
        synced = cont.reference_environment(dict(self.INIT, skills=['debug', 'review', 'anthropic-skills:pdf']))
        self.assertEqual(cont.environment_differences(synced, reference), {})  # account-synced skills: recorded only
        connected = cont.reference_environment(dict(self.INIT, tools=['Read', 'Bash', 'mcp__docs__a', 'mcp__docs__b'],
                                                    mcp_servers=[dict(name='docs', status='connected')]))
        self.assertEqual(cont.environment_differences(connected, reference), {})  # MCP tools and status: recorded only
        drifted = cont.reference_environment(dict(
            self.INIT, tools=['Bash', 'Write'], skills=['debug', 'review', 'pdf'],
            mcp_servers=[dict(name='docs', status='pending'), dict(name='other', status='connected')]))
        self.assertEqual(cont.environment_differences(drifted, reference), dict(
            mcp_servers=dict(missing=[], added=['other']), skills=dict(missing=[], added=['pdf']),
            tools=dict(missing=['Read'], added=['Write'])))

    def test_the_first_continuation_records_the_unit_reference_once_and_later_ones_match_it(self):
        with tempfile.TemporaryDirectory() as temp:
            out, path = Path(temp), Path(temp) / 'environment-r03-D4-claude-R-r1.json'
            first, later = out / 'c03-r03-G-1', out / 'c04-r03-F-1'
            for cell in (first, later):
                (cell / 'run').mkdir(parents=True)
                (cell / 'run/stdout').write_text(jsonl(self.INIT))
            env = dict(compared=cont.reference_environment(self.INIT))
            with self.assertRaises(cont.SourceError):
                cont.load_reference(path)
            self.assertIsNone(cont.unit_check(env, None, path, first))
            reference = cont.load_reference(path)
            self.assertEqual((reference['derived_from'], reference['compared']),
                             ('c03-r03-G-1', cont.reference_environment(self.INIT)['compared']))
            self.assertEqual(env['unit_reference'], dict(file=path.name, derived_from='c03-r03-G-1', differences={}))
            self.assertIn('not recorded: FileExistsError', cont.unit_check(dict(env), None, path, later))  # write-once
            self.assertEqual(cont.load_reference(path), reference)
            self.assertIsNone(cont.unit_check(env, reference, path, later))
            with_account = dict(self.INIT, mcp_servers=self.INIT['mcp_servers'] + [
                dict(name='claude.ai Docs', status='connected', source='claudeai')])
            written = json.loads(path.read_text())  # a reference written before Amendment 1 compared every server name
            (first / 'run/stdout').write_text(jsonl(with_account))
            path.write_text(json.dumps(dict(written, compared=dict(written['compared'], mcp_servers=[
                'claude.ai Docs', 'docs']), stdout_sha256=cont.digest(first / 'run/stdout'))))
            self.assertEqual(cont.load_reference(path)['compared'], reference['compared'])  # derived again from init
            self.assertIsNone(cont.unit_check(env, cont.load_reference(path), path, later))
            (first / 'run/stdout').write_text(jsonl(self.INIT))
            with self.assertRaisesRegex(cont.SourceError, 'no longer matches'):
                cont.load_reference(path)
            path.write_text(json.dumps(written))
            drifted = dict(compared=cont.reference_environment(dict(self.INIT, skills=['debug'])))
            self.assertIn('differs from the unit reference environment-r03-D4-claude-R-r1.json',
                          cont.unit_check(drifted, reference, path, later))
            self.assertEqual(drifted['unit_reference']['differences'], dict(skills=dict(missing=['review'], added=[])))
            for compared in (dict(skills=[], tools=[]), dict(skills=[], tools=[], mcp_servers='docs'),
                             dict(skills=[], tools=[], mcp_servers=[], plugins=[])):
                path.write_text(json.dumps(dict(compared=compared)))
                with self.assertRaisesRegex(cont.SourceError, 'malformed'):
                    cont.load_reference(path)

    def test_a_later_continuation_without_its_unit_reference_is_not_dispatched(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            runtime = out / 'runtime.json'
            runtime.write_text(json.dumps(dict(output=str(out), source_output=str(out / 'missing'), image=IMAGE)))
            with mock.patch.object(cont.rc, 'preflight', return_value=('venue', None)), \
                    mock.patch.object(cont.rc, 'control_unchanged', return_value=True):
                self.assertEqual(cont.run(runtime, 'c09-r01-G-2', 'r01-D3-claude-B-r1', 'G'), 3)
                self.assertIn('environment-r01-D3-claude-B-r1.json',
                              json.loads((out / 'not-dispatched-c09-r01-G-2.json').read_text())['reason'])
                self.assertFalse((out / 'verdict-c09-r01-G-2.json').exists())
                # the first continuation of the unit and the smoke (no measured unit) go on to the source checks
                self.assertEqual(cont.run(runtime, 'c01-r01-F-1', 'r01-D3-claude-B-r1', 'F'), 2)
                self.assertEqual(cont.run(runtime, 's01-r06-G', 'r06-D3-claude-B-r2', 'G'), 2)
                self.assertIn('source:', json.loads((out / 'verdict-s01-r06-G.json').read_text())['reason'])


class GradePreserved(unittest.TestCase):
    """Amendment 1: only a unit-environment STOP with intact sealed evidence is graded again, before any assessor."""

    def test_other_stops_and_changed_evidence_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            (out / 'runtime.json').write_text(json.dumps(dict(output=str(out))))
            cell = out / 'c08-r08-F-1'
            (cell / 'run').mkdir(parents=True)
            (cell / 'run/stdout').write_text('x')
            (cell / 'evidence.manifest.json').write_text(json.dumps(dict(files={'run/stdout': cont.digest(cell / 'run/stdout')}, failures=[])))
            base = dict(continuation_of='r08-D4-claude-R-r2', status='STOP',
                        evidence_manifest_sha256=cont.digest(cell / 'evidence.manifest.json'))
            verdict = out / 'verdict-c08-r08-F-1.json'
            for record, message in ((dict(base, reason='assessment failed'), 'only a unit-environment STOP'),
                                    (dict(base, reason='environment differs from the unit reference x', status='COMPLETE'),
                                     'only a unit-environment STOP'),
                                    (dict(base, reason='environment differs from the unit reference x',
                                          continuation_of='r08-D4-claude-R-r2'), 'seal.json')):
                verdict.write_text(json.dumps(record))
                with self.assertRaisesRegex((SystemExit, OSError), message):
                    cont.grade_preserved(out / 'runtime.json', 'c08-r08-F-1')
            inputs = ('plan.json', 'prompt.txt', 'baseline.json', 'continuation.txt', 'origin.json')
            for n in inputs:
                (cell / n).write_text(n)
            (cell / 'seal.json').write_text(json.dumps(dict(cell={n: cont.digest(cell / n) for n in inputs})))
            verdict.write_text(json.dumps(dict(base, reason='environment differs from the unit reference x',
                                               origin_sha256=cont.digest(cell / 'origin.json'))))
            (cell / 'baseline.json').write_text('changed')
            with self.assertRaisesRegex(SystemExit, 'sealed inputs'):
                cont.grade_preserved(out / 'runtime.json', 'c08-r08-F-1')
            (cell / 'run/stdout').write_text('changed')
            with self.assertRaisesRegex(SystemExit, 'sealed evidence'):
                cont.grade_preserved(out / 'runtime.json', 'c08-r08-F-1')
            self.assertTrue(verdict.exists())


class D4Witness(unittest.TestCase):
    """d4-writer-strict's per-test result on recorded runs: a test whose FIFO writers were never injected is STOP."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.runs = 0

    def run_record(self, *events, hung=False, end=True):
        self.runs += 1
        directory = Path(self.temp.name) / f'run{self.runs}'
        directory.mkdir()
        (directory / 'log').write_text(''.join(json.dumps([kind, 7, detail]) + '\n' for kind, detail in
                                               (('start', 1),) + events))
        (directory / 'out').write_text('1 passed\n')
        if end:
            (directory / 'end.json').write_text(json.dumps(dict(threads=[], processes=[])))
        return dict(test=f'tests/test_f.py::test_fifo_{self.runs}', mode='death', dir=str(directory), hung=hung,
                    process=mock.Mock(pid=7, returncode=0))

    def outcome(self, *runs):
        defects, stops = [], []
        for run in runs:
            d4.evaluate(run, defects, stops)
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as exit_:
            d4.finish(defects, dict(stops=stops))
        return exit_.exception.code, defects, stops

    def test_writers_that_were_never_injected_stop_and_never_pass(self):
        nonblocking = ('fifo-write', ['thread', False, '/tmp/f'])
        main = ('fifo-write', ['main', True, '/tmp/f'])
        injected = (('fifo-write', ['thread', True, '/tmp/f']), ('inject', ['death', 'thread', '/tmp/f']))
        for writes in ((nonblocking,), (main,), (nonblocking, main)):
            code, defects, stops = self.outcome(self.run_record(*writes, hung=True))
            self.assertEqual((code, defects), (2, []))  # not even a hang counts without an injection
            self.assertIn('writer not injectable', stops[0])
        self.assertEqual(self.outcome(self.run_record(*injected), self.run_record())[0], 0)  # no write-open: no STOP
        self.assertEqual(self.outcome(self.run_record(nonblocking, *injected))[0], 0)
        code, defects, stops = self.outcome(self.run_record(*injected, hung=True), self.run_record(nonblocking))
        self.assertEqual((code, len(defects), len(stops)), (1, 1, 1))  # a defect of an injected test wins
        self.assertEqual(self.outcome(self.run_record(*injected, end=False))[0], 2)
        with self.assertRaisesRegex(RuntimeError, 'did not load'):
            d4.evaluate(dict(self.run_record(), process=mock.Mock(pid=8)), [], [])

    def test_a_stall_mode_hang_after_three_injected_stalls_is_stop_not_a_defect(self):
        def stalled(count):
            events = []
            for _ in range(count):
                events += [('fifo-write', ['child', True, '/tmp/f']), ('inject', ['stall', 'child', '/tmp/f'])]
            return dict(self.run_record(*events, hung=True), mode='stall')
        code, defects, stops = self.outcome(stalled(3))
        self.assertEqual((code, defects), (2, []))
        self.assertIn('injected 40 s stalls', stops[0])
        self.assertEqual(self.outcome(stalled(2))[0], 1)  # two stalls leave room to finish: the hang is a defect


class Seeding(unittest.TestCase):
    def test_tmp_is_restored_right_after_the_volume_is_created(self):
        calls = []
        def docker(*args, **kwargs):
            calls.append(args)
            if args[0] == 'run' and fail:
                raise subprocess.CalledProcessError(1, 'docker')
            return 'ok'
        fail, volumes = False, []
        wrapped = cont.seeding(docker, Path('/seed'), IMAGE, volumes)
        wrapped('volume', 'create', '--label', 'x', 'vol')
        self.assertEqual(calls[1][:4], ('run', '--rm', '--network', 'none'))
        self.assertIn('type=volume,src=vol,dst=/dst', calls[1])
        self.assertIn('type=bind,src=/seed,dst=/src,readonly', calls[1])
        wrapped('inspect', 'cid')
        self.assertEqual(calls[-1], ('inspect', 'cid'))
        fail, calls[:] = True, []
        with self.assertRaises(subprocess.CalledProcessError):
            wrapped('volume', 'create', 'vol2')
        self.assertEqual(volumes, ['vol', 'vol2'])

    def test_a_failed_launch_removes_its_volumes_and_reports_what_stayed(self):
        calls = []
        def docker(*args, **kwargs):
            calls.append(args)
            if args[-1] == 'stuck':
                raise subprocess.CalledProcessError(1, 'docker')
            return 'ok'
        self.assertEqual(cont.discard(docker, ['vol', 'stuck']), ["stuck: Command 'docker' returned non-zero exit status 1."])
        self.assertEqual(calls, [('volume', 'rm', '--force', 'vol'), ('volume', 'rm', '--force', 'stuck')])


def cell(name, unit, arm, repair=True, fc=False, harm=False, scope=False, turn=(100, 1000, 10), full=(500, 5000, 50)):
    task = 'D3' if unit.startswith('r01') else 'D4'
    return dict(name=name, unit=unit, task=task, arm=arm, repair=repair, preservation=False, false_completion=fc,
                harm=harm, scope=scope, status='COMPLETE', complete=repair, audit_clean=not fc and not harm, witness_clean=repair,
                tree_unchanged=False, files_changed=[], cache={}, continuation=turn, operational=full)


def table(f_repairs, g_repairs, **overrides):
    """Two replicates per unit and arm; f_repairs/g_repairs map unit to its number of repairs (0-2)."""
    rows = {}
    for unit in messages.UNITS:
        for arm, wins in (('F', f_repairs), ('G', g_repairs)):
            for rep in (1, 2):
                name = f'{unit[:3]}-{arm}-{rep}'
                rows[name] = cell(name, unit, arm, repair=rep <= wins.get(unit[:3], 0), **overrides.get(name, {}))
    return rows


class Rule(unittest.TestCase):
    def test_advance_needs_margin_breadth_safety_and_cost(self):
        f, g = dict(r01=2, r03=2, r04=1, r08=1), dict(r01=1, r03=1, r04=0, r08=1)
        result = decide.rule(table(f, g))
        self.assertEqual(result['outcome'], 'ADVANCE', result['advance'])
        self.assertEqual(result['repairs'], dict(F=6, G=3))
        unit_tie = decide.rule(table(dict(r01=1, r03=2, r04=2, r08=2), dict(r01=1, r03=1, r04=0, r08=1)))
        self.assertFalse(unit_tie['advance']['d3_and_d4'])
        self.assertEqual(unit_tie['outcome'], 'INCONCLUSIVE')
        regression = decide.rule(table(dict(r01=2, r03=2, r04=2, r08=0), dict(r01=0, r03=0, r04=0, r08=1)))
        self.assertFalse(regression['advance']['every_unit'])
        costly = decide.rule(table(f, g, **{'r01-F-1': dict(turn=(10_000, 1000, 10))}))
        self.assertFalse(costly['advance']['continuation_cost'])
        self.assertTrue(costly['advance']['operational_cost'])
        self.assertEqual(costly['outcome'], 'INCONCLUSIVE')

    def test_unknown_usage_leaves_cost_unmet(self):
        f, g = dict(r01=2, r03=2, r04=1, r08=1), dict(r01=1, r03=1, r04=0, r08=1)
        result = decide.rule(table(f, g, **{'r08-G-2': dict(full=(500, None, 50))}))
        self.assertIsNone(result['advance']['operational_cost'])
        self.assertEqual(result['outcome'], 'INCONCLUSIVE')

    def test_g_without_repairs_uses_the_raw_total_fallback(self):
        f, g = dict(r01=1, r03=1, r04=0, r08=0), {}
        self.assertEqual(decide.rule(table(f, g))['outcome'], 'ADVANCE')
        heavy = {f'{u[:3]}-F-{r}': dict(turn=(126, 1000, 10)) for u in messages.UNITS for r in (1, 2)}
        self.assertFalse(decide.rule(table(f, g, **heavy))['advance']['continuation_cost'])
        light = {f'{u[:3]}-F-{r}': dict(turn=(125, 1000, 10)) for u in messages.UNITS for r in (1, 2)}
        self.assertTrue(decide.rule(table(f, g, **light))['advance']['continuation_cost'])

    def test_reject_conditions(self):
        self.assertTrue(decide.rule(table(dict(r01=1), dict(r01=1)))['reject']['f_at_most_g'])
        f, g = dict(r01=2, r03=2, r04=1, r08=1), dict(r01=1, r03=1, r04=0, r08=1)
        harm = decide.rule(table(f, g, **{'r04-F-2': dict(harm=True)}))
        self.assertEqual(harm['outcome'], 'REJECT')
        shared = decide.rule(table(f, g, **{'r08-F-2': dict(fc=True), 'r08-G-2': dict(fc=True)}))
        self.assertEqual(shared['outcome'], 'INCONCLUSIVE')  # a persisting false completion G shares: not ADVANCE
        alone = decide.rule(table(f, g, **{'r08-F-2': dict(fc=True)}))
        self.assertEqual(alone['outcome'], 'REJECT')


class Archived(unittest.TestCase):
    def test_failed_assessment_attempts_are_charged_and_unknown_usage_stays_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            cell = Path(temp) / 'c01'
            self.assertEqual(decide.archived_attempts(cell), [])
            for attempt, engine, result in (
                    ('assessment.stop-1', 'claude', dict(seconds=40, usage=model_usage(1, 2, 3, 4))),
                    ('assessment.stop-1', 'codex', dict(seconds=20, usage='UNKNOWN')),
                    ('assessment.stop-2', 'codex', dict(seconds=10, usage=dict(input_tokens=7, output_tokens=2)))):
                (cell / attempt / engine).mkdir(parents=True, exist_ok=True)
                (cell / attempt / engine / 'result.json').write_text(json.dumps(result))
            attempts = decide.archived_attempts(cell)
            self.assertEqual(attempts, [(40, 6, 4), (20, None, None), (10, 7, 2)])
            self.assertEqual(decide.add((100, 10, 1), *attempts), (170, None, None))
            self.assertEqual(decide.add((100, 10, 1), attempts[0], attempts[2]), (150, 23, 7))
            (cell / 'assessment.stop-3/claude').mkdir(parents=True)  # the run's record is lost: unknown, never zero
            self.assertEqual(decide.archived_attempts(cell)[-1], (None, None, None))
            self.assertEqual(decide.add((100, 10, 1), *decide.archived_attempts(cell)), (None, None, None))

    def test_an_unknown_wall_leaves_the_operational_cost_unmet_and_reject_computable(self):
        f, g = dict(r01=2, r03=2, r04=1, r08=1), dict(r01=1, r03=1, r04=0, r08=1)
        lost = {'r03-F-1': dict(full=(None, None, None))}
        result = decide.rule(table(f, g, **lost))
        self.assertIsNone(result['advance']['operational_cost'])
        self.assertTrue(result['advance']['continuation_cost'])
        self.assertEqual(result['outcome'], 'INCONCLUSIVE')
        cost = result['costs']['operational']['F']
        self.assertEqual((cost['wall'], cost['wall_lower_bound'], cost['input'], cost['output']), (None, 3500.0, None, None))
        self.assertEqual(cost['per_success'], dict(wall=None, input=None, output=None))
        self.assertIsNotNone(result['costs']['operational']['G']['wall'])
        self.assertEqual(decide.rule(table(f, g, **lost, **{'r04-F-2': dict(harm=True)}))['outcome'], 'REJECT')


class Load(unittest.TestCase):
    def test_repair_needs_complete_audit_and_witness_and_judgments_are_mandatory(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            for name, unit, arm, _ in decide.CELLS:
                (out / name).mkdir()
                (out / name / 'checks.json').write_text(json.dumps(dict(public=[dict(exit_code=0)])))
                (out / name / 'origin.json').write_text(json.dumps(dict(
                    source=unit, owner_status='EXITED_0', owner_seconds=200, usage='COMPLETE', input_tokens=100,
                    output_tokens=10, assessors=dict(claude=dict(seconds=60, usage=model_usage(1, 2, 3, 4)),
                                                     codex=dict(seconds=30, usage=dict(input_tokens=7, output_tokens=1))))))
                (out / f'verdict-{name}.json').write_text(json.dumps(dict(
                    task='D3' if unit.startswith('r01') else 'D4', continuation_of=unit, arm=arm, status='COMPLETE',
                    oracle=[], scope_violations=[], owner_status='HANG_TIMEOUT' if name == 'c01-r01-F-1' else 'EXITED_0',
                    owner_seconds=100, turn_usage='COMPLETE', turn_input_tokens=50, turn_output_tokens=5,
                    assessments=[dict(route=dict(engine='claude'), seconds=60, usage=model_usage(1, 1, 1, 1)),
                                 dict(route=dict(engine='codex'), seconds=30, usage='UNKNOWN')])))
            names = [n for n, *_ in decide.CELLS]
            decisions = dict(audited=names, false_completion=['c02-r01-G-1'], user_data_harm=[], adjudicated={},
                             witnesses={'d3-parseoptions-override': {n: n == 'c09-r01-G-2' for n in names if '-r01-' in n},
                                        'd4-writer-strict': {n: False for n in names if '-r01-' not in n}})
            archive = out / 'c02-r01-G-1' / 'assessment.stop-1'  # a failed attempt that regrade archived
            (archive / 'claude').mkdir(parents=True)
            (archive / 'claude/result.json').write_text(json.dumps(dict(seconds=45, usage=model_usage(1, 1, 1, 1))))
            (out / 'c03-r03-G-1/assessment.stop-1/codex').mkdir(parents=True)  # archived without its record
            rows = decide.load(out, decisions)
            self.assertEqual(rows['c02-r01-G-1']['operational'][0], 200 + 90 + 100 + 45 + 90)
            self.assertEqual(rows['c03-r03-G-1']['operational'], (None, None, None))
            self.assertEqual([n for n, c in rows.items() if not c['repair']], ['c02-r01-G-1', 'c09-r01-G-2'])
            self.assertEqual([n for n, c in rows.items() if c['preservation']], ['c09-r01-G-2'])
            self.assertEqual(rows['c01-r01-F-1']['continuation'], (5400, 50, 5))
            self.assertEqual(rows['c01-r01-F-1']['operational'], (200 + 90 + 5400 + 90, None, None))
            decisions['audited'] = names[1:]
            del decisions['witnesses']['d4-writer-strict']['c16-r08-G-2']
            with self.assertRaisesRegex(ValueError, 'c01-r01-F-1: final report not audited; c16-r08-G-2: witness'):
                decide.load(out, decisions)
            decisions['audited'] = names
            for unresolved in ('STOP', 2, 0):  # a witness error or a non-boolean result never counts as a non-repair
                decisions['witnesses']['d4-writer-strict']['c16-r08-G-2'] = unresolved
                with self.assertRaisesRegex(ValueError, f'c16-r08-G-2: witness d4-writer-strict result {unresolved!r} is not'):
                    decide.load(out, decisions)
            decisions['witnesses']['d4-writer-strict']['c16-r08-G-2'] = True
            decide.load(out, decisions)
            (out / 'verdict-c05-r04-F-1.json').write_text(json.dumps(dict(status='STOP')))
            with self.assertRaisesRegex(ValueError, 'STOP row'):
                decide.load(out, decisions)


if __name__ == '__main__':
    unittest.main()
