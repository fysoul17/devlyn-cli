from __future__ import annotations

import unittest

from src.settings_actions import DEFAULT_SETTINGS


class SettingsDefaultsTests(unittest.TestCase):
    def test_defaults_are_stable(self) -> None:
        self.assertEqual(DEFAULT_SETTINGS, {"compact": False, "page_size": 25})


if __name__ == "__main__":
    unittest.main()
