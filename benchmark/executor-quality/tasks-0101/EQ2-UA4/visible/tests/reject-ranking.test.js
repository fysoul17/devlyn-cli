import assert from "node:assert/strict";
import test from "node:test";

import { rankRejects } from "../reject-ranking.js";

test("ranks reject reasons and preserves source ties", () => {
  const rejects = [
    { source: 0, reason: "amount" },
    { source: 1, reason: "account" },
    { source: 2, reason: "amount" },
  ];
  assert.deepEqual(rankRejects(rejects), [
    { source: 1, reason: "account" },
    { source: 0, reason: "amount" },
    { source: 2, reason: "amount" },
  ]);
});
