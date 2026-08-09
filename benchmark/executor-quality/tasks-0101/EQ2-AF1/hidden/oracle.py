#!/usr/bin/env python3
import json
import pathlib
import sys


workdir = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(workdir))
from parking import assign_batch


invariant = "Parking requests are assigned by descending priority with arrival order breaking ties, every failed multi-slot request returns all tentative slots through the release pool, and when priority reordering places a release consumer before its failed producer in arrival order the higher-priority request still wins while the later-processed request can claim every returned slot."


ordered_one = assign_batch(
    [
        {"id": "low", "priority": 1, "slots": ["A"]},
        {"id": "high", "priority": 9, "slots": ["A"]},
    ],
    ["A"],
)
axis1_a = ordered_one["accepted"] == ["high"] and ordered_one["rejected"] == ["low"]

ordered_two = assign_batch(
    [
        {"id": "base", "priority": 3, "slots": ["A"]},
        {"id": "tie1", "priority": 8, "slots": ["B"]},
        {"id": "tie2", "priority": 8, "slots": ["C"]},
        {"id": "last", "priority": 1, "slots": ["A"]},
    ],
    ["A", "B", "C"],
)
axis1_b = ordered_two["accepted"] == ["tie1", "tie2", "base"]

released_one = assign_batch(
    [
        {"id": "bad", "priority": 5, "slots": ["A", "Z"]},
        {"id": "next", "priority": 5, "slots": ["A"]},
    ],
    ["A"],
)
axis2_a = released_one["accepted"] == ["next"] and released_one["rejected"] == ["bad"]

released_two = assign_batch(
    [
        {"id": "bad", "priority": 4, "slots": ["A", "B", "Z"]},
        {"id": "takea", "priority": 4, "slots": ["A"]},
        {"id": "takeb", "priority": 4, "slots": ["B"]},
    ],
    ["A", "B"],
)
axis2_b = released_two["accepted"] == ["takea", "takeb"] and released_two["rejected"] == ["bad"]

composed = assign_batch(
    [
        {"id": "low", "priority": 1, "slots": ["A"]},
        {"id": "later", "priority": 3, "slots": ["B"]},
        {"id": "middle", "priority": 6, "slots": ["B", "Z"]},
        {"id": "high", "priority": 9, "slots": ["A"]},
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
