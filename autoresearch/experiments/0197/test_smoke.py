from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'config/skills/_shared/task-complete.py'


class HistorySmoke(unittest.TestCase):
    def test_empty_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(['git', 'init', '-q', tmp], check=True)
            result = subprocess.run([sys.executable, '-B', str(CLI), 'history', '--repo', tmp], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(json.loads(result.stdout), {key: [] for key in ('runs', 'task_evidence', 'programs', 'pending_reconcile', 'unowned_artifacts')})
            self.assertFalse((Path(tmp) / '.devlyn').exists())


if __name__ == '__main__':
    unittest.main()
