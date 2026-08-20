"""Allocate an approved examination arrangement and its dependent seat plan."""

from accommodation_allocator.services.allocation_dispatch import record_allocation, seat_plan_for


def apply_accommodation_change(case):
    previous = case["accommodation"]
    case["accommodation"] = case["replacement"]
    case["seat_plan"] = seat_plan_for(case["accommodation"], "assigned")
    record_allocation(case, previous)
    case["seat_open"] = False
    return {"allocated": True, "available": False}
