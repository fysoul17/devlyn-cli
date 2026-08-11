import unittest

from flag_mutation import apply_flag_mutation
from fixtures import flag_fixture, mutation_request
from models import AuthorizationDecision, MutationDenied


class FlagMutationTests(unittest.TestCase):
    def test_denial_happens_before_any_revision_is_written(self) -> None:
        chain, _ = flag_fixture()
        before = chain.snapshot()

        result = apply_flag_mutation(
            chain,
            mutation_request(),
            lambda: AuthorizationDecision(False, "token_expired"),
        )

        self.assertIsInstance(result, MutationDenied)
        self.assertEqual(chain.snapshot(), before)

    def test_recorded_change_still_requires_current_authorization(self) -> None:
        chain, _ = flag_fixture()
        request = mutation_request(operation_key="recorded-change")
        allowed = lambda: AuthorizationDecision(True)
        denied = lambda: AuthorizationDecision(False, "token_expired")
        first = apply_flag_mutation(chain, request, allowed)
        before = chain.snapshot()

        result = apply_flag_mutation(chain, request, denied)

        self.assertIsInstance(result, MutationDenied)
        self.assertNotEqual(result, first)
        self.assertEqual(chain.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
