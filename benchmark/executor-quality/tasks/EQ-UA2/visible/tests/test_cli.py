import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ListCommandTests(unittest.TestCase):
    def test_list_prints_sorted_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog_path = Path(temporary) / "catalog.json"
            catalog_path.write_text('{"z.zip": {}, "a.zip": {}}\n', encoding="utf-8")

            completed = subprocess.run(
                [sys.executable, str(ROOT / "cli.py"), "list", str(catalog_path)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout), {"artifacts": ["a.zip", "z.zip"]})


if __name__ == "__main__":
    unittest.main()
