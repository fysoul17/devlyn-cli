# Expense approval contract

Expense requests are routed by descending urgency with submission order breaking ties, the role gate admits only submitters whose grants cover the request's cost center and amount, and when privileged and unprivileged requests interleave the role gate decides authorization before priority placement and reviewer-load assignment so denied requests never consume a reviewer's ordered slot.
