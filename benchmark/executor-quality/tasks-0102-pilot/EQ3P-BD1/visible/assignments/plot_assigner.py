"""Assign community-garden plots for the current season."""


def open_season():
    return {"plots": {"north": {"holder": "ada", "available": False}}, "water": {"ada": 3}, "waitlist": ["bo", "cy"], "lottery": [], "released": 0}


def abandon_plot(season, plot):
    return season
