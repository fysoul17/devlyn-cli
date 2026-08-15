#!/usr/bin/env python3
"""Evaluate greenhouse setpoint manifestations without changing the fixture."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


RUNNER = r'''
const { makeGreenhouse } = require("./support/fixtures");
const { updateSetpoint } = require("./editor/setpoint_editor");
const { selectCompatibleProfile, sharedAirIsAligned } = require("./interlock/zone_interlock");
const { faultProfileIsHeld } = require("./checks/sensor_fault_test");

function copy(value) {
  return JSON.parse(JSON.stringify(value));
}

function localReceipts() {
  const greenhouse = makeGreenhouse({ sensorState: "ready" });
  const before = copy(greenhouse);
  const zone = before.zones[0];
  const requested = before.profiles.find((profile) => profile.id !== zone.profileId);
  const result = updateSetpoint(greenhouse, zone.id, requested.id);
  const receipt = greenhouse.editReceipts[0];
  return {
    profile: result.updated === true && zone.profileId !== requested.id
      && greenhouse.zones.find((entry) => entry.id === zone.id).profileId === requested.id,
    receipt: result.updated === true && greenhouse.editReceipts.length === 1
      && receipt.zoneId === zone.id && receipt.profileId === requested.id,
  };
}

function faultRun(options) {
  const greenhouse = makeGreenhouse(options);
  if (options.targetIndex === 1) {
    greenhouse.zones.reverse();
  }
  const before = copy(greenhouse);
  const target = before.zones.find((zone) => zone.id === options.targetId);
  const peer = before.zones.find((zone) => zone.id !== options.targetId);
  const safe = target.lastGoodProfileId;
  const safeProfile = before.profiles.find((profile) => profile.id === safe);
  const requested = before.profiles.find((profile) => profile.airMode !== safeProfile.airMode).id;
  const legacy = before.retryJournal[0];
  const first = updateSetpoint(greenhouse, target.id, requested);
  const second = updateSetpoint(greenhouse, target.id, requested);
  const entries = greenhouse.retryJournal.filter((entry) => entry.zoneId === target.id
    && entry.requestedProfileId === requested);
  const receipts = greenhouse.editReceipts.filter((entry) => entry.zoneId === target.id
    && entry.profileId === requested);
  const retainedLegacy = greenhouse.retryJournal.find((entry) => entry.id === legacy.id);
  const targetChoice = selectCompatibleProfile(greenhouse, target.id, [requested, safe]);
  const peerChoice = selectCompatibleProfile(greenhouse, peer.id, [requested, safe]);
  return {
    interlock: sharedAirIsAligned(greenhouse) && targetChoice === safe && peerChoice === safe,
    targeted: greenhouse.zones.findIndex((zone) => zone.id === target.id) === options.targetIndex,
    restored: faultProfileIsHeld(greenhouse, target.id, before),
    journal: first.updated === true && second.updated === true && entries.length === 1 && receipts.length === 2
      && entries[0].zoneId === target.id && entries[0].requestedProfileId === requested
      && entries[0].previousProfileId === target.profileId
      && retainedLegacy !== undefined && retainedLegacy.zoneId === legacy.zoneId
      && retainedLegacy.requestedProfileId === legacy.requestedProfileId
      && retainedLegacy.previousProfileId === legacy.previousProfileId,
  };
}

const local = localReceipts();
const firstShape = { targetId: "A1", peerId: "B2", safeId: "dawn", requestedId: "mist", alternateId: "shade", group: "east", targetIndex: 0 };
const secondShape = { targetId: "C3", peerId: "D4", safeId: "veil", requestedId: "spray", alternateId: "calm", group: "west", targetIndex: 1 };
const ordered = [faultRun(firstShape), faultRun(secondShape)];
const permuted = [faultRun(secondShape), faultRun(firstShape)];
const runs = ordered.concat(permuted);

console.log(JSON.stringify({
  localA: local.profile,
  localB: local.receipt,
  remoteA: runs.every((run) => run.interlock && run.targeted),
  remoteB: runs.every((run) => run.restored),
  restore: runs.every((run) => run.journal && run.restored && run.interlock && run.targeted),
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
