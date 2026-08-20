"""Maintain the heritage queue for routine facade work.

The record keeps a contingent review note without changing a facade state.
"""


def heritage_queue(facade):
    return {"facade": facade, "state": "contingent"}
