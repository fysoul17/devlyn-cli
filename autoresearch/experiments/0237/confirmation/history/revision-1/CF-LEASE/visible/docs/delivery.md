# Worker delivery contract

Delivery is at least once. A worker may continue running after its lease expires,
so every acknowledgement and retry must be fenced by its exact claim receipt.
A receipt is usable only while its job is leased with that receipt and
`lease_until > now`. The expiration boundary belongs to the next worker:
a lease expiring at 120 can be reclaimed at 120, and its old owner cannot ack or
retry at 120. A rejected settlement returns False and changes no stored fields.
Reclaiming a job always issues a new token, even when the same worker ID is reused.

`claim(store, owner, now, lease_seconds)` returns the oldest eligible receipt or
None. Ready jobs with `available_at <= now` and expired leases are eligible;
choose by `(available_at, seq)`. Each successful claim increments `attempts`
exactly once. A lease duration must be positive. Independent SQLite connections
must not receive the same attempt, and no eligible job should disappear because
a competing claim happened. The operation is one transaction.

`complete` marks the current attempt done. `retry` puts the current attempt back
in ready state, scheduled at `now + delay`, recording its diagnostic text.
A retry delay must be nonnegative. Settling clears owner, token, and expiration.
Successful completion clears an earlier last_error; attempts remain auditable.

`process_one` invokes the handler only after obtaining a receipt. Handler
Exceptions are recorded through retry (with the configured retry delay), and
produce `retried` or `lost` depending on whether settlement still owns the lease.
Completion produces `completed` or `lost`. No job produces `idle`. A handler
BaseException is allowed to escape, leaving its lease for recovery. Database or
settlement failures must escape as well; they are not handler delivery failures.
The worker uses its injected clock again after the handler, because time may
have advanced while delivery ran. External exactly-once delivery is not promised.
