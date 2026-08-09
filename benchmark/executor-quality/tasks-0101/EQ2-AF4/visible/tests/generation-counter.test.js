import assert from "node:assert/strict";
import test from "node:test";

import { GenerationCounter } from "../generation-counter.js";

test("tracks generations independently and remembers completed batches", () => {
  const counter = new GenerationCounter({ api: 3 });
  assert.equal(counter.next("api"), 4);
  assert.equal(counter.next("media"), 1);
  counter.complete("batch-a");
  assert.equal(counter.hasCompleted("batch-a"), true);
  assert.deepEqual(counter.view(), {
    generations: { api: 4, media: 1 },
    completed: ["batch-a"],
  });
});
