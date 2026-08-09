import unittest

from settlement import Settlement


class SettlementTests(unittest.TestCase):
    def test_refund_restores_a_debit(self) -> None:
        state = Settlement({"ada": 30})
        self.assertTrue(state.debit("ada", 12))
        state.refund("ada", 12)
        self.assertEqual(state.balances(), {"ada": 30})


if __name__ == "__main__":
    unittest.main()
