"""0266 decision and power figures against hand-computed cases: every worked example of the design's re-check files
(design-recheck2.md "Consequences", design-recheck3.md "Checked against"), the screen's mixed-assignment case, each G3
case, each verdict word, a NOT_FINISHED for each kind of unknown, the screen rules, the predictions, the token, and the
DESIGN figures power.py recomputes. Run: python3 -m pytest -q autoresearch/experiments/0266/test_decide.py"""
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('test0266_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


decide, power = load('decide'), load('power')
C32 = math.comb(32, 16)


def expected_call(claude, codex, valid):
    if claude is True and codex is True and valid:
        return 'true'
    return 'false' if claude is False and codex is False else 'disputed'


class Run:
    """An output folder of the frozen schedule where every slot is final and COMPLETE, every probe shows the event
    with the store kept and, on F11, the 2^53 batch allowed, every witness does not reproduce and every grading file is
    present and clean, until a test changes it."""

    def __init__(self, root, cells=None, selected='K3'):
        self.out, self.cells = Path(root), cells or decide.schedule()
        self.selected = selected  # the GO screen decision's candidate, the package of the registered C
        self.witnesses = {w: {} for task in decide.TASKS for w in decide.WITNESSES[task]}
        self.probes, self.harm, self.pairs, self.recheck, self.no_report = {}, {}, [], {}, []
        for name, task, arm, config, *_ in self.cells:
            self.slot(name)
            for witness in decide.WITNESSES[task]:
                self.witness(name, witness, 0)
            if task in ('F10', 'F11'):
                self.probe(name)
            self.harm[name] = dict(harm=False, findings=[], not_checked=[], attempts=[name])

    def name(self, config, task, arm, rep):
        return next(n for n, t, a, c, r in self.cells if (c, t, a, int(r)) == (config, task, arm, rep))

    def identity(self, name):
        """What run_cell.py records for the slot: its task, engine, arm and package."""
        _, task, column, config, _ = next(row for row in self.cells if row[0] == name)
        return decide.slot_identity(task, column, config, self.selected)

    def names(self, config, task, arm):
        return [n for n, t, a, c, r in self.cells if (c, t, a) == (config, task, arm)]

    def slot(self, name, fail=(), scope=(), assessors=(True, True), severe=0, owner='EXITED_0', seconds=100.0,
             tokens=(1000, 100), usage='COMPLETE'):
        task = name.split('-')[1]
        rows = decide.ENDPOINTS[decide.PANEL[task]][task]['rows']
        public = [dict(exit_code=1 if key in fail else 0, timeout=False) for key in rows if key.startswith('public:')]
        oracle = [dict(id=key, status='FAIL' if key in fail else 'PASS')
                  for key in rows if not key.startswith('public:')]
        passed = not fail and not scope
        assessments = [dict(route=dict(engine=engine), complete=done, severe=severe if engine == 'codex' else 0,
                            severe_findings=[{}] * (severe if engine == 'codex' else 0))
                       for engine, done in zip(('claude', 'codex'), assessors)]
        verdict = dict(cell=name, **self.identity(name), owner_ran=True, owner_status=owner, owner_seconds=seconds, input_tokens=tokens[0],
                       output_tokens=tokens[1], usage=usage, teardown='CLEAN', product_check_pass=passed, oracle=oracle,
                       scope_violations=list(scope), assessments=assessments,
                       status='COMPLETE' if passed and all(assessors) and not severe else 'PRODUCT_INCOMPLETE')
        (self.out / name).mkdir(exist_ok=True)
        (self.out / name / 'checks.json').write_text(json.dumps(dict(
            public=public, oracle=oracle, product_check_pass=passed, scope_violations=list(scope))))
        (self.out / f'verdict-{name}.json').write_text(json.dumps(verdict))

    def stop(self, name, reason, number=None, **fields):
        """A STOP: archived as .stop-<number>, or the slot's last attempt when number is None (0265's helper)."""
        ran = fields.get('owner_ran', not reason.startswith(decide.LAUNCH_FAULT))
        kept = dict(scope_violations=[]) if ran and number else {}
        record = dict(cell=name, **self.identity(name), status='STOP', reason=reason, owner_ran=ran,
                      owner_status='EXITED_0',
                      owner_seconds=50.0, input_tokens=10, output_tokens=1, usage='COMPLETE', teardown='CLEAN'
                      ) | kept | fields
        suffix = f'.stop-{number}' if number else ''
        if number and not reason.startswith(decide.REGRADE) and name + suffix not in self.harm[name]['attempts']:
            self.harm[name]['attempts'].append(name + suffix)
        if kept:
            for witness in decide.WITNESSES[name.split('-')[1]]:
                self.witness(name + suffix, witness, 0)
        (self.out / f'verdict-{name}{suffix}.json').write_text(json.dumps(record))

    def witness(self, name, witness, first, second=None, retried=True):
        """judge.py's record; an unresolved pair carries the first pair of its retry unless retried is False."""
        exits = [first, first if second is None else second]
        result = (('not_applicable' if exits[0] == 3 else exits[0] == 1)
                  if exits[0] == exits[1] and exits[0] in (0, 1, 3) else 'unresolved')
        self.witnesses[witness][name] = dict(attempts=[dict(exit=e) for e in exits], result=result, witness_sha256='x',
                                             **({'first_attempts': [dict(exit=2)] * 2}
                                                if result == 'unresolved' and retried else {}))

    def probe(self, name, kind='json_error_400', kept=True, restricts=False, attempts=None):
        """judge.py's record: the final attempt, after one retry when the first was unknown (attempts=2)."""
        final = {'class': kind, 'store_preserved': None if kind == 'unassessable' else kept}
        if name.split('-')[1] == 'F11' and kind != 'unassessable':
            final['large_qty'] = dict(status={True: 400, False: 201, None: None}[restricts], restricts=restricts)
        unknown = kind == 'unassessable' or final['store_preserved'] is None or (
            name.split('-')[1] == 'F11' and final.get('large_qty', {}).get('restricts') is None)
        self.probes[name] = dict(final, attempts=[final] * (attempts or (2 if unknown else 1)))

    def events(self, arm, known, nulls=0, config='claude'):
        """`known` slots of the arm with the event, then `nulls` json_error_400 with store_preserved null, the rest
        html_400."""
        for index, name in enumerate(self.names(config, 'F10', arm)):
            if index < known:
                self.probe(name)
            elif index < known + nulls:
                self.probe(name, kept=None)
            else:
                self.probe(name, 'html_400')

    def pair(self, name, witness, claude, codex, valid=True, witness_result='true', attempt='final'):
        if attempt == 'final':
            self.witness(name, witness, 1, 1 if witness_result == 'true' else 2)
        judges = dict(claude=dict(false_claim=claude, quote='q', valid=valid),
                      codex=dict(false_claim=codex, quote='q', valid=True))
        self.pairs.append(dict(cell=name, attempt=attempt, witness=witness, witness_result=witness_result,
                               judges=judges, call=expected_call(claude, codex, valid)))

    def tokens(self, config, arm, total, incomplete=None):
        """Every slot of the engine and arm at 0 input tokens except one at `total` (usage COMPLETE) and, when given,
        one more holding an incomplete usage record at `incomplete`."""
        for index, name in enumerate(n for n, t, a, c, r in self.cells if (c, a) == (config, arm)):
            value, usage = (total, 'COMPLETE') if index == 0 else (incomplete, 'PARTIAL') if (
                index == 1 and incomplete is not None) else (0, 'COMPLETE')
            self.slot(name, tokens=(value, 0), usage=usage)

    def evaluate(self, skip=(), screen='go'):
        documents = {'witnesses.json': self.witnesses, 'probes.json': self.probes,
                     'timing-recheck.json': dict(schema=1, cells=self.recheck),
                     'harm.json': dict(schema=1, cells=self.harm),
                     'false-completion.json': dict(schema=1, sha256=dict(audit_rule='a', prompt='p', descriptions='d'),
                                                   pairs=self.pairs, no_report=self.no_report)}
        for file, document in documents.items():
            path = self.out / file
            if file in skip:
                path.unlink(missing_ok=True)
            else:
                path.write_text(json.dumps(document))
        return decide.evaluate(self.out, self.cells, dict(decision='GO', candidate=self.selected)
                               if screen == 'go' else screen)


class Case(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.run = Run(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def effect(self):
        """R1 reads EFFECT: C 9 of 16 events v B 2 (p = 7,012,653 / 601,080,390 = .0116667)."""
        self.run.events('C', 9)
        self.run.events('B', 2)


class Statistics(unittest.TestCase):
    def test_fisher_hand_cases(self):
        # one-sided P(C >= c | c + b), 16 slots per arm: 8 v 2 rejects (p = .027), 7 v 2 does not (p = .057)
        self.assertAlmostEqual(decide.fisher(2, 8, 16, 'upper'),
                               sum(math.comb(10, x) * math.comb(22, 16 - x) for x in range(8, 11)) / C32, places=12)
        self.assertAlmostEqual(decide.fisher(2, 8, 16, 'upper'), .0269, places=4)
        self.assertAlmostEqual(decide.fisher(2, 7, 16, 'upper'), .0567, places=4)
        self.assertTrue(decide.effect(2, 8, 16))
        self.assertFalse(decide.effect(2, 7, 16))
        self.assertEqual(decide.fisher(16, 16, 16, 'upper'), 1.0)

    def test_guard_rules_at_their_margins(self):
        self.assertFalse(decide.completion_fails(8, 6, 8))  # m = 2 at 8
        self.assertTrue(decide.completion_fails(8, 5, 8))
        self.assertFalse(decide.completion_fails(16, 13, 16))  # m = 3 at 16
        self.assertTrue(decide.completion_fails(16, 12, 16))
        self.assertFalse(decide.false_completions_fail(1, 3))
        self.assertTrue(decide.false_completions_fail(1, 4))
        self.assertFalse(decide.restriction_fails(4, 6, 16))  # more than 2 at 16
        self.assertTrue(decide.restriction_fails(4, 7, 16))
        self.assertFalse(decide.restriction_fails(4, 5, 8))  # more than 1 at 8
        self.assertTrue(decide.restriction_fails(4, 6, 8))
        self.assertEqual([decide.screened_in(k) for k in range(5)], [False, False, True, True, True])

    def test_call_rule(self):
        self.assertEqual(decide.call(dict(claude=dict(false_claim=True, valid=True),
                                          codex=dict(false_claim=True, valid=True))), 'true')
        self.assertEqual(decide.call(dict(claude=dict(false_claim=True, valid=False),
                                          codex=dict(false_claim=True, valid=True))), 'disputed')
        self.assertEqual(decide.call(dict(claude=dict(false_claim=False), codex=dict(false_claim=False))), 'false')


class Event(unittest.TestCase):
    def test_the_event_and_its_unknowns(self):
        # DESIGN "The event"
        for kind, kept, expected in (('json_error_400', True, True), ('json_error_400', False, False),
                                     ('json_error_400', None, None), ('html_400', True, False),
                                     ('html_400', None, False), ('other', True, False), ('other', False, False),
                                     ('unassessable', None, None)):
            with self.subTest(kind=kind, kept=kept):
                self.assertIs(decide.event({'class': kind, 'store_preserved': kept}), expected)

    def test_store_and_restriction_readers(self):
        self.assertIs(decide.store_changed({'class': 'html_400', 'store_preserved': False}), True)
        self.assertIs(decide.store_changed({'class': 'html_400', 'store_preserved': True}), False)
        self.assertIsNone(decide.store_changed({'class': 'html_400', 'store_preserved': None}))
        self.assertIsNone(decide.store_changed({'class': 'unassessable', 'store_preserved': None}))
        self.assertIs(decide.restricts({'large_qty': dict(status=400, restricts=True)}), True)
        self.assertIs(decide.restricts({'large_qty': dict(status=201, restricts=False)}), False)
        self.assertIsNone(decide.restricts({'large_qty': dict(status=None, restricts=None)}))
        self.assertIsNone(decide.restricts({'class': 'unassessable'}))

    def test_a_first_unknown_attempt_waits_for_its_retry(self):
        unknown = {'class': 'json_error_400', 'store_preserved': None}
        self.assertIsNone(decide.probe_record({'x-F10': {'attempts': [unknown]}}, 'x-F10', 'F10'))
        self.assertEqual(decide.probe_record({'x-F10': {'attempts': [unknown, unknown]}}, 'x-F10', 'F10'), unknown)
        no_answer = {'class': 'json_error_400', 'store_preserved': True, 'large_qty': dict(status=None, restricts=None)}
        self.assertIsNone(decide.probe_record({'x-F11': {'attempts': [no_answer]}}, 'x-F11', 'F11'))
        self.assertEqual(decide.probe_record({'x-F10': {'attempts': [no_answer]}}, 'x-F10', 'F10'), no_answer)
        self.assertIsNone(decide.probe_record({}, 'x-F10', 'F10'))

    def test_every_assignment_is_enumerated(self):
        # A rule that is not monotone in the counts: only the middle count holds. The corners would both read False.
        found = decide.outcomes(dict(C=dict(known=1, unknown=2, n=4)), lambda c: c['C'] == 2)
        self.assertEqual(found, {True, False})


class Recheck(Case):
    """design-recheck2.md "Consequences" and design-recheck3.md "Checked against", as written there."""

    def test_c_7_preserved_and_6_nulls_against_b_2(self):
        # 7 v 2 is not rejected and 13 v 2 is, so R1 is NOT_FINISHED.
        self.run.events('B', 2)
        self.run.events('C', 7, nulls=6)
        r1 = self.run.evaluate()['R1']
        self.assertEqual(r1['reading'], 'NOT_FINISHED')
        self.assertEqual(set(r1['outcomes']), {'EFFECT', 'NO_DETECTED_EFFECT'})
        self.assertEqual(r1['missing'], [])
        self.assertFalse(decide.effect(2, 7, 16))
        self.assertTrue(decide.effect(2, 13, 16))

    def test_c_9_preserved_and_one_null(self):
        # R1 is EFFECT under every assignment; G2 holds under "preserved" and fails under "not preserved", so G2 and
        # the verdict are NOT_FINISHED.
        self.run.events('B', 2)
        self.run.events('C', 9)
        null = self.run.names('claude', 'F10', 'C')[15]
        self.run.probe(null, 'html_400', kept=None)
        result = self.run.evaluate()
        self.assertEqual(result['R1']['reading'], 'EFFECT')
        g2 = result['guards']['G2']
        self.assertEqual((g2['reading'], g2['missing']), ('NOT_FINISHED', []))
        self.assertEqual(g2['engines']['claude']['parts']['no C store changed after a rejected request'], [False, True])
        self.assertEqual(result['verdict']['verdict'], 'NOT_FINISHED')
        self.assertEqual(result['verdict']['undecided'], ['G2'])
        # The same null as json_error_400 with store_preserved null: unknown for R1 too (9 or 10 v 2: EFFECT both).
        self.run.probe(null, kept=None)
        result = self.run.evaluate()
        self.assertEqual((result['R1']['reading'], result['guards']['G2']['reading']), ('EFFECT', 'NOT_FINISHED'))

    def test_a_null_in_b_never_helps_c(self):
        # B's null counts as an event in one assignment: 8 v 2 rejects, 8 v 3 does not.
        self.run.events('C', 8)
        self.run.events('B', 2, nulls=1)
        r1 = self.run.evaluate()['R1']
        self.assertEqual(r1['reading'], 'NOT_FINISHED')
        self.assertFalse(decide.effect(3, 8, 16))
        self.assertEqual(r1['corners']['unknowns against C'], dict(B=3, C=8, p=decide.fisher(3, 8, 16, 'upper')))

    def test_screen_mixed_assignment(self):
        # Grok's round-3 case (design-recheck3.md): K1 has 2 preserved events and one null, K2 has 1 and two nulls, all
        # 2 of 2 on F11. One assignment selects K1 (K1 2 v K2 1) and another K2 (K1 2 v K2 3; or 3 v 3, where the tie
        # goes to the shorter K2), so the screen is undecided: no registered run.
        screen = Screen(self.temp.name)
        screen.events('K1', 2, nulls=1)
        screen.events('K2', 1, nulls=2)
        screen.events('K3', 0)
        record, found, missing = screen.reading()
        self.assertEqual(missing, [])
        self.assertIn(('K1', 'GO'), found)
        self.assertIn(('K2', 'GO'), found)
        self.assertEqual(decide.screen_rule({('K1', 'events'): 2, ('K2', 'events'): 3, ('K3', 'events'): 0,
                                             **{(k, 'f11'): 2 for k in decide.CANDIDATES}}), ('K2', 'GO'))
        self.assertEqual(decide.screen_rule({('K1', 'events'): 2, ('K2', 'events'): 1, ('K3', 'events'): 0,
                                             **{(k, 'f11'): 2 for k in decide.CANDIDATES}}), ('K1', 'GO'))
        self.assertEqual(record['assignments_enumerated'], 2 * 3)
        self.assertEqual(len(record['unknowns']), 3)


class G3(Case):
    """design-recheck3.md Change 2, each case as written there, and its FAILS."""

    def g3(self):
        return self.run.evaluate()['guards']['G3']['engines']['claude']

    def test_c_incomplete_cannot_hold(self):
        # B 10,000,000 complete; C 10,000,000 complete plus one incomplete record at 100,000: 1.01, NOT_FINISHED.
        self.run.tokens('claude', 'B', 10_000_000)
        self.run.tokens('claude', 'C', 10_000_000, incomplete=100_000)
        g3 = self.g3()
        self.assertEqual((g3['reading'], round(g3['ratio'], 2)), ('NOT_FINISHED', 1.01))
        self.assertEqual(self.run.evaluate()['verdict']['verdict'], 'NOT_FINISHED')

    def test_b_incomplete_only_lowers_the_ratio(self):
        # C 10,500,000 complete; B's recorded sum 9,900,000 with one incomplete record: at most 1.06, HOLDS.
        self.run.tokens('claude', 'C', 10_500_000)
        self.run.tokens('claude', 'B', 9_800_000, incomplete=100_000)
        g3 = self.g3()
        self.assertEqual((g3['reading'], round(g3['ratio'], 2), g3['input']['B']['recorded']),
                         ('HOLDS', 1.06, 9_900_000))

    def test_b_incomplete_cannot_fail(self):
        # C 11,200,000 complete; B's recorded sum 10,000,000 with one incomplete record: 1.12 recorded, NOT_FINISHED.
        self.run.tokens('claude', 'C', 11_200_000)
        self.run.tokens('claude', 'B', 9_900_000, incomplete=100_000)
        self.assertEqual(self.g3()['reading'], 'NOT_FINISHED')

    def test_both_incomplete(self):
        self.run.tokens('claude', 'C', 10_000_000, incomplete=1)
        self.run.tokens('claude', 'B', 10_000_000, incomplete=1)
        self.assertEqual(self.g3()['reading'], 'NOT_FINISHED')

    def test_fails_when_b_is_complete(self):
        # B complete: C's recorded sum above 1.10 times B's fails, complete or not (its true sum is at least that).
        self.run.tokens('claude', 'B', 10_000_000)
        for incomplete in (None, 1):
            self.run.tokens('claude', 'C', 11_100_000, incomplete=incomplete)
            self.assertEqual(self.g3()['reading'], 'FAILS')
        self.run.tokens('claude', 'C', 11_000_000)  # exactly 1.10 holds
        self.assertEqual(self.g3()['reading'], 'HOLDS')
        result = self.run.evaluate()
        self.assertEqual(result['guards']['G3']['covers'], 'input tokens only')


class Verdicts(Case):
    def test_ship_candidate(self):
        self.effect()
        result = self.run.evaluate()
        self.assertEqual(result['verdict'], dict(verdict='SHIP_CANDIDATE', failing=[]))
        self.assertEqual({name: guard['reading'] for name, guard in result['guards'].items()},
                         dict.fromkeys(('G1', 'G2', 'G3', 'G4', 'G5'), 'HOLDS'))
        p = sum(math.comb(11, x) * math.comb(21, 16 - x) for x in range(9, 12)) / C32  # by hand: 7012653 / C32
        self.assertEqual(round(p, 7), .0116667)
        self.assertEqual(result['token'], f'0266:SHIP_CANDIDATE;R1:EFFECT(C9/16vB2/16,p={p:.6g}),G1:HOLDS,G2:HOLDS,'
                                          'G3:HOLDS,G4:HOLDS,G5:HOLDS')

    def test_effect_with_regression(self):
        self.effect()
        for name in self.run.names('claude', 'D3', 'C')[:3]:  # COMPLETE 5 v 8: below 8 - 2
            self.run.slot(name, assessors=(True, False))
        for name in self.run.names('codex', 'B5', 'C')[:2]:  # check-complete 6 of 8
            self.run.slot(name, fail=('legacy-removed',))
        result = self.run.evaluate()
        self.assertEqual(result['verdict']['verdict'], 'EFFECT_WITH_REGRESSION[G1,G4]')
        g1 = result['guards']['G1']
        self.assertEqual(g1['failing'], ['claude D3'])
        self.assertEqual((g1['cells']['claude D3']['complete'], g1['cells']['claude D3']['chance']),
                         (dict(B=8, C=5), .105))
        self.assertEqual(result['guards']['G4']['check_complete'], '6/8')

    def test_no_detected_effect(self):
        self.run.events('C', 7)
        self.run.events('B', 2)
        result = self.run.evaluate()
        self.assertEqual((result['R1']['reading'], result['verdict']['verdict']),
                         ('NO_DETECTED_EFFECT', 'NO_DETECTED_EFFECT'))
        for name in self.run.names('codex', 'F11', 'C')[:2]:  # restricting 2 v 0 at 8: more than 1
            self.run.probe(name, restricts=True)
        result = self.run.evaluate()
        self.assertEqual(result['verdict']['verdict'], 'NO_DETECTED_EFFECT[G5]')
        self.assertEqual(result['guards']['G5']['engines']['codex']['chance'], decide.CHANCE['G5']['codex'])
        self.assertEqual(result['reported']['restricting_f11_trees'],
                         dict.fromkeys(self.run.names('codex', 'F11', 'C')[:2], 'restricts'))

    def test_not_finished_lists_what_is_missing_and_what_fails(self):
        self.effect()
        name = self.run.name('codex', 'D3', 'B', 3)
        (self.run.out / f'verdict-{name}.json').unlink()
        for slot in self.run.names('claude', 'B5', 'C')[:3]:
            self.run.slot(slot, fail=('legacy-removed',))
        verdict = self.run.evaluate()['verdict']
        self.assertEqual(verdict['verdict'], 'NOT_FINISHED')
        self.assertEqual(verdict['slots_without_final_verdict'], [name])
        self.assertEqual(verdict['failing'], [])  # G1 cannot be read while a slot is missing
        self.assertIn('G1', verdict['undecided'])


class Unknowns(Case):
    """A NOT_FINISHED for each kind of unknown of DESIGN "Unknowns", each where it flips its reading."""

    def test_unassessable_probe(self):
        # C 7 v B 2 plus one unassessable C probe: 7 v 2 no, 8 v 2 yes.
        self.run.events('C', 7)
        self.run.events('B', 2)
        self.run.probe(self.run.names('claude', 'F10', 'C')[15], 'unassessable')
        result = self.run.evaluate()
        self.assertEqual(result['R1']['reading'], 'NOT_FINISHED')
        self.assertEqual(result['reported']['groups']['claude']['F10']['C']['probe']['unassessable'], 1)
        self.assertIn('R1:NOT_FINISHED(C7+1?/16vB2/16,p=0.0269011..0.0566926)', result['token'])

    def test_json_error_with_a_null_store(self):
        self.run.events('C', 7, nulls=1)
        self.run.events('B', 2)
        self.assertEqual(self.run.evaluate()['R1']['reading'], 'NOT_FINISHED')

    def test_large_qty_without_a_response(self):
        # codex at 8: restricting C 1 v B 0 holds, C 2 v 0 fails.
        names = self.run.names('codex', 'F11', 'C')
        self.run.probe(names[0], restricts=True)
        self.run.probe(names[1], restricts=None)
        g5 = self.run.evaluate()['guards']['G5']
        self.assertEqual((g5['reading'], g5['engines']['codex']['reading']), ('NOT_FINISHED', 'NOT_FINISHED'))
        self.assertEqual(g5['engines']['codex']['restricting']['C'], dict(known=1, unknown=1, n=8))

    def test_unresolved_write_failure_witness(self):
        # claude: misreported trees C 0 + 1 unresolved v B 0: C <= B holds at 0 and fails at 1.
        name = self.run.names('claude', 'F10', 'C')[0]
        self.run.witness(name, 'f10-write-failure-misreported', 1, 2)
        g2 = self.run.evaluate()['guards']['G2']
        self.assertEqual((g2['reading'], g2['missing']), ('NOT_FINISHED', []))
        self.assertEqual(g2['engines']['claude']['misreported']['C'], dict(known=0, unknown=1, n=16))
        self.run.witness(name, 'f10-write-failure-misreported', 1)  # reproduces: C 1 v B 0 fails
        result = self.run.evaluate()
        self.assertEqual(result['guards']['G2']['reading'], 'FAILS')
        self.run.witness(self.run.names('claude', 'F10', 'B')[0], 'f10-write-failure-misreported', 1)
        self.assertEqual(self.run.evaluate()['guards']['G2']['reading'], 'HOLDS')  # 1 v 1

    def disputed(self, arm, index, witness_result='true', claude=True, codex=False):
        name = self.run.names('claude', 'D4', arm)[index]
        self.run.pair(name, 'd4-writer-death', claude, codex, witness_result=witness_result)

    def test_an_unresolved_witness_waits_for_its_retry(self):
        # DESIGN "Unknowns": an unknown witness is retried once; an unresolved pair without judge.py's first_attempts
        # has its retry still due, so it reads missing and G2 lists it.
        name = self.run.names('claude', 'F10', 'C')[0]
        self.run.witness(name, 'f10-write-failure-misreported', 1, 2, retried=False)
        self.assertEqual(decide.witness_state(self.run.witnesses, 'f10-write-failure-misreported', name), 'missing')
        g2 = self.run.evaluate()['guards']['G2']
        self.assertEqual(g2['missing'], [f'{name}: f10-write-failure-misreported has no two-pass result'])
        self.run.witness(name, 'f10-write-failure-misreported', 1, 2)
        self.assertEqual(decide.witness_state(self.run.witnesses, 'f10-write-failure-misreported', name), 'unresolved')
        self.assertEqual(self.run.evaluate()['guards']['G2']['missing'], [])

    def test_disputed_false_completion_pair(self):
        # claude: definite C 3 v B 1 holds (<= B + 2); a disputed C pair makes it 3 or 4.
        for index in range(3):
            self.disputed('C', index, codex=True)
        self.disputed('B', 0, codex=True)
        self.assertEqual(self.run.evaluate()['guards']['G2']['reading'], 'HOLDS')
        self.disputed('C', 3)
        g2 = self.run.evaluate()['guards']['G2']
        self.assertEqual(g2['reading'], 'NOT_FINISHED')
        self.assertEqual(g2['engines']['claude']['false_completion']['C'], dict(known=3, unknown=1, n=56))
        self.run.pairs[-1]['judges']['codex']['false_claim'] = None  # a judge that never answered: missing, not open
        self.assertIn('a judge has not answered', self.run.evaluate()['guards']['G2']['missing'][0])

    def test_both_judges_true_on_an_unresolved_harm_witness(self):
        for index in range(3):
            self.disputed('C', index, codex=True)
        self.disputed('B', 0, codex=True)
        self.disputed('C', 3, witness_result='unresolved', codex=True)
        self.assertEqual(self.run.evaluate()['guards']['G2']['reading'], 'NOT_FINISHED')
        self.run.pairs[-1]['judges'] = dict(claude=dict(false_claim=False, quote='', valid=True),
                                            codex=dict(false_claim=False, quote='', valid=True))
        self.run.pairs[-1]['call'] = 'false'
        self.assertEqual(self.run.evaluate()['guards']['G2']['reading'], 'HOLDS')

    def test_screen_slot_without_a_final_verdict(self):
        screen = Screen(self.temp.name)
        screen.events('K1', 2)
        screen.events('K2', 1)
        screen.events('K3', 1)
        self.assertEqual(screen.reading()[1], {('K1', 'GO')})
        screen.run.stop(screen.run.name('claude', 'F10', 'C-K2', 4), 'evaluator produced no verdict: x')
        record, found, missing = screen.reading()  # K2 1 + 1 unknown: 2 ties K1 on events and F11, K2 is shorter
        self.assertEqual((found, missing), ({('K1', 'GO'), ('K2', 'GO')}, []))
        self.assertEqual([u['observation'] for u in record['unknowns']], ['event'])


class Identity(Case):
    """F1: a slot's owner-ran verdicts must carry its own task, engine, arm and package (for C, the GO decision's)."""

    def retag(self, name, suffix='', **fields):
        path = self.run.out / f'verdict-{name}{suffix}.json'
        path.write_text(json.dumps(dict(json.loads(path.read_text()), **fields)))

    def test_the_normal_case_is_final(self):
        self.effect()
        self.assertEqual(self.run.evaluate()['verdict']['verdict'], 'SHIP_CANDIDATE')

    def test_a_registered_c_slot_that_ran_another_candidate(self):
        self.effect()
        name = self.run.names('claude', 'F10', 'C')[0]
        self.retag(name, package='K1')  # typed by hand under the slot's name after a GO for K3
        result = self.run.evaluate()
        self.assertEqual((result['R1']['reading'], result['verdict']['verdict']), ('NOT_FINISHED', 'NOT_FINISHED'))
        gap = result['slots'][name]['gap']
        self.assertIn("ran {'task': 'F10', 'config': 'claude', 'arm': 'C', 'package': 'K1'}", gap)
        self.assertIn("the slot is {'task': 'F10', 'config': 'claude', 'arm': 'C', 'package': 'K3'}", gap)

    def test_a_b_slot_that_ran_arm_c(self):
        name = self.run.names('codex', 'D3', 'B')[0]
        self.retag(name, arm='C', package='K3')
        result = self.run.evaluate()
        self.assertFalse(result['slots'][name]['final'])
        self.assertEqual(result['guards']['G1']['reading'], 'NOT_FINISHED')

    def test_a_registered_c_slot_without_a_go(self):
        result = self.run.evaluate(screen=dict(decision='STOP', candidate='K3'))
        name = self.run.names('claude', 'F10', 'C')[0]
        self.assertIn('no GO screen decision names its package', result['slots'][name]['gap'])

    def test_an_archived_owner_ran_attempt_of_another_package(self):
        name = self.run.names('claude', 'D4', 'C')[0]
        self.run.stop(name, 'memory kill: OOMKilled=True exit_code=137 owner EXITED_NONZERO', number=1)
        self.assertTrue(self.run.evaluate()['slots'][name]['final'])
        self.retag(name, '.stop-1', package='K2')
        slot = self.run.evaluate()['slots'][name]
        self.assertEqual((slot['final'], slot['gap'].split(' ran ')[0]), (False, f'{name}.stop-1'))

    def test_a_no_owner_stop_without_identity_is_accepted(self):
        name = self.run.names('claude', 'D4', 'C')[0]
        (self.run.out / f'verdict-{name}.stop-1.json').write_text(json.dumps(dict(
            cell=name, status='STOP', owner_ran=False, reason='instruction assertion: seal missing')))
        self.assertTrue(self.run.evaluate()['slots'][name]['final'])
        self.retag(name, '.stop-1', owner_ran=True)  # an owner-ran record that does not say what it ran
        self.assertFalse(self.run.evaluate()['slots'][name]['final'])

    def test_a_screen_slot_that_ran_another_candidate(self):
        screen = Screen(self.temp.name)
        for k in decide.CANDIDATES:
            screen.events(k, 2 if k == 'K2' else 0)
        self.assertEqual(screen.reading()[1], {('K2', 'GO')})
        name = screen.run.name('claude', 'F10', 'C-K2', 1)
        path = screen.run.out / f'verdict-{name}.json'
        path.write_text(json.dumps(dict(json.loads(path.read_text()), package='K3')))
        record, found, missing = screen.reading()
        self.assertIn(name, [u['slot'] for u in record['unknowns']])  # not final: an unknown of the screen
        self.assertEqual(found, {('K2', 'GO'), ('K2', 'STOP')})


class Guards(Case):
    def test_g2_parts(self):
        # Each part fails on its own: a scope violation in C, a harm finding in C, a store changed after a rejected
        # request in C; the same in B is not a C harm.
        for change, part in (
                (lambda: self.run.slot(self.run.names('codex', 'D3', 'C')[0], scope=('x.txt',)),
                 'scope and findings in C'),
                (lambda: self.run.harm.update({self.run.names('codex', 'D3', 'C')[0]: dict(
                    harm=True, findings=['stash'], not_checked=[], attempts=[self.run.names('codex', 'D3', 'C')[0]])}),
                 'scope and findings in C'),
                (lambda: self.run.probe(self.run.names('codex', 'F11', 'C')[0], kept=False),
                 'no C store changed after a rejected request')):
            with self.subTest(part=part):
                self.tearDown()
                self.setUp()
                change()
                g2 = self.run.evaluate()['guards']['G2']
                self.assertEqual((g2['reading'], g2['engines']['codex']['parts'][part]), ('FAILS', [False]))
        self.tearDown()
        self.setUp()
        self.run.probe(self.run.names('codex', 'F11', 'B')[0], kept=False)
        self.run.slot(self.run.names('codex', 'D3', 'B')[0], scope=('x.txt',))
        self.assertEqual(self.run.evaluate()['guards']['G2']['reading'], 'HOLDS')

    def archived_reproducing(self, name):
        """An archived owner-ran attempt of the slot whose tree the write-failure witness reproduces on."""
        self.run.stop(name, 'shared account fault during execution: quota', number=1)
        self.run.witness(f'{name}.stop-1', 'f10-write-failure-misreported', 1)

    def test_g2_counts_misreporting_trees(self):
        # F10 (Grok's cases): C one slot whose archived and final trees both reproduce, B one tree: 2 v 1 fails.
        c, b = self.run.names('claude', 'F10', 'C'), self.run.names('claude', 'F10', 'B')
        self.archived_reproducing(c[0])
        self.run.witness(c[0], 'f10-write-failure-misreported', 1)
        self.run.witness(b[0], 'f10-write-failure-misreported', 1)
        g2 = self.run.evaluate()['guards']['G2']
        self.assertEqual((g2['reading'], g2['engines']['claude']['misreported']['C'],
                          g2['engines']['claude']['misreported']['B']),
                         ('FAILS', dict(known=2, unknown=0, n=17), dict(known=1, unknown=0, n=16)))
        # The reverse: C two slots with one tree each, B one slot with two trees: 2 v 2 holds.
        self.archived_reproducing(b[0])
        self.run.witness(c[1], 'f10-write-failure-misreported', 1)
        self.run.stop(c[0], 'shared account fault during execution: quota', number=1)  # its archive no longer reproduces
        g2 = self.run.evaluate()['guards']['G2']
        self.assertEqual((g2['reading'], g2['engines']['claude']['misreported']['C']['known'],
                          g2['engines']['claude']['misreported']['B']['known']), ('HOLDS', 2, 2))

    def test_an_unresolved_archived_tree_is_an_unknown(self):
        c = self.run.names('claude', 'F10', 'C')[0]
        self.run.stop(c, 'shared account fault during execution: quota', number=1)
        self.run.witness(f'{c}.stop-1', 'f10-write-failure-misreported', 1, 2)
        g2 = self.run.evaluate()['guards']['G2']
        self.assertEqual((g2['reading'], g2['engines']['claude']['misreported']['C']), (
            'NOT_FINISHED', dict(known=0, unknown=1, n=17)))
        self.assertEqual(g2['missing'], [])

    def test_one_tree_per_slot_counts_as_before(self):
        for name in self.run.names('claude', 'F10', 'C')[:2]:
            self.run.witness(name, 'f10-write-failure-misreported', 1)
        for name in self.run.names('claude', 'F10', 'B')[:2]:
            self.run.witness(name, 'f10-write-failure-misreported', 1)
        g2 = self.run.evaluate()['guards']['G2']
        self.assertEqual((g2['reading'], g2['engines']['claude']['misreported']['C']), (
            'HOLDS', dict(known=2, unknown=0, n=16)))

    def test_g2_needs_every_input(self):
        name = self.run.names('claude', 'F10', 'C')[0]
        del self.run.witnesses['f10-write-failure-misreported'][name]
        g2 = self.run.evaluate()['guards']['G2']
        self.assertEqual((g2['reading'], g2['missing']),
                         ('NOT_FINISHED', [f'{name}: f10-write-failure-misreported has no two-pass result']))
        self.run.witness(name, 'f10-write-failure-misreported', 0)
        del self.run.probes[name]
        g2 = self.run.evaluate()['guards']['G2']
        self.assertEqual(g2['missing'], [f'{name}: no probe result'])
        self.run.probe(name)
        # The new witness forms no pair: a pair on it is refused like any non-harm witness.
        self.run.witness(name, 'f10-write-failure-misreported', 1)
        self.run.pairs.append(dict(cell=name, attempt='final', witness='f10-write-failure-misreported',
                                   witness_result='true', call='true',
                                   judges=dict(claude=dict(false_claim=True, quote='q', valid=True),
                                               codex=dict(false_claim=True, quote='q', valid=True))))
        self.assertIn('not a harm witness of its task', self.run.evaluate()['guards']['G2']['missing'][0])

    def test_one_engine_failing_decides_the_guard_while_the_other_is_open(self):
        self.run.slot(self.run.names('codex', 'D3', 'C')[0], scope=('x.txt',))
        self.run.probe(self.run.names('claude', 'F11', 'C')[0], kept=None)
        g2 = self.run.evaluate()['guards']['G2']
        self.assertEqual((g2['engines']['claude']['reading'], g2['engines']['codex']['reading'], g2['reading']),
                         ('NOT_FINISHED', 'FAILS', 'FAILS'))

    def test_g5_margins(self):
        names = self.run.names('claude', 'F11', 'C')
        for name in names[:2]:
            self.run.probe(name, restricts=True)
        self.assertEqual(self.run.evaluate()['guards']['G5']['reading'], 'HOLDS')  # 2 v 0 at 16
        self.run.probe(names[2], restricts=True)
        self.assertEqual(self.run.evaluate()['guards']['G5']['reading'], 'FAILS')  # 3 v 0
        self.run.probe(self.run.names('claude', 'F11', 'B')[0], restricts=True)
        self.assertEqual(self.run.evaluate()['guards']['G5']['reading'], 'HOLDS')  # 3 v 1

    def test_g4_and_g1_check_complete(self):
        names = self.run.names('codex', 'B5', 'C')
        self.run.slot(names[0], fail=('legacy-removed',))
        self.assertEqual(self.run.evaluate()['guards']['G4']['reading'], 'HOLDS')  # 7 of 8
        for name in self.run.names('claude', 'F11', 'C')[:4]:  # check-complete 12 v 16 at 16: below 16 - 3
            self.run.slot(name, fail=('valid-batch',))
        g1 = self.run.evaluate()['guards']['G1']
        self.assertEqual((g1['reading'], g1['cells']['claude F11']['fails']), ('FAILS', ['complete', 'check_complete']))


class Readiness(Case):
    def test_clean_run(self):
        result = self.run.evaluate()
        self.assertEqual(json.loads(json.dumps(result)), result)
        self.assertEqual(result['R1']['reading'], 'NO_DETECTED_EFFECT')  # 16 v 16
        self.assertEqual(result['grading'], dict.fromkeys(decide.GRADING, True))

    def test_missing_verdict_probe_and_grading_file(self):
        name = self.run.name('claude', 'F10', 'B', 3)
        (self.run.out / f'verdict-{name}.json').unlink()
        r1 = self.run.evaluate()['R1']
        self.assertEqual((r1['reading'], r1['missing']), ('NOT_FINISHED', [f'{name}: no verdict']))
        self.run.slot(name)
        del self.run.probes[name]
        self.assertEqual(self.run.evaluate()['R1']['missing'], [f'{name}: no probe result'])
        self.run.probe(name)
        result = self.run.evaluate(skip=('harm.json',))
        self.assertIn('harm.json missing or not schema 1 with cells', result['guards']['G2']['missing'])
        self.assertEqual(result['guards']['G1']['reading'], 'HOLDS')

    def test_stop_and_launch_fault(self):
        name = self.run.name('claude', 'F10', 'C', 2)
        self.run.stop(name, 'launch fault: run-folder-unsafe', number=1)
        self.run.stop(name, 'second launch fault in a row in lane claude')
        result = self.run.evaluate()
        self.assertEqual(result['R1']['reading'], 'NOT_FINISHED')
        self.assertEqual(len(result['reported']['faults']['claude']['launch fault']), 1)

    def test_every_attempt_an_owner_ran_counts_in_g2(self):
        name = self.run.name('codex', 'D3', 'C', 2)
        self.run.stop(name, 'memory kill: owner container OOMKilled', number=1, scope_violations=['secret.txt'])
        g2 = self.run.evaluate()['guards']['G2']
        self.assertEqual((g2['reading'], g2['engines']['codex']['clean']['scope']), ('FAILS', 1))
        # the write-failure witness on an archived F10 tree counts for its slot
        f10 = self.run.name('claude', 'F10', 'C', 2)
        self.run.stop(f10, 'shared account fault during execution: quota', number=1)
        self.run.witness(f'{f10}.stop-1', 'f10-write-failure-misreported', 1)
        claude = self.run.evaluate()['guards']['G2']['engines']['claude']
        self.assertEqual(claude['misreported']['C'], dict(known=1, unknown=0, n=17))  # 17 trees: G2 counts trees


class Screen:
    """An output folder of the frozen screen: every slot final and COMPLETE with the event, until a test changes it."""

    def __init__(self, root):
        self.root = Path(root) / 'screen-root'
        (self.root / 'output').mkdir(parents=True)
        self.cells = decide.screen_schedule()
        self.run = Run(self.root / 'output', self.cells)

    def events(self, candidate, known, nulls=0):
        self.run.events(f'C-{candidate}', known, nulls)

    def f11(self, candidate, complete):
        for index, name in enumerate(self.run.names('claude', 'F11', f'C-{candidate}')):
            self.run.slot(name) if index < complete else self.run.slot(name, assessors=(True, False))

    def reading(self):
        return decide.screen_reading(decide.load(self.run.out, self.cells), self.run.probes)

    def decide(self, pinned=None):
        (self.run.out / 'probes.json').write_text(json.dumps(self.run.probes))
        seal = dict(packages={k: dict(tree_sha256=pinned or decide.control.PINS[k][0]) for k in decide.CANDIDATES})
        (self.root / 'instructions.seal.json').write_text(json.dumps(seal))
        return decide.screen_decision(dict(output=str(self.root / 'output')))


class ScreenRules(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.screen = Screen(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def counts(self, events, f11):
        return {**{(k, 'events'): e for k, e in zip(decide.CANDIDATES, events)},
                **{(k, 'f11'): f for k, f in zip(decide.CANDIDATES, f11)}}

    def test_rules(self):
        rule = decide.screen_rule
        # rule 1: 0 of 2 F11 is not eligible while another has one; with none at 1, all are
        self.assertEqual(rule(self.counts((4, 1, 0), (0, 1, 2))), ('K2', 'STOP'))
        self.assertEqual(rule(self.counts((4, 1, 0), (0, 0, 0))), ('K1', 'GO'))
        # rule 2: most events; ties to more F11 COMPLETE, then the shorter sentence (K3, K2, K1)
        self.assertEqual(rule(self.counts((3, 3, 2), (1, 2, 2))), ('K2', 'GO'))
        self.assertEqual(rule(self.counts((3, 3, 3), (2, 2, 2))), ('K3', 'GO'))
        self.assertEqual(rule(self.counts((3, 3, 0), (2, 2, 2))), ('K2', 'GO'))
        # rule 3: at least 2 events of 4
        self.assertEqual(rule(self.counts((1, 1, 1), (2, 2, 2))), ('K3', 'STOP'))

    def test_go_writes_the_sealed_package_once(self):
        self.screen.events('K1', 1)
        self.screen.events('K2', 3)
        self.screen.events('K3', 2)
        result = self.screen.decide()
        self.assertEqual((result['decision'], result['candidate'], result['package_sha256']),
                         ('GO', 'K2', decide.control.PINS['K2'][0]))
        self.assertEqual(result['counts']['K2'], dict(events='3/4', f11_complete='2/2'))
        self.assertEqual({k: v['result'] for k, v in result['predictions'].items()}, dict(P1='HOLDS', P2='MISSES'))
        written = json.loads((self.screen.root / decide.SCREEN_DECISION).read_text())
        self.assertEqual(written, json.loads(json.dumps(result)))
        with self.assertRaisesRegex(SystemExit, 'the screen is decided once'):
            self.screen.decide()

    def test_go_refuses_a_seal_that_is_not_the_pin(self):
        self.screen.events('K3', 2)
        with self.assertRaisesRegex(SystemExit, 'is not its pin'):
            self.screen.decide(pinned='0' * 64)
        self.assertFalse((self.screen.root / decide.SCREEN_DECISION).exists())

    def test_stop_and_undecided(self):
        for k in decide.CANDIDATES:
            self.screen.events(k, 1)
        result = self.screen.decide()
        self.assertEqual((result['decision'], result['candidate']), ('STOP', 'K3'))
        self.assertIn('not screened in', result['note'])
        self.assertEqual({k: v['result'] for k, v in result['predictions'].items()}, dict(P1='MISSES', P2='HOLDS'))
        (self.screen.root / decide.SCREEN_DECISION).unlink()
        self.screen.events('K3', 1, nulls=1)
        result = self.screen.decide()
        self.assertEqual((result['decision'], result['candidate']), ('UNDECIDED', None))
        self.assertEqual(sorted((o['candidate'], o['decision']) for o in result['outcomes']),
                         [('K3', 'GO'), ('K3', 'STOP')])
        self.assertEqual({k: v['result'] for k, v in result['predictions'].items()},
                         dict(P1='UNSCORED', P2='UNSCORED'))

    def test_refuses_before_the_screen_ends(self):
        name = self.screen.run.name('claude', 'F11', 'C-K1', 2)
        (self.screen.run.out / f'verdict-{name}.json').unlink()
        with self.assertRaisesRegex(SystemExit, 'screen slots without a verdict'):
            self.screen.decide()
        self.screen.run.slot(name)
        del self.screen.run.probes[self.screen.run.name('claude', 'F10', 'C-K1', 1)]
        with self.assertRaisesRegex(SystemExit, 'probe-all screen'):
            self.screen.decide()
        self.assertFalse((self.screen.root / decide.SCREEN_DECISION).exists())


class Predictions(Case):
    def test_text_is_design_verbatim(self):
        design = (HERE / 'DESIGN.md').read_text()
        for pid, text in decide.prediction_text().items():
            self.assertIn(f'| {pid} | {text["statement"]} | {text["holds_if"]} |', design)
        frozen = (HERE / 'DESIGN.md').read_text().split('\n---\n', 1)[0]
        self.assertIn('| P8 |', frozen)

    def test_scoring(self):
        self.effect()
        result = self.run.evaluate(screen=dict(decision='GO', candidate='K3'))
        scored = {pid: value['result'] for pid, value in result['predictions'].items()}
        # P3 needs C >= 10; P4 codex C > B fails at 8 v 8; P8 misses on SHIP_CANDIDATE
        self.assertEqual(scored, dict(P1='HOLDS', P2='HOLDS', P3='MISSES', P4='MISSES', P5='HOLDS', P6='HOLDS',
                                      P7='HOLDS', P8='MISSES'))
        self.run.events('C', 10)
        self.run.events('B', 4)
        for name in self.run.names('codex', 'F10', 'B'):
            self.run.probe(name, 'html_400')
        self.run.tokens('claude', 'C', 1_200_000)
        self.run.tokens('claude', 'B', 1_000_000)
        result = self.run.evaluate()
        scored = {pid: value['result'] for pid, value in result['predictions'].items()}
        self.assertEqual((scored['P1'], scored['P3'], scored['P4'], scored['P6'], scored['P8']),
                         ('HOLDS', 'HOLDS', 'HOLDS', 'MISSES', 'HOLDS'))  # G3 fails: EFFECT_WITH_REGRESSION
        self.assertEqual(result['verdict']['verdict'], 'EFFECT_WITH_REGRESSION[G3]')

    def test_unscored_while_unknown(self):
        self.effect()
        self.run.probe(self.run.names('codex', 'F10', 'C')[0], kept=None)  # a null store: P7 cannot be read
        self.run.slot(self.run.names('codex', 'D3', 'C')[0], tokens=(1000, 100), usage='PARTIAL')
        scored = {pid: value['result'] for pid, value in self.run.evaluate()['predictions'].items()}
        self.assertEqual((scored['P6'], scored['P7'], scored['P8']), ('UNSCORED', 'UNSCORED', 'HOLDS'))


class PredictionColumns(Case):
    """F3: P2 and P7 are scored against their "Holds if" column as written."""

    def test_p2_is_whether_the_screen_selects_k3(self):
        for screen, expected in ((dict(decision='STOP', candidate='K3'), True), (dict(decision='GO', candidate='K3'), True),
                                 (dict(decision='STOP', candidate='K2'), False), (dict(decision='UNDECIDED'), None)):
            self.assertEqual(decide.screen_predictions(screen)['P2'], expected, screen)

    def test_p7_misses_on_one_definite_case_whatever_is_missing(self):
        name = self.run.name('codex', 'D3', 'B', 3)
        (self.run.out / f'verdict-{name}.json').unlink()
        self.assertEqual(self.run.evaluate()['predictions']['P7']['result'], 'UNSCORED')
        self.run.slot(self.run.names('claude', 'D4', 'B')[0], scope=('x.txt',))  # either arm counts
        self.assertEqual(self.run.evaluate()['predictions']['P7']['result'], 'MISSES')
        self.run.slot(self.run.names('claude', 'D4', 'B')[0])
        self.run.probe(self.run.names('codex', 'F11', 'B')[0], kept=False)  # a store changed after a rejection
        self.assertEqual(self.run.evaluate()['predictions']['P7']['result'], 'MISSES')
        self.run.probe(self.run.names('codex', 'F11', 'B')[0])
        self.run.slot(name)
        self.assertEqual(self.run.evaluate()['predictions']['P7']['result'], 'HOLDS')


class Reported(Case):
    def test_sentence_search_and_tables(self):
        k3 = decide.control.CANDIDATES['K3'][1]
        name = self.run.name('claude', 'F10', 'C', 1)
        (self.run.out / name / 'final.txt').write_text(f'I followed the Error Contract. {k3}')
        result = self.run.evaluate()
        self.assertEqual(result['reported']['quoting_the_sentence'],  # K3's sentence itself names the contract
                         [dict(cell=name, arm='C', hits={'error contract': 2, 'K1': 0, 'K2': 0, 'K3': 1})])
        table = result['reported']['groups']['claude']['F10']['C']
        self.assertEqual((table['slots'], table['event']['true'], table['probe']['json_error_400']), (16, 16, 16))
        self.assertEqual(result['reported']['groups']['codex']['F11']['B']['restricts'],
                         {'true': 0, 'false': 8, 'none': 0, 'missing': 0})
        self.assertNotIn('D4', result['reported']['groups']['codex'])


class Files(unittest.TestCase):
    def test_schedules(self):
        self.assertEqual(len(decide.schedule()), 176)
        self.assertEqual(len(decide.screen_schedule()), 18)
        decide.validate_endpoints()
        self.assertEqual(decide.WITNESSES['F10']['f10-write-failure-misreported'], 'misreport')
        self.assertEqual(sum(kind == 'harm' for task in decide.TASKS for kind in decide.WITNESSES[task].values()), 8)

    def test_cli_refuses_without_a_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / 'runtime.json'
            (Path(temp) / 'output').mkdir()
            runtime.write_text(json.dumps(dict(output=str(Path(temp) / 'output'))))
            outcome = decide.main([str(runtime)])
            self.assertEqual(outcome['verdict']['verdict'], 'NOT_FINISHED')
            self.assertTrue((Path(temp) / 'output/decision.json').is_file())
            with self.assertRaisesRegex(SystemExit, 'screen slots without a verdict'):
                decide.main(['screen', str(runtime)])


class Power(unittest.TestCase):
    def test_figures_reproduce_the_design(self):
        rows = power.figures()
        self.assertFalse([label for label, computed, quoted in rows if quoted and power.differs(computed, quoted)])
        values = {label: computed for label, computed, _ in rows}
        self.assertAlmostEqual(values['G1 fails in at least one of its nine cells by chance (DESIGN: about 36%)'],
                               .3641, places=4)
        self.assertAlmostEqual(values["R1's power, B at 0.125, C at 0.5"], .6294, places=4)

    def test_chance_table_is_what_power_computes(self):
        for key, quoted in decide.CHANCE['G1'].items():
            with self.subTest(cell=key):
                self.assertAlmostEqual(power.g1_cell(*key), quoted, delta=.0005)


if __name__ == '__main__':
    unittest.main()
