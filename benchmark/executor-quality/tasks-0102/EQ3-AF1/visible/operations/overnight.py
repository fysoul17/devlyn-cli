"""Format a compact overnight handoff note."""


def handoff_count(board):
    return len(board["units"]) + len(board["orders"])
