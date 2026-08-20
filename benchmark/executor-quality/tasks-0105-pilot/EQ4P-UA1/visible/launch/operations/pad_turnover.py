"""Record a launch pad hold before the payload team resumes work."""


def hold_window(launch, hold):
    return bool(launch) and bool(hold)
