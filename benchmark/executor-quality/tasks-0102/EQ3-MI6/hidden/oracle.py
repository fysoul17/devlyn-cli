#!/usr/bin/env python3
"""Evaluate the election-supply fixture without writing to the supplied worktree."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROGRAM = r'''
const path = require("node:path");
const root = path.resolve(process.argv[1]);
const { createAllocation, markLocked } = require(path.join(root, "allocator", "allocation_state.js"));
const { moveSupply } = require(path.join(root, "allocator", "stock_transfer.js"));
const { drawsOnlyFromSurplus, redistributeShortfall } = require(path.join(root, "redistribution", "shortfall_redistributor.js"));
const { recountHoldFreezesInventory } = require(path.join(root, "checks", "recount_hold_test.js"));

function localA() {
  const state = createAllocation({ north: 9, south: 3 }, 4);
  const sourceId = "north";
  const targetId = "south";
  const quantity = 2;
  const beforeSource = state.counts[sourceId];
  const beforeTarget = state.counts[targetId];
  const receipt = moveSupply(state, sourceId, targetId, quantity);
  return receipt.moved && state.counts[sourceId] === beforeSource - quantity
    && state.counts[targetId] === beforeTarget + quantity;
}

function localB() {
  const state = createAllocation({ north: 6, south: 4 }, 2);
  const sourceId = "north";
  const targetId = "south";
  const before = { ...state.counts };
  const receipt = moveSupply(state, sourceId, targetId, before[sourceId] + 1);
  return !receipt.moved && receipt.reason === "count"
    && state.counts[sourceId] === before[sourceId]
    && state.counts[targetId] === before[targetId];
}

function remoteA() {
  const state = createAllocation({ alpha: 5, bravo: 8, south: 1 }, 4);
  const targetId = "south";
  const requests = [
    { sourceId: "alpha", targetId, quantity: 2 },
    { sourceId: "bravo", targetId, quantity: 2 },
  ];
  const before = { ...state.counts };
  const report = redistributeShortfall(state, moveSupply, targetId, requests);
  const delivered = report.moved.reduce((sum, receipt) => sum + receipt.quantity, 0);
  return drawsOnlyFromSurplus(state, report, requests)
    && report.blocked.length === 1 && report.moved.length === 1
    && report.blocked[0].sourceId === requests[0].sourceId
    && report.moved[0].sourceId === requests[1].sourceId
    && state.counts[requests[0].sourceId] === before[requests[0].sourceId]
    && state.counts[targetId] === before[targetId] + delivered;
}

function remoteB() {
  const state = createAllocation({ north: 8, south: 2 }, 3);
  return recountHoldFreezesInventory(moveSupply, markLocked, state, "north", "south", 2);
}

function restore() {
  const state = createAllocation({ north: 9, south: 7, east: 4 }, 4);
  const sourceId = "north";
  const targetId = "south";
  const quantity = 2;
  const beforeSource = state.counts[sourceId];
  const beforeTarget = state.counts[targetId];
  const first = moveSupply(state, sourceId, targetId, quantity);
  const firstEntry = state.transferLedger[0];
  const lockedSource = "north";
  const lockedTarget = "east";
  const beforeLockedSource = state.counts[lockedSource];
  const beforeLockedTarget = state.counts[lockedTarget];
  const frozen = recountHoldFreezesInventory(
    moveSupply,
    markLocked,
    state,
    lockedSource,
    lockedTarget,
    1,
  );
  return first.moved
    && state.counts[sourceId] === beforeSource - quantity
    && state.counts[targetId] === beforeTarget + quantity
    && frozen
    && state.counts[lockedSource] === beforeLockedSource
    && state.counts[lockedTarget] === beforeLockedTarget
    && state.transferLedger.length === 1
    && firstEntry.sourceId === sourceId
    && firstEntry.targetId === targetId
    && firstEntry.quantity === quantity
    && firstEntry.sourceBefore === beforeSource
    && firstEntry.targetBefore === beforeTarget;
}

console.log(JSON.stringify({
  localA: localA(),
  localB: localB(),
  remoteA: remoteA(),
  remoteB: remoteB(),
  restore: restore(),
}));
'''


def evaluate(workdir: Path) -> dict[str, bool]:
    result = subprocess.run(
        ["node", "-e", PROGRAM, str(workdir)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
    )
    if result.returncode:
        raise SystemExit(result.stderr or "node evaluator failed")
    values = json.loads(result.stdout)
    return {
        "local-a": bool(values["localA"]),
        "local-b": bool(values["localB"]),
        "remote-a": bool(values["remoteA"]),
        "remote-b": bool(values["remoteB"]),
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
