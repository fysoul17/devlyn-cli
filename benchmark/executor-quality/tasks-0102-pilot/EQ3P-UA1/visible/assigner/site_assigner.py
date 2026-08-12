"""Assign booking sites; the ticket assumes a site move has no charge."""


def move_site(booking, target):
    booking["site"] = target
    return {"site": target, "notice": "move recorded"}


def cancel_booking(booking):
    booking["cancelled"] = True
    return {"cancelled": True}
