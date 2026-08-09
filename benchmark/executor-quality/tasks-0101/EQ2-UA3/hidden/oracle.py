#!/usr/bin/env python3
import json
import pathlib
import sys


workdir = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(workdir))

from approval_router import route_expenses
from models import ExpenseRequest
from reviewers import Reviewer


grants = {
    "lead": {"travel": 100_000, "office": 50_000},
    "clerk": {"office": 20_000},
}
reviewers = [
    Reviewer("A", ("travel", "office")),
    Reviewer("B", ("travel", "office")),
]


def request(identifier, submitter, center, amount, urgency, submitted):
    return ExpenseRequest(identifier, submitter, center, amount, urgency, submitted)


def view(items):
    return [
        [item.request_id, item.reviewer, item.reviewer_slot]
        for item in items
    ]


first_order = route_expenses(
    [
        request("low", "lead", "travel", 100, 1, 1),
        request("high", "lead", "travel", 100, 9, 2),
    ],
    grants,
    reviewers,
)
axis1a = view(first_order) == [["high", "A", 1], ["low", "B", 1]]

tied_order = route_expenses(
    [
        request("first", "lead", "office", 100, 5, 1),
        request("middle", "lead", "office", 100, 2, 2),
        request("second", "clerk", "office", 100, 5, 3),
    ],
    grants,
    reviewers,
)
axis1b = view(tied_order) == [
    ["first", "A", 1],
    ["second", "B", 1],
    ["middle", "A", 2],
]

denied_only = route_expenses(
    [request("blocked", "clerk", "travel", 100, 8, 1)],
    grants,
    reviewers,
)
axis2a = view(denied_only) == []

filtered = route_expenses(
    [
        request("allowed", "lead", "office", 100, 8, 1),
        request("denied", "clerk", "travel", 100, 1, 2),
    ],
    grants,
    reviewers,
)
axis2b = view(filtered) == [["allowed", "A", 1]]

composed = route_expenses(
    [
        request("rogue", "clerk", "travel", 100, 10, 1),
        request("rush", "lead", "travel", 100, 8, 2),
        request("plain", "lead", "travel", 100, 3, 3),
    ],
    grants,
    reviewers,
)
interaction = view(composed) == [
    ["rush", "A", 1],
    ["plain", "B", 1],
]

invariant = "Expense requests are routed by descending urgency with submission order breaking ties, the role gate admits only submitters whose grants cover the request's cost center and amount, and when privileged and unprivileged requests interleave the role gate decides authorization before priority placement and reviewer-load assignment so denied requests never consume a reviewer's ordered slot."

print(json.dumps({"manifestations": [
    {"id": "axis1-a", "invariant": invariant, "passed": axis1a},
    {"id": "axis1-b", "invariant": invariant, "passed": axis1b},
    {"id": "axis2-a", "invariant": invariant, "passed": axis2a},
    {"id": "axis2-b", "invariant": invariant, "passed": axis2b},
    {"id": "interaction", "invariant": invariant, "passed": interaction},
]}))
