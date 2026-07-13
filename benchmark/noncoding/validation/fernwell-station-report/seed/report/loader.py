"""Load the trip log and summarise it per station."""

import csv
import os
from collections import namedtuple

DATA_DIR = "data"
STATIONS_PATH = os.path.join(DATA_DIR, "stations.csv")
TRIPS_PATH = os.path.join(DATA_DIR, "trips.csv")

#: One summary row per station. avg_minutes is a float; renderers decide how to show it.
StationSummary = namedtuple(
    "StationSummary", ["station", "trips", "total_minutes", "avg_minutes"]
)


def load_stations(path=STATIONS_PATH):
    """Return {station_id: name} for every station we know about."""
    with open(path, newline="", encoding="utf-8") as handle:
        return {row["station_id"]: row["name"] for row in csv.DictReader(handle)}


def load_summaries(trips_path=TRIPS_PATH, stations_path=STATIONS_PATH):
    """Summarise the trip log, one row per known station, ordered by station name.

    A trip whose station_id is not in stations.csv is skipped: the ops team logs
    trips from decommissioned docks that the report must not invent stations for.
    """
    stations = load_stations(stations_path)
    trips = {}
    minutes = {}

    with open(trips_path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            station_id = row["station_id"]
            if station_id not in stations:
                continue
            trips[station_id] = trips.get(station_id, 0) + 1
            minutes[station_id] = minutes.get(station_id, 0) + int(row["minutes"])

    summaries = []
    for station_id, count in trips.items():
        total = minutes[station_id]
        summaries.append(
            StationSummary(
                station=stations[station_id],
                trips=count,
                total_minutes=total,
                avg_minutes=total / count,
            )
        )
    summaries.sort(key=lambda summary: summary.station)
    return summaries
