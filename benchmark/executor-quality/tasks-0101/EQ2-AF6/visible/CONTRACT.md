# Loyalty accrual contract

Within each member cycle, authorized loyalty accrual batches sharing an idempotency key must occupy one statement entry and fold their event points into the cycle total and cap exactly once, complete member-token authorization (signature, member, status, and cycle scope) must finish before the accrual store folds any batch into that statement, and when an expired token is followed by a rotated authorized token for the same cap-closing batch the denial must leave the aggregate untouched so only the authorized retry records the entry and consumes the remaining cap.

`postAccrual(store, tokenRegistry, request, token)` returns either a statement outcome or `{ status: "denied", reason }`. A batch belongs to its member-cycle statement; its idempotency key is recorded on that statement rather than in a separate receipt cache.
