"""Lane labels used by lift operations."""


def lane_for(window):
    return {"morning": "north", "midday": "summit", "afternoon": "valley"}[window]
