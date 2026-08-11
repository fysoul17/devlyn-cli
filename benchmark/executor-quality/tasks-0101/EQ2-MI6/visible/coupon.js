export function createCoupon({ code, discountCents }) {
  if (typeof code !== "string" || code.length === 0) {
    throw new TypeError("Coupon code is required");
  }
  if (!Number.isSafeInteger(discountCents) || discountCents <= 0) {
    throw new TypeError("discountCents must be a positive integer");
  }
  return Object.freeze({ code, discountCents });
}
