import assert from "node:assert/strict";
import test from "node:test";

import { rankNotifications } from "../priority.js";

test("ranks by priority and then sequence", () => {
  const ranked = rankNotifications([
    { id: "low", priority: 1, sequence: 0 },
    { id: "one", priority: 6, sequence: 1 },
    { id: "two", priority: 6, sequence: 2 },
  ]);
  assert.deepEqual(ranked.map((item) => item.id), ["one", "two", "low"]);
});
