# Fernwell — station report

Summarises bike-share trips per station for the ops team.

## Layout

- `data/stations.csv` — the stations we report on (station_id, name).
- `data/trips.csv` — the trip log. Trips from station ids that are not in
  stations.csv are skipped by the loader.
- `report/loader.py` — `load_summaries()`, one `StationSummary` per known station.
- `report/renderer_text.py` — the plain-text report. **Other teams import
  `render_text` and diff its output**, so its formatting is a contract.
- `report/cli.py` — `python3 -m report.cli --format text`.

## Common commands

```
python3 -m report.cli --format text        # print the report
python3 -m unittest discover -s tests      # run the suite
```
