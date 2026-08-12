"""Manage the lightweight request line used by the desk."""


def requeue_hold(loan):
    hold = loan["hold"]
    hold["slot"] += 1
    hold["requeued"] += 1
    return hold["slot"]
