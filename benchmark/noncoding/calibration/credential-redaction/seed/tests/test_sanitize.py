import unittest

from src.format_event import format_event
from src.sanitize import sanitize


class SanitizerTests(unittest.TestCase):
    def test_existing_secret_keys(self) -> None:
        self.assertEqual(
            sanitize({"password": "p", "api_key": "k", "name": "n"}),
            {"password": "[redacted]", "api_key": "[redacted]", "name": "n"},
        )

    def test_adapter_delegates(self) -> None:
        self.assertEqual(format_event({"password": "p"}), '{"password": "[redacted]"}')


if __name__ == "__main__":
    unittest.main()
