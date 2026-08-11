#!/usr/bin/env python3
"""Evaluate dependent admin-gate behavior without modifying the supplied tree."""

import json
from pathlib import Path
import subprocess
import sys


WORKDIR = Path(sys.argv[1]).resolve()
RUNNER = r'''import { pathToFileURL } from "node:url";

const root = process.argv[1];
const load = async (name) => import(pathToFileURL(`${root}/${name}`).href);
const { createRateLimitFixture, validChange, validRequest } = await load("fixtures.js");

const denial = { ok: false, error: "admin_denied" };
const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);

function gateOnlyDenial(state, requestId) {
  return same(state.decisions.entries, [{
    sequence: 1,
    requestId,
    outcome: "denied",
    error: "admin_denied",
  }])
    && state.rejections.entries.length === 0
    && state.store.revisions.length === 0;
}

function missingQuorumCannotReachWriter() {
  const state = createRateLimitFixture();
  const request = validRequest({
    id: "request-one-approval",
    approvalIds: ["approval-east"],
  });
  const result = state.gate.submit(request);
  return same(result, denial) && gateOnlyDenial(state, request.id);
}

function inactivePeerCannotReachWriter() {
  const state = createRateLimitFixture();
  const request = validRequest({
    id: "request-retired-approval",
    approvalIds: ["approval-east", "approval-retired"],
  });
  const result = state.gate.submit(request);
  return same(result, denial) && gateOnlyDenial(state, request.id);
}

function differentReasonsUseWriterPriority() {
  const state = createRateLimitFixture();
  const result = state.gate.submit(validRequest({
    id: "request-mixed-defects",
    change: validChange({
      id: "change-mixed-defects",
      rules: [
        { bucket: "member", windowMs: 1_000, limit: 0 },
        { bucket: "internal", windowMs: 60_000, limit: 50 },
      ],
    }),
  }));
  return same(result, {
    ok: false,
    error: "limit_rejected",
    reason: "unknown_bucket",
    field: "rules[1].bucket",
    ruleIndex: 1,
  })
    && state.rejections.entries[0]?.reason === "unknown_bucket"
    && state.decisions.entries[0]?.reason === "unknown_bucket"
    && state.decisions.entries[0]?.outcome === "rejected"
    && state.rejections.entries.length === 1
    && state.decisions.entries.length === 1
    && state.store.revisions.length === 0;
}

function matchingReasonsKeepRuleArrival() {
  const state = createRateLimitFixture();
  const result = state.gate.submit(validRequest({
    id: "request-window-tie",
    change: validChange({
      id: "change-window-tie",
      rules: [
        { bucket: "anonymous", windowMs: 5_000, limit: 20 },
        { bucket: "member", windowMs: 10_000, limit: 50 },
      ],
    }),
  }));
  return result.reason === "invalid_window"
    && result.field === "rules[0].windowMs"
    && result.ruleIndex === 0
    && state.rejections.entries[0]?.ruleIndex === 0
    && state.decisions.entries[0]?.reason === "invalid_window"
    && state.rejections.entries.length === 1
    && state.store.revisions.length === 0;
}

function deniedMalformedChangeLeavesOnlyGateDecision() {
  const state = createRateLimitFixture();
  const request = validRequest({
    id: "request-denied-malformed",
    approvalIds: ["approval-east"],
    change: validChange({
      id: "change-denied-malformed",
      rules: [
        { bucket: "member", windowMs: 5_000, limit: 0 },
        { bucket: "internal", windowMs: 60_000, limit: 40 },
      ],
    }),
  });
  const result = state.gate.submit(request);
  return same(result, denial) && gateOnlyDenial(state, request.id);
}

process.stdout.write(JSON.stringify([
  missingQuorumCannotReachWriter(),
  inactivePeerCannotReachWriter(),
  differentReasonsUseWriterPriority(),
  matchingReasonsKeepRuleArrival(),
  deniedMalformedChangeLeavesOnlyGateDecision(),
]));
'''
INVARIANT = (
    "The admin gate must establish an active two-approver quorum before asking the limit writer to "
    "inspect a change, limit-writer rejections rank unknown-bucket before invalid-window before "
    "invalid-limit with rule arrival order breaking same-reason ties, and an unauthorized malformed "
    "change must return admin_denied while appending only an admin-denied gate decision and no writer "
    "rejection or stored limit revision."
)


completed = subprocess.run(
    ["node", "--input-type=module", "--eval", RUNNER, str(WORKDIR)],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
    timeout=10,
)
try:
    checks = json.loads(completed.stdout) if completed.returncode == 0 else []
except json.JSONDecodeError:
    checks = []
if len(checks) != 5 or any(type(value) is not bool for value in checks):
    checks = [False, False, False, False, False]

identifiers = ["axis1-a", "axis1-b", "axis2-a", "axis2-b", "interaction"]
print(
    json.dumps(
        {
            "manifestations": [
                {"id": identifier, "invariant": INVARIANT, "passed": passed}
                for identifier, passed in zip(identifiers, checks, strict=True)
            ]
        },
        separators=(",", ":"),
    )
)
