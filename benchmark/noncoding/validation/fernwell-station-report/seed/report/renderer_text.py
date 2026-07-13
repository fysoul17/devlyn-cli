"""The plain-text station report.

Two other teams import render_text and diff its output in their own pipelines, so
its formatting is a contract: it does not change.
"""

HEADER = "%-16s %5s %12s" % ("STATION", "TRIPS", "AVG MINUTES")
ROW = "%-16s %5d %12.1f"


def render_text(rows):
    """Render summary rows as the plain-text report, one line per station."""
    lines = [HEADER]
    for row in rows:
        lines.append(ROW % (row.station, row.trips, row.avg_minutes))

    total_trips = sum(row.trips for row in rows)
    total_minutes = sum(row.total_minutes for row in rows)
    overall_avg = total_minutes / total_trips if total_trips else 0.0
    lines.append(ROW % ("ALL STATIONS", total_trips, overall_avg))

    return "\n".join(lines) + "\n"
