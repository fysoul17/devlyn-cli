"""Provenance regression fixtures through inherited accounting and STOP gates."""
import importlib.util
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner0241_tests', HERE / 'runner.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
inherited = r.load('runner0240_tests_reused', HERE.parent / '0240/test_runner.py')
inherited.r = r
inherited.HERE = HERE
fixtures = inherited.fixtures
fixtures.r = r


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ApparatusTests()
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.evidence = self.f.app.frame.cell_run.evidence
        (self.f.out / 'cell/work/.devlyn').mkdir(parents=True)
        (self.f.out / 'tmp').mkdir()

    def solo(self):
        self.f.plan['arm'] = 'B'
        r.write(self.f.out / 'plan.json', self.f.plan)

    def launch(self, command, output=''):
        path = self.f.out / 'run/stdout'
        rows = self.evidence.lines(path)
        fixtures.lines(path, rows + [dict(type='assistant', message=dict(content=[dict(
            type='tool_use', name='Bash', id='call', input=dict(command=command))])),
            dict(type='user', message=dict(content=[dict(type='tool_result', tool_use_id='call', content=output)]))])

    def stopped(self, result):
        self.assertEqual(result['status'], 'STOP')
        self.assertIsNone(result['input_tokens'])
        self.assertFalse((self.f.out / 'checks.json').exists())

    def test_witness_producer_and_custody_do_not_invent_claude_work(self):
        f = self.f
        f.receipt(); f.codex(child=False)
        folder = f.out / 'cell/work/.devlyn/pair'
        folder.mkdir()
        for name in ('peer-check.json', 'peer-any.json', 'verification.output.json'):
            # This is actual witness producer metadata, not a renamed model capture.
            r.write(folder / name, dict(command='python3 witness.py', exit_code=0))
        (folder / 'peer-broken.json').write_text('{not a model result')
        shutil.copytree(folder, f.out / 'cell/work/.git/devlyn-completion/test/custody/.devlyn/pair')
        self.launch("python3 witness.py > .devlyn/pair/verification.output.json")
        self.assertEqual(self.evidence.claude_envelopes(f.out), ({}, []))
        result = f.recorded_good_product()
        self.assertEqual((result['status'], result['usage']), ('CHECKS_PASS', 'COMPLETE'))
        self.assertEqual((result['input_tokens'], result['output_tokens']), (116, 14))

    def test_unregistered_envelope_content_still_requires_bound_native_session(self):
        self.solo()
        r.write(self.f.out / 'tmp/unexpected.jsonl', dict(type='result', session_id='stranger',
                modelUsage={'claude-opus-5-5': self.f.owner_usage}, is_error=False))
        envelopes, gaps = self.evidence.claude_envelopes(self.f.out)
        self.assertEqual(list(envelopes), ['stranger'])
        self.assertEqual(gaps, [])
        result = self.f.recorded_good_product(expected_return=2)
        self.stopped(result)
        self.assertTrue(any('stranger' in gap for gap in result['usage_gaps']))

    def test_receipt_capture_failures_remain_unknown(self):
        for case in ('missing', 'malformed', 'sessionless', 'counterless'):
            with self.subTest(case=case):
                f = fixtures.ApparatusTests(); f.setUp()
                try:
                    f.plan['arm'] = 'H'; r.write(f.out / 'plan.json', f.plan)
                    folder = f.receipt(engine='claude'); f.claude()
                    path = folder / 'peer1.json'
                    if case == 'missing': path.unlink()
                    elif case == 'malformed': path.write_text('not JSON')
                    else:
                        value = r.read(path)
                        del value['session_id' if case == 'sessionless' else 'modelUsage']
                        r.write(path, value)
                    result = f.recorded_good_product(expected_return=2)
                    self.assertEqual(result['status'], 'STOP')
                    self.assertIsNone(result['input_tokens'])
                    self.assertFalse((f.out / 'checks.json').exists())
                finally:
                    f.doCleanups()

    def test_actual_arbitrary_redirect_missing_malformed_and_counterless_stops(self):
        self.solo()
        self.launch('timeout -k 5s 540s claude -p --output-format json prompt > .devlyn/arbitrary.json')
        target = self.f.out / 'cell/work/.devlyn/arbitrary.json'
        for case in ('missing', 'malformed', 'sessionless', 'counterless'):
            with self.subTest(case=case):
                if case == 'malformed':
                    target.parent.mkdir(parents=True, exist_ok=True); target.write_text('not JSON')
                elif case in ('sessionless', 'counterless'):
                    value = dict(type='result', session_id='peer', modelUsage={'claude-opus-5-5': self.f.owner_usage})
                    del value['session_id' if case == 'sessionless' else 'modelUsage']
                    r.write(target, value)
                result = self.f.recorded_good_product(name=case, expected_return=2)
                self.stopped(result)

    def test_dynamic_launch_without_usage_carrier_explicitly_stops(self):
        self.solo()
        self.launch('claude -p --output-format json prompt > "$CAPTURE"')
        self.assertEqual(self.evidence.claude_envelopes(self.f.out), ({}, []))
        result = self.f.recorded_good_product(expected_return=2)
        self.stopped(result)
        self.assertTrue(any('owner-launched Claude peer turn' in gap for gap in result['usage_gaps']), result['usage_gaps'])

    def test_echoed_documented_redirects_do_not_create_expected_captures(self):
        self.solo()
        self.launch("echo 'claude -p --output-format json prompt > missing.json'\n"
                    "cat <<'DOC'\nclaude -p --output-format json prompt > absent.json\nDOC")
        self.assertEqual(self.evidence.claude_envelopes(self.f.out), ({}, []))
        # Only classification is asserted: historical launch diagnostics are unchanged.

    def test_literal_shell_paths_and_redirected_custody_copies(self):
        self.assertEqual(r.discovery.literal_redirects(
            'env KEY=value timeout -k 5s 540s /usr/bin/claude -p --output-format json prompt '
            '2> errors.json 1> ".devlyn/capture with spaces.json"'), ['.devlyn/capture with spaces.json'])
        self.solo()
        name = '.devlyn/ordinary-capture.json'
        self.launch('claude -p --output-format json prompt > ' + name)
        target = self.f.out / 'cell/work' / name
        r.write(target, dict(type='result', session_id='peer', modelUsage={'claude-opus-5-5': self.f.owner_usage}))
        custody = self.f.out / 'cell/work/.git/custody' / name
        custody.parent.mkdir(parents=True); shutil.copyfile(target, custody)
        envelopes, gaps = self.evidence.claude_envelopes(self.f.out)
        self.assertEqual(len(envelopes['peer']), 1)
        self.assertEqual(gaps, [])
        custody.write_text('corrupt native capture copy')
        self.assertEqual(self.evidence.claude_envelopes(self.f.out)[1], [str(custody.relative_to(self.f.out))])

    def test_legacy_failed_dispatch_is_not_erased(self):
        self.solo()
        r.write(self.f.out / 'cell/work/.devlyn/verify-judge.r1.dispatch.json',
                dict(roles=dict(reviewer=dict(decision='dispatch', engine='claude'))))
        result = self.f.recorded_good_product(expected_return=2)
        self.stopped(result)
        self.assertTrue(any('dispatched claude' in gap for gap in result['usage_gaps']), result['usage_gaps'])

    def test_absolute_participant_home_capture_and_missing_carrier(self):
        self.solo()
        target = self.f.out / 'home/capture.json'
        r.write(target, dict(type='result', session_id='peer', modelUsage={'claude-opus-5-5': self.f.owner_usage}))
        command = 'claude -p --output-format json prompt > /home/participant/capture.json'
        self.launch(command)
        self.assertEqual(r.discovery.redirected_paths(self.f.out, '/home/participant/capture.json'), {target.resolve()})
        envelopes, gaps = self.evidence.claude_envelopes(self.f.out)
        self.assertEqual(envelopes['peer'][0]['path'], 'home/capture.json')
        self.assertEqual(gaps, [])
        target.unlink()
        self.assertEqual(self.evidence.claude_envelopes(self.f.out), ({}, ['home/capture.json']))

    def test_other_home_paths_are_unsupported_not_reinterpreted(self):
        for target in ('/home/capture.json', '/home/other/capture.json',
                       '/home/participant-other/capture.json', '/home/participant/../capture.json'):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, 'unsupported Claude capture mount'):
                r.discovery.redirected_paths(self.f.out, target)

    def test_participant_home_redirect_cannot_read_outside_symlink(self):
        outside = self.f.root / 'outside-home.json'
        r.write(outside, dict(type='result', session_id='outside', modelUsage={'claude-opus-5-5': self.f.owner_usage}))
        (self.f.out / 'home/capture.json').symlink_to(outside)
        self.launch('claude -p --output-format json prompt > /home/participant/capture.json')
        original_read = Path.read_text
        def bounded_read(path, *args, **kwargs):
            self.assertNotEqual(path.resolve(), outside.resolve(), 'collector read outside retained evidence')
            return original_read(path, *args, **kwargs)
        with patch.object(Path, 'read_text', bounded_read):
            envelopes, gaps = self.evidence.claude_envelopes(self.f.out)
        self.assertEqual(envelopes, {})
        self.assertEqual(gaps, ['Claude capture escapes retained evidence: /home/participant/capture.json'])

    def test_redirect_paths_and_declared_symlinks_never_read_outside_evidence(self):
        self.solo()
        outside = self.f.root / 'outside.json'
        r.write(outside, dict(type='result', session_id='outside', modelUsage={'claude-opus-5-5': self.f.owner_usage}))
        original_read = Path.read_text
        def bounded_read(path, *args, **kwargs):
            self.assertNotEqual(path.resolve(), outside.resolve(), 'collector tried to read an unrelated host file')
            return original_read(path, *args, **kwargs)
        for target in ('../../../outside.json', 'a/../../../../outside.json', '/unsupported/outside.json'):
            with self.subTest(target=target), patch.object(Path, 'read_text', bounded_read):
                self.launch('claude -p --output-format json prompt > ' + target)
                envelopes, gaps = self.evidence.claude_envelopes(self.f.out)
                self.assertNotIn('outside', envelopes)
                self.assertTrue(gaps)
        self.assertEqual(r.discovery.redirected_paths(self.f.out, '../retained.json'),
                         {(self.f.out / 'cell/retained.json').resolve()})
        folder = self.f.receipt(engine='claude')
        capture = folder / 'peer1.json'
        capture.unlink(); capture.symlink_to(outside)
        with patch.object(Path, 'read_text', bounded_read):
            envelopes, gaps = self.evidence.claude_envelopes(self.f.out)
        self.assertNotIn('outside', envelopes)
        self.assertTrue(any('capture escapes' in gap for gap in gaps), gaps)

    def test_inventory_is_private_shared_and_new_discovery_is_sealed(self):
        self.assertIs(self.f.app.frame.usage.evidence, self.evidence)
        self.assertIs(self.evidence.claude_envelopes.func, r.discovery.claude_envelopes)
        historical = r.load('unchanged_evidence0241_test', HERE.parent / '0234/evidence.py')
        self.assertEqual(historical.claude_envelopes.__module__, 'unchanged_evidence0241_test')
        paths = self.f.app.inputs()
        target = HERE / 'capture_discovery.py'
        self.assertEqual(paths[str(target)], r.digest(target))
        original = r.digest
        with patch.object(r, 'digest', side_effect=lambda p: 'changed' if p == target else original(p)):
            self.assertNotEqual(self.f.app.inputs(), paths)

    def test_request_and_guides_are_byte_identical_to_0240(self):
        for name in ('guides/H.md', 'guides/P.md', 'guides/S.md', 'tasks-smoke.json'):
            self.assertEqual((HERE / name).read_bytes(), (HERE.parent / '0240' / name).read_bytes())


def load_tests(loader, tests, pattern):
    tests.addTests(loader.loadTestsFromTestCase(inherited.RunnerTests))
    return inherited.load_tests(loader, tests, pattern)


if __name__ == '__main__':
    unittest.main(verbosity=2)
