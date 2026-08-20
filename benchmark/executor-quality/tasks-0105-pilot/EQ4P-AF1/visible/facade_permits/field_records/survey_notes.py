"""Maintain the survey notes for routine facade work.

The record keeps a contingent review note without changing a facade state.
"""


def survey_notes(facade):
    return {"facade": facade, "state": "contingent"}
