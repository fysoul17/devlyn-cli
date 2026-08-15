"""Cabinet helpers for props stored near the wings."""


def shelf_for(prop):
    return "clock-shelf" if prop.startswith("clock") else "book-shelf"
