import unittest

from fixtures import flag_fixture, mutation_request


class FlagRevisionChainTests(unittest.TestCase):
    def test_append_records_a_versioned_flag_change(self) -> None:
        chain, _ = flag_fixture()
        request = mutation_request()

        outcome = chain.append(request)

        self.assertEqual(outcome.revision, 1)
        self.assertTrue(outcome.enabled)
        self.assertEqual(chain.recorded(request.operation_key), outcome)
        self.assertEqual(len(chain.snapshot()["revisions"]), 1)


if __name__ == "__main__":
    unittest.main()
