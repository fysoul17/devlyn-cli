import assert from "node:assert/strict";
import test from "node:test";

import {
  createRateLimitFixture,
  validBatch,
  validChange,
  validRequest,
} from "../fixtures.js";

test("a mixed batch replaces the current admission on every request", () => {
  const state = createRateLimitFixture();
  const result = state.gate.applyBatch(validBatch([
    validRequest({ id: "request-applied-a", change: validChange({ id: "change-applied-a" }) }),
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
  ], "batch-mixed"));

  assert.deepEqual(result.results.map(({ requestId, error, status }) => ({
    requestId,
    error,
    status,
  })), [
    { requestId: "request-applied-a", error: undefined, status: "applied" },
    { requestId: "request-rejected", error: "limit_rejected", status: undefined },
    { requestId: "request-denied", error: "admin_denied", status: undefined },
    { requestId: "request-applied-b", error: undefined, status: "applied" },
  ]);
  assert.deepEqual(state.ledger.decisionEntries.map(({ outcome }) => outcome), [
    "applied",
    "rejected",
    "denied",
    "applied",
  ]);
  assert.equal(state.validations.entries.length, 1);
  assert.equal(state.store.revisions.length, 2);
});

test("missing role coverage denies a malformed request without writer state", () => {
  const state = createRateLimitFixture();
  const result = state.gate.applyBatch(validBatch([validRequest({
    approvalIds: ["operator-north", "operator-south"],
    change: validChange({
      rules: [{ bucket: "internal", windowMs: 5_000, limit: 0 }],
    }),
  })]));
  assert.deepEqual(result.results[0], {
    requestId: "request-edge-defaults",
    ok: false,
    error: "admin_denied",
  });
  assert.equal(state.validations.entries.length, 0);
  assert.equal(state.store.revisions.length, 0);
});
