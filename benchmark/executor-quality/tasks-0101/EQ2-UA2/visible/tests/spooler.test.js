import assert from "node:assert/strict";
import test from "node:test";

import { enqueueAll } from "../spooler.js";

test("spools one copy of an immediately repeated job", () => {
  const queue = enqueueAll([
    { id: "draft", document: "draft.pdf", priority: 5 },
    { id: "draft", document: "draft.pdf", priority: 5 },
  ]);
  assert.deepEqual(queue.map((job) => job.id), ["draft"]);
});
