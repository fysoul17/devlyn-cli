"""A compact directory for instructors."""


def coach_for(room):
    return {"studio-a": "Mina", "studio-b": "Jules"}.get(room, "Desk")
