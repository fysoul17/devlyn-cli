#!/usr/bin/env python3
"""Evaluate the recycling fixture without writing to the supplied worktree."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


RUNNER = r'''
const { makeRoute } = require("./support/fixtures");
const { removeStop } = require("./route/route_editor");
const { removalShown, boardCountIs } = require("./checks/remove_stop_test");
const { intakeForecast } = require("./forecasting/depot_intake_forecaster");
const { followupIsValid } = require("./checks/missed_pickup_policy");

const local = makeRoute();
const localResult = removeStop(local, "oak");

const remote = makeRoute();
const remoteResult = removeStop(remote, "oak");
const remoteTotals = intakeForecast(remote);

const repeated = makeRoute();
const first = removeStop(repeated, "oak");
const second = removeStop(repeated, "oak");
const after = intakeForecast(repeated);

console.log(JSON.stringify({
  localA: localResult.removed === true && removalShown(local, "oak"),
  localB: localResult.removed === true && boardCountIs(local, 2),
  remoteA: remoteResult.removed === true && remoteTotals.paper === 4 && remoteTotals.glass === 2,
  remoteB: remote.followups.length === 1 && followupIsValid(remote, remote.followups[0]),
  restore: first.removed === true && second.removed === false && repeated.moves.length === 1
    && repeated.depotRebalanceLedger.length === 1
    && repeated.depotRebalanceLedger[0].removedStopId === "oak"
    && repeated.depotRebalanceLedger[0].forecast.paper === 4
    && repeated.depotRebalanceLedger[0].forecast.glass === 2
    && after.paper === 4 && after.glass === 2 && followupIsValid(repeated, repeated.followups[0]),
}));
'''


def evaluate(workdir: Path) -> dict[str, bool]:
    result = subprocess.run(
        ["node", "-e", RUNNER], cwd=workdir, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=10,
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
