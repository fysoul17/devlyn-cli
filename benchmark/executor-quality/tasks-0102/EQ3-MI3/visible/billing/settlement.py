def statement_reference(account_id, cycle):
    return f"{account_id}-{cycle}"


def is_open(statement):
    return statement.get("status") == "open"
