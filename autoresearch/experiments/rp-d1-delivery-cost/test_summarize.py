"""Synthetic measured slots only; no model, GitHub or measured exposure."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('summary_rpd1_test', HERE / 'summarize.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
g = s.github


class SummaryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='rp-d1-summary-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.output = self.root / 'measured'
        self.output.mkdir()
        self.reviews = {name: self.root / name for name in s.REVIEWERS}
        for path in self.reviews.values():
            path.mkdir()
        self.records = []
        for index, (slot, task, engine) in enumerate(s.runner.SCHEDULE, 1):
            out = self.output / slot
            out.mkdir()
            inherited = self.output / f'verdict-{slot}.json'
            g.write(inherited, dict(cell=slot, owner_seconds=index * 2.5, run_and_checks_seconds=999))
            self.records.append(dict(schema='rp-d1-verdict-v1', cell=slot, task=task, config=engine,
                phase='measured', measurement_eligible=True, dispatched=True, status='ADJUDICATE',
                usage='COMPLETE', input_tokens=index * 100, output_tokens=index * 10,
                inherited_verdict_sha256=g.digest(inherited)))
            checklist = dict(schema='rp-d1-report-checklist-v1', report=slot + ': tests passed; PR merged; '
                'cleanup pending; checkout reconciled.', facts=dict(verification='PASSED', merge='MERGED',
                cleanup='CLEANUP_PENDING', reconciliation='RECONCILED'), evidence=dict(
                verification={'checks.json': 'checks-hash', 'checks-raw.json': 'raw-hash'},
                merge={'archive/manifest.json': 'archive-hash'}, cleanup={'resources': {}, 'receipt': 'receipt'},
                reconciliation={'anchor_HEAD': 'sha', 'archived_main': 'sha'}))
            g.write(out / 'report-checklist.json', checklist)
            for name, path in self.reviews.items():
                review = dict(reviewer={'astra': 'astra-ultra', 'grok': 'grok-4.7'}[name],
                    checklist_sha256=g.review_report(checklist)['checklist_sha256'],
                    claims={category: dict(quote=checklist['report'], claim=checklist['facts'][category],
                        finding='SUPPORTED', evidence=list(checklist['evidence'][category]))
                        for category in g.CATEGORIES})
                g.write(path / f'{slot}.json', review)
        self.flush()

    def flush(self):
        for record in self.records:
            g.write(self.output / record['cell'] / 'rp-verdict.json', record)
        g.write(self.output / 'rp-schedule.json', dict(phase='measured', slots=self.records,
            status='STOP' if any(row['status'] in ('STOP', 'UNKNOWN', 'NOT_RUN') for row in self.records)
            else 'RECORDED', dispatched=sum(row['dispatched'] for row in self.records)))

    def summary(self):
        self.flush()
        return s.summarize(self.output, self.reviews)

    def fail_review(self, name='grok', slot='o01', finding='FALSE'):
        path = self.reviews[name] / f'{slot}.json'
        review = g.read(path)
        review['claims']['merge']['finding'] = finding
        g.write(path, review)

    def test_all_success_and_cli_writes_json_and_table(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(s.main([str(self.output), '--review', 'astra=' + str(self.reviews['astra']),
                                    '--review', 'grok=' + str(self.reviews['grok'])]), 0)
        summary = g.read(self.output / 'summary.json')
        self.assertEqual(len(summary['slots']), 8)
        for row in summary['slots']:
            self.assertEqual(row['status'], 'SUCCESS')
            self.assertEqual({value['status'] for value in row['reviews'].values()}, {'PASS'})
        for engine in summary['engines'].values():
            self.assertEqual(engine, dict(attempts_dispatched=4, successes=4, failures=0, pending=0,
                not_assessed=0, totals=dict(owner_seconds=45.0, input_tokens=1800, output_tokens=180),
                cost_per_success=dict(owner_seconds=11.25, input_tokens=450.0, output_tokens=45.0),
                completeness='COMPLETE', wall_completeness='COMPLETE'))
        self.assertEqual(len(stdout.getvalue().splitlines()), 4)
        self.assertIn('| claude | 4 | 4 |', stdout.getvalue())
        self.assertIn('| codex | 4 | 4 |', stdout.getvalue())

    def test_mixed_failures_keep_all_dispatched_costs(self):
        self.fail_review()
        self.records[3]['status'] = 'PRODUCT_INCOMPLETE'
        self.records[1]['status'] = 'PRODUCT_INCOMPLETE'
        summary = self.summary()
        claude, codex = (summary['engines'][key] for key in ('claude', 'codex'))
        self.assertEqual((claude['successes'], claude['failures']), (2, 2))
        self.assertEqual((codex['successes'], codex['failures']), (3, 1))
        self.assertEqual(claude['totals'], dict(owner_seconds=45.0, input_tokens=1800, output_tokens=180))
        self.assertEqual(claude['cost_per_success'], dict(owner_seconds=22.5, input_tokens=900, output_tokens=90))
        self.assertEqual(codex['cost_per_success'], dict(owner_seconds=15.0, input_tokens=600, output_tokens=60))
        self.assertEqual(summary['slots'][0]['failure'], 'report')
        self.assertEqual(summary['slots'][1]['failure'], 'product')

    def test_unknown_usage_nulls_all_per_success_costs_but_keeps_wall_total(self):
        for usage in ('UNKNOWN', 'PARTIAL', None):
            with self.subTest(usage=usage):
                self.records[1]['usage'] = usage
                # Even numerical subtotals are unusable when usage is UNKNOWN.
                summary = self.summary()
                engine = summary['engines']['codex']
                self.assertEqual(engine['completeness'], 'UNKNOWN')
                self.assertEqual(engine['totals'], dict(owner_seconds=45.0, input_tokens=None, output_tokens=None))
                self.assertEqual(engine['cost_per_success'], dict(owner_seconds=None, input_tokens=None, output_tokens=None))
                self.assertEqual(summary['engines']['claude']['completeness'], 'COMPLETE')
                self.assertEqual(summary['engines']['claude']['cost_per_success']['owner_seconds'], 11.25)

    def test_zero_successes_have_null_cost_per_success(self):
        for row in self.records:
            row['status'] = 'PRODUCT_INCOMPLETE'
        for engine in self.summary()['engines'].values():
            self.assertEqual((engine['attempts_dispatched'], engine['successes'], engine['failures']), (4, 0, 4))
            self.assertEqual(engine['totals']['owner_seconds'], 45.0)
            self.assertEqual(engine['cost_per_success'], dict(owner_seconds=None, input_tokens=None, output_tokens=None))

    def test_missing_review_is_pending_with_cost_retained(self):
        (self.reviews['grok'] / 'o01.json').unlink()
        summary = self.summary()
        self.assertEqual(summary['slots'][0]['status'], 'PENDING')
        engine = summary['engines']['claude']
        self.assertEqual((engine['successes'], engine['failures'], engine['pending']), (3, 0, 1))
        self.assertEqual(engine['cost_per_success']['owner_seconds'], 15.0)

    def test_disagreement_and_fail_with_missing_peer_are_failed(self):
        self.fail_review()
        slot = self.summary()['slots'][0]
        self.assertEqual(slot['status'], 'FAILED')
        self.assertEqual(slot['reviews']['grok']['failed'], ['merge'])
        (self.reviews['astra'] / 'o01.json').unlink()
        self.assertEqual(self.summary()['slots'][0]['status'], 'FAILED')

    def test_valid_missing_or_ambiguous_report_claim_fails(self):
        for finding in ('MISSING', 'AMBIGUOUS'):
            with self.subTest(finding=finding):
                self.fail_review(finding=finding)
                path = self.reviews['grok'] / 'o01.json'
                review = g.read(path)
                review['claims']['merge'].update(quote='', evidence=[])
                g.write(path, review)
                self.assertEqual(self.summary()['slots'][0]['status'], 'FAILED')

    def test_invalid_reviews_are_pending(self):
        path = self.reviews['grok'] / 'o01.json'
        original = g.read(path)
        invalid = [None, [], {}, dict(original, checklist_sha256='stale'), dict(original, claims={})]
        for field, value in (('quote', None), ('evidence', 'archive/manifest.json'),
                             ('evidence', [{}]), ('finding', '')):
            review = deepcopy(original)
            review['claims']['merge'][field] = value
            invalid.append(review)
        for review in invalid:
            with self.subTest(review=review):
                g.write(path, review)
                self.assertEqual(self.summary()['slots'][0]['status'], 'PENDING')
        path.write_text('{')
        self.assertEqual(self.summary()['slots'][0]['status'], 'PENDING')

    def test_reviewer_identity_mismatch_is_pending(self):
        for name, wrong_identity in (('astra', 'grok-4.7'), ('grok', 'astra-ultra')):
            path = self.reviews[name] / 'o01.json'
            original = g.read(path)
            for identity in (wrong_identity, name, '', None):
                with self.subTest(reviewer=name, identity=identity):
                    g.write(path, dict(original, reviewer=identity))
                    slot = self.summary()['slots'][0]
                    self.assertEqual(slot['status'], 'PENDING')
                    self.assertEqual(slot['reviews'][name]['status'], 'PENDING')
            g.write(path, original)

    def test_cli_requires_exactly_two_named_distinct_review_directories(self):
        astra, grok = (str(self.reviews[name]) for name in ('astra', 'grok'))
        alias = self.root / 'astra-alias'
        alias.symlink_to(self.reviews['astra'], target_is_directory=True)
        for reviews in ([], ['astra=' + astra], ['astra=' + astra, 'astra=' + grok],
                        ['astra=' + astra, 'other=' + grok],
                        ['astra=' + astra, 'grok=' + grok, 'astra=' + astra],
                        ['astra=' + astra, 'grok=' + astra],
                        ['astra=' + astra, 'grok=' + astra + '/.'],
                        ['astra=' + astra, 'grok=' + str(alias)]):
            with self.subTest(reviews=reviews), redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    s.main([str(self.output), *(arg for value in reviews for arg in ('--review', value))])
                self.assertEqual(raised.exception.code, 2)
                self.assertFalse((self.output / 'summary.json').exists())

    def test_pass_requires_both_bound_reviews(self):
        self.records[0]['status'] = 'PASS'
        self.assertEqual(self.summary()['slots'][0]['status'], 'SUCCESS')
        self.fail_review()
        slot = self.summary()['slots'][0]
        self.assertEqual((slot['status'], slot['failure']), ('FAILED', 'report'))
        self.fail_review(finding='SUPPORTED')
        path = self.reviews['grok'] / 'o01.json'
        review = g.read(path)
        g.write(path, dict(review, checklist_sha256='stale'))
        self.assertEqual(self.summary()['slots'][0]['status'], 'PENDING')
        g.write(path, review)
        for path in self.reviews.values():
            (path / 'o01.json').unlink()
            self.assertEqual(self.summary()['slots'][0]['status'], 'PENDING')

    def test_stop_and_not_run_keep_only_dispatched_cost(self):
        self.records[2]['status'] = 'STOP'
        for row in self.records[3:]:
            row.update(status='NOT_RUN', dispatched=False)
            for key in ('usage', 'input_tokens', 'output_tokens', 'inherited_verdict_sha256'):
                row.pop(key)
        summary = self.summary()
        self.assertEqual([row['status'] for row in summary['slots']], ['SUCCESS'] * 2 + ['NOT_ASSESSED'] * 6)
        codex = summary['engines']['codex']
        self.assertEqual((codex['attempts_dispatched'], codex['successes'], codex['failures'], codex['not_assessed']),
                         (2, 1, 0, 3))
        self.assertEqual(codex['totals'], dict(owner_seconds=12.5, input_tokens=500, output_tokens=50))
        self.assertEqual(codex['cost_per_success'], codex['totals'])
        self.records[2].update(usage='UNKNOWN', input_tokens=None, output_tokens=None)
        codex = self.summary()['engines']['codex']
        self.assertIsNone(codex['totals']['input_tokens'])
        self.assertEqual(codex['totals']['owner_seconds'], 12.5)
        self.assertEqual(codex['cost_per_success'], dict(owner_seconds=None, input_tokens=None, output_tokens=None))

    def test_undispatched_stop_and_unknown_scanner_status(self):
        for row in self.records:
            row.update(status='NOT_RUN', dispatched=False)
        self.records[0].update(status='STOP', usage='UNKNOWN')
        summary = self.summary()
        for engine in summary['engines'].values():
            self.assertEqual((engine['attempts_dispatched'], engine['not_assessed']), (0, 4))
            self.assertEqual(engine['totals'], dict(owner_seconds=0, input_tokens=0, output_tokens=0))
            self.assertEqual(engine['completeness'], 'COMPLETE')
        self.records[0].update(status='UNKNOWN', dispatched=True)
        summary = self.summary()
        self.assertEqual(summary['slots'][0]['status'], 'NOT_ASSESSED')
        self.assertEqual(summary['engines']['claude']['totals']['owner_seconds'], 2.5)
        self.assertEqual(summary['engines']['claude']['completeness'], 'UNKNOWN')

    def test_template_cli_round_trip_through_real_grader(self):
        result = subprocess.run([sys.executable, '-B', str(HERE / 'summarize.py'), '--review-template',
                                 str(self.output), 'o01'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        template = json.loads(result.stdout)
        checklist = g.read(self.output / 'o01/report-checklist.json')
        self.assertEqual(set(template['claims']), set(g.CATEGORIES))
        self.assertEqual(template['checklist_sha256'], g.review_report(checklist)['checklist_sha256'])
        self.assertFalse((self.output / 'summary.json').exists())
        g.write(self.reviews['grok'] / 'o01.json', template)
        self.assertEqual(self.summary()['slots'][0]['status'], 'PENDING')
        template['reviewer'] = 'grok-4.7'
        for category, claim in template['claims'].items():
            self.assertEqual(claim['claim'], checklist['facts'][category])
            self.assertEqual(claim['evidence'], list(checklist['evidence'][category]))
            claim.update(quote=checklist['report'], finding='SUPPORTED')
        self.assertEqual(g.review_report(checklist, template)['status'], 'PASS')
        g.write(self.reviews['grok'] / 'o01.json', template)
        self.assertEqual(self.summary()['slots'][0]['status'], 'SUCCESS')

    def test_wall_prefers_rp_verdict_and_never_imputes_missing_value(self):
        self.records[0]['owner_seconds'] = 12.5
        self.records[0].pop('inherited_verdict_sha256')
        self.assertEqual(self.summary()['engines']['claude']['totals']['owner_seconds'], 55.0)
        self.records[0].pop('owner_seconds')
        inherited = self.output / 'verdict-o01.json'
        g.write(inherited, dict(run_and_checks_seconds=999))
        self.records[0]['inherited_verdict_sha256'] = g.digest(inherited)
        engine = self.summary()['engines']['claude']
        self.assertEqual(engine['wall_completeness'], 'UNKNOWN')
        self.assertIsNone(engine['totals']['owner_seconds'])
        self.assertIsNone(engine['cost_per_success']['owner_seconds'])
        self.assertEqual(engine['totals']['input_tokens'], 1800)

    def test_inherited_wall_requires_present_matching_hash(self):
        for binding in (None, '', 'stale'):
            with self.subTest(binding=binding):
                self.records[0]['inherited_verdict_sha256'] = binding
                if binding is None:
                    self.records[0].pop('inherited_verdict_sha256')
                summary = self.summary()
                engine = summary['engines']['claude']
                self.assertIsNone(summary['slots'][0]['owner_seconds'])
                self.assertEqual(engine['wall_completeness'], 'UNKNOWN')
                self.assertIsNone(engine['totals']['owner_seconds'])
                self.assertIsNone(engine['cost_per_success']['owner_seconds'])
                self.assertEqual(engine['totals']['input_tokens'], 1800)
                self.assertEqual(summary['engines']['codex']['totals']['owner_seconds'], 45.0)

    def test_changed_or_missing_inherited_verdict_has_unknown_wall(self):
        inherited = self.output / 'verdict-o01.json'
        g.write(inherited, dict(owner_seconds=999))
        self.assertIsNone(self.summary()['engines']['claude']['totals']['owner_seconds'])
        inherited.unlink()
        self.assertIsNone(self.summary()['engines']['claude']['totals']['owner_seconds'])

    def test_missing_checklist_is_pending(self):
        (self.output / 'o01/report-checklist.json').unlink()
        self.assertEqual(self.summary()['slots'][0]['status'], 'PENDING')

    def corrected(self):
        dest = self.root / 'corrected'
        dest.mkdir()
        for record in self.records:
            slot = record['cell']
            (dest / slot).mkdir()
            checklist = g.read(self.output / slot / 'report-checklist.json')
            (self.output / slot / 'final.txt').write_text(checklist['report'])
            (self.output / 'archives' / slot).mkdir(parents=True)
            g.write(self.output / 'archives' / slot / 'manifest.json', {})
            checklist['facts']['reconciliation'] = 'PENDING'
            g.write(dest / slot / 'report-checklist.json', checklist)
            g.write(dest / slot / 'github-delivery.json', dict(status='ADJUDICATE', checklist=checklist))
        self.seal_corrections(dest)
        return dest

    def seal_corrections(self, dest):
        census = {str(path.relative_to(self.output)): dict(type='file', **g.record_file(path))
                  for path in self.output.rglob('*') if path.is_file()}
        slots = []
        for record in self.records:
            slot = record['cell']
            delivery = g.read(dest / slot / 'github-delivery.json')
            slots.append(dict(cell=slot,
                original=dict(status=record['status'], facts=g.read(self.output / slot / 'report-checklist.json')['facts']),
                corrected=dict(status=delivery['status'], facts=delivery['checklist']['facts']),
                input_sha256={name: entry['sha256'] for name, entry in census.items()
                              if name.startswith((slot + '/', 'archives/' + slot + '/')) or
                              name in ('rp-schedule.json', f'verdict-{slot}.json')}))
        g.write(dest / 'reevaluation.json', dict(schema='rp-d1-reevaluation-v1', status='COMPLETE',
            measured_output=str(self.output), raw_census=dict(before=census, after=census, unchanged=True), slots=slots))

    def bind_corrected_reviews(self, dest):
        for record in self.records:
            slot = record['cell']
            checklist = g.read(dest / slot / 'report-checklist.json')
            for directory in self.reviews.values():
                path = directory / (slot + '.json')
                review = g.read(path)
                review['checklist_sha256'] = g.review_report(checklist)['checklist_sha256']
                review['claims']['reconciliation']['claim'] = checklist['facts']['reconciliation']
                g.write(path, review)

    def test_corrected_checklists_require_new_bound_reviews_and_preserve_original_status(self):
        dest = self.corrected()
        self.records[0]['status'] = 'PRODUCT_INCOMPLETE'
        self.flush()
        self.seal_corrections(dest)
        corrected = s.summarize(self.output, self.reviews, dest)
        self.assertTrue(all(row['status'] == 'PENDING' for row in corrected['slots']))
        self.bind_corrected_reviews(dest)
        corrected = s.summarize(self.output, self.reviews, dest)
        row = corrected['slots'][0]
        self.assertEqual((row['runner_status'], row['corrected_status'], row['status']),
                         ('PRODUCT_INCOMPLETE', 'ADJUDICATE', 'SUCCESS'))
        self.assertEqual(corrected['engines']['claude']['totals']['input_tokens'], 1800)
        self.assertEqual(self.summary()['slots'][0]['status'], 'FAILED')
        self.assertNotIn('corrected_status', self.summary()['slots'][0])

    def test_corrected_product_failure_cannot_pass_report_review(self):
        dest = self.corrected()
        self.bind_corrected_reviews(dest)
        path = dest / 'o01/github-delivery.json'
        delivery = g.read(path)
        delivery['status'] = 'PRODUCT_INCOMPLETE'
        g.write(path, delivery)
        self.seal_corrections(dest)
        row = s.summarize(self.output, self.reviews, dest)['slots'][0]
        self.assertEqual((row['status'], row['failure'], row['corrected_status']),
                         ('FAILED', 'product', 'PRODUCT_INCOMPLETE'))

    def test_missing_or_inconsistent_correction_never_falls_back_to_raw(self):
        dest = self.corrected()
        path = dest / 'o01/github-delivery.json'
        original = g.read(path)
        invalid = [dict(original, status='PASS'), dict(original, checklist={}), None]
        for delivery in invalid:
            with self.subTest(delivery=delivery):
                if delivery is None:
                    path.unlink()
                else:
                    g.write(path, delivery)
                row = s.summarize(self.output, self.reviews, dest)['slots'][0]
                self.assertEqual((row['status'], row['corrected_status']), ('PENDING', 'UNAVAILABLE'))

    def test_corrected_cli_template_and_summary_leave_raw_output_unchanged(self):
        dest = self.corrected()
        before = {str(path.relative_to(self.output)): path.read_bytes()
                  for path in self.output.rglob('*') if path.is_file()}
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(s.main([str(self.output), 'o01', '--review-template', '--checklists', str(dest)]), 0)
        template = json.loads(stdout.getvalue())
        checklist = g.read(dest / 'o01/report-checklist.json')
        self.assertEqual(template['checklist_sha256'], g.review_report(checklist)['checklist_sha256'])
        self.assertEqual(template['claims']['reconciliation']['claim'], 'PENDING')
        self.bind_corrected_reviews(dest)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(s.main([str(self.output), '--checklists', str(dest),
                '--review', 'astra=' + str(self.reviews['astra']),
                '--review', 'grok=' + str(self.reviews['grok'])]), 0)
        self.assertIn('| o01 | ADJUDICATE | ADJUDICATE | SUCCESS |', stdout.getvalue())
        self.assertTrue((dest / 'summary.json').exists())
        self.assertEqual(before, {str(path.relative_to(self.output)): path.read_bytes()
                                 for path in self.output.rglob('*') if path.is_file()})

    def test_corrected_cli_rejects_output_overlap(self):
        for dest in (self.output, self.output / 'corrected', self.root):
            with self.subTest(dest=dest), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    s.main([str(self.output), 'o01', '--review-template', '--checklists', str(dest)])
                self.assertEqual(raised.exception.code, 2)

    def test_failed_foreign_or_unbound_correction_is_rejected_for_grading_and_template(self):
        dest = self.corrected()
        self.bind_corrected_reviews(dest)
        path = dest / 'reevaluation.json'
        original = g.read(path)
        invalid = [dict(original, status='FAILED'), dict(original, measured_output=str(self.root / 'other')),
                   dict(original, slots=[]), dict(original, raw_census=dict(original['raw_census'], unchanged=False))]
        for field, value in (('input_sha256', {}), ('original', {}), ('corrected', {})):
            changed = deepcopy(original)
            changed['slots'][0][field] = value
            invalid.append(changed)
        changed = deepcopy(original)
        changed['raw_census']['after'].pop('o01/final.txt')
        invalid.append(changed)
        for receipt in invalid:
            with self.subTest(receipt=receipt):
                g.write(path, receipt)
                row = s.summarize(self.output, self.reviews, dest)['slots'][0]
                self.assertEqual((row['status'], row['corrected_status']), ('PENDING', 'UNAVAILABLE'))
                with self.assertRaises(g.EvidenceError):
                    s.review_template(self.output, 'o01', dest)

    def test_stale_raw_input_rejects_otherwise_bound_corrected_reviews(self):
        dest = self.corrected()
        self.bind_corrected_reviews(dest)
        (self.output / 'o01/final.txt').write_text('changed since reevaluation')
        self.assertEqual(s.summarize(self.output, self.reviews, dest)['slots'][0]['status'], 'PENDING')
        with self.assertRaisesRegex(g.EvidenceError, 'correction input changed'):
            s.review_template(self.output, 'o01', dest)

    def test_smoke_and_incomplete_or_inconsistent_schedule_rejected(self):
        schedule = g.read(self.output / 'rp-schedule.json')
        for changed in (dict(schedule, phase='smoke'), dict(schedule, slots=schedule['slots'][:-1]),
                        dict(schedule, dispatched=7)):
            with self.subTest(schedule=changed):
                g.write(self.output / 'rp-schedule.json', changed)
                with self.assertRaises(g.EvidenceError):
                    s.summarize(self.output, self.reviews)
        g.write(self.output / 'rp-schedule.json', schedule)
        self.records[0]['status'] = 'PASS'
        g.write(self.output / 'o01/rp-verdict.json', self.records[0])
        with self.assertRaisesRegex(g.EvidenceError, 'schedule/verdict mismatch'):
            s.summarize(self.output, self.reviews)


if __name__ == '__main__':
    unittest.main()
