#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys


workdir = pathlib.Path(sys.argv[1])
program = r'''
const path = require("node:path");
const { attestRollout } = require(path.join(process.argv[1], "device-attestation.js"));

const trust = { canary: ["release", "ops"], stable: ["fleet"] };
const safeAttest = (requests, waveSize = 2) => {
  try {
    return attestRollout(requests, trust, waveSize);
  } catch (error) {
    if (error.message === "wave sequencing is not implemented") {
      return {};
    }
    throw error;
  }
};
const ids = (items = []) => items.map(({ id }) => id);
const places = (items = []) => items.map(({ wave, slot }) => `${wave}.${slot}`);

const firstOrder = safeAttest([
  { id: "low", signer: "release", ring: "canary", priority: 1 },
  { id: "urgent", signer: "ops", ring: "canary", priority: 9 },
]);
const axis1a = JSON.stringify(ids(firstOrder.accepted)) === JSON.stringify(["urgent", "low"])
  && JSON.stringify(places(firstOrder.accepted)) === JSON.stringify(["1.1", "1.2"])
  && JSON.stringify(firstOrder.rejected) === JSON.stringify([]);

const tiedOrder = safeAttest([
  { id: "first", signer: "release", ring: "canary", priority: 6 },
  { id: "low", signer: "fleet", ring: "stable", priority: 2 },
  { id: "second", signer: "ops", ring: "canary", priority: 6 },
]);
const axis1b = JSON.stringify(ids(tiedOrder.accepted)) === JSON.stringify(["first", "second", "low"])
  && JSON.stringify(places(tiedOrder.accepted)) === JSON.stringify(["1.1", "1.2", "2.1"]);

const deniedOnly = safeAttest([
  { id: "intruder", signer: "unknown", ring: "canary", priority: 8 },
]);
const axis2a = JSON.stringify(deniedOnly.accepted) === JSON.stringify([])
  && JSON.stringify(deniedOnly.rejected) === JSON.stringify(["intruder"]);

const isolatedWaves = safeAttest([
  { id: "allowed", signer: "fleet", ring: "stable", priority: 1 },
  { id: "wrong", signer: "fleet", ring: "canary", priority: 9 },
], 1);
const axis2b = JSON.stringify(ids(isolatedWaves.accepted)) === JSON.stringify(["allowed"])
  && JSON.stringify(isolatedWaves.rejected) === JSON.stringify(["wrong"]);

const composed = safeAttest([
  { id: "alpha", signer: "release", ring: "canary", priority: 10 },
  { id: "rogue", signer: "unknown", ring: "canary", priority: 9 },
  { id: "beta", signer: "fleet", ring: "stable", priority: 8 },
  { id: "gamma", signer: "ops", ring: "canary", priority: 5 },
  { id: "bad", signer: "unknown", ring: "stable", priority: 4 },
]);
const interaction = JSON.stringify(ids(composed.accepted)) === JSON.stringify(["alpha", "beta", "gamma"])
  && JSON.stringify(places(composed.accepted)) === JSON.stringify(["1.1", "1.2", "2.1"])
  && JSON.stringify(composed.rejected) === JSON.stringify(["rogue", "bad"]);

process.stdout.write(JSON.stringify({ axis1a, axis1b, axis2a, axis2b, interaction }));
'''
completed = subprocess.run(
    ["node", "-e", program, str(workdir)],
    cwd=workdir,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
    timeout=20,
)
if completed.returncode != 0:
    raise RuntimeError(completed.stderr or completed.stdout)

checks = json.loads(completed.stdout)
invariant = "The wave sequencer groups firmware requests by descending rollout priority with arrival order breaking ties, device attestation rejects every wave containing a device whose signer is not trusted for its rollout ring, and when privileged and unprivileged requests interleave attestation is decided before priority placement and wave grouping so denied devices neither consume positions nor cause trusted devices to be rejected with a mixed wave."

print(json.dumps({"manifestations": [
    {"id": "axis1-a", "invariant": invariant, "passed": checks["axis1a"]},
    {"id": "axis1-b", "invariant": invariant, "passed": checks["axis1b"]},
    {"id": "axis2-a", "invariant": invariant, "passed": checks["axis2a"]},
    {"id": "axis2-b", "invariant": invariant, "passed": checks["axis2b"]},
    {"id": "interaction", "invariant": invariant, "passed": checks["interaction"]},
]}))
