"""Small report helper for the circulation counter."""


def overdue_count(loans, today):
    return sum(loan["due"] < today for loan in loans)
