#!/usr/bin/env python3
"""Evaluate harbor assignment manifestations without writing to the workdir."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROGRAM = r'''
const path = require("node:path");
const root = path.resolve(process.argv[1]);
const desk = require(path.join(root, "desk", "assignment_desk.js"));
const planner = require(path.join(root, "tide", "tide_window_planner.js"));
const checks = require(path.join(root, "checks", "abort_return_test.js"));
const fixtures = require(path.join(root, "support", "fixtures.js"));

const cases = [
  {
    assignmentId: "A-381", pilotId: "pilot-381", berthId: "berth-east-381", windowOpensAt: 43, closedAt: 58,
    pilots: [
      { id: "pilot-blocked-west", status: "assigned", assignmentId: "other-west" },
      { id: "pilot-watch", status: "assigned", assignmentId: "other-watch" },
      { id: "pilot-381", status: "ready", assignmentId: null },
      { id: "pilot-blocked-east", status: "assigned", assignmentId: "other-east" },
    ],
    berths: [
      { id: "berth-south", status: "occupied", assignmentId: "other-south" },
      { id: "berth-east-381", status: "open", assignmentId: null },
      { id: "berth-north", status: "occupied", assignmentId: "other-north" },
      { id: "berth-outer", status: "occupied", assignmentId: "other-outer" },
    ],
    pilotCandidates: ["pilot-blocked-east", "pilot-watch", "pilot-blocked-west", "pilot-381"],
    berthCandidates: ["berth-south", "berth-east-381", "berth-north", "berth-outer"],
    expectedPilotPosition: 3,
    expectedBerthPosition: 1,
  },
  {
    assignmentId: "A-722", pilotId: "pilot-722", berthId: "berth-north-722", windowOpensAt: 77, closedAt: 91,
    pilots: [
      { id: "pilot-blocked-one", status: "assigned", assignmentId: "other-one" },
      { id: "pilot-blocked-two", status: "assigned", assignmentId: "other-two" },
      { id: "pilot-blocked-three", status: "assigned", assignmentId: "other-three" },
      { id: "pilot-722", status: "ready", assignmentId: null },
      { id: "pilot-blocked-four", status: "assigned", assignmentId: "other-four" },
    ],
    berths: [
      { id: "berth-blocked-one", status: "occupied", assignmentId: "other-one" },
      { id: "berth-blocked-two", status: "occupied", assignmentId: "other-two" },
      { id: "berth-north-722", status: "open", assignmentId: null },
      { id: "berth-blocked-three", status: "occupied", assignmentId: "other-three" },
      { id: "berth-blocked-four", status: "occupied", assignmentId: "other-four" },
    ],
    pilotCandidates: ["pilot-722", "pilot-blocked-four", "pilot-blocked-one", "pilot-blocked-three", "pilot-blocked-two"],
    berthCandidates: ["berth-blocked-four", "berth-blocked-one", "berth-blocked-three", "berth-north-722", "berth-blocked-two"],
    expectedPilotPosition: 0,
    expectedBerthPosition: 3,
  },
];

function openedCase(data) {
  const harbor = fixtures.harborForScenarios(data);
  const beforeOpen = structuredClone({ pilots: harbor.pilots, berths: harbor.berths, releaseLog: harbor.releaseLog });
  const request = { assignmentId: data.assignmentId, pilotId: data.pilotId, berthId: data.berthId, plannedFor: data.closedAt - 6 };
  const opened = desk.openAssignment(harbor, request);
  const abort = planner.armAbortAtWindowClose(harbor, data.assignmentId, {
    opensAt: data.windowOpensAt, closesAt: data.closedAt,
  });
  return { harbor, beforeOpen, request, opened, abort };
}

function expectedOpen(beforeOpen, ids, kind) {
  const items = kind === "pilot" ? beforeOpen.pilots : beforeOpen.berths;
  const ready = kind === "pilot" ? "ready" : "open";
  return ids.map((id) => items.find((item) => item.id === id)).find((item) => item?.status === ready)?.id ?? null;
}

function localA() {
  return cases.every((data) => {
    const item = openedCase(data);
    const early = desk.closeAssignment(item.harbor, data.assignmentId, data.closedAt - 1);
    const receipt = desk.closeAssignment(item.harbor, data.assignmentId, data.closedAt);
    const pilot = item.harbor.pilots.find((entry) => entry.id === data.pilotId);
    const active = item.harbor.assignments.find((entry) => entry.id === data.assignmentId);
    return item.opened.opened && item.abort.armed === true && early.closed === false && active.status === "closed"
      && receipt.closed === true && pilot.status === item.beforeOpen.pilots.find((entry) => entry.id === data.pilotId).status
      && pilot.assignmentId === null;
  });
}

function localB() {
  return cases.every((data) => {
    const item = openedCase(data);
    desk.closeAssignment(item.harbor, data.assignmentId, data.closedAt);
    const repeat = desk.closeAssignment(item.harbor, data.assignmentId, data.closedAt);
    return repeat.closed === false && repeat.alreadyClosed === true && item.harbor.releaseLog.length === 1;
  });
}

function remoteA() {
  return cases.every((data) => {
    const item = openedCase(data);
    desk.closeAssignment(item.harbor, data.assignmentId, data.closedAt);
    const expectedPilot = expectedOpen(item.beforeOpen, data.pilotCandidates, "pilot");
    const expectedBerth = expectedOpen(item.beforeOpen, data.berthCandidates, "berth");
    const receipt = planner.coReserveWindow(item.harbor, {
      assignmentId: `${data.assignmentId}-next`, pilotIds: data.pilotCandidates,
      berthIds: data.berthCandidates, plannedFor: data.closedAt + 1,
    });
    return expectedPilot !== null && expectedBerth !== null
      && data.pilotCandidates.indexOf(expectedPilot) === data.expectedPilotPosition
      && data.berthCandidates.indexOf(expectedBerth) === data.expectedBerthPosition
      && receipt.reserved === true && receipt.pilotId === expectedPilot && receipt.berthId === expectedBerth;
  });
}

function remoteB() {
  return cases.every((data) => {
    const item = openedCase(data);
    desk.closeAssignment(item.harbor, data.assignmentId, data.closedAt);
    return checks.berthHandoffIsClear(item.harbor, data.berthId);
  });
}

function restore() {
  return cases.every((data) => {
    const item = openedCase(data);
    const first = desk.closeAssignment(item.harbor, data.assignmentId, data.closedAt);
    const second = desk.closeAssignment(item.harbor, data.assignmentId, data.closedAt);
    const pilotBefore = item.beforeOpen.pilots.find((entry) => entry.id === data.pilotId);
    const berthBefore = item.beforeOpen.berths.find((entry) => entry.id === data.berthId);
    const pilotAfter = item.harbor.pilots.find((entry) => entry.id === data.pilotId);
    const berthAfter = item.harbor.berths.find((entry) => entry.id === data.berthId);
    const active = item.harbor.assignments.find((entry) => entry.id === data.assignmentId);
    const expectedRelease = { assignmentId: data.assignmentId, pilotId: data.pilotId, berthId: data.berthId, closedAt: data.closedAt };
    const unrelatedBefore = item.beforeOpen.pilots.filter((entry) => entry.id !== data.pilotId)
      .concat(item.beforeOpen.berths.filter((entry) => entry.id !== data.berthId));
    const unrelatedAfter = item.harbor.pilots.filter((entry) => entry.id !== data.pilotId)
      .concat(item.harbor.berths.filter((entry) => entry.id !== data.berthId));
    return first.closed === true && second.closed === false && second.alreadyClosed === true
      && pilotAfter.status === pilotBefore.status && pilotAfter.assignmentId === pilotBefore.assignmentId
      && berthAfter.status === berthBefore.status && berthAfter.assignmentId === berthBefore.assignmentId
      && active.status === "closed" && item.harbor.releaseLog.length === item.beforeOpen.releaseLog.length + 1
      && JSON.stringify(item.harbor.releaseLog[0]) === JSON.stringify(expectedRelease)
      && JSON.stringify(unrelatedAfter) === JSON.stringify(unrelatedBefore);
  });
}

console.log(JSON.stringify({ localA: localA(), localB: localB(), remoteA: remoteA(), remoteB: remoteB(), restore: restore() }));
'''


def evaluate(workdir: Path) -> dict[str, bool]:
    result = subprocess.run(
        ["node", "-e", PROGRAM, str(workdir)], cwd=workdir, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=10,
    )
    if result.returncode:
        raise SystemExit(result.stderr or "node evaluator failed")
    values = json.loads(result.stdout)
    return {
        "local-a": bool(values["localA"]), "local-b": bool(values["localB"]),
        "remote-a": bool(values["remoteA"]), "remote-b": bool(values["remoteB"]),
        "restore": bool(values["restore"]),
    }


def main() -> None:
    values = evaluate(Path(sys.argv[1]).resolve())
    print(json.dumps({"manifestations": [
        {"id": role, "passed": values[role]}
        for role in ("local-a", "local-b", "remote-a", "remote-b", "restore")
    ]}, separators=(",", ":")))


if __name__ == "__main__":
    main()
