import unittest

from src.catalog import command


class CatalogTests(unittest.TestCase):
    def test_existing_command_is_available(self) -> None:
        self.assertEqual(command("export")["timeout_seconds"], 60)
