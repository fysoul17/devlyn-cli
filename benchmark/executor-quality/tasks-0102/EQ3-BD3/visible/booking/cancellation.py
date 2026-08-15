"""Booking-desk operations for a scheduled class."""


def new_session(capacity, award_after):
    return {
        "capacity": capacity,
        "booked_members": [],
        "attendees": [],
        "settled": [],
        "award_after": award_after,
        "credits": [],
        "refunds": [],
    }


def add_member(session, member):
    if len(session["booked_members"]) == session["capacity"] or member in session["attendees"]:
        return False
    session["attendees"].append(member)
    session["booked_members"].append(member)
    return True


def finalize_attendance(session):
    session["settled"] = session["booked_members"]


def cancel_booking(session, member, cancelled_at):
    if member not in session["attendees"]:
        return False
    session["attendees"].remove(member)
    return True
