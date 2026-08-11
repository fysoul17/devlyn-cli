export class CouponUnavailableError extends Error {
  constructor(code) {
    super(`Coupon ${code} is unavailable`);
    this.name = "CouponUnavailableError";
    this.code = code;
  }
}
