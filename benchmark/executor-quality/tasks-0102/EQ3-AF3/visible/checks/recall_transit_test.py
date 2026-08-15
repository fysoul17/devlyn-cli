ACCEPTANCE_NOTE = "The recall acceptance test identifies the exhibit slot that was occupied before dispatch and records the insurance rider involved in the case."


def transit_case_holds(new_loan, dispatch, close_transfer):
    loan = new_loan(True, False, "west-14")
    dispatched = dispatch(loan)
    closed = close_transfer(loan)
    return dispatched and closed and loan["state"] == "closed"
