"""Courtroom availability data for the scheduling desk."""


def courtroom_for(day):
    return "C-2" if day % 2 else "B-4"
