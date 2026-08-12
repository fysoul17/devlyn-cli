"""Produce a tiny daily intake summary."""


def summary(board):
    return {"units": len(board["units"]), "orders": len(board["orders"])}
