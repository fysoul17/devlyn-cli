#!/usr/bin/env python3
"""Model-free checks for both prospective Codex peer capability overrides."""
import importlib.util
import json
import os
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    'peer0240_compatibility_tests', HERE.parent / '0240' / 'test_peer.py')
COMPAT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPAT)
COMPAT.BASE = HERE.parent / '0241'
COMPAT.HERE = HERE
COMPAT.LEGACY.HERE = HERE
COMPAT.FLAG = 'features.multi_agent_v2.enabled=false'


class DualOverrideTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'posix', 'fake executables use the POSIX host')
    def test_fresh_and_resume_dispatch_and_receipts_contain_both_overrides_once(self):
        fixture = COMPAT.LEGACY.PeerTests()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        for resume in (None, 'codex-test'):
            with self.subTest(resume=resume):
                out = fixture.root / ('resume' if resume else 'fresh')
                result = fixture.invoke('codex', out=out, resume=resume)
                self.assertEqual(result.returncode, 0, result.stderr)
                call = json.loads(fixture.called.read_text(encoding='utf-8'))
                actual = call['argv']
                settings = [actual[i + 1] for i, value in enumerate(actual) if value == '-c']
                relevant = [value for value in settings if value.startswith(
                    ('agents.enabled=', 'features.multi_agent_v2.enabled='))]
                self.assertEqual(relevant, ['agents.enabled=false', COMPAT.FLAG])
                self.assertEqual(call['cwd'], str(fixture.repo))
                attempt, completion = fixture.receipt(out)
                self.assertEqual(attempt['argv'][1:], actual)
                self.assertEqual(attempt['resume'], resume)
                self.assertEqual(completion['status'], 'EXITED')
                self.assertEqual(completion['exit_code'], 0)
                self.assertTrue(completion['source_unchanged'])
                self.assertEqual((out / attempt['capture']).read_bytes(), fixture.expected.read_bytes())
                self.assertEqual((out / 'finalanswer.txt').read_text(encoding='utf-8').strip(),
                                 COMPAT.LEGACY.ANSWER)


def load_tests(loader, tests, pattern):
    for name in (
        'test_codex_fresh_and_resume_have_only_the_single_peer_override',
        'test_claude_fresh_and_resume_arguments_are_unchanged',
    ):
        tests.addTest(COMPAT.SinglePeerTests(name))
    return COMPAT.load_tests(loader, tests, pattern)


if __name__ == '__main__':
    unittest.main(verbosity=2)
