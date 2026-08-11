import { createCoupon } from "./coupon.js";
import { RedemptionStore } from "./redemption-store.js";
import { SessionAuth } from "./session-auth.js";

export function fixture({ code = "SAVE20", discountCents = 2_000 } = {}) {
  return {
    store: new RedemptionStore([createCoupon({ code, discountCents })]),
    sessions: new SessionAuth([
      { id: "session-old", accountId: "account-7", status: "expired" },
      { id: "session-live", accountId: "account-7", status: "active" },
      { id: "session-rotated", accountId: "account-7", status: "active" },
      { id: "session-other", accountId: "account-9", status: "active" },
    ]),
  };
}

export function request({
  idempotencyKey = "redeem-key-7",
  couponCode = "SAVE20",
  accountId = "account-7",
} = {}) {
  return { idempotencyKey, couponCode, accountId };
}
