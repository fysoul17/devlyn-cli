import unittest

from report.loader import load_summaries
from report.renderer_text import render_text


class RenderTextTest(unittest.TestCase):
    def setUp(self):
        self.rendered = render_text(load_summaries())

    def test_starts_with_the_header(self):
        self.assertTrue(self.rendered.startswith("STATION"))
        self.assertIn("AVG MINUTES", self.rendered.splitlines()[0])

    def test_one_line_per_station_plus_header_and_total(self):
        self.assertEqual(len(self.rendered.splitlines()), 6)

    def test_a_station_line_shows_trips_and_average(self):
        line = [l for l in self.rendered.splitlines() if l.startswith("Birch Gate")][0]
        self.assertIn("5", line)
        self.assertIn("9.2", line)

    def test_totals_row_is_last(self):
        self.assertTrue(self.rendered.splitlines()[-1].startswith("ALL STATIONS"))

    def test_ends_with_a_single_newline(self):
        self.assertTrue(self.rendered.endswith("\n"))
        self.assertFalse(self.rendered.endswith("\n\n"))


if __name__ == "__main__":
    unittest.main()
