# Loyalty accrual contract

Authorized loyalty accrual batches sharing an idempotency key must replay one cycle receipt without reapplying event points or consuming the member's cycle cap, complete member-token authorization (status plus member and cycle scopes) must occur before the accrual store reads or writes receipt state, and when identical periodic accrual attempts span expired and rotated tokens only authorized calls may create or reveal the receipt so denied calls leave balances, cap usage, and idempotency state unchanged.

`postAccrual(store, tokenRegistry, request, token)` returns either an accrual receipt or `{ status: "denied", reason }`. A signed token is not authorized until its status, member, and cycle scopes have all been checked.
