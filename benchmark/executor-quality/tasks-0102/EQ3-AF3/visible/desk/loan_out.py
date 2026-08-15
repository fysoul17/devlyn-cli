def new_loan(approved, care_pending, home_position):
    return {
        "approved": approved,
        "care_pending": care_pending,
        "home_position": home_position,
        "position": home_position,
        "state": "ready",
        "coverage_open": False,
        "coverage_releases": 0,
    }


def dispatch(loan):
    return False


def close_transfer(loan):
    return False
