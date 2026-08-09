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


priority_bands = intake([
    "A001|acct-a|10|4",
    "B002|acct-b|20|9",
    "C003|acct-c|30|4",
    "D004|acct-d|40|7",
    "E005|acct-e|50|9",
    "F006|acct-f|60|1",
])
axis1_a = priority_bands.get("posted") == [
    "B002",
    "E005",
    "D004",
    "A001",
    "C003",
    "F006",
]

stable_band = intake([
    "G007|acct-g|10|6",
    "H008|acct-h|20|6",
    "I009|acct-i|30|6",
    "J010|acct-j|40|6",
])
axis1_b = stable_band.get("posted") == ["G007", "H008", "I009", "J010"]

overlapping_issues = intake([
    "bad|wrong|-3|x",
    "K011|wrong|0|5",
    "L012|acct-l|-8|x",
])
axis2_a = overlapping_issues.get("rejected") == [
    {"source": 0, "reason": "format"},
    {"source": 2, "reason": "format"},
    {"source": 1, "reason": "account"},
]

precedence_groups = intake([
    "M013|acct-m|0|2",
    "N014|wrong|14|3",
    "broken",
    "O015|acct-o|-2|4",
    "P016|wrong|16|5",
    "Q017|acct-q|17|x",
])
axis2_b = precedence_groups.get("rejected") == [
    {"source": 2, "reason": "format"},
    {"source": 5, "reason": "format"},
    {"source": 1, "reason": "account"},
    {"source": 4, "reason": "account"},
    {"source": 0, "reason": "amount"},
    {"source": 3, "reason": "amount"},
]

edge_interleave = intake([
    "broken",
    "R018|acct-r|18|3",
    "S019|acct-s|19|8",
    "T020|wrong|20|7",
    "U021|acct-u|21|5",
    "V022|acct-v|0|9",
    "W023|acct-w|23|8",
])
center_interleave = intake([
    "X024|acct-x|24|2",
    "Y025|acct-y|25|6",
    "Z026|acct-z|-1|9",
    "A027|acct-aa|27|4",
])
interaction = edge_interleave == {
    "posted": ["S019", "W023", "U021", "R018"],
    "rejected": [
        {"source": 0, "reason": "format"},
        {"source": 3, "reason": "account"},
        {"source": 5, "reason": "amount"},
    ],
} and center_interleave == {
    "posted": ["Y025", "A027", "X024"],
    "rejected": [{"source": 2, "reason": "amount"}],
}

print(json.dumps({"manifestations": [
    {"id": "axis1-a", "invariant": invariant, "passed": axis1_a},
    {"id": "axis1-b", "invariant": invariant, "passed": axis1_b},
    {"id": "axis2-a", "invariant": invariant, "passed": axis2_a},
    {"id": "axis2-b", "invariant": invariant, "passed": axis2_b},
    {"id": "interaction", "invariant": invariant, "passed": interaction},
]}))
