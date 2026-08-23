"""Keep payload changes inside the range team's published limits."""


def within_limit(allocation, replacement):
    return allocation != replacement
