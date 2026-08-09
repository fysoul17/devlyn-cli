import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CheckDraftCommandTests(unittest.TestCase):
    def test_check_draft_prints_valid_slug(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            draft_path = Path(temporary) / "draft.json"
            draft_path.write_text(
                json.dumps({"title": "Weekly note", "slug": "weekly-note"}),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [sys.executable, str(ROOT / "cli.py"), "check-draft", str(draft_path)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                json.loads(completed.stdout), {"slug": "weekly-note", "valid": True}
            )


if __name__ == "__main__":
    unittest.main()
