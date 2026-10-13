"""Post-exposure correction on disposable sealed slots and real local Git archives."""
from copy import deepcopy
import os
import shutil
import subprocess
import sys
from unittest.mock import patch

import test_apparatus as apparatus
from test_apparatus import HERE, g, packet, r

e = r.load('reevaluate_rpd1_test', HERE / 'reevaluate.py')


class ReevaluationTests(apparatus.DeliveryFixture):
    def setUp(self):
        super().setUp()
        g.git(self.anchor, 'merge', '--ff-only', self.merge)
        marker = self.anchor / '.devlyn-install.json'
        marker.write_text('{}\n')
        marker.chmod(0o600)
        submitted = self.out / 'snapshot/.devlyn-install.json'
        submitted.write_bytes(marker.read_bytes())
        submitted.chmod(0o644)
        self.container_links()
        archived = self.freeze_archive()
        original = self.check()
        original['checklist']['facts']['reconciliation'] = 'PENDING'
        original['report_review'] = g.review_report(original['checklist'])
        g.write(self.out / 'github-delivery.json', original)
        g.write(self.out / 'report-checklist.json', original['checklist'])
        self.output, self.dest = self.root / 'measured', self.root / 'corrected'
        self.output.mkdir()
        shutil.copytree(self.out, self.output / 'o01', symlinks=True)
        shutil.copytree(self.archive, self.output / 'archives/o01')
        self.out = self.output / 'o01'
        self.records = []
        for slot, task, engine in r.SCHEDULE:
            (self.output / slot).mkdir(exist_ok=True)
            self.records.append(dict(cell=slot, task=task, config=engine, phase='measured',
                measurement_eligible=True, dispatched=slot == 'o01',
                status='ADJUDICATE' if slot == 'o01' else 'NOT_RUN'))
        self.records[0]['archive'] = dict(manifest_sha256=archived['manifest_sha256'])
        self.inherited = dict(status='CHECKS_PASS', teardown='CLEAN', snapshot=self.selection)
        self.seal()

    def flush(self):
        for record in self.records:
            g.write(self.output / record['cell'] / 'rp-verdict.json', record)
        g.write(self.output / 'rp-schedule.json', dict(phase='measured', slots=self.records,
            dispatched=sum(row['dispatched'] for row in self.records)))

    def seal(self):
        files = {str(path.relative_to(self.out)): g.digest(path)
                 for name in ('run', 'cell', 'tmp', 'home')
                 for path in (self.out / name).rglob('*') if path.is_file() and not path.is_symlink()}
        g.write(self.out / 'evidence.manifest.json', dict(files=files, failures=[]))
        self.inherited['evidence_manifest_sha256'] = g.digest(self.out / 'evidence.manifest.json')
        g.write(self.output / 'verdict-o01.json', self.inherited)
        self.records[0]['inherited_verdict_sha256'] = g.digest(self.output / 'verdict-o01.json')
        g.write(self.out / 'checked.json', dict(snapshot=packet.tree(self.out / 'snapshot'),
            checks_sha256=g.digest(self.out / 'checks.json')))
        self.flush()

    def test_cli_corrects_facts_records_hashes_and_never_writes_raw(self):
        index = self.stale_index()
        index_before = index.read_bytes()
        before = e.census(self.output)
        result = subprocess.run([sys.executable, '-B', str(HERE / 'reevaluate.py'),
            str(self.output), str(self.dest)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = g.read(self.dest / 'reevaluation.json')
        self.assertEqual(report['status'], 'COMPLETE')
        self.assertEqual(report['raw_census'], dict(before=before, after=before, unchanged=True))
        self.assertEqual(e.census(self.output), before)
        self.assertEqual(index.read_bytes(), index_before)
        row, = report['slots']
        self.assertEqual(row['disclosed_changes'], [])
        self.assertEqual(row['original'], dict(status='ADJUDICATE', facts=g.read(
            self.out / 'report-checklist.json')['facts']))
        self.assertEqual(row['corrected']['facts']['reconciliation'], 'RECONCILED')
        self.assertEqual(row['corrected']['status'], 'ADJUDICATE')
        for name in ('o01/cell/work/.git/HEAD', 'o01/checks.json', 'o01/final.txt',
                     'o01/snapshot/.devlyn-install.json', 'archives/o01/manifest.json', 'verdict-o01.json'):
            self.assertEqual(row['input_sha256'][name], g.digest(self.output / name))
        self.assertEqual(row['evaluator_sha256']['rp-d1-delivery-cost/github.py'], g.digest(HERE / 'github.py'))
        delivery = g.read(self.dest / 'o01/github-delivery.json')
        self.assertEqual(delivery['checklist'], g.read(self.dest / 'o01/report-checklist.json'))
        self.assertFalse(delivery['passed'], 'review=None must never manufacture PASS')
        template = e.summary.review_template(self.output, 'o01', self.dest)
        self.assertEqual(template['checklist_sha256'], delivery['report_review']['checklist_sha256'])

    def stale_index(self):
        tracked = self.out / 'cell/work/src/expiry/__init__.py'
        stat = tracked.stat()
        os.utime(tracked, ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))
        return self.out / e.INDEX_PATH

    def refresh_index(self):
        index = self.stale_index()
        before = index.read_bytes()
        g.git(self.out / 'cell/work', 'update-index', '--refresh')
        self.assertNotEqual(index.read_bytes(), before)
        return index

    def test_cli_accepts_only_disclosed_index_changes_and_records_equivalence(self):
        index = self.refresh_index()
        with self.assertRaisesRegex(e.github.EvidenceError, 'sealed evidence changed'):
            e.reevaluate(self.output, self.dest)
        shutil.rmtree(self.dest)
        # A second slot exercises the repeatable CLI option with distinct disclosures.
        shutil.rmtree(self.output / 'o02')
        shutil.copytree(self.out, self.output / 'o02', symlinks=True)
        shutil.copytree(self.output / 'archives/o01', self.output / 'archives/o02')
        g.write(self.output / 'verdict-o02.json', self.inherited)
        self.records[1].update(dispatched=True, status='ADJUDICATE',
            archive=self.records[0]['archive'],
            inherited_verdict_sha256=g.digest(self.output / 'verdict-o02.json'))
        self.flush()
        # Evaluation must also preserve the disclosed index when stats become stale again.
        self.stale_index()
        before = e.census(self.output)
        result = subprocess.run([sys.executable, '-B', str(HERE / 'reevaluate.py'),
            str(self.output), str(self.dest), '--disclosed-change', 'o01:' + e.INDEX_PATH,
            '--disclosed-change', 'o02:' + e.INDEX_PATH], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = g.read(self.dest / 'reevaluation.json')
        self.assertEqual(report['status'], 'COMPLETE')
        self.assertEqual(report['raw_census'], dict(before=before, after=before, unchanged=True))
        self.assertEqual(e.census(self.output), before)
        self.assertEqual([row['cell'] for row in report['slots']], ['o01', 'o02'])
        for row in report['slots']:
            change, = row['disclosed_changes']
            self.assertEqual(change, dict(path=e.INDEX_PATH,
                sealed_sha256=g.read(self.out / 'evidence.manifest.json')['files'][e.INDEX_PATH],
                current_sha256=g.digest(index), equivalence_checks=[
                    dict(command=['git', 'diff', '--cached', '--quiet', 'HEAD'], passed=True),
                    dict(command=['git', 'ls-files', '-v', '-z'], passed=True)]))
            self.assertNotEqual(change['sealed_sha256'], change['current_sha256'])
            self.assertEqual(row['corrected']['status'], 'ADJUDICATE')
            e.summary.review_template(self.output, row['cell'], self.dest)

    def test_disclosure_does_not_excuse_any_other_sealed_change(self):
        self.refresh_index()
        tracked = self.out / 'cell/work/src/expiry/__init__.py'
        tracked.write_bytes(tracked.read_bytes() + b'\n')
        with patch.object(e.github, 'done_check') as done:
            with self.assertRaisesRegex(e.github.EvidenceError, 'sealed evidence changed'):
                e.reevaluate(self.output, self.dest, ['o01:' + e.INDEX_PATH])
        done.assert_not_called()
        report = g.read(self.dest / 'reevaluation.json')
        self.assertEqual(report['status'], 'FAILED')
        self.assertTrue(report['raw_census']['unchanged'])
        self.assertFalse((self.dest / 'o01').exists())

    def test_non_index_or_malformed_disclosures_are_rejected(self):
        for value in ('o01:cell/work/.git/HEAD', 'o01:cell/work/.git/./index',
                      'o01:cell/work/.git/../.git/index', 'o01:/cell/work/.git/index',
                      'o99:' + e.INDEX_PATH, e.INDEX_PATH):
            with self.subTest(value=value):
                result = subprocess.run([sys.executable, '-B', str(HERE / 'reevaluate.py'),
                    str(self.output), str(self.dest), '--disclosed-change', value],
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn('disclosed change must be', result.stderr)
                self.assertFalse(self.dest.exists())

    def test_disclosure_requires_an_eligible_slot_and_a_sealed_index(self):
        with self.assertRaisesRegex(e.github.EvidenceError, 'eligible archived slot'):
            e.reevaluate(self.output, self.dest, ['o02:' + e.INDEX_PATH])
        shutil.rmtree(self.dest)
        manifest = g.read(self.out / 'evidence.manifest.json')
        del manifest['files'][e.INDEX_PATH]
        g.write(self.out / 'evidence.manifest.json', manifest)
        self.inherited['evidence_manifest_sha256'] = g.digest(self.out / 'evidence.manifest.json')
        g.write(self.output / 'verdict-o01.json', self.inherited)
        self.records[0]['inherited_verdict_sha256'] = g.digest(self.output / 'verdict-o01.json')
        self.flush()
        with self.assertRaisesRegex(e.github.EvidenceError, 'requires sealed index'):
            e.reevaluate(self.output, self.dest, ['o01:' + e.INDEX_PATH])

    def test_disclosed_index_must_match_head(self):
        anchor = self.out / 'cell/work'
        name = 'src/expiry/__init__.py'
        old_blob = g.git(anchor, 'rev-parse', 'HEAD^:' + name)
        g.git(anchor, 'update-index', '--cacheinfo', '100644,' + old_blob + ',' + name)
        before = e.census(self.output)
        with patch.object(e.github, 'done_check') as done:
            with self.assertRaises(e.github.EvidenceError):
                e.reevaluate(self.output, self.dest, ['o01:' + e.INDEX_PATH])
        done.assert_not_called()
        report = g.read(self.dest / 'reevaluation.json')
        self.assertEqual(report['raw_census'], dict(before=before, after=before, unchanged=True))
        change, = report['slots'][0]['disclosed_changes']
        self.assertEqual(change['equivalence_checks'], [
            dict(command=['git', 'diff', '--cached', '--quiet', 'HEAD'], passed=False)])
        self.assertFalse((self.dest / 'o01').exists())

    def test_disclosed_index_rejects_all_assume_unchanged_and_skip_worktree_tags(self):
        anchor = self.out / 'cell/work'
        index = anchor / '.git/index'
        original = index.read_bytes()
        for tag, flags in (('h', ['--assume-unchanged']), ('S', ['--skip-worktree']),
                           ('s', ['--skip-worktree', '--assume-unchanged'])):
            with self.subTest(tag=tag):
                for flag in flags:
                    g.git(anchor, 'update-index', flag, 'src/expiry/__init__.py')
                self.assertIn(tag + ' src/expiry/__init__.py', g.git(anchor, 'ls-files', '-v'))
                before = e.census(self.output)
                with patch.object(e.github, 'done_check') as done:
                    with self.assertRaisesRegex(e.github.EvidenceError, 'index has .* flags'):
                        e.reevaluate(self.output, self.dest, ['o01:' + e.INDEX_PATH])
                done.assert_not_called()
                report = g.read(self.dest / 'reevaluation.json')
                self.assertEqual(report['raw_census'], dict(before=before, after=before, unchanged=True))
                self.assertFalse(report['slots'][0]['disclosed_changes'][0]['equivalence_checks'][-1]['passed'])
                index.write_bytes(original)
                shutil.rmtree(self.dest)

    def test_only_dispatched_eligible_statuses_with_archives_are_evaluated(self):
        for row, status in zip(self.records[1:], ['PASS', 'STOP', 'UNKNOWN', 'NOT_RUN',
                                                'ADJUDICATE', 'PRODUCT_INCOMPLETE', 'STOP']):
            row.update(status=status, dispatched=status != 'NOT_RUN')
        self.records[0]['status'] = 'PRODUCT_INCOMPLETE'
        self.flush()
        with patch.object(e.github, 'done_check', wraps=e.github.done_check) as done:
            report = e.reevaluate(self.output, self.dest)
        done.assert_called_once()
        self.assertIsNone(done.call_args.kwargs['review'])
        self.assertEqual([row['cell'] for row in report['slots']], ['o01'])
        self.assertEqual(report['slots'][0]['corrected']['status'], 'ADJUDICATE')

    def test_inherited_product_failure_cannot_be_promoted(self):
        self.inherited['status'] = 'PRODUCT_INCOMPLETE'
        self.records[0]['status'] = 'PRODUCT_INCOMPLETE'
        self.seal()
        report = e.reevaluate(self.output, self.dest)
        self.assertEqual(report['slots'][0]['corrected']['status'], 'PRODUCT_INCOMPLETE')
        self.assertEqual(g.read(self.dest / 'o01/github-delivery.json')['status'], 'PRODUCT_INCOMPLETE')

    def test_mode_only_stale_input_invalidates_corrected_template(self):
        e.reevaluate(self.output, self.dest)
        marker = self.out / 'cell/work/.devlyn-install.json'
        marker.chmod(0o700)
        with self.assertRaisesRegex(e.github.EvidenceError, 'correction input changed'):
            e.summary.review_template(self.output, 'o01', self.dest)

    def test_corrupt_archive_is_rejected_before_done_check_and_raw_census_recorded(self):
        (self.output / 'archives/o01/repository.json').write_text('{}')
        before = e.census(self.output)
        with patch.object(e.github, 'done_check') as done:
            with self.assertRaisesRegex(e.github.EvidenceError, 'archive file census'):
                e.reevaluate(self.output, self.dest)
        done.assert_not_called()
        report = g.read(self.dest / 'reevaluation.json')
        self.assertEqual(report['status'], 'FAILED')
        self.assertEqual(report['raw_census'], dict(before=before, after=before, unchanged=True))
        self.assertFalse((self.dest / 'o01').exists())

    def test_changed_sealed_and_checked_inputs_are_rejected(self):
        for name in ('cell/work/src/expiry/__init__.py', 'snapshot/src/expiry/__init__.py',
                     'checks.json', 'evidence.manifest.json'):
            with self.subTest(name=name):
                path = self.out / name
                original = path.read_bytes()
                path.write_bytes(original + b'\n')
                with patch.object(e.github, 'done_check') as done:
                    with self.assertRaises(e.github.EvidenceError):
                        e.reevaluate(self.output, self.dest)
                done.assert_not_called()
                self.assertTrue(g.read(self.dest / 'reevaluation.json')['raw_census']['unchanged'])
                path.write_bytes(original)
                shutil.rmtree(self.dest)

    def test_changed_inherited_or_archive_binding_is_rejected(self):
        original = deepcopy(self.records[0])
        for field in ('inherited_verdict_sha256', 'archive'):
            with self.subTest(field=field):
                self.records[0][field] = 'stale' if field != 'archive' else dict(manifest_sha256='stale')
                self.flush()
                with self.assertRaisesRegex(e.github.EvidenceError, 'binding changed'):
                    e.reevaluate(self.output, self.dest)
                self.records[0] = deepcopy(original)
                shutil.rmtree(self.dest)

    def test_destination_must_be_new_and_disjoint_including_symlink_alias(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.output, target_is_directory=True)
        before = e.census(self.output)
        self.dest.mkdir()
        for dest in (self.output, self.output / 'new', self.root, alias / 'new', self.dest):
            with self.subTest(dest=dest), self.assertRaises(e.github.EvidenceError):
                e.reevaluate(self.output, dest)
        self.assertEqual(e.census(self.output), before)

    def test_census_includes_hidden_files_and_hashes_symlinks_without_following(self):
        link = self.output / '.external-link'
        link.symlink_to(self.root / 'absent')
        census = e.census(self.output)
        self.assertEqual(census['.external-link']['type'], 'symlink')
        self.assertIn('o01/cell/work/.git/config', census)
        link.unlink()
        link.symlink_to(self.root / 'different')
        self.assertNotEqual(e.census(self.output), census)

    def test_detects_unexpected_raw_mutation_and_withholds_corrected_files(self):
        done_check = e.github.done_check
        def changed(*args, **kwargs):
            done = done_check(*args, **kwargs)
            (self.output / 'unexpected-file').write_text('synthetic concurrent writer')
            return done
        with patch.object(e.github, 'done_check', side_effect=changed):
            with self.assertRaisesRegex(e.github.EvidenceError, 'changed during reevaluation'):
                e.reevaluate(self.output, self.dest)
        report = g.read(self.dest / 'reevaluation.json')
        self.assertEqual(report['status'], 'FAILED')
        self.assertFalse(report['raw_census']['unchanged'])
        self.assertFalse((self.dest / 'o01').exists())


if __name__ == '__main__':
    import unittest
    unittest.main()
