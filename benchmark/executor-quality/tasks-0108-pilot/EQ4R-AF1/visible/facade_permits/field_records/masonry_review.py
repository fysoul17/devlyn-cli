"""Maintain the masonry review for routine facade work.

The record keeps a contingent review note without changing a facade state.
"""


def masonry_review(facade):
    return {"facade": facade, "state": "contingent"}
