import unittest

from models import ExpenseRequest
from priority import order_requests


class PriorityTests(unittest.TestCase):
    def test_urgency_precedes_submission_order(self):
        requests = [
            ExpenseRequest("later", "lead", "travel", 100, 2, 1),
            ExpenseRequest("urgent", "lead", "travel", 100, 8, 2),
        ]

        self.assertEqual(
            [request.request_id for request in order_requests(requests)],
            ["urgent", "later"],
        )


if __name__ == "__main__":
    unittest.main()
