import unittest

from fixtures import flag_fixture, mutation_request
from models import MutationDenied


class ActorTokenGatewayTests(unittest.TestCase):
    def test_active_token_rotation_replays_one_flag_revision(self) -> None:
        _, gateway = flag_fixture()
        request = mutation_request()

        first = gateway.mutate_flag(request, "token-current")
        second = gateway.mutate_flag(request, "token-rotated")

        self.assertEqual(second, first)
        self.assertEqual(len(gateway.state["revisions"]), 1)

    def test_expired_retry_cannot_read_an_authorized_result(self) -> None:
        _, gateway = flag_fixture()
        request = mutation_request(operation_key="rotation-check")
        committed = gateway.mutate_flag(request, "token-current")
        before = gateway.state

        denied = gateway.mutate_flag(request, "token-old")
        replayed = gateway.mutate_flag(request, "token-rotated")

        self.assertIsInstance(denied, MutationDenied)
        self.assertEqual(replayed, committed)
        self.assertEqual(gateway.state, before)


if __name__ == "__main__":
    unittest.main()
