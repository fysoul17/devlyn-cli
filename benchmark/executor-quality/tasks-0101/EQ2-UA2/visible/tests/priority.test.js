import assert from "node:assert/strict";
import test from "node:test";

import { rankJobs } from "../priority.js";

test("ranks urgent work first and keeps arrival order for ties", () => {
  const jobs = [
    { id: "early", priority: 4, sequence: 0 },
    { id: "urgent", priority: 8, sequence: 1 },
    { id: "later", priority: 4, sequence: 2 },
  ];
  assert.deepEqual(rankJobs(jobs).map((job) => job.id), ["urgent", "early", "later"]);
});
