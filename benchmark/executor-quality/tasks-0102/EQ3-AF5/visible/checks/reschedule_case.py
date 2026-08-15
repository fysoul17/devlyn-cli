def can_rebook(order):
    return order["status"] == "scheduled" and order["requested_date"] == "2026-09-18"
