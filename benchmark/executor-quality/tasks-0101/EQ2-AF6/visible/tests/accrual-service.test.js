import assert from "node:assert/strict";
import test from "node:test";

import { postAccrual } from "../accrual-service.js";
import { accrualRequest, loyaltyFixture } from "../fixtures.js";

test("authorized retries occupy one batch entry in the cycle statement", () => {
  const { store, tokens } = loyaltyFixture();
  const request = accrualRequest();
  const first = postAccrual(store, tokens, request, "token-current");
  const second = postAccrual(store, tokens, request, "token-rotated");
  assert.deepEqual(second, first);
  const [statement] = store.snapshot().statements;
  assert.equal(statement.batches.length, 1);
  assert.equal(statement.cyclePoints, 55);
});

test("a token for another member leaves statement state untouched", () => {
  const { store, tokens } = loyaltyFixture();
  const before = store.snapshot();
  assert.deepEqual(postAccrual(store, tokens, accrualRequest(), "token-outsider"), {
    status: "denied",
    reason: "token_member_mismatch",
  });
  assert.deepEqual(store.snapshot(), before);
});
