"""Batch parking assignment."""

from allocator import SlotAllocator
from models import normalize_request


def assign_batch(requests: list[dict], slots: list[str]) -> dict:
    normalized = [normalize_request(request) for request in requests]
    allocator = SlotAllocator(slots)
    accepted: list[str] = []
    rejected: list[str] = []

    for request in normalized:
        complete = True
        for slot in request["slots"]:
            if not allocator.claim(request["id"], slot):
                complete = False
                break
        if not complete:
            rejected.append(request["id"])
            continue
        allocator.commit(request["id"])
        accepted.append(request["id"])

    return {
        "accepted": accepted,
        "rejected": rejected,
        "available": allocator.available(),
    }
