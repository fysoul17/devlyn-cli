import assert from "node:assert/strict";
import test from "node:test";

import { normalizeJob } from "../job.js";

test("normalizes queue input", () => {
  assert.deepEqual(normalizeJob({ id: 42, document: "memo", priority: "3" }, 7), {
    id: "42",
    document: "memo",
    priority: 3,
    sequence: 7,
  });
});
