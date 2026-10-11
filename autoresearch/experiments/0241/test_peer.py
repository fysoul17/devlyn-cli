#!/usr/bin/env python3
"""Model-free checks for the literal Codex configuration-key repair."""
import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / '0240'
SPEC = importlib.util.spec_from_file_location('peer0240_compatibility_tests', PREVIOUS / 'test_peer.py')
COMPAT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COMPAT)
COMPAT.HERE = HERE
COMPAT.LEGACY.HERE = HERE
COMPAT.FLAG = 'agents.enabled=false'


class LiteralRepairTests(unittest.TestCase):
    def test_helper_differs_only_by_the_approved_literal_replacement(self):
        previous = (PREVIOUS / 'peer.py').read_bytes()
        current = (HERE / 'peer.py').read_bytes()
        old = b'features.multi_agent=false'
        new = b'agents.enabled=false'
        self.assertEqual(previous.count(old), 1)
        self.assertEqual(current.count(new), 1)
        self.assertNotIn(old, current)
        self.assertEqual(current, previous.replace(old, new))


def load_tests(loader, tests, pattern):
    tests.addTests(loader.loadTestsFromTestCase(COMPAT.SinglePeerTests))
    return COMPAT.load_tests(loader, tests, pattern)


if __name__ == '__main__':
    unittest.main(verbosity=2)
