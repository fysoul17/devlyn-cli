"""Registry display fields kept outside the desk transaction."""


def display_name(record):
    return record.get("id", "unknown")
