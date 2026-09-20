import subprocess
import sys
import unittest


class ExistingContract(unittest.TestCase):
    def test_existing_self_test(self):
        result = subprocess.run([sys.executable, '-B', 'package/terminal-claim-check.py', '--self-test'],
                                capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
