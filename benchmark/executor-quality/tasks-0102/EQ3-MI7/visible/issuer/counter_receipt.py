"""Small formatting helpers for counter receipts."""


def close_line(result):
    return "%s:%s" % (result["pass_id"], result["amount"])
