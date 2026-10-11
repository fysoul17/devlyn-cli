import tempfile
import unittest
from pathlib import Path
from beacon import Loader, ConfigManager, ConfigError
from helpers import write

class Smoke(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_flat_include_and_override(self):
        write(self.root, 'base.json', values={'port': 7000, 'mode': 'base'})
        root = write(self.root, 'app.json', include=['base.json'], values={'mode': 'app'})
        resolved = Loader().load(root)
        self.assertEqual(resolved.values, {'port': 7000, 'mode': 'app'})
        self.assertEqual(set(resolved.dependencies), {root, self.root / 'base.json'})

    def test_initial_manager(self):
        root = write(self.root, 'app.json', values={'port': 7000})
        manager = ConfigManager(root)
        self.assertIsNone(manager.current)
        self.assertEqual(manager.reload().generation, 1)
        self.assertEqual(manager.current.values, {'port': 7000})

    def test_missing_file(self):
        root = write(self.root, 'app.json', include=['missing.json'])
        with self.assertRaises(ConfigError) as raised:
            Loader().load(root)
        self.assertEqual(raised.exception.path, self.root / 'missing.json')
