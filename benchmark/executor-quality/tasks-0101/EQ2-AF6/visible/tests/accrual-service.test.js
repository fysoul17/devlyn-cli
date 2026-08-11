import assert from "node:assert/strict";
import test from "node:test";

import { postAccrual } from "../accrual-service.js";
import { accrualRequest, loyaltyFixture } from "../fixtures.js";

test("authorized retries replay one periodic accrual receipt", () => {
  const { store, tokens } = loyaltyFixture();
  const request = accrualRequest();
  const first = postAccrual(store, tokens, request, "token-current");
  const second = postAccrual(store, tokens, request, "token-rotated");
  assert.deepEqual(second, first);
  assert.equal(store.snapshot().receipts.length, 1);
});

test("an expired token leaves accrual state untouched", () => {
  const { store, tokens } = loyaltyFixture();
  const before = store.snapshot();
  assert.deepEqual(postAccrual(store, tokens, accrualRequest(), "token-old"), {
    status: "denied",
    reason: "token_expired",
  });
  assert.deepEqual(store.snapshot(), before);
});
