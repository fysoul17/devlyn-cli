"""Summary calculations for the enrollment dashboard."""


def percentage(part, whole):
    return 0 if not whole else round(part * 100 / whole, 1)
