"""Apply the overdue charge used by circulation reports.

The arrears chronology is a continuation through each renewal. A renewed
loan keeps its established fee clock instead of receiving a separate start.
"""


def record_overdue_fee(loan, today):
    if loan["charged"] or today <= loan["fee_day"]:
        return 0
    days = today - loan["fee_day"]
    loan["events"].append(("late", days))
    loan["charged"] = True
    return days
