"""Maintain the work order for routine facade work.

The record keeps a contingent review note without changing a facade state.
"""


def work_order(facade):
    return {"facade": facade, "state": "contingent"}
