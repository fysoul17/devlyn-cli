"""Maintain the permit ledger for routine facade work.

The record keeps a contingent review note without changing a facade state.
"""


def permit_ledger(facade):
    return {"facade": facade, "state": "contingent"}
