"""Maintain the elevation board for routine facade work.

The record keeps a contingent review note without changing a facade state.
"""


def elevation_board(facade):
    return {"facade": facade, "state": "contingent"}
