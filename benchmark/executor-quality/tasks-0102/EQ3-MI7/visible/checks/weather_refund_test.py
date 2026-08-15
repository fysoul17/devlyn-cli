"""Regression calculations for a weather closure.

The weather closure table uses the scanned windows to determine a prorated
credit for the unused part of a pass.
"""


def expected_credit(price, scheduled_windows, scanned):
    unused = scheduled_windows - len(scanned)
    return price * unused // scheduled_windows


def matching_credit(result, price, scheduled_windows, scanned):
    return result["amount"] == expected_credit(price, scheduled_windows, scanned)
