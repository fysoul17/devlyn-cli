#!/usr/bin/env python3
import json
import pathlib
import sys


workdir = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(workdir))
from reservation import reserve_batch


invariant = "Seat holds are processed by descending priority with arrival order breaking ties, every failed request releases all tentative seats, and when reordering makes a middle request fail after a partial hold the higher-priority request still wins while a later request can use every released seat."


ordering_one = reserve_batch(
    [
        {"id": "low", "priority": 1, "seats": ["A"]},
        {"id": "high", "priority": 9, "seats": ["A"]},
    ],
    ["A"],
)
axis1_a = ordering_one["accepted"] == ["high"] and ordering_one["rejected"] == ["low"]

ordering_two = reserve_batch(
    [
        {"id": "lowa", "priority": 1, "seats": ["A"]},
        {"id": "lowb", "priority": 2, "seats": ["B"]},
        {"id": "topa", "priority": 9, "seats": ["A"]},
        {"id": "topb", "priority": 8, "seats": ["B"]},
    ],
    ["A", "B"],
)
axis1_b = ordering_two["accepted"] == ["topa", "topb"]

rollback_one = reserve_batch(
    [{"id": "bad", "priority": 4, "seats": ["A", "Z"]}],
    ["A"],
)
axis2_a = rollback_one["rejected"] == ["bad"] and rollback_one["available"] == ["A"]

rollback_two = reserve_batch(
    [
        {"id": "bad", "priority": 5, "seats": ["B", "Z"]},
        {"id": "next", "priority": 5, "seats": ["B"]},
    ],
    ["B"],
)
axis2_b = rollback_two["accepted"] == ["next"] and rollback_two["rejected"] == ["bad"]

composed = reserve_batch(
    [
        {"id": "low", "priority": -1, "seats": ["A"]},
        {"id": "high", "priority": 10, "seats": ["A"]},
        {"id": "middle", "priority": 5, "seats": ["B", "A"]},
        {"id": "later", "priority": 0, "seats": ["B"]},
    ],
    ["A", "B"],
)
interaction = composed["accepted"] == ["high", "later"] and composed["rejected"] == ["middle", "low"]

print(json.dumps({"manifestations": [
    {"id": "axis1-a", "invariant": invariant, "passed": axis1_a},
    {"id": "axis1-b", "invariant": invariant, "passed": axis1_b},
    {"id": "axis2-a", "invariant": invariant, "passed": axis2_a},
    {"id": "axis2-b", "invariant": invariant, "passed": axis2_b},
    {"id": "interaction", "invariant": invariant, "passed": interaction},
]}))
