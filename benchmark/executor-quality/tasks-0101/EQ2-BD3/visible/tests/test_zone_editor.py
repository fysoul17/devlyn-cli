import unittest

from zone_editor import edit_zone


class ZoneEditorTests(unittest.TestCase):
    def test_returns_placed_and_rejected_rows(self):
        result = edit_zone([
            {"change": "good", "owner": "good.example.", "type": "TXT", "value": "ready", "priority": 3},
            {"change": "bad", "owner": "bad.example.", "type": "MX", "value": "mail.example.", "priority": 2},
        ])
        self.assertEqual(result, {
            "placed": ["good"],
            "rejected": [{"source": 1, "reason": "type"}],
        })


if __name__ == "__main__":
    unittest.main()
