"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { rankRequests } = require("../priority");

test("ranks higher rollout priority first and keeps ties stable", () => {
  const ranked = rankRequests([
    { id: "low", priority: 1, arrival: 0 },
    { id: "first", priority: 5, arrival: 1 },
    { id: "second", priority: 5, arrival: 2 },
  ]);

  assert.deepEqual(ranked.map(({ id }) => id), ["first", "second", "low"]);
});
