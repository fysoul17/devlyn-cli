#!/usr/bin/env python3
"""Evaluate bakery manifestations without changing the supplied fixture."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


RUNNER = r'''
const { makeProductionDay } = require("./support/fixtures");
const { failRise } = require("./planner/batch_planner");
const { nextOvenBatch } = require("./oven/oven_scheduler");
const { proofStockIsSettled } = require("./checks/failed_proof_policy");

function before(day) {
  return day.ingredients.map((item) => ({ ...item }));
}

function ovenOrder(day, thermal) {
  const batchId = day.batches[0].id;
  const same = { id: `${batchId}-same`, group: thermal.lastGroup, readyAt: thermal.lastFinishedAt + 2 };
  const changed = {
    id: `${batchId}-changed`,
    group: day.groupCards.find((group) => group !== thermal.lastGroup),
    readyAt: thermal.lastFinishedAt + 2,
  };
  const immediate = nextOvenBatch(day, [
    changed,
    same,
  ], thermal.lastFinishedAt + 4);
  const delayedSame = {
    ...same,
    id: `${batchId}-delayed-same`,
    readyAt: thermal.lastFinishedAt + thermal.changeoverMinutes + 1,
  };
  const delayed = nextOvenBatch(day, [
    delayedSame,
    changed,
  ], thermal.lastFinishedAt + thermal.changeoverMinutes);
  return immediate === same && delayed === changed;
}

const local = makeProductionDay();
const localId = local.batches[0].id;
const localResult = failRise(local, localId);

const remote = makeProductionDay();
const remoteBefore = before(remote);
const remoteId = remote.batches[0].id;
const remoteThermal = { ...remote.ovenSlots[0] };
failRise(remote, remoteId);

const repeated = makeProductionDay();
const repeatedBefore = before(repeated);
const repeatedId = repeated.batches[0].id;
const repeatedThermal = { ...repeated.ovenSlots[0] };
const first = failRise(repeated, repeatedId);
const second = failRise(repeated, repeatedId);

console.log(JSON.stringify({
  localA: localResult.requeued === true && local.retryQueue.length === 1 && local.retryQueue[0] === localId,
  localB: local.batches[0].status === "queued" && local.batches[0].riseState === "failed",
  remoteA: remote.ovenSlots[0].locked === false && ovenOrder(remote, remoteThermal),
  remoteB: proofStockIsSettled(remote, remoteId, remoteBefore),
  restore: first.requeued === true && second.requeued === true
    && repeated.retryQueue.filter((entry) => entry === repeatedId).length === 1
    && proofStockIsSettled(repeated, repeatedId, repeatedBefore)
    && ovenOrder(repeated, repeatedThermal),
}));
'''


def evaluate(workdir: Path) -> dict[str, bool]:
    result = subprocess.run(
        ["node", "-e", RUNNER], cwd=workdir, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=10,
    )
    if result.returncode:
        raise SystemExit(result.stderr or "node runner failed")
    return json.loads(result.stdout)


def main() -> None:
    values = evaluate(Path(sys.argv[1]))
    roles = ("local-a", "local-b", "remote-a", "remote-b", "restore")
    keys = ("localA", "localB", "remoteA", "remoteB", "restore")
    print(json.dumps({"manifestations": [
        {"id": role, "passed": bool(values[key])} for role, key in zip(roles, keys)
    ]}, separators=(",", ":")))


if __name__ == "__main__":
    main()
