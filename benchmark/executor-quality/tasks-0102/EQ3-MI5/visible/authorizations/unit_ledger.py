def remaining_units(state):
    return state["units_left"]


def debit_rows(state, fill_id):
    return [row for row in state["debits"] if row["fill_id"] == fill_id]
