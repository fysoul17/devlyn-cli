"""Maintain the archive calendar for routine facade work.

The record keeps a contingent review note without changing a facade state.
"""


def archive_calendar(facade):
    return {"facade": facade, "state": "contingent"}
