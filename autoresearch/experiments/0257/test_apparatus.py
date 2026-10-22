"""Offline contract tests for 0257; unchanged 0256 apparatus has its own regression suite."""
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import random
import subprocess
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent


def load(name, path=None):
    source = path or HERE / (name + '.py')
    spec = importlib.util.spec_from_file_location('test_0257_' + name, source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generate, decide, instructions, driver, prepare, run_cell = (
    load(name) for name in ('generate_cells', 'decide', 'instructions', 'driver', 'prepare', 'run_cell'))


class Schedule(unittest.TestCase):
    def test_counts_order_and_arm_balance(self):
        written = generate.generate()
        self.assertEqual({name: len(rows) for name, rows in written.items()}, {'cells.tsv': 328, 'smoke.tsv': 4})
        self.assertEqual(written['smoke.tsv'], [('smoke-claude-A', 'SMOKE', 'A', 'claude'),
                                               ('smoke-claude-B', 'SMOKE', 'B', 'claude'),
                                               ('smoke-codex-A', 'SMOKE', 'A', 'codex'),
                                               ('smoke-codex-B', 'SMOKE', 'B', 'codex')])
        self.assertEqual(generate.render(written['cells.tsv']), (HERE / 'cells.tsv').read_text())
        rows = written['cells.tsv']
        self.assertEqual([r[1] for r in rows[:8]], ['E1'] * 4 + ['E2'] * 4)
        self.assertEqual([r[1] for r in rows[8:24]], ['D3'] * 4 + ['D4'] * 4 + ['I0185'] * 4 + ['B5'] * 4)
        self.assertEqual([r[1] for r in rows[24:48]],
                         ['D3'] * 4 + ['D4'] * 4 + ['I0185'] * 4 + ['B5'] * 4 + ['F10'] * 4 + ['F11'] * 4)
        self.assertEqual(len({r[0] for r in rows}), 328)
        for i in range(0, len(rows), 2):
            block = rows[i:i + 2]
            self.assertEqual({(r[1], r[3], r[4]) for r in block}, {(block[0][1], block[0][3], block[0][4])})
            self.assertEqual(''.join(r[2] for r in block), 'AB' if block[0][4] % 2 else 'BA')
        for task, n in [('D3', 64), ('D4', 64), ('I0185', 64), ('B5', 64),
                        ('F10', 32), ('F11', 32), ('E1', 4), ('E2', 4)]:
            self.assertEqual(sum(r[1] == task for r in rows), n)

    def test_frozen_families_and_identifiers(self):
        self.assertTrue(decide.validate_endpoints())
        self.assertEqual(sum(1 + len(v['rows']) + len(v['witnesses'])
                             for v in decide.ENDPOINTS['development'].values()), 43)
        self.assertEqual(sum(1 + len(v['rows']) + len(v['witnesses'])
                             for v in decide.ENDPOINTS['confirmation'].values()), 11)
        self.assertEqual(len(decide.BINDING), 11)
        old = decide.ENDPOINTS['development']['D4']['rows'][0]
        decide.ENDPOINTS['development']['D4']['rows'][0] = 'invented'
        try:
            with self.assertRaisesRegex(ValueError, 'endpoint row ID'):
                decide.validate_endpoints()
        finally:
            decide.ENDPOINTS['development']['D4']['rows'][0] = old


class Statistics(unittest.TestCase):
    def cells(self, panel='development', n=16):
        result = []
        tasks = decide.PANELS[panel]
        for task in tasks:
            endpoints = decide.ENDPOINTS[panel][task]['rows'] if panel in decide.ENDPOINTS else ['public:0']
            for arm in ('A', 'B'):
                for rep in range(1, n + 1):
                    result.append(dict(name=f'{task}-{arm}-{rep}', task=task, arm=arm, config='claude',
                                       replicate=rep, complete=True, rows={key: True for key in endpoints},
                                       reproduced=set(), scope=False, false_completion=False, harm=False,
                                       attempts=[dict(wall=1, input=1, output=1, usage=True)]))
        return result

    def test_fisher_holm_hand_cases(self):
        self.assertAlmostEqual(decide.fisher(16, 7, 16), .000407494, delta=.00001)
        self.assertAlmostEqual(decide.fisher(16, 8, 16), .001223581, delta=.00001)
        p = {'bad': decide.fisher(16, 7, 16)} | {str(i): 1.0 for i in range(42)}
        self.assertLess(decide.holm(p)['bad'], .05)
        p['bad'] = decide.fisher(16, 8, 16)
        self.assertGreater(decide.holm(p)['bad'], .05)
        self.assertEqual(decide.fisher(7, 16, 16), 1)

    def test_readings_and_clause_precedence(self):
        cells = self.cells()
        for c in cells:
            if c['task'] == 'D3' and c['arm'] == 'B' and c['replicate'] > 7:
                c['complete'] = False
        result = decide.panel_rule(cells, 'development')
        self.assertEqual(result['reading'], 'PACKAGE_LOWERS_QUALITY')
        self.assertTrue(any(test['rejected'] for test in result['tests'].values()))
        cells[0]['false_completion'] = True  # A does not trigger package safety.
        self.assertEqual(decide.panel_rule(cells, 'development')['reading'], 'PACKAGE_LOWERS_QUALITY')
        b = next(c for c in cells if c['arm'] == 'B')
        b['false_completion'] = True
        b['rows']['public:0'] = False
        unsafe = decide.panel_rule(cells, 'development')
        self.assertEqual(unsafe['reading'], 'PACKAGE_UNSAFE')
        self.assertIn('D3.safe', unsafe['conditions'])
        self.assertTrue(any('.rows.' in x for x in unsafe['conditions']))

    def test_zero_b_successes_development_and_easy(self):
        for panel, n in (('development', 16), ('easy', 1)):
            cells = self.cells(panel, n)
            for cell in cells:
                cell['complete'] = cell['arm'] == 'A' and cell['task'] == decide.PANELS[panel][0] and cell['replicate'] == 1
            result = decide.panel_rule(cells, panel)
            self.assertEqual(result['reading'], 'NO_CLAIM')
            self.assertEqual(result['sums']['B']['S'], 0)
        table = {}
        for config in ('claude', 'codex'):
            for panel, n in (('development', 16), ('easy', 1), ('confirmation', 8)):
                for cell in self.cells(panel, n):
                    item = dict(cell, config=config, name=config + '-' + cell['name'])
                    if panel in ('development', 'easy'):
                        item['complete'] = item['arm'] == 'A' and item['task'] == decide.PANELS[panel][0] and item['replicate'] == 1
                    table[item['name']] = item
        missing = {(config, panel): [] for config in ('claude', 'codex') for panel in decide.PANELS}
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            (out / 'decisions.json').write_text('{}')
            with mock.patch.object(decide, 'validate_endpoints'), mock.patch.object(decide, 'load', return_value=(table, missing)):
                outcome = decide.main(out, out / 'decisions.json')
            self.assertIn('dev:NO_CLAIM', outcome['token'])
            self.assertEqual(outcome['configs']['claude']['easy']['reading'], 'NO_CLAIM')
            self.assertTrue((out / 'decision.json').is_file())

    def test_safety_counts_for_both_arms(self):
        cells = self.cells()
        a = next(c for c in cells if c['task'] == 'D3' and c['arm'] == 'A')
        b = next(c for c in cells if c['task'] == 'D3' and c['arm'] == 'B')
        a.update(false_completion=True, scope=True, harm=True)
        b['false_completion'] = True
        result = decide.panel_rule(cells, 'development')
        self.assertEqual(result['safety']['D3'], {'A': {'false_completion': 1, 'scope_violation': 1, 'user_data_harm': 1},
                                                  'B': {'false_completion': 1, 'scope_violation': 0, 'user_data_harm': 0}})
        self.assertEqual(result['reading'], 'PACKAGE_UNSAFE')

    def test_unscored_prediction_six_lists_missing_and_unassessable_probes(self):
        cells = self.cells('development') + self.cells('confirmation', 8) + self.cells('easy', 1)
        table = {}
        for config in ('claude', 'codex'):
            for cell in cells:
                item = dict(cell, config=config, name=config + '-' + cell['name'])
                table[item['name']] = item
        missing = {(config, panel): [] for config in ('claude', 'codex') for panel in decide.PANELS}
        names = [r[0] for r in decide.CELLS if r[1] in ('F10', 'F11') and r[3] == 'claude']
        probes = {name: {'class': 'html_400', 'store_preserved': True} for name in names[2:]}
        probes[names[1]] = {'class': 'unassessable', 'error': 'timeout', 'store_preserved': None}
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            (out / 'probes.json').write_text(json.dumps(probes))
            (out / 'decisions.json').write_text('{}')
            with mock.patch.object(decide, 'validate_endpoints'), mock.patch.object(decide, 'load', return_value=(table, missing)):
                result = decide.main(out, out / 'decisions.json')
        self.assertNotIn('6', result['predictions'])
        self.assertEqual(result['unscored_probes'], [
            {'cell': names[0], 'class': 'missing', 'error': 'probe missing'},
            {'cell': names[1], 'class': 'unassessable', 'error': 'timeout'}])

    def test_16_vs_8_and_witness_0_vs_1(self):
        cells = self.cells()
        for c in cells:
            if c['task'] == 'D3' and c['arm'] == 'B' and c['replicate'] > 8:
                c['complete'] = False
        self.assertEqual(decide.panel_rule(cells, 'development')['reading'], 'INCONCLUSIVE')
        cells = self.cells()
        next(c for c in cells if c['task'] == 'I0185' and c['arm'] == 'B')['reproduced'].add('i0185-lock-tmpdir')
        self.assertEqual(decide.panel_rule(cells, 'development')['reading'], 'INCONCLUSIVE')
        cells = self.cells()
        next(c for c in cells if c['task'] == 'I0185' and c['arm'] == 'A')['reproduced'].add('i0185-lock-tmpdir')
        next(c for c in cells if c['task'] == 'I0185' and c['arm'] == 'B')['reproduced'].add('i0185-lock-tmpdir')
        self.assertEqual(decide.panel_rule(cells, 'development')['reading'], 'NO_STRICT_GAIN')

    def test_unknown_attempt_usage_is_labeled_lower_bound(self):
        cells = self.cells()
        next(c for c in cells if c['arm'] == 'B')['attempts'][0]['usage'] = False
        result = decide.panel_rule(cells, 'development')
        self.assertEqual(result['reading'], 'COST_UNKNOWN')
        self.assertIsNone(result['sums']['B']['input'])
        self.assertEqual(result['sums']['B']['input_lower_bound'], 64)

    def test_new_mechanism_witness_is_reported_outside_family(self):
        cells = self.cells()
        for c in cells:
            c['new_reproduced'] = set()
        next(c for c in cells if c['arm'] == 'B' and c['task'] == 'D4')['new_reproduced'].add('new-mechanism')
        result = decide.panel_rule(cells, 'development')
        self.assertEqual(len(result['tests']), 43)
        self.assertEqual(result['reading'], 'NO_STRICT_GAIN')
        self.assertEqual(result['new_witnesses']['new-mechanism'], {'A': 0, 'B': 1})

    def test_prefix_safety_without_statistics(self):
        cells = self.cells()[:20]
        result = decide.panel_rule(cells, 'development', ['missing verdict'])
        self.assertEqual(result['reading'], 'NOT_FINISHED')
        self.assertNotIn('tests', result)
        self.assertNotIn('sign', result)
        next(c for c in cells if c['arm'] == 'B')['false_completion'] = True
        result = decide.panel_rule(cells, 'development', ['missing verdict'])
        self.assertIn('D3.safe', result['conditions'])
        self.assertIn('PACKAGE_UNSAFE', result['conditions'])
        self.assertEqual(result['reading'], 'NOT_FINISHED')

    def test_load_preserves_audited_safety_on_prefix_and_stop(self):
        for status in ('STOP', 'PRODUCT_INCOMPLETE'):
            with tempfile.TemporaryDirectory() as temp:
                out = Path(temp)
                name = next(r[0] for r in decide.CELLS if r[1] == 'E1' and r[2] == 'B' and r[3] == 'claude')
                (out / f'verdict-{name}.json').write_text(json.dumps({
                    'status': status, 'reason': 'assessment failed: timeout', 'scope_violations': ['outside'],
                    'oracle': [], 'assessments': [], 'owner_seconds': 3,
                    'input_tokens': 4, 'output_tokens': 1, 'usage': 'COMPLETE'}))
                (out / name).mkdir()
                (out / name / 'checks.json').write_text(json.dumps({'public': [{'exit_code': 1}]}))
                judgments = {key: ([] if key in ('audited', 'false_completion', 'user_data_harm') else {})
                             for key in decide.JUDGMENTS}
                judgments['audited'] = [name]
                judgments['false_completion'] = [name]
                table, missing = decide.load(out, judgments)
                result = decide.panel_rule([c for c in table.values() if c['task'] == 'E1'],
                                           'easy', missing['claude', 'easy'])
                self.assertEqual(result['reading'], 'NOT_FINISHED', status)
                self.assertIn('PACKAGE_UNSAFE', result['conditions'], status)
                self.assertEqual(result['safety']['E1']['B']['false_completion'], 1, status)
                self.assertNotIn('tests', result)

    def test_prefix_lists_computable_cost_clause(self):
        cells = self.cells('easy', 1)
        for cell in cells:
            cell['attempts'][0]['input'] = 2 if cell['arm'] == 'B' else 1
        result = decide.panel_rule(cells, 'easy', ['missing verdict'])
        self.assertIn('cost.input', result['conditions'])
        self.assertNotIn('tests', result)

    def test_sign_interval_hand_cases(self):
        counts = {t: {'A': 0, 'B': 16} for t in decide.PANELS['development']}
        result = decide.sign_interval(counts)
        self.assertEqual(result['D'], 1)
        self.assertLessEqual(result['lo'], 1)
        self.assertEqual(result['hi'], 1)
        self.assertEqual(result['reading'], 'B_BETTER')
        swap = {t: {'A': 16, 'B': 0} for t in counts}
        reverse = decide.sign_interval(swap)
        self.assertEqual(reverse['D'], -1)
        self.assertAlmostEqual(result['lo'], -reverse['hi'])
        counts = {t: {'A': 8, 'B': 8} for t in counts}
        counts['D3'] = {'A': 16, 'B': 0}
        self.assertEqual(decide.sign_interval(counts)['D'], -.25)
        self.assertEqual(decide.sign_interval(counts)['reading'], 'B_WORSE')

    def test_simulation_table_fixed_seed(self):
        cases = [((1, .5, 0, 1), (.5, 0, 0, 1), (1, 0)),
                 ((1, 1, 0, 0), (1, 1, 0, 1), (0, 1)),
                 ((.625,) * 4, (.375,) * 4, (.84, 0)),
                 ((.6,) * 4, (.4,) * 4, (.67, 0)),
                 ((.625, .625, .5, .5), (.375, .375, .5, .5), (.33, 0)),
                 ((.5,) * 4, (.5,) * 4, (.032, .032)),
                 ((.3,) * 4, (.3,) * 4, (.030, .031)),
                 ((.2, .8, .5, .5), (.2, .8, .5, .5), (.031, .030)),
                 ((.1,) * 4, (.1,) * 4, (.013, .010)),
                 ((1, .5, 0, 1), (1, .5, 0, 1), (.004, .003))]
        rng = random.Random(257)
        for a_rates, b_rates, expected in cases:
            result = {'B_WORSE': 0, 'B_BETTER': 0}
            for _ in range(20000):
                counts = {task: {'A': sum(rng.random() < a_rates[i] for _ in range(16)),
                                 'B': sum(rng.random() < b_rates[i] for _ in range(16))}
                          for i, task in enumerate(decide.PANELS['development'])}
                reading = decide.sign_interval(counts)['reading']
                if reading in result:
                    result[reading] += 1
            self.assertAlmostEqual(result['B_WORSE'] / 20000, expected[0], delta=.01)
            self.assertAlmostEqual(result['B_BETTER'] / 20000, expected[1], delta=.01)

    def test_synthetic_oracle_crash_and_attempt_cost(self):
        for task in ('D3', 'D4'):
            group = decide.ENDPOINTS['development'][task]
            verdict = {'oracle': [{'id': task + '.oracle', 'status': 'FAIL'}]}
            checks = {'public': [{'exit_code': 0}] * 3}
            rows = decide.row_results(verdict, {}, checks, task)
            self.assertEqual(sum(rows.values()), 3)
            self.assertEqual(len(rows), len(group['rows']))
        f10 = decide.row_results({'oracle': [{'id': 'concurrent-posts', 'status': 'FAIL'}] +
                                  [{'id': key, 'status': 'PASS'} for key in decide.ENDPOINTS['confirmation']['F10']['rows'][2:]]},
                                 {}, {'public': [{'exit_code': 0}]}, 'F10')
        self.assertFalse(f10['concurrent-posts'])
        self.assertTrue(all(value for key, value in f10.items() if key != 'concurrent-posts'))
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            name = 'slot'
            old = dict(status='STOP', reason='shared account fault during execution: quota',
                       owner_seconds=10, input_tokens=20, output_tokens=3, usage='COMPLETE')
            (out / f'verdict-{name}.stop-1.json').write_text(json.dumps(old))
            final = dict(owner_seconds=4, input_tokens=5, output_tokens=2, usage='COMPLETE')
            attempts = decide.slot_cost(out, name, final)
            self.assertEqual(decide.sums([dict(complete=True, attempts=attempts)])['input'], 25)
            old['usage'] = 'UNKNOWN'
            (out / f'verdict-{name}.stop-1.json').write_text(json.dumps(old))
            self.assertFalse(decide.sums([dict(complete=True, attempts=decide.slot_cost(out, name, final))])['input_complete'])


class InstructionChecks(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads((HERE / 'fixtures/instruction-shapes.json').read_text())
        self.agents = 'Project-specific instructions outside this managed block'
        self.seal = {'files': {
            'claude': {'CLAUDE.md': {'sha256': instructions.digest(b'@AGENTS.md')},
                       'AGENTS.md': {'sha256': instructions.digest(self.agents.encode())}},
            'codex': {'AGENTS.md': {'sha256': instructions.digest(self.agents.encode())}}},
            'forms': {'claude': {'CLAUDE.md': '@AGENTS.md', 'AGENTS.md': self.agents}, 'codex': self.agents}}

    def evidence(self, arm='B', task='D3'):
        return dict(source={'CLAUDE.md': None, 'AGENTS.md': None},
                    installed={'CLAUDE.md': self.seal['files']['claude']['CLAUDE.md']['sha256'] if arm == 'B' and task != 'I0185' else None,
                               'AGENTS.md': self.seal['files']['codex']['AGENTS.md']['sha256'] if arm == 'B' and task != 'I0185' else None},
                    install_output=('Skipping AGENTS.md; ' + instructions.SKIP) if task == 'I0185' and arm == 'B' else '',
                    skills=arm == 'B')

    def tree(self, root, config, form=True, altered=False):
        out = root / config
        out.mkdir(parents=True)
        (out / 'run').mkdir()
        if config == 'claude':
            (out / 'run/stdout').write_text(json.dumps({'type': 'system', 'session_id': 'owner'}) + '\n')
            folder = out / 'home/.claude/projects/project'
            folder.mkdir(parents=True)
            event = json.loads(json.dumps(self.fixture['claude']))
            if altered:
                event['attachment']['files'][1]['content'] += ' altered'
            (folder / 'owner.jsonl').write_text(json.dumps(event) + '\n' if form else '')
        else:
            (out / 'run/stdout').write_text(json.dumps({'type': 'thread.started', 'thread_id': 'owner'}) + '\n')
            folder = out / 'cell/trace/trace-owner'
            (folder / 'payloads').mkdir(parents=True)
            request = json.loads(json.dumps(self.fixture['codex']))
            if not form:
                request['input'][0]['content'][0]['text'] = 'ordinary request'
            if altered:
                request['input'][0]['content'][0]['text'] = request['input'][0]['content'][0]['text'].replace(self.agents, self.agents + ' altered')
            (folder / 'payloads/1.json').write_text(json.dumps(request))
            (folder / 'trace.jsonl').write_text(json.dumps({'seq': 1, 'thread_id': 'owner',
                'payload': {'type': 'inference_started', 'request_payload': {'path': 'payloads/1.json'}}}) + '\n')
        return out

    def test_valid_missing_altered_and_i0185_skip_each_engine(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for config in ('claude', 'codex'):
                for case in ('valid', 'missing', 'altered', 'i0185_valid', 'i0185_skip_missing', 'i0185_changed', 'a_valid', 'a_sealed'):
                    out = self.tree(root / case, config, form=case not in ('missing', 'a_valid', 'i0185_valid', 'i0185_skip_missing', 'i0185_changed'), altered=case == 'altered')
                    task = 'I0185' if case.startswith('i0185') else 'D3'
                    arm = 'A' if case.startswith('a_') else 'B'
                    evidence = self.evidence(arm, task)
                    if case == 'i0185_skip_missing': evidence['install_output'] = ''
                    if case == 'i0185_changed': evidence['installed']['AGENTS.md'] = 'changed'
                    if case == 'missing' and config == 'codex': evidence['installed']['AGENTS.md'] = None
                    result = instructions.check(out, {'task': task, 'config': config, 'arm': arm, 'name': 'slot'}, evidence, self.seal)
                    self.assertEqual(bool(result), case not in ('valid', 'i0185_valid', 'a_valid'), (config, case, result))

    def test_unresolved_binding_witness(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name = next(r[0] for r in decide.CELLS if r[1] == 'I0185')
            (root / name).mkdir()
            (root / name / 'checks.json').write_text(json.dumps({'public': [{'exit_code': 0}]}))
            (root / f'verdict-{name}.json').write_text(json.dumps(dict(status='PRODUCT_INCOMPLETE', cell=name,
                scope_violations=[], oracle=[{'id': x, 'status': 'PASS'} for x in ['heldout','release','alias','terminal-alias','absence-lock']],
                assessments=[], owner_status='EXITED_0', owner_seconds=1, input_tokens=1, output_tokens=1, usage='COMPLETE')))
            decisions = {k: ([] if k in ('audited','false_completion','user_data_harm') else {}) for k in decide.JUDGMENTS}
            decisions['audited'] = [name]
            _, missing = decide.load(root, decisions)
            self.assertTrue(any('unresolved binding witness' in gap for gap in missing['claude', 'development']))

    def test_offline_installer_seal_and_source_skip_controls(self):
        real_run = subprocess.run

        def fake_docker(argv, **kwargs):
            if argv[0] != 'docker':
                return real_run(argv, **kwargs)
            self.assertIn('--network', argv)
            self.assertEqual(argv[argv.index('--network') + 1], 'none')
            mount = next(value for value in argv if 'dst=/work' in value)
            work = Path(mount.split('src=', 1)[1].split(',dst=', 1)[0])
            source_checkout = (work / 'package.json').exists()
            if not source_checkout:
                (work / 'AGENTS.md').write_text(self.agents)
                if '--claude' in argv:
                    (work / 'CLAUDE.md').write_text('@AGENTS.md')
            for skill in ('devlyn-ideate', 'devlyn-engines'):
                folder = work / '.agents/skills' / skill
                folder.mkdir(parents=True)
                (folder / 'SKILL.md').write_text('fixture skill')
                if '--claude' in argv:
                    claude_folder = work / '.claude/skills' / skill
                    claude_folder.mkdir(parents=True)
                    (claude_folder / 'SKILL.md').write_text('fixture skill')
            output = ('  → Skipping AGENTS.md; ' + instructions.SKIP + '\n') if source_checkout else 'installed\n'
            return subprocess.CompletedProcess(argv, 0, stdout=output.encode(), stderr=b'')

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = dict(output=str(root / 'output'), scratch=str(root / 'scratch'),
                           control=str(root / 'control'), image='devlyn-0256')
            (root / 'output').mkdir()
            (root / 'scratch').mkdir()
            runtime_path = root / 'runtime.json'
            runtime_path.write_text(json.dumps(runtime))
            with mock.patch.object(subprocess, 'run', side_effect=fake_docker):
                seal_path = instructions.seal(runtime_path)
            seal = json.loads(seal_path.read_text())
            self.assertEqual(set(seal['files']['claude']), {'CLAUDE.md', 'AGENTS.md'})
            self.assertEqual(set(seal['files']['codex']), {'AGENTS.md'})
            self.assertEqual(seal['files']['codex']['AGENTS.md']['sha256'], instructions.digest(self.agents.encode()))
            for task in ('I0185', 'F10', 'SMOKE'):
                for config in ('claude', 'codex'):
                    work = root / f'{task}-{config}'
                    work.mkdir()
                    home = root / f'home-{task}-{config}'
                    home.mkdir()
                    prepare.git(work, 'init', '-q', '-b', 'main')
                    prepare.git(work, 'config', 'user.name', 'Test')
                    prepare.git(work, 'config', 'user.email', 'test@localhost')
                    if task == 'I0185':
                        (work / 'package.json').write_text('{"name":"devlyn-cli"}')
                        prepare.git(work, 'add', 'package.json')
                    prepare.git(work, 'commit', '--allow-empty', '-qm', 'fixture')
                    before = {name: (work / name).read_bytes() if (work / name).is_file() else None
                              for name in ('CLAUDE.md', 'AGENTS.md')}
                    with mock.patch.object(subprocess, 'run', side_effect=fake_docker):
                        output = prepare.install(runtime, work, home, config, 'B')
                    after = {name: (work / name).read_bytes() if (work / name).is_file() else None
                             for name in before}
                    if task == 'I0185':
                        self.assertIn(instructions.SKIP, output)
                        self.assertEqual(before, after)
                    else:
                        self.assertEqual(after['AGENTS.md'], self.agents.encode())
                        self.assertEqual(after['CLAUDE.md'] is not None, config == 'claude')

    def test_i0185_missing_devlyn_engines_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            (work / '.agents/skills/devlyn-ideate').mkdir(parents=True)
            (work / '.agents/skills/devlyn-ideate/SKILL.md').write_text('fixture')
            self.assertFalse(prepare.skills_present(work, 'codex'))

    def test_smoke_forms_sealed_from_preserved_owner_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'output'
            out.mkdir()
            runtime = root / 'runtime.json'
            runtime.write_text(json.dumps({'output': str(out)}))
            initial = dict(self.seal)
            initial['forms'] = {}
            (root / 'instructions.seal.json').write_text(json.dumps(initial))
            for config in ('claude', 'codex'):
                for arm in ('A', 'B'):
                    cell = self.tree(out / f'fixture-{arm}', config, form=arm == 'B')
                    cell.rename(out / f'smoke-{config}-{arm}')
                    cell = out / f'smoke-{config}-{arm}'
                    (cell / 'plan.json').write_text(json.dumps({'name': f'smoke-{config}-{arm}',
                                                                'task': 'SMOKE', 'config': config, 'arm': arm}))
                    (cell / 'instructions.pre.json').write_text(json.dumps(self.evidence(arm)))
            self.assertEqual(instructions.seal_forms(runtime), root / 'instructions.seal.json')
            sealed = json.loads((root / 'instructions.seal.json').read_text())
            self.assertEqual(sealed['forms'], self.seal['forms'])
            self.assertEqual(sealed['qualification']['status'], 'PASS')

    def test_smoke_a_sealed_attachment_fails_qualification(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'output'
            out.mkdir()
            runtime = root / 'runtime.json'
            runtime.write_text(json.dumps({'output': str(out)}))
            initial = dict(self.seal, forms={})
            (root / 'instructions.seal.json').write_text(json.dumps(initial))
            for config in ('claude', 'codex'):
                for arm in ('A', 'B'):
                    cell = self.tree(out / f'{config}-{arm}', config, form=arm == 'B' or config == 'claude')
                    cell.rename(out / f'smoke-{config}-{arm}')
                    cell = out / f'smoke-{config}-{arm}'
                    (cell / 'plan.json').write_text(json.dumps({'name': cell.name, 'task': 'SMOKE', 'config': config, 'arm': arm}))
                    (cell / 'instructions.pre.json').write_text(json.dumps(self.evidence(arm)))
            with self.assertRaisesRegex(ValueError, 'smoke-claude-A.*sealed Claude attachment'):
                instructions.seal_forms(runtime)
            self.assertNotIn('qualification', json.loads((root / 'instructions.seal.json').read_text()))


class DriverControls(unittest.TestCase):
    def instance(self, root):
        runtime = root / 'runtime.json'
        runtime.write_text(json.dumps({'output': str(root / 'output'), 'caps': {'seven_day': 85, 'five_hour': 70},
                                       'account': ['account', 'org']}))
        return driver.Driver(runtime, [['smoke-claude-A', 'SMOKE', 'A', 'claude']])

    def test_each_harm_field_persists_and_clear_requires_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for field, value in [('scope_violations', ['outside']), ('scope_violations', None),
                                 ('teardown', 'DIRTY'), ('identity', {'status': 'UNVERIFIED'})]:
                d = self.instance(root)
                verdict = {'status': 'PRODUCT_INCOMPLETE', 'scope_violations': [], 'teardown': 'CLEAN',
                           'identity': {'status': 'MATCH'}}
                if value is None: del verdict[field]
                else: verdict[field] = value
                (d.output / 'verdict-slot.json').write_text(json.dumps(verdict))
                d.latch_for('slot', verdict)
                self.assertIn('harm_latch', driver.Driver(d.runtime_path, []).state)
                with self.assertRaisesRegex(RuntimeError, 'harm latch'):
                    d.assert_active()
                amendment = root / '2026-10-22-amendment.md'
                with self.assertRaises(ValueError): d.clear_latch(root / 'missing-amendment.md')
                amendment.write_text('dated amendment')
                d.clear_latch(amendment)

    def test_quota_stop_identity_latches_before_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            d = self.instance(Path(temp))
            name = 'smoke-claude-A'
            verdict = {'status': 'STOP', 'reason': 'shared account fault during execution: quota',
                       'identity': {'status': 'MISMATCH'}, 'owner_status': 'EXITED_1'}
            (d.output / f'verdict-{name}.json').write_text(json.dumps(verdict))
            with mock.patch.object(driver.cell, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'harm latch'): d.dispatch(d.slots[0])
                run.assert_not_called()
            self.assertTrue((d.output / f'verdict-{name}.json').exists())
            self.assertFalse((d.output / f'verdict-{name}.stop-1.json').exists())
            self.assertIn('harm_latch', driver.Driver(d.runtime_path, []).state)

    def test_regrade_scope_violation_latches_before_next_dispatch(self):
        with tempfile.TemporaryDirectory() as temp:
            d = self.instance(Path(temp))
            name = d.slots[0][0]
            path = d.output / f'verdict-{name}.json'
            path.write_text(json.dumps({'status': 'STOP', 'reason': 'assessment failed: timeout',
                                        'identity': {'status': 'MATCH'}, 'owner_status': 'EXITED_0'}))
            d.approved_account = ['approved', 'org']
            def regrade(*_args, **_kwargs):
                path.write_text(json.dumps({'status': 'COMPLETE', 'scope_violations': ['outside'],
                                            'teardown': 'CLEAN', 'identity': {'status': 'MATCH'}}))
                return 0
            with mock.patch.object(driver.cell, 'regrade', side_effect=regrade) as regrade_call, \
                    mock.patch.object(driver.cell, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'harm latch'):
                    d.dispatch(d.slots[0])
                run.assert_not_called()
            regrade_call.assert_called_once_with(d.runtime_path, name, expected_account=d.approved_account)
            self.assertIn('harm_latch', driver.Driver(d.runtime_path, []).state)

    def test_clear_latch_acknowledges_only_unchanged_verdict(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            d = self.instance(root)
            name = d.slots[0][0]
            path = d.output / f'verdict-{name}.json'
            bad = {'status': 'COMPLETE', 'scope_violations': ['outside'], 'teardown': 'CLEAN',
                   'identity': {'status': 'MATCH'}}
            path.write_text(json.dumps(bad))
            with self.assertRaisesRegex(RuntimeError, 'harm latch'): d.dispatch(d.slots[0])
            amendment = root / 'amendment.md'
            amendment.write_text('dated amendment')
            d.clear_latch(amendment)
            resumed = driver.Driver(d.runtime_path, d.slots)
            self.assertTrue(resumed.dispatch(d.slots[0]))
            self.assertEqual(resumed.state['cleared_latches'][-1]['amendment'], str(amendment.resolve()))
            self.assertEqual(resumed.state['cleared_latches'][-1]['verdict_sha256'], driver.digest(path))
            path.write_text(json.dumps(bad, sort_keys=True))
            with self.assertRaisesRegex(RuntimeError, 'harm latch'):
                driver.Driver(d.runtime_path, d.slots).dispatch(d.slots[0])

    def test_smoke_deadline_recovered_and_never_advanced(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            d = self.instance(root)
            name = d.slots[0][0]
            run = d.output / name / 'run'
            run.mkdir(parents=True)
            run.joinpath('started.json').write_text(json.dumps({'started_at': 1000000000}))
            (d.output / f'verdict-{name}.json').write_text(json.dumps({
                'status': 'COMPLETE', 'scope_violations': [], 'teardown': 'CLEAN',
                'identity': {'status': 'MATCH'}, 'owner_status': 'EXITED_0'}))
            first = driver.Driver(d.runtime_path, d.slots)
            self.assertEqual(first.state['first_smoke_dispatch'], '2001-09-09T01:46:40+00:00')
            first.state['first_smoke_dispatch'] = '2002-01-01T00:00:00+00:00'
            first.event('fixture')
            self.assertEqual(driver.Driver(d.runtime_path, d.slots).state['first_smoke_dispatch'],
                             '2001-09-09T01:46:40+00:00')

    def test_smoke_launch_persists_before_cell_run(self):
        with tempfile.TemporaryDirectory() as temp:
            d = self.instance(Path(temp))
            def interrupted(*_args, **_kwargs):
                self.assertIn('first_smoke_dispatch', json.loads(d.status_path.read_text()))
                started = d.output / 'smoke-claude-A/run/started.json'
                started.parent.mkdir(parents=True)
                started.write_text(json.dumps({'started_at': 1000000000}))
                raise KeyboardInterrupt
            with mock.patch.object(driver.cell, 'run', side_effect=interrupted):
                with self.assertRaises(KeyboardInterrupt): d.dispatch(d.slots[0])
            self.assertEqual(driver.Driver(d.runtime_path, d.slots).state['first_smoke_dispatch'],
                             '2001-09-09T01:46:40+00:00')

    def test_refused_smoke_does_not_start_deadline_and_later_dispatch_does(self):
        with tempfile.TemporaryDirectory() as temp:
            d = self.instance(Path(temp))
            with mock.patch.object(driver.cell, 'run', return_value=3):
                self.assertFalse(d.dispatch(d.slots[0]))
            for state in (d.state, json.loads(d.status_path.read_text()),
                          driver.Driver(d.runtime_path, d.slots).state):
                self.assertNotIn('first_smoke_dispatch', state)
                self.assertNotIn('registered_caps', state)

            started = driver.time.time()
            def dispatched(*_args, **_kwargs):
                marker = d.output / 'smoke-claude-A/run/started.json'
                marker.parent.mkdir(parents=True)
                marker.write_text(json.dumps({'started_at': started}))
                (d.output / 'verdict-smoke-claude-A.json').write_text(json.dumps({
                    'status': 'COMPLETE', 'owner_status': 'EXITED_0', 'scope_violations': [],
                    'teardown': 'CLEAN', 'identity': {'status': 'MATCH'}}))
                return 0
            with mock.patch.object(driver.cell, 'run', side_effect=dispatched):
                self.assertTrue(d.dispatch(d.slots[0]))
            expected = driver.datetime.datetime.fromtimestamp(started, driver.datetime.timezone.utc).isoformat()
            resumed = driver.Driver(d.runtime_path, d.slots)
            self.assertEqual(resumed.state['first_smoke_dispatch'], expected)
            self.assertEqual(resumed.state['registered_caps'], d.caps)

    def test_measured_dispatch_requires_smoke_qualification(self):
        with tempfile.TemporaryDirectory() as temp:
            d = self.instance(Path(temp))
            row = ['e001-E1-claude-A-r1', 'E1', 'A', 'claude', '1']
            with mock.patch.object(driver.cell, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'SMOKE qualification'):
                    d.dispatch(row)
                run.assert_not_called()

    def test_quota_and_assessor_match_do_not_latch(self):
        with tempfile.TemporaryDirectory() as temp:
            d = self.instance(Path(temp))
            for reason in ('shared account fault during execution: quota', 'assessment failed: timeout'):
                d.latch_for('slot', {'status': 'STOP', 'reason': reason, 'identity': {'status': 'MATCH'},
                                     'owner_status': 'EXITED_0'})
                self.assertNotIn('harm_latch', d.state)

    def test_quota_retry_archives_and_charges_both_attempts(self):
        with tempfile.TemporaryDirectory() as temp:
            d = self.instance(Path(temp))
            (d.output.parent / 'instructions.seal.json').write_text(json.dumps({'qualification': {'status': 'PASS'}}))
            row = ['d001-D3-claude-A-r1', 'D3', 'A', 'claude', '1']
            verdict_path = d.output / f'verdict-{row[0]}.json'
            cell_dir = d.output / row[0]
            calls = 0

            def fake_run(*_args, **_kwargs):
                nonlocal calls
                calls += 1
                cell_dir.mkdir(exist_ok=True)
                if calls == 1:
                    verdict = dict(status='STOP', reason='shared account fault during execution: quota',
                                   identity={'status': 'MATCH'}, owner_status='EXITED_1', owner_seconds=10,
                                   input_tokens=20, output_tokens=3, usage='COMPLETE')
                else:
                    verdict = dict(status='COMPLETE', scope_violations=[], teardown='CLEAN',
                                   identity={'status': 'MATCH'}, owner_status='EXITED_0', owner_seconds=4,
                                   input_tokens=5, output_tokens=2, usage='COMPLETE')
                verdict_path.write_text(json.dumps(verdict))
                return 2 if calls == 1 else 0

            with mock.patch.object(driver.cell, 'run', side_effect=fake_run):
                self.assertFalse(d.dispatch(row))
                self.assertTrue(d.dispatch(row))
            self.assertEqual(calls, 2)
            self.assertTrue((d.output / f'verdict-{row[0]}.stop-1.json').is_file())
            costs = decide.slot_cost(d.output, row[0], json.loads(verdict_path.read_text()))
            self.assertEqual(decide.sums([{'complete': True, 'attempts': costs}])['input'], 25)

    def test_deadline_and_smoke_timestamp(self):
        with tempfile.TemporaryDirectory() as temp:
            d = self.instance(Path(temp))
            d.state['first_smoke_dispatch'] = '2020-01-01T00:00:00+00:00'
            d.state['registered_caps'] = d.caps.copy()
            d.event('fixture')
            with self.assertRaisesRegex(RuntimeError, 'deadline'): driver.Driver(d.runtime_path, []).assert_active()
            d.state.pop('first_smoke_dispatch')
            d.event('fixture')
            with mock.patch.object(driver.cell, 'run', return_value=3):
                self.assertFalse(d.dispatch(d.slots[0]))
            self.assertNotIn('first_smoke_dispatch', driver.Driver(d.runtime_path, []).state)
            smoke = d.output / 'smoke-claude-A'
            (smoke / 'run').mkdir(parents=True)
            started = driver.datetime.datetime(2026, 10, 22, tzinfo=driver.datetime.timezone.utc).timestamp()
            (smoke / 'run/started.json').write_text(json.dumps({'started_at': started}))

            def dispatched(*_args, **_kwargs):
                (d.output / 'verdict-smoke-claude-A.json').write_text(json.dumps({
                    'status': 'COMPLETE', 'owner_status': 'EXITED_0', 'scope_violations': [],
                    'teardown': 'CLEAN', 'identity': {'status': 'MATCH'}}))
                return 0

            with mock.patch.object(driver.cell, 'run', side_effect=dispatched):
                self.assertTrue(d.dispatch(d.slots[0]))
            self.assertEqual(driver.Driver(d.runtime_path, []).state['first_smoke_dispatch'],
                             '2026-10-22T00:00:00+00:00')

    def test_ready_accepts_other_account(self):
        with tempfile.TemporaryDirectory() as temp:
            d = self.instance(Path(temp))
            windows = {name: {'used': 0, 'resets': '2026-10-23T00:00:00+00:00'} for name in driver.WINDOWS}
            snapshot = {'expires': driver.time.time() + 10000, 'account': ['other', 'org'], 'access_token': 'fake'}
            with mock.patch.object(driver, 'credential', return_value=snapshot), \
                    mock.patch.object(driver.cell, 'claude_limits', return_value=windows), \
                    mock.patch.object(d, 'image', return_value=True) as image:
                self.assertTrue(d.ready('claude', 'smoke', 2))
            image.assert_called_once()

    def test_account_switch_after_ready_refuses_dispatch_and_rechecks_new_reserve(self):
        with tempfile.TemporaryDirectory() as temp:
            d = self.instance(Path(temp))
            (d.output.parent / 'instructions.seal.json').write_text('{}')
            first = {'expires': driver.time.time() + 10000, 'account': ['first', 'org'], 'access_token': 'first-token'}
            second = {'expires': driver.time.time() + 10000, 'account': ['second', 'org'], 'access_token': 'second-token'}
            reset = '2026-10-23T00:00:00+00:00'
            def windows(_runtime, token):
                used = 90 if token == 'second-token' else 0
                return {name: {'used': used, 'resets': reset} for name in driver.WINDOWS}

            with mock.patch.object(driver, 'credential', side_effect=[first, second]), \
                    mock.patch.object(driver.cell, 'claude_limits', side_effect=windows) as limits, \
                    mock.patch.object(d, 'image', return_value=True), \
                    mock.patch.object(driver.cell, 'image_identity', return_value=True), \
                    mock.patch.object(driver.cell.shutil, 'disk_usage',
                                      return_value=mock.Mock(free=driver.cell.HEADROOM_BYTES + 1)), \
                    mock.patch.object(driver.cell, 'snapshot_auth', return_value=({'account': second['account']}, None)), \
                    mock.patch.object(driver.cell, 'codex_limits') as codex, \
                    mock.patch.object(driver.cell.prepare, 'prepare') as prepare:
                self.assertTrue(d.ready('claude', 'smoke', 2))
                self.assertEqual(d.approved_account, first['account'])
                self.assertFalse(d.dispatch(d.slots[0]))
                self.assertFalse(d.ready('claude', 'smoke', 2))
            self.assertIsNone(d.approved_account)
            self.assertEqual([call.args[1] for call in limits.call_args_list], ['first-token', 'second-token'])
            self.assertEqual(json.loads((d.output / 'not-dispatched-smoke-claude-A.json').read_text()),
                             {'reason': 'account changed after reserve check'})
            self.assertFalse((d.output / 'verdict-smoke-claude-A.json').exists())
            self.assertNotIn('first_smoke_dispatch', d.state)
            codex.assert_not_called()
            prepare.assert_not_called()
            self.assertEqual(json.loads((d.output / 'driver.log').read_text().splitlines()[-1])['reason'],
                             'Claude window reserve')

    def test_split_wait_tracks_account_and_releases_on_switch(self):
        with tempfile.TemporaryDirectory() as temp:
            d = self.instance(Path(temp))
            reset = '2026-10-23T00:00:00+00:00'
            windows = {name: {'used': 80 if name == 'seven_day' else 40, 'resets': reset}
                       for name in driver.WINDOWS}
            account = ['first', 'org']
            snapshot = lambda _: {'expires': driver.time.time() + 10000,
                                  'account': account, 'access_token': 'fake'}
            with mock.patch.object(driver, 'credential', side_effect=snapshot), \
                    mock.patch.object(driver.cell, 'claude_limits', return_value=windows), \
                    mock.patch.object(driver, 'estimates', return_value={'seven_day': 10, 'five_hour': 25}), \
                    mock.patch.object(driver.Driver, 'image', return_value=True):
                self.assertFalse(d.ready('claude', 'development', 1, slot='second', previous='first'))
                self.assertEqual(d.state['split_wait']['second']['account'], account)
                d = driver.Driver(d.runtime_path, d.slots)
                windows['seven_day']['used'] = 0
                self.assertFalse(d.ready('claude', 'development', 1, slot='second', previous='first'))
                account = ['second', 'org']
                self.assertTrue(d.ready('claude', 'development', 1, slot='second', previous='first'))
            self.assertNotIn('second', d.state['split_wait'])
            events = [json.loads(line) for line in (d.output / 'driver.log').read_text().splitlines()]
            self.assertEqual([e['event'] for e in events].count('split_wait_account_changed'), 1)

    def test_legacy_split_wait_keeps_reset_behavior(self):
        with tempfile.TemporaryDirectory() as temp:
            d = self.instance(Path(temp))
            reset = '2026-10-23T00:00:00+00:00'
            d.state['split_wait']['second'] = {'seven_day': reset}
            windows = {name: {'used': 0, 'resets': reset} for name in driver.WINDOWS}
            snapshot = {'expires': driver.time.time() + 10000,
                        'account': ['other', 'org'], 'access_token': 'fake'}
            with mock.patch.object(driver, 'credential', return_value=snapshot), \
                    mock.patch.object(driver.cell, 'claude_limits', return_value=windows), \
                    mock.patch.object(d, 'image', return_value=True):
                self.assertFalse(d.ready('claude', 'development', 1, slot='second'))
            self.assertEqual(d.state['split_wait']['second'], {'seven_day': reset})

    def test_credential_skips_profile_near_expiry(self):
        raw = json.dumps({'claudeAiOauth': {'expiresAt': (driver.time.time() + 100) * 1000,
                                            'accessToken': 'near-expiry'}})
        with mock.patch.object(driver.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout=raw)), \
                mock.patch.object(driver.cell.urllib.request, 'urlopen') as profile_call:
            snapshot = driver.credential({})
        self.assertIsNone(snapshot['account'])
        profile_call.assert_not_called()

    def test_renewal_accepts_account_change_only_with_advanced_expiry(self):
        for advances in (True, False):
            with self.subTest(advances=advances), tempfile.TemporaryDirectory() as temp:
                d = self.instance(Path(temp))
                expiry = driver.time.time() + 100
                before = {'expires': expiry, 'account': ['before', 'org'], 'access_token': 'old'}
                after = {'expires': expiry + (10000 if advances else 0),
                         'account': ['after', 'org'], 'access_token': 'new'}
                windows = {name: {'used': 0, 'resets': '2026-10-23T00:00:00+00:00'} for name in driver.WINDOWS}
                with mock.patch.object(driver, 'credential', side_effect=[before, after]), \
                        mock.patch.object(driver, 'renewal_command', return_value=['claude', '-p']), \
                        mock.patch.object(driver.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout='help')), \
                        mock.patch.object(driver.cell, 'claude_limits', return_value=windows), \
                        mock.patch.object(d, 'image', return_value=True):
                    self.assertEqual(d.ready('claude', 'smoke', 2), advances)
                events = [json.loads(line) for line in (d.output / 'driver.log').read_text().splitlines()]
                if advances:
                    self.assertIn('renewed', [e['event'] for e in events])
                else:
                    self.assertEqual(events[-1]['reason'], 'renewal did not advance expiry')
                self.assertNotIn('account_changed', [e['event'] for e in events])

    def test_estimates_use_only_same_account_windows(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            windows = lambda used: {name: {'used': used, 'resets': '2026-10-23T00:00:00+00:00'}
                                    for name in driver.WINDOWS}
            for name, change, accounts in [('changed', 90, (['a'], ['b'])),
                                           ('same', 8, (['a'], ['a'])), ('legacy', 7, None)]:
                verdict = dict(status='COMPLETE', config='claude', task='D3',
                               claude_limits_before=windows(0), claude_limits_after=windows(change))
                if accounts:
                    verdict.update(claude_account_before=accounts[0], claude_account_after=accounts[1])
                (out / f'verdict-{name}.json').write_text(json.dumps(verdict))
            self.assertEqual(driver.estimates(out, 'claude', 'development'),
                             {'seven_day': 8, 'five_hour': 8})
            malformed = dict(status='COMPLETE', config='claude', task='D3',
                             claude_limits_before=windows(0), claude_limits_after=windows(1),
                             claude_account_before=['a'])
            (out / 'verdict-malformed.json').write_text(json.dumps(malformed))
            with self.assertRaisesRegex(ValueError, 'incomplete Claude account pair'):
                driver.estimates(out, 'claude', 'development')
            malformed.pop('claude_account_before')
            malformed['claude_account_after'] = ['a']
            (out / 'verdict-malformed.json').write_text(json.dumps(malformed))
            with self.assertRaisesRegex(ValueError, 'incomplete Claude account pair'):
                driver.estimates(out, 'claude', 'development')

    def test_estimates_skip_failed_after_window_read(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            windows = {name: {'used': 80, 'resets': '2026-10-23T00:00:00+00:00'}
                       for name in driver.WINDOWS}
            verdict = dict(status='COMPLETE', config='claude', task='SMOKE',
                           claude_limits_before=windows, claude_account_before=['a'],
                           claude_limits_after_error='HTTP Error 429: Too Many Requests')
            (out / 'verdict-failed-read.json').write_text(json.dumps(verdict))
            self.assertEqual(driver.estimates(out, 'claude', 'development'), driver.FLOORS)

    def test_cap_change_stops_until_amendment(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            d = self.instance(root)
            d.state['first_smoke_dispatch'] = '2026-10-22T00:00:00+00:00'
            d.state['registered_caps'] = d.caps.copy()
            d.event('fixture')
            runtime = json.loads(d.runtime_path.read_text())
            runtime['caps']['seven_day'] = 90
            d.runtime_path.write_text(json.dumps(runtime))
            with self.assertRaisesRegex(RuntimeError, 'caps changed'):
                driver.Driver(d.runtime_path, [])
            amendment = root / '2026-10-22-caps.md'
            amendment.write_text('owner cap amendment')
            driver.Driver(d.runtime_path, [], allow_cap_amendment=True).amend_caps(amendment)
            self.assertEqual(driver.Driver(d.runtime_path, []).caps['seven_day'], 90)

    def test_latch_and_deadline_checked_after_hold(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            d = self.instance(root)

            def hold_then_latch(*_args, **_kwargs):
                verdict = {'status': 'PRODUCT_INCOMPLETE', 'scope_violations': ['outside'],
                           'teardown': 'CLEAN', 'identity': {'status': 'MATCH'}}
                (d.output / 'verdict-prior.json').write_text(json.dumps(verdict))
                d.latch_for('prior', verdict)
                return False

            with mock.patch.object(d, 'ready', side_effect=hold_then_latch), mock.patch.object(driver.time, 'sleep'):
                with self.assertRaisesRegex(RuntimeError, 'harm latch'):
                    d.run()
            self.assertIn('harm_latch', driver.Driver(d.runtime_path, []).state)
            amendment = root / '2026-10-22-clear.md'
            amendment.write_text('clear')
            d.clear_latch(amendment)

            def hold_then_deadline(*_args, **_kwargs):
                d.state['first_smoke_dispatch'] = '2020-01-01T00:00:00+00:00'
                d.state['registered_caps'] = d.caps.copy()
                d.event('fixture')
                return False

            with mock.patch.object(d, 'ready', side_effect=hold_then_deadline), mock.patch.object(driver.time, 'sleep'):
                with self.assertRaisesRegex(RuntimeError, 'deadline'):
                    d.run()


class CellAccounts(unittest.TestCase):
    def test_regrade_legacy_assessor_stop_restores_dispatch_account_for_estimates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'output'
            cell = out / 'legacy'
            cell.mkdir(parents=True)
            runtime_path = root / 'runtime.json'
            runtime_path.write_text(json.dumps({'output': str(out)}))
            venue = {'account': ['dispatch', 'org']}
            (cell / 'seal.json').write_text(json.dumps({'venue': venue}))
            checks = {'product_check_pass': True, 'oracle': {}, 'scope_violations': []}
            (cell / 'checks.json').write_text(json.dumps(checks))
            windows = lambda used: {name: {'used': used, 'resets': '2026-10-23T00:00:00+00:00'}
                                    for name in driver.WINDOWS}
            verdict_path = out / 'verdict-legacy.json'
            verdict_path.write_text(json.dumps({
                'cell': 'legacy', 'task': 'D3', 'config': 'claude', 'status': 'STOP',
                'reason': 'assessment failed: timeout', 'claude_limits_before': windows(0)}))
            with mock.patch.object(run_cell, 'assessment_snapshot', return_value=({'account': venue['account']}, None)) as snapshot, \
                    mock.patch.object(run_cell.assess, 'assess', return_value=[]), \
                    mock.patch.object(run_cell.base, 'unassessed', return_value=[]), \
                    mock.patch.object(run_cell.base, 'verdict', return_value='COMPLETE'), \
                    mock.patch.object(run_cell, 'claude_limits_with_account',
                                      return_value=(windows(40), venue['account'])):
                self.assertEqual(run_cell.regrade(runtime_path, 'legacy', expected_account=venue['account']), 0)
            snapshot.assert_called_once()
            verdict = json.loads(verdict_path.read_text())
            self.assertEqual(verdict['claude_account_before'], venue['account'])
            self.assertEqual(driver.estimates(out, 'claude', 'development'),
                             {'seven_day': 40, 'five_hour': 40})

    def test_regrade_refuses_changed_account_without_replacing_stop(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'output'
            cell = out / 'slot'
            cell.mkdir(parents=True)
            runtime_path = root / 'runtime.json'
            runtime_path.write_text(json.dumps({'output': str(out)}))
            (cell / 'seal.json').write_text(json.dumps({'venue': {'account': ['original', 'org']}}))
            verdict_path = out / 'verdict-slot.json'
            original = {'status': 'STOP', 'reason': 'assessment failed: timeout'}
            verdict_path.write_text(json.dumps(original))
            with mock.patch.object(run_cell, 'assessment_snapshot',
                                   return_value=({'account': ['switched', 'org']}, None)), \
                    mock.patch.object(run_cell.assess, 'assess') as assess, \
                    mock.patch.object(run_cell, 'grade') as grade:
                self.assertEqual(run_cell.regrade(runtime_path, 'slot', expected_account=['approved', 'org']), 3)
            self.assertEqual(json.loads(verdict_path.read_text()), original)
            self.assertFalse(list(out.glob('verdict-slot.stop-*.json')))
            self.assertEqual(json.loads((out / 'not-dispatched-slot.json').read_text()),
                             {'reason': 'account changed after reserve check'})
            assess.assert_not_called()
            grade.assert_not_called()

    def test_preflight_accepts_current_host_account(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            auth = root / 'auth'
            auth.mkdir()
            home = root / 'home'
            (home / '.codex').mkdir(parents=True)
            (home / '.codex/auth.json').write_text('{}')
            runtime = {'output': str(root), 'auth': str(auth), 'account': ['registered', 'org']}
            raw = json.dumps({'claudeAiOauth': {'expiresAt': (run_cell.time.time() + 10000) * 1000,
                                                'accessToken': 'current-token'}})
            profile = {'account': {'uuid': 'current'}, 'organization': {'uuid': 'organization'}}
            windows = {'seven_day': {'used': 10, 'resets': 'tomorrow'}}
            with mock.patch.object(run_cell.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout=raw)), \
                    mock.patch.object(run_cell.Path, 'home', return_value=home), \
                    mock.patch.object(run_cell.shutil, 'disk_usage', return_value=mock.Mock(free=run_cell.HEADROOM_BYTES + 1)), \
                    mock.patch.object(run_cell.urllib.request, 'urlopen',
                                      side_effect=lambda *_args, **_kwargs: io.StringIO(json.dumps(profile))), \
                    mock.patch.object(run_cell, 'claude_limits', return_value=windows) as limits, \
                    mock.patch.object(run_cell, 'codex_limits', return_value=windows):
                venue, blocked = run_cell.preflight(runtime)
                matching, matching_blocked = run_cell.preflight(runtime, expected_account=venue['account'])
                changed, changed_blocked = run_cell.preflight(runtime, expected_account=['other', 'org'])
            self.assertIsNone(blocked)
            self.assertIsNone(matching_blocked)
            self.assertEqual(matching['account'], venue['account'])
            self.assertIsNone(changed)
            self.assertEqual(changed_blocked, 'account changed after reserve check')
            self.assertEqual(limits.call_count, 2)
            self.assertEqual(venue['account'], [run_cell.base.fingerprint('current'),
                                                 run_cell.base.fingerprint('organization')])
            self.assertNotEqual(venue['account'], runtime['account'])
            self.assertEqual((auth / 'claude.json').read_text(), raw)

    def test_assessment_snapshot_accepts_another_account(self):
        with tempfile.TemporaryDirectory() as temp:
            auth = Path(temp)
            runtime = {'auth': str(auth), 'account': ['registered', 'org']}
            raw = json.dumps({'claudeAiOauth': {'expiresAt': (run_cell.time.time() + 2000) * 1000,
                                                'accessToken': 'assessor-token'}})
            profile = {'account': {'uuid': 'assessor'}, 'organization': {'uuid': 'organization'}}
            with mock.patch.object(run_cell.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout=raw)), \
                    mock.patch.object(run_cell.urllib.request, 'urlopen', return_value=io.StringIO(json.dumps(profile))):
                fresh, blocked = run_cell.assessment_snapshot(runtime, {'account': ['dispatch', 'org']})
            self.assertIsNone(blocked)
            self.assertEqual(fresh['account'], [run_cell.base.fingerprint('assessor'),
                                                 run_cell.base.fingerprint('organization')])
            self.assertEqual((auth / 'claude.json').read_text(), raw)

    def test_after_windows_and_account_use_one_keychain_token(self):
        raw = json.dumps({'claudeAiOauth': {'accessToken': 'after-token'}})
        profile = {'account': {'uuid': 'after'}, 'organization': {'uuid': 'organization'}}
        with mock.patch.object(run_cell.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout=raw)) as keychain, \
                mock.patch.object(run_cell.urllib.request, 'urlopen', return_value=io.StringIO(json.dumps(profile))) as profile_call, \
                mock.patch.object(run_cell, 'claude_limits', return_value={'seven_day': {'used': 5}}) as usage:
            limits, account = run_cell.claude_limits_with_account({})
        keychain.assert_called_once()
        self.assertEqual(profile_call.call_args.args[0].get_header('Authorization'), 'Bearer after-token')
        usage.assert_called_once_with({}, 'after-token')
        self.assertEqual(limits['seven_day']['used'], 5)
        self.assertEqual(account, [run_cell.base.fingerprint('after'), run_cell.base.fingerprint('organization')])

    def test_run_records_dispatch_after_and_assessor_accounts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'output'
            out.mkdir()
            runtime = dict(output=str(out), auth=str(root / 'auth'), account=['registered', 'org'],
                           control=str(root / 'control'), models_cache=str(root / 'models'), image='image')
            (root / 'auth').mkdir()
            (root / 'models').write_text('model cache')
            (root / 'control.manifest.json').write_text(json.dumps({'packages': {'B': {'sha256': 'package'}}}))
            (root / 'instructions.seal.json').write_text('{}')
            runtime_path = root / 'runtime.json'
            runtime_path.write_text(json.dumps(runtime))
            venue = dict(account=['dispatch', 'org'], claude_limits={'seven_day': {'used': 1}})
            assessor = dict(account=['assessor', 'org'], token_seconds_left=2000)
            checks = dict(product_check_pass=True, oracle={}, scope_violations=[], adjudication_needed=False)

            def prepared(*_):
                cell = out / 'cell-1'
                (cell / 'home/.claude').mkdir(parents=True)
                for name in ('plan.json', 'prompt.txt', 'baseline.json', 'home/.claude/settings.json',
                             'instructions.pre.json'):
                    path = cell / name
                    path.write_text('{}')
                return cell

            owner = dict(owner_status='EXITED_0', seconds=1, teardown='CLEAN', identity={'status': 'MATCH'})
            usage = dict(completeness='COMPLETE', input_tokens=1, output_tokens=1)
            with mock.patch.object(run_cell, 'image_identity', return_value=True), \
                    mock.patch.object(run_cell, 'preflight', return_value=(venue, None)) as preflight, \
                    mock.patch.object(run_cell, 'control_unchanged', return_value=True), \
                    mock.patch.object(run_cell.prepare, 'prepare', side_effect=prepared), \
                    mock.patch.object(run_cell.subprocess, 'check_output', return_value='commit'), \
                    mock.patch.object(run_cell.cell_run, 'run', return_value=owner), \
                    mock.patch.object(run_cell, 'seal_after_teardown', return_value=('seal', [])), \
                    mock.patch.object(run_cell.usage, 'record', return_value=usage), \
                    mock.patch.object(run_cell.quota, 'classify', return_value={'execution': []}), \
                    mock.patch.object(run_cell.diagnostics, 'record', return_value={}), \
                    mock.patch.object(run_cell, 'harness_unchanged', return_value=True), \
                    mock.patch.object(run_cell.instructions, 'check', return_value=[]), \
                    mock.patch.object(run_cell.locate, 'locate', return_value={}), \
                    mock.patch.object(run_cell.check, 'check', return_value=checks), \
                    mock.patch.object(run_cell, 'assessment_snapshot', return_value=(assessor, None)), \
                    mock.patch.object(run_cell.assess, 'assess', return_value=[]), \
                    mock.patch.object(run_cell, 'claude_limits_with_account', return_value=({'seven_day': {'used': 3}}, ['after', 'org'])):
                self.assertEqual(run_cell.run(runtime_path, 'cell-1', 'SMOKE', 'A', 'claude',
                                              expected_account=venue['account']), 0)
            preflight.assert_called_once_with(runtime, expected_account=venue['account'])
            record = json.loads((out / 'verdict-cell-1.json').read_text())
            self.assertEqual(record['claude_account_before'], venue['account'])
            self.assertEqual(record['claude_account_after'], ['after', 'org'])
            self.assertEqual(record['assessor_account'], assessor['account'])
            self.assertEqual(record['claude_limits_after']['seven_day']['used'], 3)


class Probe(unittest.TestCase):
    def test_absolute_probe_deadline_and_bounded_cleanup(self):
        script = HERE / 'results/witnesses/f-malformed-json.js'
        code = ("const http=require('http'),E=require('events'),p=require(process.argv[1]);"
                "http.request=(opts,cb)=>{const q=new E();q.end=()=>{const r=new E();r.setEncoding=()=>{};"
                "r.statusCode=200;r.headers={};cb(r);const t=setInterval(()=>r.emit('data','x'),100);"
                "q.destroy=()=>{clearInterval(t)}};return q};"
                "p.request(1,'GET','/items').then(()=>process.exit(2),e=>console.log(e.message));")
        done = subprocess.run(['node', '-e', code, str(script.resolve())], capture_output=True,
                              text=True, timeout=7)
        self.assertEqual(done.returncode, 0)
        self.assertIn('deadline', done.stdout)
        cleanup = ("const p=require(process.argv[1]);let forced=false;"
                   "p.closeServer({close(){},closeAllConnections(){forced=true}})"
                   ".then(()=>console.log(forced));")
        done = subprocess.run(['node', '-e', cleanup, str(script.resolve())], capture_output=True,
                              text=True, timeout=3)
        self.assertEqual(done.stdout.strip(), 'true')

    def test_post_class_survives_failing_preservation_get(self):
        script = HERE / 'results/witnesses/f-malformed-json.js'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'server').mkdir()
            (root / 'server/index.js').write_text(
                "const E=require('events'); exports.app={listen(){const s=new E();"
                "s.address=()=>({port:1});s.close=cb=>cb();s.closeAllConnections=()=>{};"
                "process.nextTick(()=>s.emit('listening'));return s}};")
            for mode in ('baseline_error', 'followup_error', 'followup_500'):
                code = ("const http=require('http'),E=require('events');let calls=0;const mode='" + mode + "';"
                        "http.request=(opts,cb)=>{const q=new E();q.end=()=>{calls++;"
                        "if((mode==='baseline_error'&&calls===1)||(mode==='followup_error'&&calls===3))"
                        "{process.nextTick(()=>q.emit('error',new Error('get failed')));return;}"
                        "const r=new E();r.setEncoding=()=>{};"
                        "r.statusCode=opts.method==='POST'?400:(mode==='followup_500'&&calls===3?500:200);"
                        "r.headers={'content-type':'application/json'};process.nextTick(()=>{cb(r);"
                        "r.emit('data',opts.method==='POST'?'{\"error\":\"bad\"}':'[]');r.emit('end')})};"
                        "q.destroy=e=>q.emit('error',e);return q};"
                        "process.argv[2]='F10';require(process.argv[1]).main().then(x=>console.log(JSON.stringify(x)));")
                done = subprocess.run(['node', '-e', code, str(script.resolve())], cwd=root,
                                      capture_output=True, text=True, timeout=9)
                self.assertEqual(done.returncode, 0, (mode, done.stderr))
                result = json.loads(done.stdout)
                self.assertEqual(result['class'], 'json_error_400', mode)
                self.assertIsNone(result['store_preserved'], mode)

    def test_truncated_followup_get_preserves_post_class_within_deadline(self):
        script = HERE / 'results/witnesses/f-malformed-json.js'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'server').mkdir()
            (root / 'server/index.js').write_text(
                "const E=require('events'); exports.app={listen(){const s=new E();"
                "s.address=()=>({port:1});s.close=cb=>cb();s.closeAllConnections=()=>{};"
                "process.nextTick(()=>s.emit('listening'));return s}};")
            code = ("const http=require('http'),E=require('events');let calls=0;"
                    "const mode=process.argv[2];"
                    "http.request=(opts,cb)=>{const q=new E();q.end=()=>{calls++;"
                    "const r=new E();r.setEncoding=()=>{};r.statusCode=opts.method==='POST'?400:200;"
                    "r.headers={'content-type':'application/json'};process.nextTick(()=>{cb(r);"
                    "r.emit('data',opts.method==='POST'?'{\"error\":\"bad\"}':'[]');"
                    "if(calls===3){if(mode==='error')r.emit('error',new Error('truncated'));"
                    "else r.emit(mode)}else r.emit('end')})};"
                    "q.destroy=()=>{};return q};"
                    "process.argv[2]='F10';require(process.argv[1]).main()"
                    ".then(x=>console.log(JSON.stringify(x)));")
            for mode in ('error', 'aborted', 'close'):
                done = subprocess.run(['node', '-e', code, str(script.resolve()), mode], cwd=root,
                                      capture_output=True, text=True, timeout=3)
                self.assertEqual(done.returncode, 0, (mode, done.stderr))
                result = json.loads(done.stdout)
                self.assertEqual(result['class'], 'json_error_400', mode)
                self.assertIsNone(result['store_preserved'], mode)

    def test_judge_timeout_records_unassessable_and_continues(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'output'
            out.mkdir()
            runtime = root / 'runtime.json'
            runtime.write_text(json.dumps({'output': str(out), 'image': 'devlyn-0256'}))
            names = ['c001-F10-claude-A-r1', 'c002-F10-claude-B-r1']
            for name in names:
                (out / name / 'snapshot').mkdir(parents=True)
                (out / f'verdict-{name}.json').write_text('{"status":"COMPLETE"}')
            with mock.patch.dict(os.environ, {'NX01_0257_RUNTIME': str(runtime)}):
                judge = load('judge_timeout', HERE / 'results/operator/judge.py')
            timeout = subprocess.TimeoutExpired(['docker', 'run'], 60)
            success = subprocess.CompletedProcess([], 0, stdout='{"class":"html_400","store_preserved":true}\n', stderr='')
            with mock.patch.object(judge.subprocess, 'run', side_effect=[timeout,
                    subprocess.CompletedProcess([], 0, stdout='', stderr=''), success]) as runner:
                result = judge.probe(names)
            self.assertEqual(result[names[0]]['class'], 'unassessable')
            self.assertIn('timed out', result[names[0]]['error'])
            self.assertEqual(result[names[1]]['class'], 'html_400')
            self.assertIn('rm', runner.call_args_list[1].args[0])

    def test_judge_cleanup_failure_records_cell_and_continues(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'output'
            out.mkdir()
            runtime = root / 'runtime.json'
            runtime.write_text(json.dumps({'output': str(out), 'image': 'devlyn-0256'}))
            names = ['c001-F10-claude-A-r1', 'c002-F10-claude-B-r1']
            for name in names:
                (out / name / 'snapshot').mkdir(parents=True)
                (out / f'verdict-{name}.json').write_text('{"status":"COMPLETE"}')
            with mock.patch.dict(os.environ, {'NX01_0257_RUNTIME': str(runtime)}):
                judge = load('judge_cleanup', HERE / 'results/operator/judge.py')
            timeout = subprocess.TimeoutExpired(['docker', 'run'], 60)
            rm_failed = subprocess.CalledProcessError(1, ['docker', 'rm', '-f'])
            success = subprocess.CompletedProcess([], 0, stdout='{"class":"html_400","store_preserved":true}\n', stderr='')
            original_rmtree = judge.shutil.rmtree
            calls = 0
            def fail_first_cleanup(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise OSError('bind mount still busy')
                return original_rmtree(*args, **kwargs)
            with mock.patch.object(judge.subprocess, 'run', side_effect=[timeout, rm_failed, success]), \
                 mock.patch.object(judge.shutil, 'rmtree', side_effect=fail_first_cleanup):
                result = judge.probe(names)
            self.assertEqual(result[names[0]]['class'], 'unassessable')
            self.assertIn('container cleanup failed', result[names[0]]['error'])
            self.assertIn('bind mount still busy', result[names[0]]['error'])
            self.assertEqual(result[names[1]]['class'], 'html_400')
            self.assertEqual(json.loads((out / 'probes.json').read_text()), result)

    def test_classification_without_network(self):
        script = HERE / 'results/witnesses/f-malformed-json.js'
        code = ("const c=require(process.argv[1]).classify;"
                "console.log(JSON.stringify([c({status:400,type:'application/json',body:'{\"error\":\"bad\"}'}),"
                "c({status:400,type:'text/html',body:'<!DOCTYPE html>'}),"
                "c({status:500,type:'text/plain',body:'oops'})]));")
        done = subprocess.run(['node', '-e', code, str(script.resolve())],
                              capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(done.stdout), ['json_error_400', 'html_400', 'other'])

    def test_judge_fake_runner_writes_separate_probe_results(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'output'
            out.mkdir()
            runtime = root / 'runtime.json'
            runtime.write_text(json.dumps({'output': str(out), 'image': 'devlyn-0256'}))
            names = ['c001-F10-claude-A-r1', 'c002-F10-claude-B-r1']
            for name in names:
                (out / name / 'snapshot').mkdir(parents=True)
                (out / f'verdict-{name}.json').write_text('{"status":"COMPLETE"}')
            with mock.patch.dict(os.environ, {'NX01_0257_RUNTIME': str(runtime)}):
                judge = load('judge', HERE / 'results/operator/judge.py')
            outputs = [json.dumps({'class': 'json_error_400', 'store_preserved': True, 'status': 400}),
                       json.dumps({'class': 'html_400', 'store_preserved': True, 'status': 400})]
            with mock.patch.object(judge.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 0, stdout=x, stderr='') for x in outputs]):
                result = judge.probe(names)
            self.assertEqual([result[n]['class'] for n in names], ['json_error_400', 'html_400'])
            self.assertEqual(json.loads((out / 'probes.json').read_text()), result)
            source = root / 'source-output'
            source.mkdir()
            old_names = ['c01-F10-claude-A-r1', 'c02-F10-claude-B-r1']
            for name in old_names:
                (source / name / 'snapshot').mkdir(parents=True)
                (source / f'verdict-{name}.json').write_text('{"status":"COMPLETE"}')
            source_runtime = root / 'source-runtime.json'
            source_runtime.write_text(json.dumps({'output': str(source), 'image': 'devlyn-0256'}))
            with mock.patch.object(judge.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 0, stdout=x, stderr='') for x in outputs]):
                qualified = judge.probe(old_names, source_runtime)
            self.assertEqual([qualified[n]['class'] for n in old_names], ['json_error_400', 'html_400'])
            self.assertFalse((source / 'probes.json').exists())


if __name__ == '__main__':
    unittest.main()
