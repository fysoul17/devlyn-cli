"""Archive retention calculation."""


def retain_for_years(closed):
    return 7 if closed else 0
