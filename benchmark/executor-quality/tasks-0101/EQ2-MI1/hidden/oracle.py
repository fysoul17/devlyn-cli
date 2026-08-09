#!/usr/bin/env python3
import json
import pathlib
import sys


workdir = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(workdir))
from auction import settle_round


invariant = "Bid book entries settle by descending amount with arrival order breaking ties, every rejected claim refunds its tentative debit, and when reordering makes a middle bid fail after its debit the highest bid still wins while a later bid from the refunded account can settle another lot."


ordering_one = settle_round(
    [
        {"id": "low", "bidder": "lo", "lot": "x", "amount": 10},
        {"id": "high", "bidder": "hi", "lot": "x", "amount": 90},
    ],
    {"lo": 20, "hi": 100},
)
axis1_a = ordering_one["accepted"] == ["high"] and ordering_one["sold"] == {"x": "high"}

ordering_two = settle_round(
    [
        {"id": "lowa", "bidder": "la", "lot": "a", "amount": 10},
        {"id": "lowb", "bidder": "lb", "lot": "b", "amount": 20},
        {"id": "topa", "bidder": "ta", "lot": "a", "amount": 80},
        {"id": "topb", "bidder": "tb", "lot": "b", "amount": 70},
    ],
    {"la": 20, "lb": 30, "ta": 90, "tb": 80},
)
axis1_b = ordering_two["accepted"] == ["topa", "topb"]

rollback_one = settle_round(
    [{"id": "bad", "bidder": "sam", "lot": "x", "amount": 40, "fee": 5}],
    {"sam": 45},
    {"x": "old"},
)
axis2_a = rollback_one["rejected"] == ["bad"] and rollback_one["balances"] == {"sam": 45}

rollback_two = settle_round(
    [
        {"id": "bad", "bidder": "sam", "lot": "x", "amount": 40, "fee": 5},
        {"id": "next", "bidder": "sam", "lot": "y", "amount": 40, "fee": 5},
    ],
    {"sam": 45},
    {"x": "old"},
)
axis2_b = rollback_two["accepted"] == ["next"] and rollback_two["balances"] == {"sam": 0}

composed = settle_round(
    [
        {"id": "low", "bidder": "lo", "lot": "x", "amount": 10},
        {"id": "high", "bidder": "hi", "lot": "x", "amount": 100, "fee": 5},
        {"id": "middle", "bidder": "shared", "lot": "x", "amount": 60, "fee": 5},
        {"id": "later", "bidder": "shared", "lot": "y", "amount": 36, "fee": 4},
    ],
    {"lo": 20, "hi": 200, "shared": 100},
)
interaction = (
    composed["accepted"] == ["high", "later"]
    and composed["rejected"] == ["middle", "low"]
    and composed["sold"] == {"x": "high", "y": "later"}
    and composed["balances"]["shared"] == 60
)

print(json.dumps({"manifestations": [
    {"id": "axis1-a", "invariant": invariant, "passed": axis1_a},
    {"id": "axis1-b", "invariant": invariant, "passed": axis1_b},
    {"id": "axis2-a", "invariant": invariant, "passed": axis2_a},
    {"id": "axis2-b", "invariant": invariant, "passed": axis2_b},
    {"id": "interaction", "invariant": invariant, "passed": interaction},
]}))
