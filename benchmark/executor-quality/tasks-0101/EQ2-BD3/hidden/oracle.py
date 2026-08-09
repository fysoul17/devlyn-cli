#!/usr/bin/env python3
import json
import pathlib
import sys


workdir = pathlib.Path(sys.argv[1])
sys.dont_write_bytecode = True
sys.path.insert(0, str(workdir))
from zone_editor import edit_zone


invariant = "Record applier candidates are processed by descending deployment priority with source order breaking ties, syntax ranking reports rejected changes by owner errors before type errors before value errors and source order breaking ties, and when malformed and valid changes interleave under that processing order the ranked rejection report preserves that error precedence while a rejected change never reserves its owner or prevents a later valid record for that owner from being placed."


def execute(changes: list[dict]) -> dict:
    try:
        return edit_zone(changes)
    except NotImplementedError:
        return {}


ordered = execute([
    {"change": "tail", "owner": "tail.example.", "type": "A", "value": "192.0.2.10", "priority": 1},
    {"change": "head", "owner": "head.example.", "type": "TXT", "value": "primary", "priority": 9},
    {"change": "middle", "owner": "middle.example.", "type": "CNAME", "value": "target.example.", "priority": 5},
])
axis1_a = ordered.get("placed") == ["head", "middle", "tail"]

tied = execute([
    {"change": "first-tie", "owner": "a.example.", "type": "TXT", "value": "one", "priority": 7},
    {"change": "low", "owner": "b.example.", "type": "AAAA", "value": "2001:db8::1", "priority": 2},
    {"change": "second-tie", "owner": "c.example.", "type": "A", "value": "192.0.2.11", "priority": 7},
])
axis1_b = tied.get("placed") == ["first-tie", "second-tie", "low"]

multi_issue = execute([
    {"change": "many-bad", "owner": "missing-dot", "type": "MX", "value": "", "priority": 3},
])
axis2_a = multi_issue.get("rejected") == [{"source": 0, "reason": "owner"}]

ranked_errors = execute([
    {"change": "bad-value", "owner": "value.example.", "type": "A", "value": "not-ip", "priority": 8},
    {"change": "bad-type", "owner": "type.example.", "type": "MX", "value": "mail.example.", "priority": 1},
])
axis2_b = ranked_errors.get("rejected") == [
    {"source": 1, "reason": "type"},
    {"source": 0, "reason": "value"},
]

composed = execute([
    {"change": "mail-last", "owner": "mail.example.", "type": "A", "value": "192.0.2.20", "priority": 1},
    {"change": "bad-shared", "owner": "api.example.", "type": "MX", "value": "mail.example.", "priority": 9},
    {"change": "api-valid", "owner": "api.example.", "type": "A", "value": "192.0.2.21", "priority": 7},
    {"change": "bad-owner", "owner": "broken owner", "type": "TXT", "value": "note", "priority": 8},
    {"change": "web-valid", "owner": "www.example.", "type": "CNAME", "value": "origin.example.", "priority": 6},
])
interaction = composed.get("placed") == ["api-valid", "web-valid", "mail-last"] and composed.get("rejected") == [
    {"source": 3, "reason": "owner"},
    {"source": 1, "reason": "type"},
]

print(json.dumps({"manifestations": [
    {"id": "axis1-a", "invariant": invariant, "passed": axis1_a},
    {"id": "axis1-b", "invariant": invariant, "passed": axis1_b},
    {"id": "axis2-a", "invariant": invariant, "passed": axis2_a},
    {"id": "axis2-b", "invariant": invariant, "passed": axis2_b},
    {"id": "interaction", "invariant": invariant, "passed": interaction},
]}))
