import unittest

from record_applier import apply_changes


class RecordApplierTests(unittest.TestCase):
    def test_applies_valid_changes_by_priority(self):
        result = apply_changes([
            {"change": "later", "owner": "later.example.", "type": "A", "value": "192.0.2.1", "priority": 1},
            {"change": "first", "owner": "first.example.", "type": "A", "value": "192.0.2.2", "priority": 8},
        ])
        self.assertEqual([item["change"] for item in result["placed"]], ["first", "later"])


if __name__ == "__main__":
    unittest.main()
