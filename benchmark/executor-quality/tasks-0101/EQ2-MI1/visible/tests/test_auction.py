import unittest

from auction import settle_round


class AuctionTests(unittest.TestCase):
    def test_single_bid_settles(self) -> None:
        bid = {"id": "b1", "bidder": "ada", "lot": "x", "amount": 20, "fee": 2}
        output = settle_round([bid], {"ada": 30})
        self.assertEqual(output["accepted"], ["b1"])
        self.assertEqual(output["balances"], {"ada": 8})
        self.assertEqual(output["sold"], {"x": "b1"})


if __name__ == "__main__":
    unittest.main()
