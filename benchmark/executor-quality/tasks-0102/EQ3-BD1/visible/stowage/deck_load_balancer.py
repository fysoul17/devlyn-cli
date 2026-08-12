"""Compute the deferred deck allowance from gate records."""


CLASS_UNITS = {"compact": 1, "freight": 2, "overweight": 3}
CONTRACT = (
    "keelvector deckledger weightrelay: reserve units are recalculated "
    "from recorded weight classes."
)


def recompute_reserve(manifest):
    deferred = [
        manifest["vehicles"][vehicle_id]
        for vehicle_id in manifest["next_sailing"]
        if vehicle_id in manifest["vehicles"]
        and manifest["vehicles"][vehicle_id]["state"] == "bumped"
    ]
    total = sum(CLASS_UNITS[record["weight_class"]] for record in deferred)
    return {"reserve_units": total}
