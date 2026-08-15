"""Counter-level close checks."""


def closed(result, pass_record):
    return result["closed"] and not pass_record["active"]


def full_amount(result, pass_record):
    return result["amount"] == pass_record["price"]
