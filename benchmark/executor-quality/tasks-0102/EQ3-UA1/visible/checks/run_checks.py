"""Run the visible regression case for this loan-desk ticket."""

import pathlib
import sys


ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from circulation.fee_escalator import record_overdue_fee
from loan_desk.renewal_intake import renew_loan


def sample(pending):
    return {
        "due": 18,
        "fee_day": 10,
        "charged": False,
        "events": [],
        "hold": {"pending": pending, "slot": 4, "requeued": 0},
    }


if __name__ == "__main__":
    normal = sample(False)
    assert renew_loan(normal, 20, record_overdue_fee) == {"accepted": True, "renewed": True}
    assert normal["due"] == 34 and normal["fee_day"] == 10
    blocked = sample(True)
    assert renew_loan(blocked, 20, record_overdue_fee) == {"accepted": False, "renewed": False}
    assert not blocked.get("renewed")
    assert blocked["due"] == 18 and blocked["hold"]["slot"] == 4
    assert blocked["events"] == [("late", 10)]
    print("loan-desk checks complete")
