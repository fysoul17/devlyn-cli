import unittest

from reservation import reserve_batch


class ReservationTests(unittest.TestCase):
    def test_single_request_is_committed(self) -> None:
        output = reserve_batch([{"id": "r1", "priority": 3, "seats": ["A"]}], ["A"])
        self.assertEqual(output["accepted"], ["r1"])
        self.assertEqual(output["assignments"], {"r1": ["A"]})


if __name__ == "__main__":
    unittest.main()
