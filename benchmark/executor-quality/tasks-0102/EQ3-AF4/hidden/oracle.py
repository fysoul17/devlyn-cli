#!/usr/bin/env python3
"""Evaluate harvest-state manifestations without changing the supplied tree."""

import json
import subprocess
import sys
from pathlib import Path


def evaluate(workdir: Path) -> dict[str, bool]:
    program = r'''
const recorder = require(process.argv[1]);
const ledger = require(process.argv[2]);

function state() {
  return {
    fieldInventory: ["B-17", "B-18"],
    lots: { "L-7": { rejected: false } },
    binRecords: [],
    gradeEntries: [],
  };
}

function partial() {
  const value = state();
  recorder.recordPick(value, { id: "B-17", lotId: "L-7", expectedWeight: 16 });
  recorder.recordPick(value, { id: "B-18", lotId: "L-7", expectedWeight: 15 });
  recorder.recordGrade(value, "B-17", 15);
  return value;
}

function localOne() {
  const value = state();
  recorder.recordPick(value, { id: "B-17", lotId: "L-7", expectedWeight: 16 });
  return value.binRecords[0].status === "picked";
}

function localTwo() {
  const value = state();
  recorder.recordPick(value, { id: "B-17", lotId: "L-7", expectedWeight: 16 });
  recorder.recordPick(value, { id: "B-18", lotId: "L-7", expectedWeight: 15 });
  return value.binRecords.every((bin) => bin.status === "picked") && value.fieldInventory.length === 0;
}

function remoteA() {
  const value = partial();
  recorder.rejectLot(value, "L-7");
  return ledger.acceptedWeight(value, "L-7") === 0;
}

function remoteB() {
  const value = partial();
  recorder.rejectLot(value, "L-7");
  return value.fieldInventory.slice().sort().join(",") === "B-17,B-18" && value.gradeEntries[0].voided;
}

function restore() {
  const value = partial();
  recorder.rejectLot(value, "L-7");
  recorder.rejectLot(value, "L-7");
  return value.fieldInventory.slice().sort().join(",") === "B-17,B-18"
    && value.binRecords.every((bin) => bin.status === "field")
    && value.gradeEntries.length === 1
    && value.gradeEntries[0].voided;
}

process.stdout.write(JSON.stringify({
  one: localOne(),
  two: localTwo(),
  three: remoteA(),
  four: remoteB(),
  five: restore(),
}));
'''
    result = subprocess.run(
        [
            "node",
            "-e",
            program,
            str(workdir / "picking" / "pick_recorder.js"),
            str(workdir / "grading" / "grader_ledger.js"),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "node evaluation failed")
    payload = json.loads(result.stdout)
    return {
        "local-a": bool(payload["one"]),
        "local-b": bool(payload["two"]),
        "remote-a": bool(payload["three"]),
        "remote-b": bool(payload["four"]),
        "restore": bool(payload["five"]),
    }


def main() -> None:
    results = evaluate(Path(sys.argv[1]))
    print(json.dumps({"manifestations": [
        {"id": role, "passed": passed} for role, passed in results.items()
    ]}, separators=(",", ":")))


if __name__ == "__main__":
    main()
