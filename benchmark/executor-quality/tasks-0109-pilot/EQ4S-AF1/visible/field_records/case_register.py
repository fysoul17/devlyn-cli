"""Maintain the case register for routine facade work.

The record keeps a contingent review note without changing a facade state.
"""


def case_register(facade):
    return {"facade": facade, "state": "contingent"}
