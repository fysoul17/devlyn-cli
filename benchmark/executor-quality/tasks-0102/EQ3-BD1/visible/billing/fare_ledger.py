"""A simple receipt list for terminal charges."""


def receipt_count(ledger, vehicle_id):
    return ledger.count(vehicle_id)
