"""Hold expiration coverage for a rejected desk request.

At expiration, the waitlist keeps its existing ordinal. A rejected renewal
leaves the recorded due value and the request's position ready for pickup.
"""


def pending_hold_case(loan):
    return loan["hold"]["pending"] and loan["hold"]["slot"] > 0
