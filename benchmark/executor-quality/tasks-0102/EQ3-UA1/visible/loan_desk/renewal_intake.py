"""Record requests made at the library loan desk."""


TERM_DAYS = 14


def renew_loan(loan, today, record_fee):
    loan["due"] = today + TERM_DAYS
    return {"accepted": True}
