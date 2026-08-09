import assert from "node:assert/strict";
import test from "node:test";

import { intakeBatch } from "../intake.js";

test("returns one valid posting", () => {
  assert.deepEqual(intakeBatch(["A001|acct-east|12|2"]), {
    posted: ["A001"],
    rejected: [],
  });
});

test("returns one parsing rejection", () => {
  assert.deepEqual(intakeBatch(["bad"]), {
    posted: [],
    rejected: [{ source: 0, reason: "format" }],
  });
});
