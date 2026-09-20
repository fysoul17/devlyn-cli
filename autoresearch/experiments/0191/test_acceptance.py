"""Public regression against the actual packaged module, with local fixtures."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RecoveryTests(unittest.TestCase):
    def invoke(self, project):
        return subprocess.run(['node', '-e',
            "require(process.argv[1]).updateInstructions('AGENTS.md')",
            str(ROOT / 'package/bin/instructions.js')], cwd=project,
            capture_output=True, timeout=20)

    def test_backup_rejects_link_without_writing_target(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            base = Path(temp)
            project = base / 'project'; project.mkdir()
            target = base / 'target'; target.mkdir()
            original = b'\xef\xbb\xbf# Local rules\r\nKeep these bytes.\r\n'
            (project / 'AGENTS.md').write_bytes(original)
            (project / '.devlyn').symlink_to(target, target_is_directory=True)
            result = self.invoke(project)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((project / 'AGENTS.md').read_bytes(), original)
            self.assertEqual(list(target.iterdir()), [])
            self.assertTrue((project / '.devlyn').is_symlink())
            self.assertIn(b'.devlyn', result.stderr)

    def test_normal_backup_and_repeat(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            project = Path(temp)
            original = b'\xef\xbb\xbf# Local rules\r\nKeep these bytes.\r\n'
            dest = project / 'AGENTS.md'; dest.write_bytes(original)
            first = self.invoke(project)
            self.assertEqual(first.returncode, 0, first.stderr)
            after = dest.read_bytes()
            self.assertTrue(after.startswith(original))
            backups = list((project / '.devlyn/instructions').glob('*.backup'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), original)
            second = self.invoke(project)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(dest.read_bytes(), after)
            self.assertEqual(list((project / '.devlyn/instructions').glob('*.backup')), backups)


if __name__ == '__main__':
    unittest.main()
