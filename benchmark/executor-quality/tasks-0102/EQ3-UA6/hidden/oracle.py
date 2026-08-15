#!/usr/bin/env python3
"""Evaluate the porting fixture without writing to the supplied worktree."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


RUNNER = r'''
const { makePortState } = require("./support/fixtures");
const { correctionFor } = require("./porting/request_builder");
const { resubmitPortIn } = require("./porting/port_in_intake");
const { notifyCarrier } = require("./carrier/carrier_notifier");
const { correctionShown } = require("./checks/port_in_intake_test");
const { matchesOriginalMapping } = require("./checks/rollback_window_test");

const correction = correctionFor("SUB-91", "PR-41", "NorthLink");
const local = makePortState();
const localResult = resubmitPortIn(local, correction, notifyCarrier);

const remote = makePortState();
const originalRequestId = remote.requests[0].id;
const notificationHistory = JSON.stringify(remote.notifications);
const remoteResult = resubmitPortIn(remote, correction, notifyCarrier);
const current = remote.requests.find((request) => request.id === originalRequestId);

const repeated = makePortState();
const originalRequests = repeated.requests.map((request) => ({
  id: request.id,
  number: request.number,
  originalMapping: { ...request.originalMapping },
}));
const originalHistory = JSON.stringify(repeated.notifications);
const first = resubmitPortIn(repeated, correctionFor("SUB-91", "PR-41", "NorthLink"), notifyCarrier);
const second = resubmitPortIn(repeated, correctionFor("SUB-92", "PR-58", "SkyBridge"), notifyCarrier);
const retry = resubmitPortIn(repeated, correctionFor("SUB-91", "PR-41", "NorthLink"), notifyCarrier);
const restoredMappings = originalRequests.every((request) => {
  const restored = repeated.numberMap[request.number];
  const original = request.originalMapping;
  return restored.subscriptionId === original.subscriptionId
    && restored.carrier === original.carrier
    && restored.route === original.route;
});
const originalIdsRemain = originalRequests.every((request) => repeated.requests.some(
  (currentRequest) => currentRequest.id === request.id,
));

console.log(JSON.stringify({
  localA: localResult.accepted === true && correctionShown(localResult, local, correction),
  localB: localResult.accepted === true && local.requests.length === 2
    && local.requests.some((request) => request.status === "resubmitted"),
  remoteA: remoteResult.accepted === true && current !== undefined
    && JSON.stringify(remote.notifications) === notificationHistory,
  remoteB: current !== undefined && matchesOriginalMapping(remote, current),
  restore: first.accepted === true && second.accepted === true && retry.accepted === true
    && restoredMappings && originalIdsRemain
    && JSON.stringify(repeated.notifications) === originalHistory,
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
