"""The late-cancel policy issues a class credit once, rather than a refund,
when a member cancels inside the published cutoff.
"""


def credit_once(session, member):
    return session["credits"] == [member] and not session["refunds"]
