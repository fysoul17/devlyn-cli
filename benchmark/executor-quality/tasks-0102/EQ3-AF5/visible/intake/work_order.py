def new_order(order_id, tenant, requested_date):
    return {
        "id": order_id,
        "tenant": tenant,
        "requested_date": requested_date,
        "status": "access_missed",
        "clock_opened_at": 100,
        "no_access_visits": [],
        "access_bookings": [],
        "fee_waivers": [],
    }


def reschedule_order(order, requested_date):
    order["requested_date"] = requested_date
    return False


def record_no_access(order, happened_at):
    order["clock_opened_at"] = happened_at
    order["no_access_visits"].append(happened_at)
    order["status"] = "access_missed"
    return False
