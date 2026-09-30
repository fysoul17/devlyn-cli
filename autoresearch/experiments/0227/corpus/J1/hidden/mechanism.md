# J1 mechanism record

- **Family:** boundary semantics.
- **Mandatory clause:** “For a present, non-stale entry with an available value, `has(key, { minTTL })` returns true when its remaining TTL is greater than or equal to `minTTL`, and false when it is less. Entries without an expiration satisfy every accepted minimum.”
- **Trigger:** A fresh entry has a finite, positive remaining TTL exactly equal to the supplied positive `minTTL`.
- **Causal code path:** `has()` forwards to `#has`; the entry passes the existing availability and staleness checks. The new minimum guard rejects before the normal hit and optional age-refresh path. The twin uses `<=` in this rejection guard where the reference uses `<`.
- **Incorrect behavior:** The twin returns false and, when requested, reports `Status.has === 'ttl'` for an entry that meets the stated minimum. The reference accepts it.
- **Executable witness:** `J1-O1` in `hidden/oracle.md`: insert at 100 with TTL 100, inspect at 175, and assert `has('a', { minTTL: 25 }) === true`.
- **Near-miss exclusions:** A remaining lifetime strictly below the minimum must be rejected; that is not the defect. Negative lifetime, missing keys, and pending misses are existing false cases. The library's zero-remaining-TTL staleness rule is unchanged because the new guard applies only to positive minima. Invalid-input rejection, recency mutation, refreshing age before checking, and aborting a pending fetch would be separate defects rather than this comparator mechanism.
- **Public-check survival:** Public tests use 20/30 (and fractional 20.5/30.5) around a remaining TTL of 25, exercise both comparison outcomes, and cover the status branches. They do not use a positive equality input. No coverage, lint, typing, or test configuration is weakened.
