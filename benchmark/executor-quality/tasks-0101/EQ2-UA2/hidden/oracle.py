#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys


workdir = pathlib.Path(sys.argv[1])
runner = r'''import { pathToFileURL } from "node:url";
const modulePath = pathToFileURL(process.argv[1]).href;
const { enqueueAll } = await import(modulePath);
const submissions = JSON.parse(process.argv[2]);
const queued = enqueueAll(submissions, Number(process.argv[3]));
process.stdout.write(JSON.stringify(queued));
'''
invariant = "The spooler fills each bounded printer queue by descending priority with arrival order breaking ties, the job dedup index absorbs every repeated job ID exactly once before it can consume queue capacity, and when a duplicate submission surrounds a priority reorder the emitted queue contains the highest-priority unique jobs in that order with one copy of the repeated job regardless of its arrival slot."


def enqueue(submissions, capacity):
    completed = subprocess.run(
        [
            "node",
            "--input-type=module",
            "--eval",
            runner,
            str(workdir / "spooler.js"),
            json.dumps(submissions),
            str(capacity),
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


def ids(queue):
    return [job["id"] for job in queue]


ordered_one = enqueue([
    {"id": "slow", "document": "a", "priority": 1},
    {"id": "rush", "document": "b", "priority": 9},
    {"id": "mid", "document": "c", "priority": 4},
], 2)
axis1_a = ids(ordered_one) == ["rush", "mid"]

ordered_two = enqueue([
    {"id": "first", "document": "a", "priority": 6},
    {"id": "second", "document": "b", "priority": 6},
    {"id": "top", "document": "c", "priority": 8},
], 3)
axis1_b = ids(ordered_two) == ["top", "first", "second"]

repeated_one = enqueue([
    {"id": "form", "document": "a", "priority": 5},
    {"id": "form", "document": "a", "priority": 5},
], 2)
axis2_a = ids(repeated_one) == ["form"]

repeated_two = enqueue([
    {"id": "chart", "document": "a", "priority": 7},
    {"id": "note", "document": "b", "priority": 2},
    {"id": "chart", "document": "a", "priority": 7},
], 3)
axis2_b = ids(repeated_two) == ["chart", "note"]

duplicate_early = enqueue([
    {"id": "blue", "document": "plans", "priority": 10},
    {"id": "repair", "document": "ticket", "priority": 9},
    {"id": "blue", "document": "plans", "priority": 10},
    {"id": "invoice", "document": "bill", "priority": 7},
    {"id": "draft", "document": "memo", "priority": 2},
], 3)
duplicate_late = enqueue([
    {"id": "repair", "document": "ticket", "priority": 9},
    {"id": "blue", "document": "plans", "priority": 10},
    {"id": "invoice", "document": "bill", "priority": 7},
    {"id": "blue", "document": "plans", "priority": 10},
    {"id": "draft", "document": "memo", "priority": 2},
], 3)
interaction = (
    ids(duplicate_early) == ["blue", "repair", "invoice"]
    and ids(duplicate_late) == ["blue", "repair", "invoice"]
)

print(json.dumps({"manifestations": [
    {"id": "axis1-a", "invariant": invariant, "passed": axis1_a},
    {"id": "axis1-b", "invariant": invariant, "passed": axis1_b},
    {"id": "axis2-a", "invariant": invariant, "passed": axis2_a},
    {"id": "axis2-b", "invariant": invariant, "passed": axis2_b},
    {"id": "interaction", "invariant": invariant, "passed": interaction},
]}))
