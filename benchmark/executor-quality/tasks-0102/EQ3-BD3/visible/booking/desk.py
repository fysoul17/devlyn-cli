"""Small helpers used by the front desk."""


def open_seats(session):
    return session["capacity"] - len(session["booked_members"])


def attendee_names(session):
    return tuple(session["attendees"])
