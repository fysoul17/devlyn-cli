import unittest

from syntax_ranking import build_ranked_plan


class SyntaxRankingTests(unittest.TestCase):
    def test_reports_owner_before_value(self):
        result = build_ranked_plan([
            {"change": "bad-value", "owner": "v.example.", "type": "A", "value": "bad", "priority": 9},
            {"change": "bad-owner", "owner": "missing-dot", "type": "TXT", "value": "ok", "priority": 1},
        ])
        self.assertEqual(result["rejected"], [
            {"source": 1, "reason": "owner"},
            {"source": 0, "reason": "value"},
        ])


if __name__ == "__main__":
    unittest.main()
