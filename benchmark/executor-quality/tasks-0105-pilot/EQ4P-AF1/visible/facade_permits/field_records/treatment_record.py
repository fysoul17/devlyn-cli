"""Maintain the treatment record for routine facade work.

The record keeps a contingent review note without changing a facade state.
"""


def treatment_record(facade):
    return {"facade": facade, "state": "contingent"}
