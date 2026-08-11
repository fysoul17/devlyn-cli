import assert from "node:assert/strict";
import test from "node:test";

import { createAccrualEvent } from "../accrual-event.js";
import { accrualRequest, loyaltyFixture } from "../fixtures.js";

test("event aggregation observes the per-cycle points cap", () => {
  const { store } = loyaltyFixture({ maxPoints: 60 });
  const receipt = store.aggregate(accrualRequest({
    events: [
      createAccrualEvent({ eventId: "large-purchase", cycleId: "2026-W32", points: 50 }),
      createAccrualEvent({ eventId: "survey", cycleId: "2026-W32", points: 30 }),
    ],
  }));
  assert.equal(receipt.pointsAwarded, 60);
  assert.deepEqual(receipt.allocations, [
    { eventId: "large-purchase", points: 50 },
    { eventId: "survey", points: 10 },
  ]);
});
