"""Allocate the replacement payload at the payload window."""

from payload_window.services.swap_dispatch import record_swap


def apply_payload_swap(launch):
    previous = launch["allocation"]
    launch["allocation"] = launch["replacement"]
    record_swap(launch, previous)
    launch["slot_open"] = True
    return {"accepted": True, "held": False}
