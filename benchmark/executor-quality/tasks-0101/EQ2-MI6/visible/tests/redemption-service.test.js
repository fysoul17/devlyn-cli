import assert from "node:assert/strict";
import test from "node:test";

import { fixture, request } from "../fixtures.js";
import { redeemCoupon } from "../redemption-service.js";

test("authorized retries return one redemption", () => {
  const { store, sessions } = fixture();
  const attempt = request();
  const first = redeemCoupon(store, sessions, attempt, "session-live");
  const second = redeemCoupon(store, sessions, attempt, "session-live");
  assert.deepEqual(second, first);
  assert.equal(store.snapshot().redemptions.length, 1);
});

test("an expired session leaves redemption state unchanged", () => {
  const { store, sessions } = fixture();
  const before = store.snapshot();
  assert.deepEqual(redeemCoupon(store, sessions, request(), "session-old"), {
    status: "denied",
    reason: "session_expired",
  });
  assert.deepEqual(store.snapshot(), before);
});
