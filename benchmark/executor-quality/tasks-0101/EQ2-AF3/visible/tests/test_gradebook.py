import unittest

from gradebook import import_rows


class GradebookTests(unittest.TestCase):
    def test_single_valid_row_is_placed(self) -> None:
        result = import_rows([{"student": "s1", "score": 90, "rank": 4}], 1)
        self.assertEqual(result["placed"], ["s1"])
        self.assertEqual(result["rejected"], [])


if __name__ == "__main__":
    unittest.main()
