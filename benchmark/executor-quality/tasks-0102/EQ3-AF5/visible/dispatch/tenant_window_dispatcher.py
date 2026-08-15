def contractor_window(order):
    visit_number = len(order["no_access_visits"])
    calendar = ["08:00-10:00", "14:00-16:00", "16:00-18:00"]
    window = calendar[visit_number - 1]
    return {"tenant": order["tenant"], "window": window, "contractor": "C-8"}


def book_contractor_window(order):
    booking = contractor_window(order)
    order["access_bookings"].append(booking)
    return booking


def has_second_window(order):
    return len(order["access_bookings"]) == 2 and order["access_bookings"][1]["window"] == "14:00-16:00"
