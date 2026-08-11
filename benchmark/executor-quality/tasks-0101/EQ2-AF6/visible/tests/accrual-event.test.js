import assert from "node:assert/strict";
import test from "node:test";

import { createAccrualEvent } from "../accrual-event.js";

test("accrual events are validated and frozen", () => {
  const event = createAccrualEvent({ eventId: "purchase-7", cycleId: "2026-W32", points: 25 });
  assert.deepEqual(event, { eventId: "purchase-7", cycleId: "2026-W32", points: 25 });
  assert.equal(Object.isFrozen(event), true);
  assert.throws(() => createAccrualEvent({ eventId: "", cycleId: "2026-W32", points: 25 }), TypeError);
});
