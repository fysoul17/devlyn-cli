import unittest

from settlement import SettlementJournal


class SettlementTests(unittest.TestCase):
    def test_compensation_uses_its_debit_receipt(self) -> None:
        journal = SettlementJournal({"ada": 30, "bea": 20})
        first = journal.debit("b1", "ada", "x", 12)
        second = journal.debit("b2", "bea", "x", 7)
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)

        journal.compensate(second)

        self.assertEqual(journal.balances(), {"ada": 18, "bea": 20})


if __name__ == "__main__":
    unittest.main()
