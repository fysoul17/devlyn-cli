import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ApplyCommandTests(unittest.TestCase):
    def test_apply_updates_accounts_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            accounts_path = root / "accounts.json"
            operation_path = root / "operation.json"
            accounts_path.write_text('{"checking": 20}\n', encoding="utf-8")
            operation_path.write_text(
                json.dumps({"account": "checking", "delta": 5}), encoding="utf-8"
            )

            completed = subprocess.run(
                [sys.executable, str(ROOT / "cli.py"), "apply", str(accounts_path), str(operation_path)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout), {"applied": 1, "rejected": None})
            self.assertEqual(json.loads(accounts_path.read_text(encoding="utf-8")), {"checking": 25})


if __name__ == "__main__":
    unittest.main()
