import assert from "node:assert/strict";
import test from "node:test";

import { createAccrualEvent } from "../accrual-event.js";
import { accrualRequest, loyaltyFixture } from "../fixtures.js";

test("a statement folds several events against one cycle cap", () => {
  const { store } = loyaltyFixture({ maxPoints: 60 });
  const outcome = store.postStatementBatch(accrualRequest({
    events: [
      createAccrualEvent({ eventId: "large-purchase", cycleId: "2026-W32", points: 50 }),
      createAccrualEvent({ eventId: "survey", cycleId: "2026-W32", points: 30 }),
    ],
  }));
  assert.equal(outcome.pointsAwarded, 60);
  assert.deepEqual(outcome.allocations, [
    { eventId: "large-purchase", points: 50 },
    { eventId: "survey", points: 10 },
  ]);
  const [statement] = store.snapshot().statements;
  assert.equal(statement.cyclePoints, 60);
  assert.equal(statement.batches.length, 1);
});
