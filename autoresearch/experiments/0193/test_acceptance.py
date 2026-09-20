from pathlib import Path
import runpy
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ConfigurationTests(unittest.TestCase):
    def test_broken_link_is_preserved(self):
        module = runpy.run_path(str(ROOT / 'package/role-config.py'))
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            work = Path(temporary); (work / '.devlyn').mkdir()
            path = work / '.devlyn/engines.json'; path.symlink_to('absent.json')
            for action in (lambda: module['resolve'](work, 'claude', available=lambda _: True),
                           lambda: module['edit'](work, 'worker', '{"engine":"codex"}')):
                with self.assertRaisesRegex(ValueError, 'BLOCKED:invalid-engine-config'):
                    action()
                self.assertTrue(path.is_symlink())
                self.assertEqual(str(path.readlink()), 'absent.json')

    def test_missing_and_valid_configuration(self):
        module = runpy.run_path(str(ROOT / 'package/role-config.py'))
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            work = Path(temporary)
            self.assertEqual(module['resolve'](work, 'claude', available=lambda _: True)['legacy_source'], 'default')
            module['edit'](work, 'worker', '{"engine":"codex"}')
            self.assertEqual(module['resolve'](work, 'claude', available=lambda _: True)['roles']['worker']['engine'], 'codex')
