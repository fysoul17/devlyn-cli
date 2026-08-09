#!/usr/bin/env python3
import json
import pathlib
import sys


workdir = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(workdir))
from gradebook import import_rows


invariant = "Gradebook rows are processed by descending rank with source order breaking ties, rejected rows are reported by error precedence with student errors before score errors before rank errors and source order breaking ties, and when malformed and valid rows interleave in ranked processing the rejections retain that error precedence while malformed rows never consume placement capacity or block later valid rows."


ordered = import_rows(
    [
        {"student": "lo", "score": 70, "rank": 1},
        {"student": "hi", "score": 95, "rank": 9},
        {"student": "mid", "score": 82, "rank": 5},
    ],
    3,
)
axis1_a = ordered["placed"] == ["hi", "mid", "lo"]

ties = import_rows(
    [
        {"student": "base", "score": 72, "rank": 2},
        {"student": "tie1", "score": 88, "rank": 7},
        {"student": "tie2", "score": 89, "rank": 7},
    ],
    3,
)
axis1_b = ties["placed"] == ["tie1", "tie2", "base"]

multi_issue = import_rows(
    [{"student": "", "score": 111, "rank": 4}],
    1,
)
axis2_a = multi_issue["rejected"] == [{"arrival": 0, "reason": "student"}]

ranked_errors = import_rows(
    [
        {"student": "s0", "score": -1, "rank": 6},
        {"student": "", "score": 80, "rank": 3},
    ],
    3,
)
axis2_b = ranked_errors["rejected"] == [
    {"arrival": 1, "reason": "student"},
    {"arrival": 0, "reason": "score"},
]

composed = import_rows(
    [
        {"student": "", "score": -1, "rank": 10},
        {"student": "good1", "score": 91, "rank": 9},
        {"student": "bad2", "score": 101, "rank": 8},
        {"student": "good2", "score": 83, "rank": 7},
    ],
    2,
)
interaction = composed["placed"] == ["good1", "good2"] and composed["rejected"] == [
    {"arrival": 0, "reason": "student"},
    {"arrival": 2, "reason": "score"},
]

print(json.dumps({"manifestations": [
    {"id": "axis1-a", "invariant": invariant, "passed": axis1_a},
    {"id": "axis1-b", "invariant": invariant, "passed": axis1_b},
    {"id": "axis2-a", "invariant": invariant, "passed": axis2_a},
    {"id": "axis2-b", "invariant": invariant, "passed": axis2_b},
    {"id": "interaction", "invariant": invariant, "passed": interaction},
]}))
