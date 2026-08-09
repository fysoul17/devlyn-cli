import unittest

from approval_router import route_expenses
from models import ExpenseRequest, RoutedExpense
from reviewers import Reviewer


class ApprovalRouterTests(unittest.TestCase):
    def test_routes_an_authorized_request(self):
        request = ExpenseRequest("trip", "lead", "travel", 500, 4, 1)
        result = route_expenses(
            [request],
            {"lead": {"travel": 750}},
            [Reviewer("A", ("travel",))],
        )

        self.assertEqual(result, [RoutedExpense("trip", "A", 1)])


if __name__ == "__main__":
    unittest.main()
