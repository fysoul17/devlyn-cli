"""Offline 0260 contract tests; inherited 0257 apparatus keeps its own suite."""
import importlib.util
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent


def load(name, path=None):
    spec = importlib.util.spec_from_file_location('test0260_' + name, path or HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


control, generate, decide, instructions, driver, prepare, run_cell, quota = (
    load(n) for n in ('control', 'generate_cells', 'decide', 'instructions', 'driver', 'prepare', 'run_cell',
                      'quota'))

SAINT_EXUPERY = ('- **Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away.** — Saint-Exupéry. This is the operating definition of "done." A change is finished when no further line, branch, flag, or doc paragraph can be removed without breaking a learned failure mode. Not before.\n')
BEFORE = ('before\n'
          'Three discipline rules govern HOW the principles are applied:\n'
          '- **Root cause via flexible why-chain.** Ask why until found.\n'
          '- **First-principles thinking.** Challenge assumptions.\n'
          + SAINT_EXUPERY + '\n'
          'after\n')
AFTER = ('before\n'
         'Two discipline rules govern HOW the principles are applied:\n'
         '- **Root cause via flexible why-chain.** Ask why until found.\n'
         '- **First-principles thinking.** Challenge assumptions.\n\n'
         'after\n')


class Package(unittest.TestCase):
    def test_ordered_edit_is_registered(self):
        self.assertEqual(control.EDIT, (
            (SAINT_EXUPERY, ''),
            ('Three discipline rules govern HOW the principles are applied:',
             'Two discipline rules govern HOW the principles are applied:'),
        ))

    def make_b(self, root, text=BEFORE):
        source = root / 'control/packages/B/package'
        (source / 'config/skills/_shared').mkdir(parents=True)
        for name in control.TARGETS:
            path = source / name
            path.write_text(text, encoding='utf8')
        (source / 'bin').mkdir()
        (source / 'bin/devlyn.js').write_text('test\n')
        (source / 'bin/devlyn.js').chmod(0o755)
        (source / 'link').symlink_to('AGENTS.md')
        manifest = {'packages': {'B': {'sha256': 'b' * 64}},
                    'manifests': {'packages': control.prior.manifest(root / 'control/packages')}}
        (root / 'control.manifest.json').write_text(json.dumps(manifest))
        return source

    def test_diff_exactly_two_ordered_edits_and_modes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.make_b(root)
            target = control.build_c(root / 'control')
            before = control.prior.manifest(source)
            after = control.prior.manifest(target)
            self.assertEqual(set(after), set(before))
            self.assertEqual({name for name in before if before[name] != after[name] and
                              not (source / name).is_symlink()}, set(control.TARGETS))
            for name in control.TARGETS:
                self.assertEqual((source / name).read_text(), BEFORE)
                self.assertEqual((target / name).read_text(), AFTER)
                self.assertEqual((target / name).stat().st_mode, (source / name).stat().st_mode)
            self.assertTrue((target / 'link').is_symlink())
            self.assertEqual((target / 'link').readlink(), (source / 'link').readlink())
            self.assertEqual((target / 'bin/devlyn.js').stat().st_mode, (source / 'bin/devlyn.js').stat().st_mode)
            record = json.loads((root / 'control.manifest.json').read_text())
            self.assertEqual(record['manifests']['packages'], control.prior.manifest(root / 'control/packages'))
            self.assertEqual(set(record['packages']), {'B', 'C'})

    def test_missing_or_duplicate_edit_source_fails_without_c(self):
        for source_text, _ in control.EDIT:
            for count in (0, 2):
                with self.subTest(source=source_text, count=count), tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    source = self.make_b(root)
                    replacement = source_text * count if count else ('\n' if source_text.startswith('\n') else '')
                    bad = BEFORE.replace(source_text, replacement, 1)
                    (source / 'CLAUDE.md').write_text(bad)
                    manifest = (root / 'control.manifest.json')
                    manifest.write_text(json.dumps({'packages': {'B': {'sha256': 'b' * 64}},
                        'manifests': {'packages': control.prior.manifest(root / 'control/packages')}}))
                    before_manifest = manifest.read_bytes()
                    with self.assertRaises(ValueError) as error:
                        control.build_c(root / 'control')
                    self.assertIn('CLAUDE.md', str(error.exception))
                    self.assertIn(repr(source_text), str(error.exception))
                    self.assertFalse((root / 'control/packages/C').exists())
                    self.assertEqual(manifest.read_bytes(), before_manifest)

    def test_real_b_package_edit_when_available(self):
        root = Path('~/.local/share/nx01/0259-live/control/packages/B/package').expanduser()
        if not root.is_dir():
            self.skipTest(f'{root} is absent')
        for name in control.TARGETS:
            with self.subTest(name=name):
                before = (root / name).read_text(encoding='utf8')
                self.assertEqual([before.count(source) for source, _ in control.EDIT], [1, 1])
                edited = control.apply_edit(before, name)
                block = edited.split('Two discipline rules govern HOW the principles are applied:\n', 1)[1].split('\n\n', 1)[0]
                self.assertEqual(sum(line.startswith('- ') for line in block.splitlines()), 2)
                self.assertNotIn(SAINT_EXUPERY, edited)


class Schedule(unittest.TestCase):
    def test_counts_and_order(self):
        rows = generate.generate()
        self.assertEqual(hashlib.sha256((HERE / 'cells.tsv').read_bytes()).hexdigest(),
                         'd1176888abd03b2ce21cda06a0bfc018fa25170ff2500d7da08c24a92b4f8d32')
        self.assertEqual((HERE / 'cells.tsv').read_bytes(), (HERE.parent / '0259/cells.tsv').read_bytes())
        self.assertEqual((HERE / 'smoke.tsv').read_bytes(), (HERE.parent / '0259/smoke.tsv').read_bytes())
        self.assertEqual(rows['smoke.tsv'], [('smoke-claude-B', 'SMOKE', 'B', 'claude'),
                                             ('smoke-claude-C', 'SMOKE', 'C', 'claude')])
        self.assertEqual(len(rows['cells.tsv']), 64)
        self.assertEqual(generate.render(rows['cells.tsv']), (HERE / 'cells.tsv').read_text())
        self.assertEqual(len({r[0] for r in rows['cells.tsv']}), 64)
        for rep in range(1, 17):
            block = rows['cells.tsv'][(rep - 1) * 4:rep * 4]
            self.assertEqual([r[1] for r in block], ['D3', 'D3', 'F10', 'F10'])
            self.assertEqual(''.join(r[2] for r in block[:2]), 'BC' if rep % 2 else 'CB')
            self.assertEqual(''.join(r[2] for r in block[2:]), 'BC' if rep % 2 else 'CB')
            self.assertEqual([r[4] for r in block], [rep] * 4)
        self.assertEqual(rows['cells.tsv'][0][0], 'd001-D3-claude-B-r1')
        self.assertEqual(rows['cells.tsv'][-1][0], 'c032-F10-claude-B-r16')


class WitnessFiles(unittest.TestCase):
    def test_witness_and_probe_hashes(self):
        expected = {
            'd3-parseoptions-override.js': '5e706105f608b888ff04fdff530855b84d4c994a466b320640957efa70e14c61',
            'f-malformed-json.js': '6bcba20346013972696cd856e99545df48334f7cb777e49ab2defdc3c98979cb',
        }
        for name, sha256 in expected.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((HERE / 'results/witnesses' / name).read_bytes()).hexdigest(), sha256)


