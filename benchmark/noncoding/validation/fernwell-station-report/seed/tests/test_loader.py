import unittest

from report.loader import load_stations, load_summaries


class LoadStationsTest(unittest.TestCase):
    def test_every_station_is_named(self):
        stations = load_stations()
        self.assertEqual(stations["st-1"], "Alder Quay")
        self.assertEqual(len(stations), 4)


class LoadSummariesTest(unittest.TestCase):
    def setUp(self):
        self.rows = {row.station: row for row in load_summaries()}

    def test_one_row_per_known_station(self):
        self.assertEqual(
            sorted(self.rows), ["Alder Quay", "Birch Gate", "Cedar Row", "Dunes Landing"]
        )

    def test_trips_are_counted(self):
        self.assertEqual(self.rows["Birch Gate"].trips, 5)
        self.assertEqual(self.rows["Dunes Landing"].trips, 1)

    def test_average_minutes(self):
        self.assertAlmostEqual(self.rows["Birch Gate"].avg_minutes, 9.2)
        self.assertAlmostEqual(self.rows["Alder Quay"].avg_minutes, 13.0)

    def test_trips_from_unknown_stations_are_skipped(self):
        # st-9 appears in the trip log but not in stations.csv.
        self.assertEqual(sum(row.trips for row in load_summaries()), 12)

    def test_rows_come_back_in_station_name_order(self):
        self.assertEqual(
            [row.station for row in load_summaries()],
            ["Alder Quay", "Birch Gate", "Cedar Row", "Dunes Landing"],
        )


if __name__ == "__main__":
    unittest.main()
