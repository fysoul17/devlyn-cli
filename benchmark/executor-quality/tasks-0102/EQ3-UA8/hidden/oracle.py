#!/usr/bin/env python3
"""Evaluate restack manifestations without writing to the supplied fixture."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


RUNNER = r'''
const { rejectedYard } = require("./support/fixtures");
const { deepCopy } = require("./support/deep_copy");
const { request } = require("./support/ids");
const { layoutSnapshot } = require("./yard/stack_lookup");
const { restackContainer } = require("./planner/stack_planner");
const { craneDebitMatches } = require("./crane/crane_sequencer");
const { journaledReconciliationMatches } = require("./journal/restack_journal_test");
const { fullTargetFailureRetainsContainer } = require("./checks/restack_local_test");
const { repeatedFullTargetFailureIsStable } = require("./checks/repeat_local_test");

function sameJson(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
}

function asymmetricYard() {
  return {
    stacks: [
      { id: "P-10", containers: ["CTR-61", "CTR-62"], capacity: 5, rejectedContainerIds: [] },
      { id: "Q-03", containers: ["CTR-70", "CTR-71", "CTR-72"], capacity: 6, rejectedContainerIds: ["CTR-62"] },
      { id: "R-18", containers: ["CTR-83", "CTR-84", "CTR-85"], capacity: 4, rejectedContainerIds: [] },
      { id: "S-07", containers: ["CTR-91"], capacity: 7, rejectedContainerIds: ["CTR-85"] },
      { id: "T-22", containers: ["CTR-99", "CTR-98"], capacity: 3, rejectedContainerIds: [] },
    ],
    craneLedger: [
      { liftId: "lift-history-a", operationId: "prior-lift-a", containerId: "CTR-04", from: "K-01", to: "K-02" },
      { liftId: "lift-history-b", operationId: "prior-lift-b", containerId: "CTR-05", from: "K-03", to: "K-04" },
    ],
    journal: [
      { operationId: "prior-move-a", type: "arrival-note", containerId: "CTR-04", sourceStackId: "K-01", targetStackId: "K-02" },
      { operationId: "prior-move-b", type: "inspection-note", containerId: "CTR-05", sourceStackId: "K-03", targetStackId: "K-04" },
      { operationId: "prior-move-c", type: "handoff-note", containerId: "CTR-06", sourceStackId: "K-05", targetStackId: "K-06" },
    ],
    completedRestacks: [],
  };
}

function runCase(yard, orderedRequests) {
  const beforeLayout = deepCopy(layoutSnapshot(yard));
  const beforeLedger = deepCopy(yard.craneLedger);
  const beforeJournal = deepCopy(yard.journal);
  const outcomes = [];
  for (const item of orderedRequests) {
    outcomes.push(restackContainer(yard, item));
    outcomes.push(restackContainer(yard, item));
  }
  const eachFailed = outcomes.every((outcome) => outcome.moved === false && outcome.reason === "placement-rejected");
  const everyCraneDebit = orderedRequests.every((item) => craneDebitMatches(yard, beforeLedger, item));
  const everyJournalRestore = orderedRequests.every((item) => journaledReconciliationMatches(yard, beforeLayout, item));
  const expectedLedgerIds = beforeLedger.map((entry) => entry.operationId).concat(orderedRequests.map((item) => item.operationId));
  const expectedJournalIds = beforeJournal.map((entry) => entry.operationId).concat(orderedRequests.map((item) => item.operationId));
  return {
    beforeLayout,
    beforeLedger,
    beforeJournal,
    yard,
    eachFailed,
    everyCraneDebit,
    everyJournalRestore,
    layoutRestored: sameJson(layoutSnapshot(yard), beforeLayout),
    priorLedgerPreserved: sameJson(yard.craneLedger[0], beforeLedger[0]),
    priorJournalPreserved: sameJson(yard.journal[0], beforeJournal[0]),
    ledgerOrder: sameJson(yard.craneLedger.map((entry) => entry.operationId), expectedLedgerIds),
    journalOrder: sameJson(yard.journal.map((entry) => entry.operationId), expectedJournalIds),
  };
}

const standardRequests = [
  request("OP-ALPHA", "CTR-19", "A-01", "B-04"),
  request("OP-BRAVO", "CTR-17", "D-02", "E-06"),
];
const asymmetricRequests = [
  request("OP-DELTA", "CTR-62", "P-10", "Q-03"),
  request("OP-ECHO", "CTR-85", "R-18", "S-07"),
];
const forward = runCase(rejectedYard(), standardRequests);
const reversed = runCase(asymmetricYard(), asymmetricRequests.slice().reverse());

console.log(JSON.stringify({
  localA: fullTargetFailureRetainsContainer(),
  localB: repeatedFullTargetFailureIsStable(),
  remoteA: forward.eachFailed && forward.everyCraneDebit && forward.ledgerOrder
    && reversed.eachFailed && reversed.everyCraneDebit && reversed.ledgerOrder,
  remoteB: forward.everyJournalRestore && forward.journalOrder
    && reversed.everyJournalRestore && reversed.journalOrder,
  restore: forward.layoutRestored && forward.priorLedgerPreserved && forward.priorJournalPreserved
    && reversed.layoutRestored && reversed.priorLedgerPreserved && reversed.priorJournalPreserved,
}));
'''


def evaluate(workdir: Path) -> dict[str, bool]:
    result = subprocess.run(
        ["node", "-e", RUNNER], cwd=workdir, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False, timeout=10,
    )
    if result.returncode:
        raise SystemExit(result.stderr or "node runner failed")
    values = json.loads(result.stdout)
    return {
        "local-a": bool(values["localA"]),
        "local-b": bool(values["localB"]),
        "remote-a": bool(values["remoteA"]),
        "remote-b": bool(values["remoteB"]),
        "restore": bool(values["restore"]),
    }


def main() -> None:
    values = evaluate(Path(sys.argv[1]))
    print(json.dumps({"manifestations": [
        {"id": role, "passed": values[role]}
        for role in ("local-a", "local-b", "remote-a", "remote-b", "restore")
    ]}, separators=(",", ":")))


if __name__ == "__main__":
    main()
