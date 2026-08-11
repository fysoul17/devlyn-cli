import assert from "node:assert/strict";
import test from "node:test";

import { createRateLimitFixture, validRequest } from "../fixtures.js";

test("an admitted request writes one revision and one gate decision", () => {
  const state = createRateLimitFixture();
  const result = state.gate.submit(validRequest());
  assert.equal(result.status, "applied");
  assert.equal(state.store.revisions.length, 1);
  assert.deepEqual(state.store.revisions[0].approvedBy, ["approval-east", "approval-west"]);
  assert.equal(state.decisions.entries[0].outcome, "applied");
  assert.equal(state.rejections.entries.length, 0);
});

test("one approver cannot write a well-formed change", () => {
  const state = createRateLimitFixture();
  const result = state.gate.submit(validRequest({ approvalIds: ["approval-east"] }));
  assert.deepEqual(result, { ok: false, error: "admin_denied" });
  assert.equal(state.store.revisions.length, 0);
  assert.equal(state.rejections.entries.length, 0);
  assert.equal(state.decisions.entries[0].outcome, "denied");
});
