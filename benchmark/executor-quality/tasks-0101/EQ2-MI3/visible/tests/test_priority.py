import unittest

from models import RoomRequest
from priority import order_requests


class PriorityTests(unittest.TestCase):
    def test_priority_descends_and_ties_keep_submission_order(self):
        requests = [
            RoomRequest("low", "sam", "atlas", 10, 20, 1, 0),
            RoomRequest("first", "sam", "atlas", 20, 30, 5, 1),
            RoomRequest("second", "sam", "atlas", 30, 40, 5, 2),
        ]

        self.assertEqual(
            ["first", "second", "low"],
            [request.request_id for request in order_requests(requests)],
        )


if __name__ == "__main__":
    unittest.main()
