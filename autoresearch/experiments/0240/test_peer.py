#!/usr/bin/env python3
"""Model-free compatibility checks for the prospective single-peer launcher."""
import importlib.util
import json
import os
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
BASE = HERE.parent / '0238'
SPEC = importlib.util.spec_from_file_location('peer0238_compatibility_tests', BASE / 'test_peer.py')
LEGACY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LEGACY)
LEGACY.HERE = HERE  # Reuse fixtures while installing only the prospective helper.
FLAG = 'features.multi_agent=false'


class SinglePeerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = runpy.run_path(str(BASE / 'peer.py'))
        cls.after = runpy.run_path(str(HERE / 'peer.py'))

    def test_codex_fresh_and_resume_have_only_the_single_peer_override(self):
        for resume in (None, 'exact-session-id'):
            with self.subTest(resume=resume):
                args = ('codex', 'registered-model', 'max', Path('/repo with spaces'), '원본 prompt', resume)
                previous = self.before['argv_for'](*args)
                current = self.after['argv_for'](*args)
                self.assertEqual(current.count(FLAG), 1)
                position = current.index(FLAG)
                self.assertEqual(current[position - 1], '-c')
                self.assertEqual(current[:position - 1] + current[position + 1:], previous)

    def test_claude_fresh_and_resume_arguments_are_unchanged(self):
        for resume in (None, 'exact-session-id'):
            with self.subTest(resume=resume), patch('uuid.uuid4', return_value='fixed-session-id'):
                args = ('claude', 'registered-model', 'max', Path('/repo'), '원본 prompt', resume)
                self.assertEqual(self.after['argv_for'](*args), self.before['argv_for'](*args))
                self.assertNotIn(FLAG, self.after['argv_for'](*args))

    @unittest.skipUnless(os.name == 'posix', 'fake executables use the POSIX host')
    def test_fake_codex_dispatch_and_receipts_include_override_on_both_turns(self):
        fixture = LEGACY.PeerTests()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        for resume in (None, 'codex-test'):
            with self.subTest(resume=resume):
                out = fixture.root / ('resume' if resume else 'fresh')
                result = fixture.invoke('codex', out=out, resume=resume)
                self.assertEqual(result.returncode, 0, result.stderr)
                actual = json.loads(fixture.called.read_text(encoding='utf-8'))['argv']
                self.assertEqual(actual.count(FLAG), 1)
                self.assertEqual(actual[actual.index(FLAG) - 1], '-c')
                attempt, completion = fixture.receipt(out)
                self.assertEqual(attempt['argv'][1:], actual)
                self.assertEqual(attempt['resume'], resume)
                self.assertEqual(completion['status'], 'EXITED')
                self.assertEqual(completion['exit_code'], 0)
                self.assertTrue(completion['source_unchanged'])
                self.assertEqual((out / attempt['capture']).read_bytes(), fixture.expected.read_bytes())


def load_tests(loader, tests, pattern):
    for name in (
        'test_original_native_stdout_stderr_and_final_answer',
        'test_source_change_is_recorded_and_fails',
        'test_fresh_output_is_required_without_dispatch',
        'test_terminal_error_or_missing_terminal_never_succeeds',
    ):
        tests.addTest(LEGACY.PeerTests(name))
    return tests


if __name__ == '__main__':
    unittest.main(verbosity=2)
