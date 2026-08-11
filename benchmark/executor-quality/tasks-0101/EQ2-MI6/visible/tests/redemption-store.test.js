import assert from "node:assert/strict";
import test from "node:test";

import { CouponUnavailableError } from "../errors.js";
import { fixture, request } from "../fixtures.js";

test("a single-use coupon creates one redemption record", () => {
  const { store } = fixture();
  const redeemed = store.redeem(request());
  assert.equal(redeemed.status, "redeemed");
  assert.equal(store.snapshot().redemptions.length, 1);
  assert.throws(() => store.redeem(request({ idempotencyKey: "another-key" })), CouponUnavailableError);
});
