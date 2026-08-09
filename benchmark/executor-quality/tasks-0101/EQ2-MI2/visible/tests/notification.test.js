import assert from "node:assert/strict";
import test from "node:test";

import { normalizeNotification } from "../notification.js";

test("normalizes a notification submission", () => {
  assert.deepEqual(
    normalizeNotification(
      { id: 12, body: "hello", priority: "4", recipients: [7, "sam"] },
      3,
    ),
    { id: "12", body: "hello", priority: 4, recipients: ["7", "sam"], sequence: 3 },
  );
});
