import assert from "node:assert/strict";
import test from "node:test";

import { scheduleFanout } from "../scheduler.js";

test("fans out independent notifications in schedule order", () => {
  const deliveries = scheduleFanout([
    { id: "low", body: "l", priority: 1, recipients: ["zo"] },
    { id: "high", body: "h", priority: 8, recipients: ["ann", "bo"] },
  ]);
  assert.deepEqual(
    deliveries.map(({ id, recipient }) => [id, recipient]),
    [["high", "ann"], ["high", "bo"], ["low", "zo"]],
  );
});
