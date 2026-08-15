#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


PROGRAM = r'''
const path = require("node:path");
const api = require(process.argv[1]);
const planner = require(path.join(path.dirname(process.argv[1]), "..", "planning", "batch_optimizer.js"));
const mode = process.argv[2];
const state = api.createDispatchState();
const add = (id, courier, rank) => api.addAssignment(state, { orderId: id, courierId: courier, rank });
let passed = false;

if (mode === "localA") {
  add("order-17", "courier-4", 3);
  api.declineAssignment(state, "order-17");
  const item = state.assignments.get("order-17");
  passed = item.courierId === null && item.status === "waiting" && state.waitingOrders.length === 1;
} else if (mode === "localB") {
  add("order-29", "courier-8", 5);
  api.declineAssignment(state, "order-29");
  const item = state.assignments.get("order-29");
  passed = item.courierId === null && state.waitingOrders[0]?.rank === 5;
} else if (mode === "remoteA") {
  add("order-41", "courier-2", 4);
  const wave = planner.sealWave(state, "wave-7", ["order-41"]);
  api.declineAssignment(state, "order-41");
  const item = state.assignments.get("order-41");
  passed = item.courierId === "courier-2" && planner.snapshotMatches(wave, state) && state.waitingOrders.length === 1;
} else if (mode === "remoteB") {
  add("order-53", "courier-6", 4);
  planner.sealWave(state, "wave-8", ["order-53"]);
  api.declineAssignment(state, "order-53");
  api.declineAssignment(state, "order-53");
  passed = state.waitingOrders.length === 1 && state.waitingOrders[0].rank === 4;
} else if (mode === "restore") {
  add("order-67", "courier-9", 2);
  const wave = planner.sealWave(state, "wave-9", ["order-67"]);
  api.declineAssignment(state, "order-67");
  api.declineAssignment(state, "order-67");
  const item = state.assignments.get("order-67");
  passed = planner.snapshotMatches(wave, state) && item.courierId === "courier-9" && state.waitingOrders.length === 1 && state.waitingOrders[0].rank === 2;
}

process.stdout.write(JSON.stringify({ passed }));
'''


def run(workdir: Path, mode: str) -> bool:
    result = subprocess.run(
        ["node", "-e", PROGRAM, str(workdir / "dispatch" / "courier_assigner.js"), mode],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
    )
    if result.returncode:
        raise SystemExit(result.stderr)
    return bool(json.loads(result.stdout)["passed"])


def main() -> None:
    workdir = Path(sys.argv[1]).resolve()
    modes = ["localA", "localB", "remoteA", "remoteB", "restore"]
    identifiers = ["local-a", "local-b", "remote-a", "remote-b", "restore"]
    manifestations = [
        {"id": identifier, "passed": run(workdir, mode)}
        for identifier, mode in zip(identifiers, modes)
    ]
    print(json.dumps({"manifestations": manifestations}, separators=(",", ":")))


if __name__ == "__main__":
    main()
