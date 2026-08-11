import assert from "node:assert/strict";
import test from "node:test";

import { createRateLimitFixture, validChange } from "../fixtures.js";

test("writer selects policy priority across different issue reasons", () => {
  const state = createRateLimitFixture();
  const result = state.writer.inspect(validChange({
    rules: [
      { bucket: "member", windowMs: 1_000, limit: 0 },
      { bucket: "internal", windowMs: 60_000, limit: 50 },
    ],
  }));
  assert.equal(result.reason, "unknown_bucket");
  assert.equal(result.ruleIndex, 1);
  assert.equal(state.rejections.entries.length, 1);
});

test("writer keeps rule arrival order when issue reasons match", () => {
  const state = createRateLimitFixture();
  const result = state.writer.inspect(validChange({
    rules: [
      { bucket: "anonymous", windowMs: 5_000, limit: 20 },
      { bucket: "member", windowMs: 10_000, limit: 50 },
    ],
  }));
  assert.equal(result.reason, "invalid_window");
  assert.equal(result.ruleIndex, 0);
});
