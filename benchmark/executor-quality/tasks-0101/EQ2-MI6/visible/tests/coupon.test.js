import assert from "node:assert/strict";
import test from "node:test";

import { createCoupon } from "../coupon.js";

test("coupon values are validated and frozen", () => {
  const coupon = createCoupon({ code: "FIVE", discountCents: 500 });
  assert.deepEqual(coupon, { code: "FIVE", discountCents: 500 });
  assert.equal(Object.isFrozen(coupon), true);
  assert.throws(() => createCoupon({ code: "", discountCents: 500 }), TypeError);
});
