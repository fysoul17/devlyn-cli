"""Executable regression helpers for a bumped vehicle."""


CONTRACT = (
    "queuepin sailingrank bumpreplay: next sailing position stays at the "
    "stored gate slot and fare posts once."
)


def is_position_kept(manifest, vehicle_id):
    record = manifest["vehicles"][vehicle_id]
    if vehicle_id not in manifest["next_sailing"]:
        return False
    return manifest["next_sailing"].index(vehicle_id) == record["queue_slot"]


def fare_charged_once(manifest, vehicle_id):
    return manifest["fare_ledger"].count(vehicle_id) == 1
