import { CouponUnavailableError } from "./errors.js";

function copy(value) {
  return structuredClone(value);
}

export class RedemptionStore {
  #coupons;
  #deduplication = new Map();
  #redemptions = [];
  #nextSequence = 1;

  constructor(coupons) {
    this.#coupons = new Map(
      coupons.map((coupon) => [coupon.code, { ...coupon, redeemedBy: null }]),
    );
  }

  replay(idempotencyKey) {
    const result = this.#deduplication.get(idempotencyKey);
    return result ? copy(result) : null;
  }

  remember(idempotencyKey, result) {
    if (!this.#deduplication.has(idempotencyKey)) {
      this.#deduplication.set(idempotencyKey, copy(result));
    }
  }

  redeem(request) {
    const coupon = this.#coupons.get(request.couponCode);
    if (!coupon || coupon.redeemedBy !== null) {
      throw new CouponUnavailableError(request.couponCode);
    }

    coupon.redeemedBy = request.accountId;
    const result = {
      status: "redeemed",
      redemptionId: `redemption-${this.#nextSequence}`,
      accountId: request.accountId,
      couponCode: coupon.code,
      discountCents: coupon.discountCents,
    };
    this.#nextSequence += 1;
    this.#redemptions.push(copy(result));
    return copy(result);
  }

  snapshot() {
    return {
      coupons: [...this.#coupons.values()].map(copy),
      redemptions: this.#redemptions.map(copy),
      deduplication: [...this.#deduplication.entries()].map(([key, value]) => [key, copy(value)]),
      nextSequence: this.#nextSequence,
    };
  }
}
