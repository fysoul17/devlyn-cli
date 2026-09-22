"""Failure evidence must survive transport compaction; no model calls."""
import importlib.util
from pathlib import Path
import tempfile
import json
from unittest.mock import patch
import unittest

spec = importlib.util.spec_from_file_location('packet', Path(__file__).with_name('packet.py'))
packet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packet)
SUCCESS = "# Subtest: succeeds\nok 1 - succeeds\n  ---\n  duration_ms: 1.2\n  type: 'test'\n  ...\n"
FAILURE = "not ok 2 - fails\n  ---\n  error: |-\n    ok 1 - embedded literal\n    # Subtest: embedded literal\n  ...\n"
FOOTER = '1..2\n# tests 2\n# suites 0\n# pass 1\n# fail 1\n# cancelled 0\n# skipped 0\n# todo 0\n# duration_ms 3\n'


class PacketTests(unittest.TestCase):
    def test_failures_unknown_output_directives_and_counts_survive(self):
        keep = 'unexpected stdout\nBail out! diagnostic\nok 3 - later # SKIP reason\n'
        raw = 'TAP version 13\n' + SUCCESS + FAILURE + keep + FOOTER
        compact = packet.compact_tap(raw)
        self.assertNotIn(SUCCESS, compact)
        for text in (FAILURE, keep, FOOTER):
            self.assertIn(text, compact)

    def test_unknown_or_truncated_failure_is_never_compacted(self):
        raw = 'TAP version 13\n' + SUCCESS + FAILURE + FOOTER
        for invalid in (raw[:-20], raw.replace('  ...\n', '', 1).replace('  ...\n', ''),
                        raw.replace(FAILURE, ''), raw.replace('TAP version 13', 'unrecognized')):
            self.assertEqual(packet.compact_tap(invalid), invalid)

    def test_unknown_success_diagnostics_survive(self):
        extra = SUCCESS.replace('  ...', '  error: must remain\n  ...')
        raw = 'TAP version 13\n' + extra + FAILURE + FOOTER
        self.assertIn('ok 1 - succeeds\n  ---\n', packet.compact_tap(raw))
        self.assertIn('error: must remain', packet.compact_tap(raw))

    def test_copied_review_omitted_but_originals_unchanged(self):
        with tempfile.TemporaryDirectory() as name:
            work = Path(name)
            review = work / '.devlyn/reviews/call-1/answer.txt'
            review.parent.mkdir(parents=True)
            review.write_text('prior verdict')
            checks = work / '.devlyn/checks-final'
            checks.mkdir()
            (checks / 'review.stdout').write_text('prior verdict\n')
            (checks / 'tests.stdout').write_text('TAP version 13\n' + SUCCESS + FAILURE + FOOTER)
            before = {p: p.read_bytes() for p in work.rglob('*') if p.is_file()}
            result = '\n'.join(packet.checks(work))
            self.assertNotIn('prior verdict', result)
            self.assertIn('sha256=', result)
            self.assertIn(FAILURE, result)
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_assessor_preserves_duration_lines_in_source_diff_and_diagnostics(self):
        spec = importlib.util.spec_from_file_location('assess', Path(__file__).with_name('assess.py'))
        assess = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(assess)
        with tempfile.TemporaryDirectory() as name:
            cell = Path(name)
            work = cell / 'work'
            (work / '.devlyn/checks-final').mkdir(parents=True)
            (work / 'source.txt').write_text('duration_ms: important source\n')
            (work / '.devlyn/caller.json').write_text(json.dumps(dict(
                request='retain evidence', allowed=['source.txt'], review_files=['source.txt'])))
            diagnostic = FAILURE.replace('  error:', '  duration_ms: 0.596833\n  error:')
            (work / '.devlyn/checks-final/test.stdout').write_text('TAP version 13\n' + SUCCESS + diagnostic + FOOTER)
            (cell / 'local-seal.json').write_text('{"eligible_for_assessment": true}')
            (cell / 'checks.json').write_text('{}')
            runtime = cell / 'runtime.json'
            runtime.write_text('{"scratch": "unused"}')
            # Stop exactly before credentials/model dispatch; inspect the real written prompt.
            with patch.object(assess.subprocess, 'check_output', return_value='+duration_ms: important diff\n'), \
                    patch.object(assess.tempfile, 'TemporaryDirectory', side_effect=RuntimeError('test dispatch barrier')):
                with self.assertRaisesRegex(RuntimeError, 'test dispatch barrier'):
                    assess.assess(cell, runtime)
            prompt = (cell / 'assessment/.devlyn/reviews/call-1/prompt.txt').read_text()
            for required in ('duration_ms: important source', '+duration_ms: important diff', diagnostic, FOOTER):
                self.assertIn(required, prompt)


if __name__ == '__main__':
    unittest.main()
