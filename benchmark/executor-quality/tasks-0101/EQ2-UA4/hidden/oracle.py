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
invariant = "Invoice lines are posted by descending priority with source order breaking ties, parsing rejects are reported with format errors before account errors before amount errors and source order breaking ties, and when malformed and valid lines interleave each posting records the cumulative amount of valid lines in posting order while rejects retain their own precedence without advancing that total or preventing later valid postings."


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


priority_ledger = intake([
    "A101|acct-east|12.5|2",
    "B202|acct-west|30|9",
    "C303|acct-north|7.5|5",
    "D404|acct-south|4|5",
])
axis1_a = priority_ledger.get("posted") == [
    {"invoice": "B202", "postedTotal": 30},
    {"invoice": "C303", "postedTotal": 37.5},
    {"invoice": "D404", "postedTotal": 41.5},
    {"invoice": "A101", "postedTotal": 54},
]

tied_ledger = intake([
    "E505|acct-red|1.25|6",
    "F606|acct-blue|2.5|6",
    "G707|acct-green|3.75|6",
])
split_bands = intake([
    "H808|acct-cyan|8|1",
    "I909|acct-magenta|9|4",
])
axis1_b = tied_ledger.get("posted") == [
    {"invoice": "E505", "postedTotal": 1.25},
    {"invoice": "F606", "postedTotal": 3.75},
    {"invoice": "G707", "postedTotal": 7.5},
] and split_bands.get("posted") == [
    {"invoice": "I909", "postedTotal": 9},
    {"invoice": "H808", "postedTotal": 17},
]

issue_precedence = intake([
    "bad|wrong|-3|x",
    "J010|wrong|10|3",
    "K111|acct-gray|0|8",
    "broken",
])
axis2_a = issue_precedence.get("rejected") == [
    {"source": 0, "reason": "format"},
    {"source": 3, "reason": "format"},
    {"source": 1, "reason": "account"},
    {"source": 2, "reason": "amount"},
]

format_ties = intake([
    "bad|acct-rose|4|2",
    "L212|acct-lime|5|x",
])
account_ties = intake([
    "M313|wrong|6|1",
    "N414|also-wrong|7|9",
    "O515|acct-gold|-2|4",
])
axis2_b = format_ties.get("rejected") == [
    {"source": 0, "reason": "format"},
    {"source": 1, "reason": "format"},
] and account_ties.get("rejected") == [
    {"source": 0, "reason": "account"},
    {"source": 1, "reason": "account"},
    {"source": 2, "reason": "amount"},
]

interleaved_ledger = intake([
    "P616|acct-alpha|10|2",
    "Q717|wrong|90|10",
    "R818|acct-beta|20|8",
    "broken",
    "S919|acct-delta|-5|9",
    "T020|acct-gamma|7|5",
    "bad|acct-epsilon|40|7",
    "U121|acct-zeta|3|8",
])
interaction = interleaved_ledger == {
    "posted": [
        {"invoice": "R818", "postedTotal": 20},
        {"invoice": "U121", "postedTotal": 23},
        {"invoice": "T020", "postedTotal": 30},
        {"invoice": "P616", "postedTotal": 40},
    ],
    "rejected": [
        {"source": 3, "reason": "format"},
        {"source": 6, "reason": "format"},
        {"source": 1, "reason": "account"},
        {"source": 4, "reason": "amount"},
    ],
}

print(json.dumps({"manifestations": [
    {"id": "axis1-a", "invariant": invariant, "passed": axis1_a},
    {"id": "axis1-b", "invariant": invariant, "passed": axis1_b},
    {"id": "axis2-a", "invariant": invariant, "passed": axis2_a},
    {"id": "axis2-b", "invariant": invariant, "passed": axis2_b},
    {"id": "interaction", "invariant": invariant, "passed": interaction},
]}))
