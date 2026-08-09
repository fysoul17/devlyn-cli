#!/usr/bin/env python3
import json
import pathlib
import sys


workdir = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(workdir))
from transcode_queue import run_queue


invariant = "Manifest dedup schedules encoder-feed entries by descending priority with arrival order breaking ties, absorbs every repeated submission ID exactly once, and when a duplicate submission surrounds a priority reorder the dependent manifest output preserves that priority order while containing only one manifest for the repeated entity regardless of its arrival slot."


def execute(submissions: list[dict], existing: list[str] | None = None) -> dict:
    try:
        return run_queue(submissions, existing)
    except NotImplementedError:
        return {}


ordered_one = execute(
    [
        {"id": "low", "asset": "a", "priority": 1},
        {"id": "high", "asset": "b", "priority": 9},
    ]
)
axis1_a = ordered_one.get("scheduled") == ["high", "low"] and ordered_one.get("priorities") == [9, 1]

ordered_two = execute(
    [
        {"id": "low", "asset": "a", "priority": 1},
        {"id": "tie1", "asset": "b", "priority": 6},
        {"id": "tie2", "asset": "c", "priority": 6},
    ]
)
axis1_b = ordered_two.get("scheduled") == ["tie1", "tie2", "low"]

repeated_one = execute(
    [
        {"id": "clip", "asset": "a", "priority": 4},
        {"id": "clip", "asset": "a", "priority": 4},
        {"id": "next", "asset": "b", "priority": 2},
    ]
)
axis2_a = repeated_one.get("scheduled") == ["clip", "next"] and repeated_one.get("records") == ["clip", "next"]

repeated_two = execute(
    [
        {"id": "old", "asset": "a", "priority": 5},
        {"id": "new", "asset": "b", "priority": 2},
    ],
    ["old"],
)
axis2_b = repeated_two.get("scheduled") == ["new"] and repeated_two.get("records") == ["old", "new"]

composed = execute(
    [
        {"id": "movie", "asset": "cut-a", "priority": 1},
        {"id": "spot", "asset": "ad", "priority": 9},
        {"id": "movie", "asset": "cut-a", "priority": 7},
        {"id": "promo", "asset": "teaser", "priority": 5},
    ]
)
interaction = (
    composed.get("scheduled") == ["spot", "movie", "promo"]
    and composed.get("priorities") == [9, 7, 5]
    and composed.get("records") == ["spot", "movie", "promo"]
)

print(json.dumps({"manifestations": [
    {"id": "axis1-a", "invariant": invariant, "passed": axis1_a},
    {"id": "axis1-b", "invariant": invariant, "passed": axis1_b},
    {"id": "axis2-a", "invariant": invariant, "passed": axis2_a},
    {"id": "axis2-b", "invariant": invariant, "passed": axis2_b},
    {"id": "interaction", "invariant": invariant, "passed": interaction},
]}))
