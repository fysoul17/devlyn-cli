import unittest

from ledger import LedgerError, apply_operation


class ApplyOperationTests(unittest.TestCase):
    def test_applies_valid_operation(self) -> None:
        accounts = {"checking": 20}

        apply_operation(accounts, {"account": "checking", "delta": -5})

        self.assertEqual(accounts, {"checking": 15})

    def test_rejects_negative_balance_without_mutation(self) -> None:
        accounts = {"checking": 20}

        with self.assertRaisesRegex(LedgerError, "insufficient funds"):
            apply_operation(accounts, {"account": "checking", "delta": -25})

        self.assertEqual(accounts, {"checking": 20})


if __name__ == "__main__":
    unittest.main()
