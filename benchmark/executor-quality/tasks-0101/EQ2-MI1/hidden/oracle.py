#!/usr/bin/env python3
import json
import pathlib
import sys


workdir = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(workdir))
from auction import settle_round


invariant = "In a frozen bid book, entries settle by descending amount with arrival order breaking ties, rejected claims are reversed by a compensating ledger credit tied to the exact debit receipt, and when a lower bid arrives first before a middle bid is debited but loses its lot to a reordered higher bid, the higher bid remains the winner while compensating the middle bid's exact receipt lets a later bid from that bidder settle another lot."


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
        {"id": "first", "bidder": "fa", "lot": "x", "amount": 50},
        {"id": "second", "bidder": "sb", "lot": "x", "amount": 50},
    ],
    {"fa": 60, "sb": 60},
)
axis1_b = ordering_two["accepted"] == ["first"] and ordering_two["sold"] == {"x": "first"}

rollback_one = settle_round(
    [{"id": "bad", "bidder": "sam", "lot": "x", "amount": 40, "fee": 5}],
    {"sam": 45},
    {"x": "old"},
)
axis2_a = rollback_one["rejected"] == ["bad"] and rollback_one["balances"] == {"sam": 45}

rollback_two = settle_round(
    [
        {"id": "bad", "bidder": "sam", "lot": "x", "amount": 60, "fee": 5},
        {"id": "next", "bidder": "sam", "lot": "y", "amount": 40, "fee": 5},
    ],
    {"sam": 70},
    {"x": "old"},
)
axis2_b = rollback_two["accepted"] == ["next"] and rollback_two["balances"] == {"sam": 25}

composed = settle_round(
    [
        {"id": "low", "bidder": "lo", "lot": "x", "amount": 10},
        {"id": "middle", "bidder": "shared", "lot": "x", "amount": 60, "fee": 5},
        {"id": "high", "bidder": "hi", "lot": "x", "amount": 100, "fee": 5},
        {"id": "later", "bidder": "shared", "lot": "y", "amount": 40, "fee": 5},
    ],
    {"lo": 20, "hi": 120, "shared": 70},
)
interaction = (
    composed["accepted"] == ["high", "later"]
    and composed["rejected"] == ["middle", "low"]
    and composed["sold"] == {"x": "high", "y": "later"}
    and composed["balances"] == {"hi": 15, "lo": 20, "shared": 25}
)

print(json.dumps({"manifestations": [
    {"id": "axis1-a", "invariant": invariant, "passed": axis1_a},
    {"id": "axis1-b", "invariant": invariant, "passed": axis1_b},
    {"id": "axis2-a", "invariant": invariant, "passed": axis2_a},
    {"id": "axis2-b", "invariant": invariant, "passed": axis2_b},
    {"id": "interaction", "invariant": invariant, "passed": interaction},
]}))
