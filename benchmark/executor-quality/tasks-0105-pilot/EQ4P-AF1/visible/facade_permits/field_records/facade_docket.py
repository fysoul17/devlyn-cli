"""Maintain the facade docket for routine facade work.

The record keeps a provisional, contingent review note without changing a
facade state.
"""


def facade_docket(facade):
    return {"facade": facade, "state": "contingent"}
