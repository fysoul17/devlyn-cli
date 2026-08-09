import unittest

from models import ExpenseRequest
from role_gate import is_authorized


class RoleGateTests(unittest.TestCase):
    def test_grant_covers_center_and_amount(self):
        request = ExpenseRequest("trip", "lead", "travel", 500, 4, 1)
        grants = {"lead": {"travel": 750}}

        self.assertTrue(is_authorized(request, grants))
        self.assertFalse(is_authorized(request, {"lead": {"travel": 400}}))


if __name__ == "__main__":
    unittest.main()
