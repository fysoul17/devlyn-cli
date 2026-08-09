import unittest

from models import ExpenseRequest
from reviewers import Reviewer, choose_reviewer


class ReviewerTests(unittest.TestCase):
    def test_least_loaded_eligible_reviewer_wins(self):
        reviewers = [Reviewer("A", ("travel",)), Reviewer("B", ("travel",))]
        request = ExpenseRequest("trip", "lead", "travel", 500, 4, 1)

        selected = choose_reviewer(reviewers, request, {"A": 2, "B": 1})

        self.assertEqual(selected.name, "B")


if __name__ == "__main__":
    unittest.main()
