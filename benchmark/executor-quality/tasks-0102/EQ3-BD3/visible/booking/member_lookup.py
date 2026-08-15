"""Member lookups supplied to the booking desk."""


def display_name(member):
    return member.replace("-", " ").title()
