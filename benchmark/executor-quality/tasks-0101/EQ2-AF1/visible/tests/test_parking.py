import unittest

from parking import assign_batch


class ParkingTests(unittest.TestCase):
    def test_single_request_is_assigned(self) -> None:
        result = assign_batch([{"id": "car", "priority": 2, "slots": ["P1"]}], ["P1"])
        self.assertEqual(result["accepted"], ["car"])
        self.assertEqual(result["available"], [])


if __name__ == "__main__":
    unittest.main()