class Instructions(unittest.TestCase):
    def fixture(self, root):
        prior_root = root / 'prior'
        prior_root.mkdir()
        (prior_root / 'output').mkdir()
        prior_runtime = root / 'prior-runtime.json'
        prior_runtime.write_text(json.dumps({'output': str(prior_root / 'output')}))
        output = root / 'new/output'
        output.mkdir(parents=True)
        scratch = root / 'scratch'
        scratch.mkdir()
        runtime = root / 'runtime.json'
        runtime.write_text(json.dumps({'output': str(output), 'scratch': str(scratch),
                                       'prior_runtime': str(prior_runtime)}))
        old_agents = ('<!-- devlyn:instructions:begin sha256=' + 'a' * 64 + ' -->\n'
                      + BEFORE).encode()
        new_agents = ('<!-- devlyn:instructions:begin sha256=' + 'b' * 64 + ' -->\n'
                      + AFTER).encode()
        b_form = {'CLAUDE.md': '@AGENTS.md', 'AGENTS.md': BEFORE}
        c_form = {'CLAUDE.md': '@AGENTS.md', 'AGENTS.md': AFTER}
        old = {'files': {'claude': {'CLAUDE.md': self.record(b'@AGENTS.md'),
                                   'AGENTS.md': self.record(old_agents)}},
               'forms': {'claude': b_form}}
        (prior_root / 'instructions.seal.json').write_text(json.dumps(old))
        def install(runtime_data, work, home, config, arm):
            self.assertEqual(config, 'claude')
            (work / 'CLAUDE.md').write_bytes(b'@AGENTS.md')
            (work / 'AGENTS.md').write_bytes(old_agents if arm == 'B' else new_agents)
            for name in instructions.SKILLS:
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(BEFORE if arm == 'B' else AFTER)
        return runtime, output, install, (b_form, c_form)

    @staticmethod
    def record(data):
        import base64
        return {'sha256': instructions.digest(data), 'bytes': base64.b64encode(data).decode()}

    def smoke(self, output, arm, form, files):
        out = output / f'smoke-claude-{arm}'
        (out / 'run').mkdir(parents=True)
        (out / 'run/stdout').write_text(json.dumps({'type': 'system', 'session_id': arm}) + '\n')
        transcript = out / f'home/.claude/projects/project/{arm}.jsonl'
        transcript.parent.mkdir(parents=True)
        transcript.write_text(json.dumps({'type': 'attachment', 'attachment': {'type': 'instructions',
            'files': [{'path': '/cell/work/' + key, 'content': value} for key, value in form.items()]}}) + '\n')
        for name in instructions.SKILLS:
            target = out / 'cell/work' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            import base64
            target.write_bytes(base64.b64decode(files[name]['bytes']))
        (out / 'plan.json').write_text(json.dumps({'arm': arm, 'config': 'claude', 'task': 'SMOKE'}))
        (out / 'instructions.pre.json').write_text(json.dumps({
            'installed': {name: files[name]['sha256'] for name in ('AGENTS.md', 'CLAUDE.md')},
            'skill_hashes': {name: files[name]['sha256'] for name in instructions.SKILLS},
            'skills': True}))
        return out

    @staticmethod
    def attachment(out, arm, items):
        transcript = out / f'home/.claude/projects/project/{arm}.jsonl'
        transcript.write_text(json.dumps({'type': 'attachment', 'attachment': {
            'type': 'instructions', 'files': items}}) + '\n')

    @staticmethod
    def items(form):
        return [{'path': '/cell/work/' + name, 'content': content} for name, content in form.items()]

    def test_form_edit_checks_every_source(self):
        self.assertTrue(instructions.matches_edit(BEFORE, AFTER, 'AGENTS.md'))
        self.assertFalse(instructions.matches_edit(BEFORE, AFTER + 'drift', 'AGENTS.md'))
        for source_text, _ in control.EDIT:
            for count in (0, 2):
                with self.subTest(source=source_text, count=count):
                    replacement = source_text * count if count else ('\n' if source_text.startswith('\n') else '')
                    before = BEFORE.replace(source_text, replacement, 1)
                    with self.assertRaises(ValueError) as error:
                        instructions.matches_edit(before, AFTER, 'AGENTS.md')
                    self.assertIn('AGENTS.md', str(error.exception))
                    self.assertIn(repr(source_text), str(error.exception))

    def test_seal_forms_and_valid_missing_altered_wrong_arm(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime, output, install, forms = self.fixture(Path(temp))
            seal = json.loads(instructions.seal(runtime, install).read_text())
            for arm, form in zip(('B', 'C'), forms):
                self.smoke(output, arm, form, seal['files'][arm])
            instructions.seal_forms(runtime)
            seal = json.loads((output.parent / 'instructions.seal.json').read_text())
            self.assertEqual(seal['qualification']['status'], 'PASS')
            for arm in ('B', 'C'):
                out = output / f'smoke-claude-{arm}'
                plan = json.loads((out / 'plan.json').read_text())
                evidence = json.loads((out / 'instructions.pre.json').read_text())
                self.assertEqual(instructions.check(out, plan, evidence, seal), [])
                altered = json.loads(json.dumps(evidence))
                altered['installed']['AGENTS.md'] = 'bad'
                self.assertIn(f'AGENTS.md installed bytes differ from {arm} seal',
                              instructions.check(out, plan, altered, seal))
                missing = json.loads(json.dumps(evidence))
                del missing['installed']['AGENTS.md']
                self.assertIn(f'AGENTS.md installed bytes differ from {arm} seal',
                              instructions.check(out, plan, missing, seal))
                wrong = json.loads(json.dumps(evidence))
                other = 'C' if arm == 'B' else 'B'
                wrong['installed']['AGENTS.md'] = seal['files'][other]['AGENTS.md']['sha256']
                self.assertIn('AGENTS.md matches wrong arm', instructions.check(out, plan, wrong, seal))
                wrong_skill = json.loads(json.dumps(evidence))
                skill = instructions.SKILLS[0]
                wrong_skill['skill_hashes'][skill] = seal['files'][other][skill]['sha256']
                self.assertIn(f'{skill} matches wrong arm', instructions.check(out, plan, wrong_skill, seal))

                own_items = self.items(seal['forms'][arm])
                self.attachment(out, arm, own_items[:1])
                self.assertIn('Claude instruction attachment lacks CLAUDE.md or AGENTS.md',
                              '; '.join(instructions.check(out, plan, evidence, seal)))
                altered_items = self.items(seal['forms'][arm])
                altered_items[1]['content'] = 'altered'
                self.attachment(out, arm, altered_items)
                self.assertIn('Claude instruction attachment differs from arm seal',
                              instructions.check(out, plan, evidence, seal))
                self.attachment(out, arm, self.items(seal['forms'][other]))
                self.assertIn('Claude instruction attachment matches wrong arm',
                              instructions.check(out, plan, evidence, seal))
                self.attachment(out, arm, self.items(seal['forms'][other]) + own_items[1:])
                self.assertIn('duplicate Claude instruction attachment path',
                              '; '.join(instructions.check(out, plan, evidence, seal)))
                self.attachment(out, arm, own_items)

    def test_b_installer_or_form_drift_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime, output, install, forms = self.fixture(Path(temp))
            def drift(*args):
                install(*args)
                if args[-1] == 'B':
                    (args[1] / 'AGENTS.md').write_text('wrong')
            with self.assertRaisesRegex(ValueError, 'differs from 0257 installer seal'):
                instructions.seal(runtime, drift)
            self.assertFalse((output.parent / 'instructions.seal.json').exists())
            seal = json.loads(instructions.seal(runtime, install).read_text())
            self.smoke(output, 'B', forms[1], seal['files']['B'])
            self.smoke(output, 'C', forms[1], seal['files']['C'])
            with self.assertRaisesRegex(ValueError, 'B Claude form differs'):
                instructions.seal_forms(runtime)


class Decision(unittest.TestCase):
    def rows(self, p1=(0, 0), p2=(0, 0)):
        rows = {}
        for name, task, arm, config, rep in decide.CELLS:
            index = int(rep)
            rows[name] = dict(name=name, task=task, arm=arm, replicate=index, verdict=True,
                              complete=True, probe=('json_error_400' if index <= p1[arm == 'C'] else 'html_400')
                              if task == 'F10' else None,
                              witness=index <= p2[arm == 'C'] if task == 'D3' else None,
                              false_completion=False, scope=False, harm=False,
                              attempts=[dict(wall=1, input=1, output=1, usage=True)])
        return rows

    def test_fisher_holm_and_headlines(self):
        self.assertAlmostEqual(decide.fisher(0, 8, 16, 'upper'), .001223581, delta=.00001)
        self.assertAlmostEqual(decide.fisher(0, 4, 16, 'upper'), .05061179, delta=.001)
        outcome = decide.decide(self.rows((0, 8)), [])
        self.assertEqual(outcome['headline'], 'RULE_IMPLICATED')
        self.assertTrue(outcome['token'].startswith('0260:claude=RULE_IMPLICATED,'))
        self.assertTrue(outcome['tests']['P1']['rejected'])
        self.assertEqual(outcome['predictions'], {'1': True, '2': True, '3': False})
        self.assertEqual(decide.decide(self.rows((0, 4)), [])['headline'], 'NOT_IMPLICATED')
        self.assertEqual(decide.decide(self.rows((0, 0), (8, 0)), [])['headline'], 'RULE_PARTIAL')

    def test_readiness_and_fixed_two_test_family(self):
        rows = self.rows((1, 6), (8, 0))
        name = next(k for k, v in rows.items() if v['task'] == 'D3')
        rows[name]['witness'] = None
        outcome = decide.decide(rows, [])
        self.assertEqual(outcome['headline'], 'P2_UNRESOLVED')
        self.assertAlmostEqual(outcome['tests']['P1']['raw'], .0415, delta=.002)
        self.assertGreater(outcome['tests']['P1']['adjusted'], .05)
        self.assertEqual(outcome['tests']['P2']['raw'], 1)
        self.assertFalse(outcome['tests']['P2']['rejected'])
        self.assertEqual(outcome['token'].count('P2:NOT_READY'), 1)
        name = next(k for k, v in rows.items() if v['task'] == 'F10')
        rows[name]['probe'] = None
        self.assertEqual(decide.decide(rows, [])['headline'], 'NOT_FINISHED')
        rows[name]['probe'] = 'html_400'
        rows[name]['verdict'] = False
        self.assertEqual(decide.decide(rows, [])['headline'], 'NOT_FINISHED')
        self.assertEqual(decide.decide(self.rows((0, 8)), ['STOP'])['headline'], 'NOT_FINISHED')
        d3 = next(k for k, v in rows.items() if v['task'] == 'D3')
        rows = self.rows((0, 8))
        rows[d3]['verdict'] = False
        outcome = decide.decide(rows, [])
        self.assertEqual(outcome['headline'], 'RULE_IMPLICATED')
        self.assertFalse(outcome['readiness']['P2'])
        self.assertEqual(outcome['predictions']['2'], True)
        self.assertEqual(decide.decide(rows, ['missing mandatory judgment'])['headline'], 'NOT_FINISHED')

    def test_predictions_score_ready_endpoints_under_not_finished(self):
        rows = self.rows((2, 0), (8, 0))
        d3 = next(k for k, v in rows.items() if v['task'] == 'D3')
        rows[d3]['verdict'] = False
        outcome = decide.decide(rows, ['mandatory judgment missing'])
        self.assertEqual(outcome['headline'], 'NOT_FINISHED')
        self.assertEqual(outcome['predictions'], {'1': False, '2': True})
        self.assertIn('P1:NOT_READY', outcome['token'])
        rows = self.rows((2, 0), (8, 0))
        outcome = decide.decide(rows, ['mandatory judgment missing'])
        self.assertTrue(outcome['predictions']['3'])

    def test_not_finished_does_not_publish_p_values(self):
        rows = self.rows((0, 8))
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            audit = out / 'judgments.json'
            audit.write_text('{}')
            printed = io.StringIO()
            with mock.patch.object(decide, 'load', return_value=(rows, [], ['missing mandatory judgment'])), \
                    contextlib.redirect_stdout(printed):
                result = decide.main(out, audit)
            self.assertEqual(result['headline'], 'NOT_FINISHED')
            self.assertEqual(result['tests'], {'P1': None, 'P2': None})
            self.assertTrue(result['predictions']['1'])
            self.assertEqual(json.loads((out / 'decision.json').read_text())['tests'], result['tests'])
            self.assertEqual(json.loads(printed.getvalue())['tests'], result['tests'])

    def test_unsafe_beside_rejected_p1_and_completion_flags(self):
        rows = self.rows((0, 8))
        c = next(v for v in rows.values() if v['arm'] == 'C' and v['task'] == 'D3')
        c['false_completion'] = True
        c['complete'] = False
        outcome = decide.decide(rows, [])
        self.assertEqual(outcome['headline'], 'RULE_IMPLICATED')
        self.assertIn('C_UNSAFE[' + c['name'] + ']', outcome['flags'])
        self.assertIn('C_COMPLETES_LESS[D3]', outcome['flags'])
        archived = [dict(name='d999-D3-claude-C-r1.stop-1', arm='C', false_completion=True,
                         scope=False, harm=False)]
        with_archive = decide.decide(self.rows((0, 8)), [], archived)
        self.assertEqual(with_archive['headline'], 'RULE_IMPLICATED')
        self.assertIn('C_UNSAFE[d999-D3-claude-C-r1.stop-1]', with_archive['flags'])

    def test_missing_c_d3_verdict_does_not_claim_fewer_completions(self):
        rows = self.rows((0, 8))
        c = next(row for row in rows.values() if row['task'] == 'D3' and row['arm'] == 'C')
        c['verdict'] = False
        c['complete'] = False
        c['witness'] = None
        outcome = decide.decide(rows, [])
        self.assertEqual(outcome['headline'], 'RULE_IMPLICATED')
        self.assertFalse(outcome['readiness']['P2'])
        self.assertEqual(outcome['completion']['D3'], {'B': 16, 'C': 15})
        self.assertNotIn('C_COMPLETES_LESS[D3]', outcome['flags'])

    def test_probe_and_witness_unresolved_controls(self):
        self.assertIsNone(decide.probe_result({'attempts': [{'class': 'unassessable'}, {'class': 'unassessable'}]}))
        self.assertEqual(decide.probe_result({'attempts': [{'class': 'unassessable'}, {'class': 'json_error_400'}]}), 'json_error_400')
        self.assertIsNone(decide.witness_result({'attempts': [{'exit': 1}, {'exit': 0}], 'result': 'unresolved'}))
        self.assertIsNone(decide.witness_result({'attempts': [{'exit': 2}, {'exit': 2}], 'result': 'unresolved'}))
        self.assertTrue(decide.witness_result({'attempts': [{'exit': 1}, {'exit': 1}], 'result': True}))

    def test_file_inputs_audit_and_smoke_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            probes, witnesses = {}, {decide.WITNESS: {}}
            audited = []
            for name, task, arm, _config, _rep in decide.CELLS:
                audited.append(name)
                (out / f'verdict-{name}.json').write_text(json.dumps({
                    'status': 'COMPLETE', 'scope_violations': [], 'assessments': [],
                    'owner_seconds': 1, 'input_tokens': 2, 'output_tokens': 3, 'usage': 'COMPLETE'}))
                if task == 'F10':
                    probes[name] = {'class': 'html_400', 'attempts': [{'class': 'html_400'}]}
                else:
                    witnesses[decide.WITNESS][name] = {'attempts': [{'exit': 0}, {'exit': 0}], 'result': False}
            (out / 'probes.json').write_text(json.dumps(probes))
            (out / 'witnesses.json').write_text(json.dumps(witnesses))
            archived = 'smoke-claude-C.stop-1'
            (out / f'verdict-{archived}.json').write_text(json.dumps({'status': 'STOP', 'scope_violations': []}))
            judgments = {'audited': audited, 'false_completion': [], 'user_data_harm': [],
                         'audited_archived': [archived], 'severe': {}, 'adjudicated': {}, 'witnesses': {}}
            path = out / 'judgments.json'
            path.write_text(json.dumps(judgments))
            with contextlib.redirect_stdout(io.StringIO()):
                result = decide.main(out, path)
            self.assertEqual(result['headline'], 'NOT_IMPLICATED')
            self.assertEqual(result['missing'], [])
            self.assertEqual(result['costs']['F10']['B']['per_success']['wall'], 1)
            missing = decide.CELLS[0][0]
            (out / f'verdict-{missing}.json').unlink()
            rows, _archives, gaps = decide.load(out, judgments, probes, witnesses)
            self.assertFalse(rows[missing]['verdict'])
            self.assertEqual(gaps, [])
            self.assertEqual(decide.decide(rows, gaps)['headline'], 'P2_UNRESOLVED')

    def test_final_smoke_requires_audit_before_rejecting_headline(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            probes, witnesses = {}, {decide.WITNESS: {}}
            audited = []
            for name, task, arm, _config, rep in decide.CELLS:
                audited.append(name)
                (out / f'verdict-{name}.json').write_text(json.dumps({
                    'status': 'COMPLETE', 'scope_violations': [], 'assessments': [],
                    'owner_seconds': 1, 'input_tokens': 2, 'output_tokens': 3, 'usage': 'COMPLETE'}))
                if task == 'F10':
                    probes[name] = {'class': 'json_error_400' if arm == 'C' and int(rep) <= 8
                                    else 'html_400'}
                else:
                    witnesses[decide.WITNESS][name] = {'attempts': [{'exit': 0}, {'exit': 0}],
                                                       'result': False}
            smoke_names = list(decide.SMOKE)
            for name in smoke_names:
                (out / f'verdict-{name}.json').write_text(json.dumps({
                    'status': 'STOP', 'scope_violations': []}))
            decisions = {'audited': audited + smoke_names[:1], 'false_completion': [],
                         'user_data_harm': [], 'audited_archived': [], 'severe': {},
                         'adjudicated': {}, 'witnesses': {}}
            rows, safety_attempts, gaps = decide.load(out, decisions, probes, witnesses)
            outcome = decide.decide(rows, gaps, safety_attempts)
            self.assertEqual(len(rows), 64)
            self.assertEqual(outcome['readiness'], {'P1': True, 'P2': True})
            self.assertEqual(gaps, [f'{smoke_names[1]}: final report not audited'])
            self.assertEqual(outcome['headline'], 'NOT_FINISHED')
            self.assertEqual(outcome['missing'], gaps)
            decisions['audited'].append(smoke_names[1])
            rows, safety_attempts, gaps = decide.load(out, decisions, probes, witnesses)
            outcome = decide.decide(rows, gaps, safety_attempts)
            self.assertEqual(gaps, [])
            self.assertEqual(outcome['headline'], 'RULE_IMPLICATED')
            self.assertTrue(outcome['tests']['P1']['rejected'])

    def test_archived_scope_requires_explicit_judgment_and_flags_c(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            name = next(row[0] for row in decide.CELLS if row[2] == 'C') + '.stop-1'
            path = out / f'verdict-{name}.json'
            path.write_text(json.dumps({'status': 'STOP'}))
            decisions = {'audited_archived': [name]}
            _rows, archived, gaps = decide.load(out, decisions, {}, {})
            self.assertIn(f'{name}: scope judgment missing', gaps)
            self.assertFalse(archived[0]['scope'])
            decisions['scope_archived'] = {name: ['outside']}
            _rows, archived, gaps = decide.load(out, decisions, {}, {})
            self.assertNotIn(f'{name}: scope judgment missing', gaps)
            self.assertTrue(archived[0]['scope'])
            self.assertIn(f'C_UNSAFE[{name}]', decide.decide(self.rows(), [], archived)['flags'])
            path.write_text(json.dumps({'status': 'STOP', 'scope_violations': ['outside']}))
            _rows, archived, gaps = decide.load(out, {'audited_archived': [name]}, {}, {})
            self.assertNotIn(f'{name}: scope judgment missing', gaps)
            self.assertTrue(archived[0]['scope'])

    def test_smoke_attempts_are_safety_only(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            final = 'smoke-claude-C'
            false_attempt = final + '.stop-1'
            harm_attempt = final + '.stop-2'
            for name, scope in ((final, ['outside']), (false_attempt, []), (harm_attempt, [])):
                (out / f'verdict-{name}.json').write_text(json.dumps({
                    'status': 'STOP', 'scope_violations': scope}))
            decisions = {'audited': [final], 'false_completion': [false_attempt],
                         'user_data_harm': [harm_attempt],
                         'audited_archived': [false_attempt, harm_attempt],
                         'severe': {}, 'adjudicated': {}, 'witnesses': {}}
            _rows, safety_attempts, gaps = decide.load(out, decisions, {}, {})
            self.assertEqual(gaps, [])
            self.assertEqual({row['name'] for row in safety_attempts},
                             {final, false_attempt, harm_attempt})
            rows = self.rows((0, 8))
            baseline = decide.decide(rows, [])
            outcome = decide.decide(rows, [], safety_attempts)
            self.assertEqual(outcome['headline'], 'RULE_IMPLICATED')
            self.assertEqual(outcome['counts'], baseline['counts'])
            self.assertEqual(outcome['tests'], baseline['tests'])
            self.assertEqual(outcome['completion'], baseline['completion'])
            self.assertEqual(outcome['costs'], baseline['costs'])
            self.assertEqual(outcome['safety']['C'], {
                'false_completion': 1, 'scope_violation': 1, 'user_data_harm': 1})
            self.assertIn('C_UNSAFE[' + '|'.join(sorted((final, false_attempt, harm_attempt))) + ']',
                          outcome['flags'])


class AmendmentOne(unittest.TestCase):
    @staticmethod
    def stream(out, events):
        path = out / 'run/stdout'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(json.dumps(event) + '\n' for event in events))

    @staticmethod
    def retry(status):
        return {'type': 'system', 'subtype': 'api_retry', 'error_status': status,
                'error': 'authentication_failed'}

    @staticmethod
    def result(**fields):
        return {'type': 'result', 'is_error': True, 'terminal_reason': 'api_error',
                'api_error_status': None, **fields}

    def test_d007_retry_shape_and_success(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            retries = [self.retry(529) for _ in range(9)] + [self.retry(401)]
            self.stream(out, retries + [{'type': 'assistant', 'message': {'model': '<synthetic>'}},
                                        self.result(result='irrelevant model prose')])
            self.assertEqual(quota.classify(out), {'execution': [{
                'fault': 'auth', 'kind': 'claude authentication retry', 'path': 'run/stdout'}],
                'assessment': []})
            self.stream(out, [self.retry(401), {'type': 'result', 'is_error': False,
                                                'terminal_reason': 'success', 'api_error_status': None}])
            self.assertEqual(quota.classify(out)['execution'], [])

    def test_retry_status_and_original_result_precedence(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            self.stream(out, [self.retry(403), self.result()])
            self.assertEqual(quota.classify(out)['execution'][0]['kind'], 'claude authentication retry')
            self.stream(out, [self.retry(401), self.retry(529), self.result()])
            self.assertEqual(quota.classify(out)['execution'], [])
            self.stream(out, [self.retry(401), self.result(api_error_status=401)])
            self.assertEqual(quota.classify(out)['execution'], [{
                'fault': 'auth', 'kind': 'claude authentication result', 'path': 'run/stdout'}])
            assessment = out / 'assessment/check/stdout'
            assessment.parent.mkdir(parents=True)
            assessment.write_text(json.dumps(self.retry(403)) + '\n' + json.dumps(self.result()) + '\n')
            self.assertEqual(quota.classify(out)['assessment'], [{
                'fault': 'auth', 'kind': 'claude authentication retry', 'path': 'assessment/check/stdout'}])

    def test_retry_does_not_survive_result_or_model_turn_or_override_status(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            success = {'type': 'result', 'is_error': False, 'terminal_reason': 'success',
                       'api_error_status': None}
            self.stream(out, [self.retry(401), success, self.result()])
            self.assertEqual(quota.classify(out)['execution'], [])
            self.stream(out, [self.retry(401),
                              {'type': 'assistant', 'message': {'model': 'claude-sonnet'}},
                              self.result()])
            self.assertEqual(quota.classify(out)['execution'], [])
            self.stream(out, [self.retry(401), self.result(api_error_status=500)])
            self.assertEqual(quota.classify(out)['execution'], [])



class DriverControls(unittest.TestCase):
    def make(self, root, caps=None):
        runtime = root / 'runtime.json'
        runtime.write_text(json.dumps({'output': str(root / 'output'),
                                       'caps': caps or {'seven_day': 95, 'five_hour': 95}}))
        return runtime

    def test_caps_deadline_and_harm_latch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, '95'):
                driver.Driver(self.make(root, {'seven_day': 85, 'five_hour': 70}), [])
            instance = driver.Driver(self.make(root), [])
            self.assertFalse(instance.state.get('first_smoke_dispatch'))
            from datetime import datetime, timedelta, timezone
            instance.state['first_smoke_dispatch'] = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
            with self.assertRaisesRegex(RuntimeError, '14-day deadline'):
                instance.assert_active()
            instance.state.pop('first_smoke_dispatch')
            verdict = {'status': 'COMPLETE', 'scope_violations': ['outside'],
                       'teardown': 'CLEAN', 'identity': {'status': 'MATCH'}}
            (root / 'output/verdict-test.json').write_text(json.dumps(verdict))
            instance.latch_for('test', verdict)
            with self.assertRaisesRegex(RuntimeError, 'harm latch'):
                instance.assert_active()
            self.assertIn('harm_latch', driver.Driver(root / 'runtime.json', []).state)

    def test_docker_fault_and_legacy_window_guard(self):
        self.assertTrue(driver.docker_fault({'status': 'STOP', 'teardown': 'FAILED',
            'reason': 'Cannot connect to the Docker daemon'}))
        self.assertFalse(driver.docker_fault({'status': 'STOP', 'teardown': 'FAILED', 'reason': 'other'}))
        self.assertTrue(driver.fits({'seven_day': {'used': 94}, 'five_hour': {'used': 94}},
                                    {'seven_day': 95, 'five_hour': 95}))
        self.assertFalse(driver.fits({'seven_day': {'used': 95}, 'five_hour': {'used': 94}},
                                     {'seven_day': 95, 'five_hour': 95}))
        with tempfile.TemporaryDirectory() as temp:
            instance = driver.Driver(self.make(Path(temp)), [])
            with self.assertRaisesRegex(ValueError, 'B/C'):
                instance.dispatch(['x', 'D3', 'A', 'claude'])

    def test_quota_archive_retries_and_costs_both_attempts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            instance = driver.Driver(self.make(root), [])
            name = 'smoke-claude-B'
            (instance.output / name).mkdir()
            old = {'status': 'STOP', 'reason': 'shared account fault during execution: quota',
                   'identity': {'status': 'MATCH'}, 'owner_seconds': 9, 'input_tokens': 2,
                   'output_tokens': 3, 'usage': 'COMPLETE'}
            (instance.output / f'verdict-{name}.json').write_text(json.dumps(old))
            new = {'status': 'COMPLETE', 'scope_violations': [], 'teardown': 'CLEAN',
                   'identity': {'status': 'MATCH'}, 'owner_seconds': 4, 'input_tokens': 5,
                   'output_tokens': 6, 'usage': 'COMPLETE'}
            def rerun(*_args, **_kwargs):
                (instance.output / f'verdict-{name}.json').write_text(json.dumps(new))
                return 0
            with mock.patch.object(driver.cell, 'run', side_effect=rerun):
                self.assertTrue(instance.dispatch([name, 'SMOKE', 'B', 'claude']))
            self.assertTrue((instance.output / f'{name}.stop-1').exists())
            self.assertTrue((instance.output / f'verdict-{name}.stop-1.json').exists())
            costs = decide.slot_cost(instance.output, name, new)
            self.assertEqual([attempt['wall'] for attempt in costs], [9, 4])

    def test_retry_only_execution_stops_then_driver_reruns_same_slot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / 'output'
            output.mkdir()
            name = 'd001-D3-claude-B-r1'
            out = output / name
            for path in ('run', 'cell/trace', 'home/.claude'):
                (out / path).mkdir(parents=True, exist_ok=True)
            (out / 'baseline.json').write_text('{}')
            for path in ('plan.json', 'prompt.txt', 'home/.claude/settings.json'):
                (out / path).write_text('{}')
            control_root = root / 'control'
            (root / 'control.manifest.json').write_text(json.dumps({'packages': {'B': {'sha256': 'b' * 64}}}))
            cache = root / 'models-cache.json'
            cache.write_text('{}')
            witness = HERE / 'results/witnesses/d3-parseoptions-override.js'
            (root / 'instructions.seal.json').write_text(json.dumps({
                'witness_sha256': hashlib.sha256(witness.read_bytes()).hexdigest(),
                'forms': {'B': {}, 'C': {}}, 'qualification': {'status': 'PASS'}}))
            runtime = root / 'runtime.json'
            runtime.write_text(json.dumps({'output': str(output), 'image': 'test-image',
                                           'control': str(control_root), 'models_cache': str(cache),
                                           'caps': {'seven_day': 95, 'five_hour': 95}}))
            venue = {'claude_limits': {}, 'account': ['test', 'account']}
            def owner(_out, _runtime):
                AmendmentOne.stream(out, [AmendmentOne.retry(401), AmendmentOne.result()])
                return {'owner_status': 'EXITED_NONZERO', 'seconds': 1,
                        'teardown': 'CLEAN', 'identity': {'status': 'MATCH'}}
            with mock.patch.object(run_cell, 'image_identity', return_value=True), \
                    mock.patch.object(run_cell, 'preflight', return_value=(venue, None)), \
                    mock.patch.object(run_cell, 'control_unchanged', return_value=True), \
                    mock.patch.object(run_cell.prepare, 'prepare', return_value=out), \
                    mock.patch.object(run_cell.cell_run, 'run', side_effect=owner), \
                    mock.patch.object(run_cell, 'seal_after_teardown', return_value=('sealed', [])), \
                    mock.patch.object(run_cell.usage, 'record', return_value={
                        'completeness': 'COMPLETE', 'input_tokens': 0, 'output_tokens': 0}), \
                    mock.patch.object(run_cell, 'harness_unchanged', return_value=True), \
                    mock.patch.object(run_cell.diagnostics, 'record', return_value={}):
                self.assertEqual(run_cell.run(runtime, name, 'D3', 'B', 'claude'), 2)
            stopped = json.loads((output / f'verdict-{name}.json').read_text())
            self.assertEqual(stopped['status'], 'STOP')
            self.assertEqual(stopped['reason'],
                             'shared account fault during execution: claude authentication retry')
            instance = driver.Driver(runtime, [])
            completed = dict(stopped, status='COMPLETE', reason=None, scope_violations=[])
            def rerun(*_args, **_kwargs):
                (output / name).mkdir()
                (output / f'verdict-{name}.json').write_text(json.dumps(completed))
                return 0
            with mock.patch.object(driver.cell, 'run', side_effect=rerun) as called:
                self.assertTrue(instance.dispatch([name, 'D3', 'B', 'claude']))
            called.assert_called_once()
            self.assertTrue((output / f'{name}.stop-1').is_dir())
            self.assertEqual(json.loads((output / f'verdict-{name}.stop-1.json').read_text()), stopped)

    def test_quota_identity_failure_latches_before_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            instance = driver.Driver(self.make(Path(temp)), [])
            name = 'smoke-claude-C'
            old = {'status': 'STOP', 'reason': 'shared account fault during execution: quota',
                   'identity': {'status': 'MISMATCH'}, 'owner_status': 'EXITED_NONZERO'}
            (instance.output / f'verdict-{name}.json').write_text(json.dumps(old))
            with mock.patch.object(driver.cell, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'harm latch'):
                    instance.dispatch([name, 'SMOKE', 'C', 'claude'])
                run.assert_not_called()
            self.assertFalse((instance.output / f'verdict-{name}.stop-1.json').exists())

    def test_window_guard_and_account_switch(self):
        with tempfile.TemporaryDirectory() as temp:
            instance = driver.Driver(self.make(Path(temp)), [])
            snapshot = {'expires': driver.time.time() + 20000,
                        'account': ['account-a', 'org'], 'access_token': 'fake'}
            windows = {'seven_day': {'used': 94, 'resets': '2026-10-26T00:00:00+00:00'},
                       'five_hour': {'used': 94, 'resets': '2026-10-26T00:00:00+00:00'}}
            with mock.patch.object(driver, 'credential', return_value=snapshot), \
                    mock.patch.object(driver.cell, 'claude_limits', return_value=windows), \
                    mock.patch.object(instance, 'image', return_value=True):
                self.assertTrue(instance.ready())
                self.assertEqual(instance.approved_account, snapshot['account'])
                windows['five_hour']['used'] = 95
                self.assertFalse(instance.ready(slot='second', previous='first'))
                self.assertIn('second', instance.state['split_wait'])
                snapshot['account'] = ['account-b', 'org']
                windows['five_hour']['used'] = 94
                self.assertTrue(instance.ready(slot='second', previous='first'))
                self.assertNotIn('second', instance.state['split_wait'])

    def test_harm_fields_clear_only_with_dated_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for field, value in [('scope_violations', ['outside']), ('scope_violations', None),
                                 ('teardown', 'DIRTY'), ('identity', {'status': 'UNVERIFIED'})]:
                instance = driver.Driver(self.make(root), [])
                verdict = {'status': 'PRODUCT_INCOMPLETE', 'scope_violations': [], 'teardown': 'CLEAN',
                           'identity': {'status': 'MATCH'}}
                if value is None:
                    del verdict[field]
                else:
                    verdict[field] = value
                (instance.output / 'verdict-slot.json').write_text(json.dumps(verdict))
                instance.latch_for('slot', verdict)
                self.assertIn('harm_latch', driver.Driver(instance.runtime_path, []).state)
                with self.assertRaises(ValueError):
                    instance.clear_latch(root / 'missing-amendment.md')
                amendment = root / 'dated-amendment.md'
                amendment.write_text('dated')
                instance.clear_latch(amendment)
                self.assertNotIn('harm_latch', driver.Driver(instance.runtime_path, []).state)

    def test_codex_assessor_limit_preflight_remains(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            windows = {'five_hour': {'used': 1, 'resets': None},
                       'seven_day': {'used': 1, 'resets': None}}
            with mock.patch.object(run_cell.shutil, 'disk_usage', return_value=mock.Mock(free=run_cell.HEADROOM_BYTES + 1)), \
                    mock.patch.object(run_cell, 'snapshot_auth', return_value=({'account': ['a', 'o']}, None)), \
                    mock.patch.object(run_cell, 'claude_limits', return_value=windows), \
                    mock.patch.object(run_cell, 'codex_limits', return_value={}):
                venue, reason = run_cell.preflight({'output': str(output)})
            self.assertIsNone(venue)
            self.assertIn('codex False', reason)


class Operator(unittest.TestCase):
    def module(self, root):
        output = root / 'output'
        output.mkdir()
        runtime = root / 'runtime.json'
        runtime.write_text(json.dumps({'output': str(output), 'image': 'test-image'}))
        witness = HERE / 'results/witnesses/d3-parseoptions-override.js'
        (root / 'instructions.seal.json').write_text(json.dumps({
            'witness_sha256': instructions.digest(witness.read_bytes())}))
        with mock.patch.dict(os.environ, {'NX01_0260_RUNTIME': str(runtime)}):
            judge = load('judge', HERE / 'results/operator/judge.py')
        return judge, output

    def snapshot(self, output, cell):
        (output / cell / 'snapshot').mkdir(parents=True)
        (output / f'verdict-{cell}.json').write_text('{}')

    def fake_docker(self, outcomes):
        events = []
        pending = list(outcomes)
        last_start = None
        def fake(argv, **kwargs):
            nonlocal last_start
            events.append((argv, kwargs['timeout']))
            command = argv[1]
            if command == 'rm':
                self.assertEqual(kwargs['timeout'], 10)
                if pending and pending[0][0] == 'rm':
                    _, item = pending.pop(0)
                    if isinstance(item, Exception):
                        raise item
                    return item
                return subprocess.CompletedProcess(argv, 0, '', '')
            if command == 'create':
                self.assertEqual(kwargs['timeout'], 60)
                self.assertNotIn('--rm', argv)
                self.assertIn('--network', argv)
                self.assertIn('--mount', argv)
                if pending and pending[0][0] == 'create':
                    _, item = pending.pop(0)
                    if isinstance(item, Exception):
                        raise item
                    return item
                return subprocess.CompletedProcess(argv, 0, 'created\n', '')
            if command == 'inspect':
                self.assertEqual(argv[:4], ['docker', 'inspect', '--format', '{{json .State}}'])
                self.assertEqual(kwargs['timeout'], 10)
                if pending and pending[0][0] == 'inspect':
                    _, item = pending.pop(0)
                    if isinstance(item, Exception):
                        raise item
                    return item
                exit_code = last_start.returncode if isinstance(last_start, subprocess.CompletedProcess) else 137
                return subprocess.CompletedProcess(argv, 0, json.dumps({
                    'StartedAt': '2026-10-27T00:00:00Z', 'Running': False, 'ExitCode': exit_code}), '')
            self.assertEqual(argv[:3], ['docker', 'start', '-a'])
            phase, item = pending.pop(0)
            self.assertEqual(phase, 'start')
            last_start = item
            if isinstance(item, Exception):
                raise item
            return item
        return fake, events, pending

    def test_witness_exit_and_timeout_are_recorded_twice(self):
        with tempfile.TemporaryDirectory() as temp:
            judge, output = self.module(Path(temp))
            cell = 'd001-D3-claude-B-r1'
            self.snapshot(output, cell)
            fake, events, pending = self.fake_docker([
                ('start', subprocess.CompletedProcess([], 2, '', 'throw')),
                ('start', subprocess.TimeoutExpired(['docker', 'start'], 10))])
            with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                result = judge.run(HERE / 'results/witnesses/d3-parseoptions-override.js', [cell])
            self.assertFalse(pending)
            self.assertEqual([call[0][1] for call in events], ['create', 'start', 'inspect', 'rm'] * 2)
            self.assertEqual([call[1] for call in events], [60, 10, 10, 10] * 2)
            self.assertEqual(result[cell]['result'], 'unresolved')
            self.assertEqual([x['exit'] for x in result[cell]['attempts']], [2, 2])
            stored = json.loads((output / 'witnesses.json').read_text())
            self.assertEqual(stored['d3-parseoptions-override'][cell], result[cell])
            (Path(temp) / 'instructions.seal.json').write_text(json.dumps({'witness_sha256': 'bad'}))
            with self.assertRaisesRegex(ValueError, 'differs from pre-SMOKE seal'):
                judge.run(HERE / 'results/witnesses/d3-parseoptions-override.js', [cell])
            revised = Path(temp) / 'd3-parseoptions-override.js'
            revised.write_text('process.exit(1)')
            with self.assertRaisesRegex(ValueError, cell + ': witness differs'):
                judge.run(revised, [cell])

    def test_witness_requires_marker_and_clean_stderr(self):
        for responses, expected in ((
            [subprocess.CompletedProcess([], 1, '', 'Cannot connect to the Docker daemon'),
             subprocess.CompletedProcess([], 1, 'P0258-WITNESS bypass\n', '')], [2, 1]), (
            [subprocess.CompletedProcess([], 0, 'P0258-WITNESS public\n', 'client error'),
             subprocess.CompletedProcess([], 0, 'P0258-WITNESS public\n', '')], [2, 0])):
            with tempfile.TemporaryDirectory() as temp:
                judge, output = self.module(Path(temp))
                cell = 'd001-D3-claude-B-r1'
                self.snapshot(output, cell)
                fake, _, _ = self.fake_docker([('start', item) for item in responses])
                with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                    result = judge.run(HERE / 'results/witnesses/d3-parseoptions-override.js', [cell])[cell]
                self.assertEqual([a['exit'] for a in result['attempts']], expected)
                self.assertEqual(result['result'], 'unresolved')
                self.assertIn(responses[0].stderr, result['attempts'][0]['error'])

    def test_generic_witness_json_exit_one_reproduces(self):
        with tempfile.TemporaryDirectory() as temp:
            judge, output = self.module(Path(temp))
            cell = 'd001-D3-claude-B-r1'
            self.snapshot(output, cell)
            witness = Path(temp) / 'generic.js'
            witness.write_text('process.exit(1)')
            response = subprocess.CompletedProcess([], 1, '{"reproduced":true}\n', '')
            fake, events, _ = self.fake_docker([('start', response)] * 2)
            with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                result = judge.run(witness, [cell])[cell]
            self.assertEqual([call[1] for call in events], [60, 30, 10, 10] * 2)
            self.assertEqual([attempt['exit'] for attempt in result['attempts']], [1, 1])
            self.assertIs(result['result'], True)
            self.assertEqual(json.loads((output / 'witnesses.json').read_text())['generic'][cell], result)

    def test_probe_retries_unassessable_once_and_records_both(self):
        with tempfile.TemporaryDirectory() as temp:
            judge, output = self.module(Path(temp))
            cell = 'c001-F10-claude-B-r1'
            self.snapshot(output, cell)
            fake, events, _ = self.fake_docker([
                ('start', subprocess.CompletedProcess([], 2, '', 'first failure')),
                ('start', subprocess.CompletedProcess([], 0,
                    '{"class":"json_error_400","store_preserved":true}\n', ''))])
            with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                result = judge.probe([cell])[cell]
            self.assertEqual([call[1] for call in events], [60, 60, 10, 10] * 2)
            self.assertEqual([x['class'] for x in result['attempts']], ['unassessable', 'json_error_400'])
            self.assertEqual(result['class'], 'json_error_400')
            self.assertEqual(json.loads((output / 'probes.json').read_text())[cell], result)

    def test_probe_retries_non_object_and_malformed_json(self):
        for invalid in ('null', '[]', '{broken'):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as temp:
                judge, output = self.module(Path(temp))
                cell = 'c001-F10-claude-B-r1'
                self.snapshot(output, cell)
                fake, events, _ = self.fake_docker([
                    ('start', subprocess.CompletedProcess([], 0, invalid + '\n', '')),
                    ('start', subprocess.CompletedProcess([], 0, '{"class":"html_400"}\n', ''))])
                with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                    result = judge.probe([cell])[cell]
                self.assertEqual(len(events), 8)
                self.assertEqual([a['class'] for a in result['attempts']], ['unassessable', 'html_400'])

    def test_probe_retry_create_failure_preserves_first_attempt(self):
        with tempfile.TemporaryDirectory() as temp:
            judge, output = self.module(Path(temp))
            cell = 'c001-F10-claude-B-r1'
            self.snapshot(output, cell)
            fake, events, _ = self.fake_docker([
                ('start', subprocess.CompletedProcess([], 2, '', 'first failure')),
                ('create', subprocess.CompletedProcess([], 1, '', 'name already in use'))])
            with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                with self.assertRaisesRegex(RuntimeError, cell + ': docker create failed'):
                    judge.probe([cell])
            partial = json.loads((output / 'probes.json').read_text())[cell]
            self.assertEqual([a['class'] for a in partial['attempts']], ['unassessable'])
            self.assertEqual(len(events), 6)
            fake, events, _ = self.fake_docker([
                ('start', subprocess.CompletedProcess([], 0, '{"class":"html_400"}\n', ''))])
            with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                resumed = judge.probe([cell])[cell]
            self.assertEqual([call[0][1] for call in events], ['create', 'start', 'inspect', 'rm'])
            self.assertEqual(resumed['attempts'][0], partial['attempts'][0])
            self.assertEqual([a['class'] for a in resumed['attempts']], ['unassessable', 'html_400'])

    def test_witness_second_create_failure_preserves_first_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            judge, output = self.module(Path(temp))
            cell = 'd001-D3-claude-B-r1'
            self.snapshot(output, cell)
            witness = HERE / 'results/witnesses/d3-parseoptions-override.js'
            fake, events, _ = self.fake_docker([
                ('start', subprocess.CompletedProcess([], 1, 'P0258-WITNESS bypass\n', '')),
                ('create', subprocess.TimeoutExpired(['docker', 'create'], 60))])
            with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                with self.assertRaisesRegex(RuntimeError, cell + ': docker create failed'):
                    judge.run(witness, [cell])
            partial = json.loads((output / 'witnesses.json').read_text())[witness.stem][cell]
            self.assertEqual(partial['result'], 'unresolved')
            self.assertEqual([a['exit'] for a in partial['attempts']], [1])
            self.assertEqual(partial['witness_sha256'], hashlib.sha256(witness.read_bytes()).hexdigest())
            self.assertEqual(len(events), 6)
            fake, events, _ = self.fake_docker([
                ('start', subprocess.CompletedProcess([], 1, 'P0258-WITNESS bypass\n', ''))])
            with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                resumed = judge.run(witness, [cell])[cell]
            self.assertEqual([call[0][1] for call in events], ['create', 'start', 'inspect', 'rm'])
            self.assertEqual(resumed['attempts'][0], partial['attempts'][0])
            self.assertIs(resumed['result'], True)

    def test_complete_cells_are_returned_without_docker(self):
        with tempfile.TemporaryDirectory() as temp:
            judge, output = self.module(Path(temp))
            probe_cell = 'c001-F10-claude-B-r1'
            witness_cell = 'd001-D3-claude-B-r1'
            for cell in (probe_cell, witness_cell):
                self.snapshot(output, cell)
            witness = HERE / 'results/witnesses/d3-parseoptions-override.js'
            fake, _, _ = self.fake_docker([
                ('start', subprocess.CompletedProcess([], 0, '{"class":"html_400"}\n', '')),
                ('start', subprocess.CompletedProcess([], 0, 'P0258-WITNESS public\n', '')),
                ('start', subprocess.CompletedProcess([], 0, 'P0258-WITNESS public\n', ''))])
            with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                probe = judge.probe([probe_cell])[probe_cell]
                run = judge.run(witness, [witness_cell])[witness_cell]
            probes_before = (output / 'probes.json').read_bytes()
            witnesses_before = (output / 'witnesses.json').read_bytes()
            with mock.patch.object(judge.subprocess, 'run', side_effect=AssertionError('Docker was called')):
                self.assertEqual(judge.probe([probe_cell])[probe_cell], probe)
                self.assertEqual(judge.run(witness, [witness_cell])[witness_cell], run)
            self.assertEqual((output / 'probes.json').read_bytes(), probes_before)
            self.assertEqual((output / 'witnesses.json').read_bytes(), witnesses_before)

    def test_witness_hash_change_requires_new_file_name(self):
        with tempfile.TemporaryDirectory() as temp:
            judge, output = self.module(Path(temp))
            cell = 'd001-D3-claude-B-r1'
            self.snapshot(output, cell)
            witness = Path(temp) / 'generic.js'
            witness.write_text('process.exit(0)')
            fake, _, _ = self.fake_docker([
                ('start', subprocess.CompletedProcess([], 0, '', ''))] * 2)
            with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                judge.run(witness, [cell])
            witness.write_text('process.exit(1)')
            with mock.patch.object(judge.subprocess, 'run', side_effect=AssertionError('Docker was called')):
                with self.assertRaisesRegex(ValueError, cell + ': witness differs'):
                    judge.run(witness, [cell])

    def test_cleanup_failure_records_started_outcome(self):
        for mode in ('probe', 'run'):
            for failure in (subprocess.CalledProcessError(1, ['docker', 'rm'], stderr='remove failed'),
                            subprocess.TimeoutExpired(['docker', 'rm'], 10)):
                with self.subTest(mode=mode, failure=type(failure).__name__), tempfile.TemporaryDirectory() as temp:
                    judge, output = self.module(Path(temp))
                    cell = 'c001-F10-claude-B-r1' if mode == 'probe' else 'd001-D3-claude-B-r1'
                    self.snapshot(output, cell)
                    started = (subprocess.CompletedProcess([], 0, '{"class":"html_400"}\n', '')
                               if mode == 'probe' else
                               subprocess.CompletedProcess([], 1, 'P0258-WITNESS bypass\n', ''))
                    fake, events, _ = self.fake_docker([
                        ('start', started), ('rm', failure),
                        ('create', subprocess.CompletedProcess([], 1, '', 'name already in use'))]
                        if mode == 'run' else [('start', started), ('rm', failure)])
                    with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                        if mode == 'probe':
                            judge.probe([cell])
                        else:
                            with self.assertRaisesRegex(RuntimeError, cell + ': docker create failed'):
                                judge.run(HERE / 'results/witnesses/d3-parseoptions-override.js', [cell])
                    record = json.loads((output / ('probes.json' if mode == 'probe' else 'witnesses.json')).read_text())
                    record = record[cell] if mode == 'probe' else record['d3-parseoptions-override'][cell]
                    attempt = record['attempts'][0]
                    self.assertEqual(attempt['class'] if mode == 'probe' else attempt['exit'],
                                     'html_400' if mode == 'probe' else 1)
                    self.assertIn('cleanup_error', attempt)
                    self.assertIn(str(failure), attempt['cleanup_error'])
                    self.assertEqual([call[0][1] for call in events],
                                     ['create', 'start', 'inspect', 'rm'] + (['create', 'rm'] if mode == 'run' else []))

    def test_create_failure_preserves_earlier_cells_without_recording_failed_cell(self):
        for phase in ('create_error', 'create_timeout'):
            for mode in ('probe', 'run'):
                with self.subTest(phase=phase, mode=mode), tempfile.TemporaryDirectory() as temp:
                    judge, output = self.module(Path(temp))
                    cells = (['c001-F10-claude-B-r1', 'c002-F10-claude-C-r1'] if mode == 'probe'
                             else ['d001-D3-claude-B-r1', 'd002-D3-claude-C-r1'])
                    for cell in cells:
                        self.snapshot(output, cell)
                    normal = (subprocess.CompletedProcess([], 0, '{"class":"html_400"}\n', '')
                              if mode == 'probe' else
                              subprocess.CompletedProcess([], 0, 'P0258-WITNESS public\n', ''))
                    failure = (subprocess.CompletedProcess([], 1, '', 'daemon error') if phase == 'create_error'
                               else subprocess.TimeoutExpired(['docker', 'create'], 60))
                    prior = [('start', normal)] if mode == 'probe' else [('start', normal)] * 2
                    fake, events, _ = self.fake_docker(prior + [('create', failure)])
                    with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                        with self.assertRaisesRegex(RuntimeError, cells[1] + ': docker create failed'):
                            if mode == 'probe':
                                judge.probe(cells)
                            else:
                                judge.run(HERE / 'results/witnesses/d3-parseoptions-override.js', cells)
                    record = json.loads((output / ('probes.json' if mode == 'probe' else 'witnesses.json')).read_text())
                    recorded = record if mode == 'probe' else record['d3-parseoptions-override']
                    self.assertIn(cells[0], recorded)
                    self.assertNotIn(cells[1], recorded)
                    self.assertEqual(events[-1][0][:3], ['docker', 'rm', '-f'])
                    self.assertFalse(any(call[0][:3] == ['docker', 'start', '-a'] and
                                         call[0][-1].startswith(('probe-' + cells[1], 'witness-' + cells[1]))
                                         for call in events))

    def test_start_timeout_records_probe_and_witness(self):
        with tempfile.TemporaryDirectory() as temp:
            judge, output = self.module(Path(temp))
            probe_cell = 'c001-F10-claude-B-r1'
            witness_cell = 'd001-D3-claude-B-r1'
            for cell in (probe_cell, witness_cell):
                self.snapshot(output, cell)
            fake, _, _ = self.fake_docker([
                ('start', subprocess.TimeoutExpired(['docker', 'start'], 60)),
                ('start', subprocess.CompletedProcess([], 0, '{"class":"html_400"}\n', ''))])
            with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                probe = judge.probe([probe_cell])[probe_cell]
            self.assertEqual([a['class'] for a in probe['attempts']], ['unassessable', 'html_400'])
            fake, _, _ = self.fake_docker([
                ('start', subprocess.TimeoutExpired(['docker', 'start'], 10)),
                ('start', subprocess.CompletedProcess([], 0, 'P0258-WITNESS public\n', ''))])
            with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                witness = judge.run(HERE / 'results/witnesses/d3-parseoptions-override.js', [witness_cell])[witness_cell]
            self.assertEqual([a['exit'] for a in witness['attempts']], [2, 0])

    def test_never_started_witness_preserves_earlier_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            judge, output = self.module(Path(temp))
            cell = 'd001-D3-claude-B-r1'
            self.snapshot(output, cell)
            witness = Path(temp) / 'generic.js'
            witness.write_text('process.exit(0)')
            zero = subprocess.CompletedProcess([], 0, json.dumps({
                'StartedAt': '0001-01-01T00:00:00Z', 'Running': False, 'ExitCode': 0}), '')
            fake, events, _ = self.fake_docker([
                ('start', subprocess.CompletedProcess([], 0, 'pass\n', '')),
                ('start', subprocess.CompletedProcess([], 1, '', 'daemon failed to start')),
                ('inspect', zero)])
            with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                with self.assertRaisesRegex(RuntimeError, cell + ': container never started: daemon failed to start'):
                    judge.run(witness, [cell])
            stored = json.loads((output / 'witnesses.json').read_text())['generic'][cell]
            self.assertEqual([attempt['exit'] for attempt in stored['attempts']], [0])
            self.assertEqual(stored['result'], 'unresolved')
            self.assertEqual([call[0][1] for call in events][-4:], ['create', 'start', 'inspect', 'rm'])

    def test_never_started_probe_preserves_earlier_attempt(self):
        with tempfile.TemporaryDirectory() as temp:
            judge, output = self.module(Path(temp))
            cell = 'c001-F10-claude-B-r1'
            self.snapshot(output, cell)
            zero = subprocess.CompletedProcess([], 0, json.dumps({
                'StartedAt': '0001-01-01T00:00:00Z', 'Running': False, 'ExitCode': 0}), '')
            fake, events, _ = self.fake_docker([
                ('start', subprocess.CompletedProcess([], 2, '', 'first failure')),
                ('start', subprocess.CompletedProcess([], 1, '', 'daemon failed to start')),
                ('inspect', zero)])
            with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                with self.assertRaisesRegex(RuntimeError, cell + ': container never started: daemon failed to start'):
                    judge.probe([cell])
            stored = json.loads((output / 'probes.json').read_text())[cell]
            self.assertEqual([attempt['class'] for attempt in stored['attempts']], ['unassessable'])
            self.assertEqual([call[0][1] for call in events][-4:], ['create', 'start', 'inspect', 'rm'])

    def test_unreadable_container_state_records_no_attempt(self):
        failures = (
            subprocess.CompletedProcess([], 1, '', 'inspect daemon error'),
            subprocess.TimeoutExpired(['docker', 'inspect'], 10),
            subprocess.CompletedProcess([], 0, '[]', ''),
            subprocess.CompletedProcess([], 0, '{"StartedAt":"now","Running":false}', ''),
        )
        for failure in failures:
            for mode in ('run', 'probe'):
                with self.subTest(failure=str(failure), mode=mode), tempfile.TemporaryDirectory() as temp:
                    judge, output = self.module(Path(temp))
                    cell = 'd001-D3-claude-B-r1' if mode == 'run' else 'c001-F10-claude-B-r1'
                    self.snapshot(output, cell)
                    fake, events, _ = self.fake_docker([
                        ('start', subprocess.CompletedProcess([], 1, '', 'start diagnostic')),
                        ('inspect', failure)])
                    with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                        with self.assertRaisesRegex(RuntimeError, cell + ': container state unreadable:'):
                            if mode == 'run':
                                judge.run(HERE / 'results/witnesses/d3-parseoptions-override.js', [cell])
                            else:
                                judge.probe([cell])
                    path = output / ('witnesses.json' if mode == 'run' else 'probes.json')
                    if path.exists():
                        record = json.loads(path.read_text())
                        self.assertNotIn(cell, record.get('d3-parseoptions-override', {}) if mode == 'run' else record)
                    self.assertEqual([call[0][1] for call in events], ['create', 'start', 'inspect', 'rm'])

    def test_running_or_mismatched_state_is_unassessable_with_diagnostic(self):
        for running, exit_code in ((True, 1), (False, 0)):
            for mode in ('run', 'probe'):
                with self.subTest(running=running, exit_code=exit_code, mode=mode), tempfile.TemporaryDirectory() as temp:
                    judge, output = self.module(Path(temp))
                    cell = 'd001-D3-claude-B-r1' if mode == 'run' else 'c001-F10-claude-B-r1'
                    self.snapshot(output, cell)
                    state = subprocess.CompletedProcess([], 0, json.dumps({
                        'StartedAt': '2026-10-27T00:00:00Z', 'Running': running, 'ExitCode': exit_code}), '')
                    response = subprocess.CompletedProcess([], 1, '', 'startup stderr')
                    fake, _, _ = self.fake_docker([('start', response), ('inspect', state)] * 2)
                    with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                        if mode == 'run':
                            result = judge.run(HERE / 'results/witnesses/d3-parseoptions-override.js', [cell])[cell]
                        else:
                            result = judge.probe([cell])[cell]
                    for attempt in result['attempts']:
                        self.assertEqual(attempt['exit'] if mode == 'run' else attempt['class'],
                                         2 if mode == 'run' else 'unassessable')
                        self.assertIn('docker start exit 1', attempt['error'])
                        self.assertIn(f'container ExitCode {exit_code}', attempt['error'])
                        self.assertIn('startup stderr', attempt['error'])

    def test_started_container_uses_inspected_exit_code(self):
        with tempfile.TemporaryDirectory() as temp:
            judge, _ = self.module(Path(temp))
            state = subprocess.CompletedProcess([], 0, json.dumps({
                'StartedAt': '2026-10-27T00:00:00Z', 'Running': False, 'ExitCode': 1}), '')
            start = subprocess.CompletedProcess([], 1, 'witness output', 'witness stderr')
            fake, events, _ = self.fake_docker([('start', start), ('inspect', state)])
            with mock.patch.object(judge.subprocess, 'run', side_effect=fake):
                done, cleanup_error, invalid_error = judge.docker_attempt(
                    'cell', 'container', ['--network', 'none', '--mount', 'type=bind,src=/tmp,dst=/work'], 30)
            self.assertEqual((done.returncode, done.stdout, done.stderr),
                             (1, 'witness output', 'witness stderr'))
            self.assertIsNone(cleanup_error)
            self.assertIsNone(invalid_error)
            self.assertEqual([call[0][1] for call in events], ['create', 'start', 'inspect', 'rm'])


if __name__ == '__main__':
    unittest.main()
