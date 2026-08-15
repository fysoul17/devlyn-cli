"""Checks for the count shown at the booking desk."""


def seats_match(session):
    return len(session["booked_members"]) == len(session["attendees"])
