import assert from "node:assert/strict";
import test from "node:test";

import { parseLine } from "../line-parser.js";

test("parses a valid invoice line", () => {
  assert.deepEqual(parseLine("A001|acct-north|42.50|3", 2), {
    ok: true,
    value: { id: "A001", account: "acct-north", amount: 42.5, priority: 3, source: 2 },
  });
});

test("uses the highest-precedence reason for one malformed line", () => {
  assert.deepEqual(parseLine("bad|wrong|-4|x", 0), {
    ok: false,
    error: { source: 0, reason: "format" },
  });
});
