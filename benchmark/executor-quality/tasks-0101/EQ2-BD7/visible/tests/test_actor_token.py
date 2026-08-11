import unittest

from fixtures import flag_fixture, mutation_request


class ActorTokenTests(unittest.TestCase):
    def test_expired_and_wrong_environment_tokens_are_denied(self) -> None:
        _, gateway = flag_fixture()
        request = mutation_request()

        self.assertEqual(gateway.authorize("token-old", request).reason, "token_expired")
        self.assertEqual(
            gateway.authorize("token-production", request).reason,
            "token_environment_denied",
        )

    def test_active_rotated_token_keeps_the_same_actor_grant(self) -> None:
        _, gateway = flag_fixture()
        request = mutation_request()

        self.assertTrue(gateway.authorize("token-current", request).authorized)
        self.assertTrue(gateway.authorize("token-rotated", request).authorized)


if __name__ == "__main__":
    unittest.main()
