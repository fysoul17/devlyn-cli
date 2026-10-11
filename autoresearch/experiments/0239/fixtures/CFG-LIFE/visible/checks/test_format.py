import tempfile
import unittest
from pathlib import Path
from beacon import Loader, ConfigError

class FormatSmoke(unittest.TestCase):
    def test_invalid_document_shapes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'app.json'
            for value in ['[]', '{"values": []}', '{"include": "a.json"}', '{"unknown": 1}', '{broken']:
                path.write_text(value, encoding='utf-8')
                with self.subTest(value=value), self.assertRaises(ConfigError):
                    Loader().load(path)

    def test_empty_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'app.json'
            path.write_text('{}', encoding='utf-8')
            self.assertEqual(Loader().load(path).values, {})
