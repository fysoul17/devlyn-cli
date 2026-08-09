#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys


workdir = pathlib.Path(sys.argv[1])
runner = r'''import { pathToFileURL } from "node:url";
const modulePath = pathToFileURL(process.argv[1]).href;
const { intakeBatch } = await import(modulePath);
const lines = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(intakeBatch(lines)));
'''
invariant = "Invoice lines are posted by descending priority with source order breaking ties, parsing rejects are reported with format errors before account errors before amount errors and source order breaking ties, and when malformed and valid lines interleave the rejects retain that precedence while rejected lines never suppress or occupy positions among valid postings."


def intake(lines):
    completed = subprocess.run(
        [
            "node",
            "--input-type=module",
            "--eval",
            runner,
            str(workdir / "intake.js"),
            json.dumps(lines),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10,
    )
    if completed.returncode != 0:
        return {}
    return json.loads(completed.stdout)


ordered = intake([
    "A001|acct-low|10|1",
    "B002|acct-high|20|9",
    "C003|acct-mid|30|5",
])
axis1_a = ordered.get("posted") == ["B002", "C003", "A001"]

tied = intake([
    "D004|acct-one|10|7",
    "E005|acct-low|20|2",
    "F006|acct-two|30|7",
])
axis1_b = tied.get("posted") == ["D004", "F006", "E005"]

multi_issue = intake([
    "bad|wrong|-3|x",
])
axis2_a = multi_issue.get("rejected") == [{"source": 0, "reason": "format"}]

ranked_errors = intake([
    "G007|acct-west|-1|3",
    "H008|wrong|12|4",
    "I009|acct-east|0|8",
])
axis2_b = ranked_errors.get("rejected") == [
    {"source": 1, "reason": "account"},
    {"source": 0, "reason": "amount"},
    {"source": 2, "reason": "amount"},
]

composed = intake([
    "J010|acct-tail|10|1",
    "K011|acct-bad|-2|8",
    "L012|acct-head|30|9",
    "M013|wrong|14|7",
    "N014|acct-zero|0|6",
    "O015|acct-mid|20|5",
])
interaction = composed.get("posted") == ["L012", "O015", "J010"] and composed.get(
    "rejected"
) == [
    {"source": 3, "reason": "account"},
    {"source": 1, "reason": "amount"},
    {"source": 4, "reason": "amount"},
]

print(json.dumps({"manifestations": [
    {"id": "axis1-a", "invariant": invariant, "passed": axis1_a},
    {"id": "axis1-b", "invariant": invariant, "passed": axis1_b},
    {"id": "axis2-a", "invariant": invariant, "passed": axis2_a},
    {"id": "axis2-b", "invariant": invariant, "passed": axis2_b},
    {"id": "interaction", "invariant": invariant, "passed": interaction},
]}))
