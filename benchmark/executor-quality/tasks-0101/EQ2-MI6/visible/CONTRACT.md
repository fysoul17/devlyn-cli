# Coupon redemption contract

Authorized coupon redemption requests sharing an idempotency key must produce one redemption record and replay the same success without consuming the coupon again, every request must pass current session authorization before the redemption store reads or writes deduplication state, and across repeated identical attempts under expired and rotated sessions an authorization failure must neither reveal an earlier success nor reserve the coupon nor create a deduplication entry.
