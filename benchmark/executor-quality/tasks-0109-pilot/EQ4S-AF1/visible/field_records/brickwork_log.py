"""Maintain the brickwork log for routine facade work.

The record keeps a contingent review note without changing a facade state.
"""


def brickwork_log(facade):
    return {"facade": facade, "state": "contingent"}
