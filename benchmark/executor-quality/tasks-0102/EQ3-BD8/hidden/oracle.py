#!/usr/bin/env python3
"""Evaluate seed-receiving manifestations without changing the supplied fixture."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


RUNNER = r'''
const { makeWarehouse } = require("./support/fixtures");
const { copy } = require("./support/deep_copy");
const { receiveLot, recordSampleFailure } = require("./receiver/lot_receiver");
const { distributeLot } = require("./shipping/shipment_board");

function same(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
}

function evaluateCase(input) {
  const warehouse = makeWarehouse(input);
  const beforeReceipt = copy(warehouse);
  const first = receiveLot(warehouse, input.lotId, input.receivedAt);
  const afterReceipt = copy(warehouse);
  const second = receiveLot(warehouse, input.lotId, input.receivedAt);
  const targetLotBefore = beforeReceipt.lots.find((item) => item.id === input.lotId);
  const localA = first.accepted === true
    && warehouse.receipts.length === beforeReceipt.receipts.length + 1
    && warehouse.receipts[0].lotId === input.lotId && warehouse.receipts[0].receivedAt === input.receivedAt;
  const localB = second.accepted === false && warehouse.receipts.length === 1
    && second.lotId === input.lotId && second.receivedAt === input.receivedAt;
  for (const portion of input.newPortions) {
    distributeLot(warehouse, input.lotId, portion.shipmentId, portion.units);
  }
  const beforeFailure = copy(warehouse);
  const targetBefore = beforeReceipt.classLimits.find((item) => item.classCode === input.classCode);
  const untouchedBefore = beforeFailure.classLimits.find((item) => item.classCode === input.otherClass);
  const expectedPortions = beforeFailure.distributions.filter((item) => item.lotId === input.lotId);
  const firstFailure = recordSampleFailure(warehouse, input.lotId, input.failedAt);
  const afterFirstFailure = copy(warehouse);
  const secondFailure = recordSampleFailure(warehouse, input.lotId, input.failedAt);
  const lot = warehouse.lots.find((item) => item.id === input.lotId);
  const targetAfter = warehouse.classLimits.find((item) => item.classCode === input.classCode);
  const untouchedAfter = warehouse.classLimits.find((item) => item.classCode === input.otherClass);
  const tray = warehouse.trays.find((item) => item.lotId === input.lotId);
  const recalls = warehouse.recalls.filter((item) => item.lotId === input.lotId);
  const remoteA = beforeReceipt.lots.findIndex((item) => item.id === input.lotId) === input.targetLotIndex
    && beforeReceipt.classLimits.findIndex((item) => item.classCode === input.classCode) === input.targetClassIndex
    && targetLotBefore.status === "pending" && afterReceipt.lots.find((item) => item.id === input.lotId).status === "received"
    && afterReceipt.trays.length === beforeReceipt.trays.length + 1
    && afterReceipt.classLimits.find((item) => item.classCode === input.classCode).used === targetBefore.used + 1
    && tray !== undefined && tray.classCode === input.classCode && tray.released === true
    && targetAfter.used === targetBefore.used && warehouse.trayReleases.filter((item) => item.lotId === input.lotId).length === 1;
  const remoteB = firstFailure.closed === true && lot !== undefined && lot.status === "quarantined"
    && recalls.length === expectedPortions.length
    && recalls.every((recall, index) => recall.shipmentId === expectedPortions[index].shipmentId
      && recall.units === expectedPortions[index].units && recall.failedAt === input.failedAt);
  const restore = secondFailure.closed === false && firstFailure.lotId === input.lotId
    && same(warehouse.recalls, afterFirstFailure.recalls)
    && same(warehouse.distributions, beforeFailure.distributions)
    && targetAfter.used === targetBefore.used && untouchedAfter.used === untouchedBefore.used
    && warehouse.trayReleases.filter((item) => item.lotId === input.lotId).length === 1;
  return { localA, localB, remoteA, remoteB, restore };
}

const cases = [
  {
    lotId: "LOT-ALPHA", classCode: "heritage", otherClass: "dwarf", units: 80, receivedAt: 14, failedAt: 19,
    targetLotIndex: 1, targetClassIndex: 1,
    lots: [
      { id: "LOT-WILLOW", classCode: "dwarf", units: 22 },
      { id: "LOT-ALPHA", classCode: "heritage", units: 80 },
      { id: "LOT-EMBER", classCode: "dwarf", units: 18 },
    ],
    classLimits: [{ classCode: "dwarf", limit: 9, used: 4 }, { classCode: "heritage", limit: 7, used: 2 }],
    distributions: [{ shipmentId: "SHIP-OLD", units: 11 }, { lotId: "LOT-WILLOW", shipmentId: "SHIP-WILLOW", units: 2 }],
    newPortions: [{ shipmentId: "SHIP-LATE", units: 7 }, { shipmentId: "SHIP-NEXT", units: 5 }],
  },
  {
    lotId: "LOT-BRAVO", classCode: "dwarf", otherClass: "heritage", units: 53, receivedAt: 31, failedAt: 36,
    targetLotIndex: 2, targetClassIndex: 2,
    lots: [
      { id: "LOT-ORCHID", classCode: "heritage", units: 28 },
      { id: "LOT-THYME", classCode: "rare", units: 16 },
      { id: "LOT-BRAVO", classCode: "dwarf", units: 53 },
      { id: "LOT-UMBER", classCode: "heritage", units: 31 },
    ],
    classLimits: [
      { classCode: "heritage", limit: 8, used: 6 },
      { classCode: "rare", limit: 4, used: 1 },
      { classCode: "dwarf", limit: 6, used: 1 },
    ],
    distributions: [
      { shipmentId: "SHIP-PRIOR", units: 3 },
      { shipmentId: "SHIP-EARLY", units: 12 },
      { lotId: "LOT-ORCHID", shipmentId: "SHIP-ORCHID", units: 4 },
    ],
    newPortions: [{ shipmentId: "SHIP-SECOND", units: 4 }, { shipmentId: "SHIP-FIRST", units: 6 }],
  },
];
const results = [cases, cases.slice().reverse()].flatMap((order) => order.map(evaluateCase));
console.log(JSON.stringify({
  localA: results.every((result) => result.localA),
  localB: results.every((result) => result.localB),
  remoteA: results.every((result) => result.remoteA),
  remoteB: results.every((result) => result.remoteB),
  restore: results.every((result) => result.restore),
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
