import assert from "node:assert/strict";
import test from "node:test";

import { createRateLimitFixture, validChange } from "../fixtures.js";

const ADMITTED = Object.freeze({
  ok: true,
  tier: "edge",
  approvedBy: ["operator-north", "security-edge"],
});

test("writer traverses policy checks before rule source order", () => {
  const state = createRateLimitFixture();
  const result = state.writer.apply(validChange({
    rules: [
      { bucket: "member", windowMs: 1_000, limit: 0 },
      { bucket: "internal", windowMs: 60_000, limit: 40 },
    ],
  }), ADMITTED);
  assert.equal(result.reason, "unknown_bucket");
  assert.equal(result.ruleIndex, 1);
});

test("writer retains source order inside one policy check", () => {
  const state = createRateLimitFixture();
  const result = state.writer.apply(validChange({
    rules: [
      { bucket: "anonymous", windowMs: 5_000, limit: 20 },
      { bucket: "member", windowMs: 10_000, limit: 50 },
    ],
  }), ADMITTED);
  assert.equal(result.reason, "invalid_window");
  assert.equal(result.ruleIndex, 0);
});

test("a denied admission cannot publish a prepared validation", () => {
  const state = createRateLimitFixture();
  const result = state.writer.apply(
    validChange({ rules: [{ bucket: "internal", windowMs: 5_000, limit: 0 }] }),
    { ok: false, error: "admin_denied" },
  );
  assert.deepEqual(result, { ok: false, error: "admin_denied" });
  assert.equal(state.validations.entries.length, 0);
  assert.equal(state.store.revisions.length, 0);
});
