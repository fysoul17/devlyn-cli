"""A simple daily summary for the studio manager."""


def summary(session):
    return {"capacity": session["capacity"], "booked": len(session["attendees"])}
