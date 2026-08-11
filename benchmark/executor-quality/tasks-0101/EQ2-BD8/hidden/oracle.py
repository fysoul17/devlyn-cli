#!/usr/bin/env python3
"""Evaluate rate-limit administration behavior without mutating the supplied tree."""

import json
from pathlib import Path
import subprocess
import sys


WORKDIR = Path(sys.argv[1]).resolve()
RUNNER = r'''import { pathToFileURL } from "node:url";

const root = process.argv[1];
const load = async (name) => import(pathToFileURL(`${root}/${name}`).href);
const { createRateLimitFixture, validBatch, validChange, validRequest } = await load("fixtures.js");

const admitted = Object.freeze({
  ok: true,
  tier: "edge",
  approvedBy: ["operator-north", "security-edge"],
});
const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);

function deniedMalformedRequest(approvalIds, rules) {
  const state = createRateLimitFixture();
  const batch = state.gate.applyBatch(validBatch([validRequest({
    approvalIds,
    change: validChange({ rules }),
  })]));
  return same(batch.results[0], {
    requestId: "request-edge-defaults",
    ok: false,
    error: "admin_denied",
  })
    && state.ledger.approvalEntries.length === 1
    && state.ledger.approvalEntries[0].ok === false
    && state.ledger.decisionEntries.length === 1
    && state.ledger.decisionEntries[0].outcome === "denied"
    && state.validations.entries.length === 0
    && state.store.revisions.length === 0;
}

function missingRoleStopsValidation() {
  return deniedMalformedRequest(
    ["operator-north", "operator-south"],
    [{ bucket: "internal", windowMs: 5_000, limit: 0 }],
  );
}

function inactiveApprovalStopsValidation() {
  return deniedMalformedRequest(
    ["operator-north", "security-retired"],
    [{ bucket: "member", windowMs: 10_000, limit: 0 }],
  );
}

function distinctIssuesUseWriterPriority() {
  const state = createRateLimitFixture();
  const result = state.writer.apply(validChange({
    rules: [
      { bucket: "member", windowMs: 1_000, limit: 0 },
      { bucket: "internal", windowMs: 60_000, limit: 40 },
    ],
  }), admitted);
  const entry = state.validations.entries[0];
  return same(result, {
    ok: false,
    error: "limit_rejected",
    reason: "unknown_bucket",
    field: "rules[1].bucket",
    ruleIndex: 1,
  })
    && entry?.reason === "unknown_bucket"
    && entry?.ruleIndex === 1
    && state.validations.entries.length === 1
    && state.store.revisions.length === 0;
}

function sameIssueUsesRuleSourceOrder() {
  const state = createRateLimitFixture();
  const result = state.writer.apply(validChange({
    rules: [
      { bucket: "anonymous", windowMs: 5_000, limit: 20 },
      { bucket: "member", windowMs: 10_000, limit: 50 },
    ],
  }), admitted);
  const entry = state.validations.entries[0];
  return result.reason === "invalid_window"
    && result.field === "rules[0].windowMs"
    && result.ruleIndex === 0
    && entry?.reason === "invalid_window"
    && entry?.ruleIndex === 0
    && state.validations.entries.length === 1
    && state.store.revisions.length === 0;
}

function accumulatedGateStateDoesNotCarryAdmission() {
  const state = createRateLimitFixture();
  const batch = state.gate.applyBatch(validBatch([
    validRequest({
      id: "request-applied-a",
      change: validChange({ id: "change-applied-a" }),
    }),
    validRequest({
      id: "request-rejected",
      change: validChange({
        id: "change-rejected",
        rules: [
          { bucket: "member", windowMs: 1_000, limit: 0 },
          { bucket: "internal", windowMs: 60_000, limit: 40 },
        ],
      }),
    }),
    validRequest({
      id: "request-denied",
      tier: "core",
      approvalIds: ["operator-north", "security-edge"],
      change: validChange({
        id: "change-denied",
        rules: [{ bucket: "internal", windowMs: 5_000, limit: 0 }],
      }),
    }),
    validRequest({
      id: "request-applied-b",
      tier: "core",
      approvalIds: ["operator-north", "security-core"],
      change: validChange({ id: "change-applied-b" }),
    }),
  ], "batch-accumulated"));
  return same(batch.results.map(({ requestId, error, status }) => ({
    requestId,
    error,
    status,
  })), [
    { requestId: "request-applied-a", status: "applied" },
    { requestId: "request-rejected", error: "limit_rejected" },
    { requestId: "request-denied", error: "admin_denied" },
    { requestId: "request-applied-b", status: "applied" },
  ])
    && same(state.ledger.approvalEntries.map(({ ok }) => ok), [true, true, false, true])
    && same(state.ledger.decisionEntries.map(({ outcome }) => outcome), [
      "applied",
      "rejected",
      "denied",
      "applied",
    ])
    && state.validations.entries.length === 1
    && state.validations.entries[0].sequence === 1
    && state.validations.entries[0].changeId === "change-rejected"
    && state.validations.entries[0].reason === "unknown_bucket"
    && state.store.revisions.length === 2
    && state.store.revisions[0].changeId === "change-applied-a"
    && state.store.revisions[1].changeId === "change-applied-b"
    && state.store.revisions[1].tier === "core";
}

process.stdout.write(JSON.stringify([
  missingRoleStopsValidation(),
  inactiveApprovalStopsValidation(),
  distinctIssuesUseWriterPriority(),
  sameIssueUsesRuleSourceOrder(),
  accumulatedGateStateDoesNotCarryAdmission(),
]));
'''
INVARIANT = (
    "The admin gate must bind every rate-limit change in a batch to that change's current "
    "operator-and-security approval before the limit writer may publish a validation result, writer "
    "errors select unknown-bucket before invalid-window before invalid-limit with rule source order "
    "breaking same-reason ties, and when an unauthorized malformed change follows authorized and "
    "rejected changes in the same batch its result must remain admin_denied with a denied gate decision "
    "and no inherited admission, validation entry, or stored revision while later authorized changes "
    "continue from the accumulated journal state."
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
