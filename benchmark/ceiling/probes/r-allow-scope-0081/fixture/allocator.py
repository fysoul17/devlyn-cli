"""Allocate a fixed resource pool across incoming requests."""


def allocate(requests, capacity):
    accepted, rejected = [], []
    remaining = capacity
    for req in requests:
        if req["amount"] <= remaining:
            remaining -= req["amount"]
            accepted.append(req["id"])
        else:
            rejected.append(req["id"])
    return {"accepted": accepted, "rejected": rejected, "remaining": remaining}
