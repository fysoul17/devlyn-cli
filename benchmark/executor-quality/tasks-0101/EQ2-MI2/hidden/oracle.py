#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys


workdir = pathlib.Path(sys.argv[1])
runner = r'''import { pathToFileURL } from "node:url";
const modulePath = pathToFileURL(process.argv[1]).href;
const { scheduleFanout } = await import(modulePath);
const submissions = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(scheduleFanout(submissions)));
'''
invariant = "The scheduler emits notifications by the highest priority seen for each notification with first submission order breaking ties, the delivery dedup records each notification-recipient pair exactly once, and when a duplicate submission surrounds a priority reorder the fanout preserves that effective priority order while delivering the repeated notification once per recipient regardless of the duplicate's arrival slot."


def schedule(submissions):
    completed = subprocess.run(
        [
            "node",
            "--input-type=module",
            "--eval",
            runner,
            str(workdir / "scheduler.js"),
            json.dumps(submissions),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10,
    )
    if completed.returncode != 0:
        return []
    return json.loads(completed.stdout)


def signature(deliveries):
    return [[item["id"], item["recipient"], item["priority"]] for item in deliveries]


ordered_one = schedule([
    {"id": "low", "body": "l", "priority": 1, "recipients": ["a"]},
    {"id": "high", "body": "h", "priority": 9, "recipients": ["b"]},
    {"id": "mid", "body": "m", "priority": 4, "recipients": ["c"]},
])
axis1_a = signature(ordered_one) == [["high", "b", 9], ["mid", "c", 4], ["low", "a", 1]]

ordered_two = schedule([
    {"id": "one", "body": "1", "priority": 6, "recipients": ["a", "b"]},
    {"id": "two", "body": "2", "priority": 6, "recipients": ["c"]},
    {"id": "top", "body": "t", "priority": 8, "recipients": ["d"]},
])
axis1_b = signature(ordered_two) == [
    ["top", "d", 8],
    ["one", "a", 6],
    ["one", "b", 6],
    ["two", "c", 6],
]

repeated_one = schedule([
    {"id": "note", "body": "n", "priority": 5, "recipients": ["a", "b"]},
    {"id": "note", "body": "n", "priority": 5, "recipients": ["a", "b"]},
])
axis2_a = signature(repeated_one) == [["note", "a", 5], ["note", "b", 5]]

repeated_two = schedule([
    {"id": "memo", "body": "m", "priority": 3, "recipients": ["a", "a", "b"]},
    {"id": "memo", "body": "m", "priority": 3, "recipients": ["a", "a", "b"]},
])
axis2_b = signature(repeated_two) == [["memo", "a", 3], ["memo", "b", 3]]

late_raise = schedule([
    {"id": "pulse", "body": "p", "priority": 2, "recipients": ["ann"]},
    {"id": "alert", "body": "a", "priority": 7, "recipients": ["ops"]},
    {"id": "pulse", "body": "p", "priority": 9, "recipients": ["bo", "ann"]},
    {"id": "later", "body": "l", "priority": 1, "recipients": ["zo"]},
])
early_raise = schedule([
    {"id": "pulse", "body": "p", "priority": 9, "recipients": ["bo", "ann"]},
    {"id": "alert", "body": "a", "priority": 7, "recipients": ["ops"]},
    {"id": "pulse", "body": "p", "priority": 2, "recipients": ["ann"]},
    {"id": "later", "body": "l", "priority": 1, "recipients": ["zo"]},
])
interaction = (
    signature(late_raise) == [
        ["pulse", "ann", 9],
        ["pulse", "bo", 9],
        ["alert", "ops", 7],
        ["later", "zo", 1],
    ]
    and signature(early_raise) == [
        ["pulse", "bo", 9],
        ["pulse", "ann", 9],
        ["alert", "ops", 7],
        ["later", "zo", 1],
    ]
)

print(json.dumps({"manifestations": [
    {"id": "axis1-a", "invariant": invariant, "passed": axis1_a},
    {"id": "axis1-b", "invariant": invariant, "passed": axis1_b},
    {"id": "axis2-a", "invariant": invariant, "passed": axis2_a},
    {"id": "axis2-b", "invariant": invariant, "passed": axis2_b},
    {"id": "interaction", "invariant": invariant, "passed": interaction},
]}))
