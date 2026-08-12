"""Vehicle check-in state kept at the terminal gate."""


def open_manifest():
    return {
        "vehicles": {
            "sedan-2": {"state": "queued", "weight_class": "compact", "queue_slot": 0},
            "truck-8": {"state": "queued", "weight_class": "overweight", "queue_slot": 1},
            "moped-4": {"state": "queued", "weight_class": "compact", "queue_slot": 2},
        },
        "current_sailing": ["sedan-2", "truck-8", "moped-4"],
        "next_sailing": ["van-11", "bus-5", "trailer-6"],
        "bumped": [],
        "fare_ledger": [],
        "booking_units": {"truck-8": 3},
    }


def close_gate(manifest, vehicle_id):
    record = manifest["vehicles"][vehicle_id]
    if record["state"] != "queued":
        return manifest
    if record["weight_class"] == "overweight":
        return manifest
    record["state"] = "boarded"
    return manifest
