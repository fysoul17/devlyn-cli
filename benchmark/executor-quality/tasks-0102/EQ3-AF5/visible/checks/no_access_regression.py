def noaccess_clock_has_continuity(order, original):
    sla_clock = order["clock_opened_at"]
    return sla_clock == original


def waived_once(order):
    return order["fee_waivers"] == [{"order": order["id"], "amount": 75}]
