def approved_case(dispatch, new_loan):
    loan = new_loan(True, False, "east-02")
    return dispatch(loan) and loan["state"] == "in_transit"
