"""Maintain the drawing index for routine facade work.

The record keeps a contingent review note without changing a facade state.
"""


def drawing_index(facade):
    return {"facade": facade, "state": "contingent"}
