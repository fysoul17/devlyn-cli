#!/usr/bin/env python3
"""Evaluate the five discovery manifestations without changing the supplied tree."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def inspect(workdir: Path) -> list[bool]:
    program = r'''
const path = require("node:path");
const root = process.argv[1];
const assigner = require(path.join(root, "assigner", "reviewer_assigner.js"));
const detector = require(path.join(root, "oversight", "conflict_detector.js"));
const state = assigner.createReviewState();
assigner.removeSubmittedPaper(state, "P-204");
const capacitiesAfterFirstRemoval = state.reviewers.map((reviewer) => reviewer.availableSlots);
const historyAfterFirstRemoval = state.reviewHistory.map((review) => review.id);
assigner.removeSubmittedPaper(state, "P-204");
const slots = state.reviewers.every((reviewer) => reviewer.availableSlots === 1);
const repeated = state.reviewers.every((reviewer, index) => reviewer.availableSlots === 1 && reviewer.availableSlots === capacitiesAfterFirstRemoval[index]) && state.reviewHistory.length === historyAfterFirstRemoval.length && state.reviewHistory.every((review, index) => review.id === historyAfterFirstRemoval[index]);
const conflicts = detector.findSchedulingConflicts(state, [{ reviewerId: "rhea" }]).length === 0;
const recorded = state.reviewHistory.length === 1 && state.reviewHistory[0].id === "R-81";
process.stdout.write(JSON.stringify([slots, repeated, conflicts, recorded, slots && conflicts && recorded]));
'''
    result = subprocess.run(
        ["node", "-e", program, str(workdir)],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "node evaluation failed")
    values = json.loads(result.stdout)
    if not isinstance(values, list) or len(values) != 5 or any(not isinstance(value, bool) for value in values):
        raise RuntimeError("node evaluation returned an invalid result")
    return values


def main() -> int:
    values = inspect(Path(sys.argv[1]))
    ids = ("local-a", "local-b", "remote-a", "remote-b", "restore")
    print(json.dumps({"manifestations": [{"id": ident, "passed": value} for ident, value in zip(ids, values)]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
