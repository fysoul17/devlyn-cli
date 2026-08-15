"""Pay-period labels for class administration."""


def period_label(day):
    return f"week-{day // 7 + 1}"
