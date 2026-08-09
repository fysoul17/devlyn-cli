import unittest

from access_policy import AccessPolicy
from models import RoomRequest


class AccessPolicyTests(unittest.TestCase):
    def test_pass_must_cover_room_zone(self):
        policy = AccessPolicy({"sam": {"shared"}}, {"atlas": "shared", "oak": "secure"})
        shared = RoomRequest("one", "sam", "atlas", 10, 20, 1, 0)
        secure = RoomRequest("two", "sam", "oak", 10, 20, 1, 1)

        self.assertTrue(policy.allows(shared))
        self.assertFalse(policy.allows(secure))


if __name__ == "__main__":
    unittest.main()
