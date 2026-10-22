# Fix round 2 for 0257 amendment 1

Same limits as `results/amend-1-contract.md` (edit only `0257/driver.py`, `0257/run_cell.py`, `0257/test_apparatus.py`;
no git actions, no network, no credentials). Keep the uncommitted amendment-1 changes; apply only these fixes.
Review records: `results/amend-1-r1-astra.md`, `results/amend-1-r1-grok.md`.

1. **Regrade of a pre-amendment STOP crashes `estimates`.** The regrade path (`run_cell.py`, the function that loads
   `seal.json`'s venue and calls `grade`) can grade a verdict written before this amendment, which has no
   `claude_account_before`; `grade` then writes `claude_account_after` and `estimates` raises. Fix: the regrade
   path sets `claude_account_before` from the sealed `venue['account']` when the record lacks it (the venue is the
   dispatch account by construction). Test: regrading a legacy assessor STOP yields a verdict `estimates` accepts.
2. **Split waits ignore the account.** A persisted `split_wait` entry (driver `ready`) keeps holding after the login
   moves to another account whose reset happens to be within 600 s of the stored one. Fix: store the account
   fingerprint with each split wait; when the current account differs from the stored one, drop that wait (log an
   event) and evaluate the reserve normally. A legacy wait without an account keeps today's behavior. Test both.
3. **Revert the near-expiry `credential` change and the renewal `account_changed` event.** Per-cell account fields
   already record every switch, so the event is not needed, and the extra profile lookup near expiry adds a new
   failure path. Restore `credential`'s `expiry - time.time() <= 300` branch exactly as before the amendment, remove
   the `account_changed` event, and remove or adapt its test. A renewal is accepted when the expiry advances, as now.
4. **Weak test.** In the `estimates` test, make the matching-account cell's change the largest value, so dropping
   matching-account deltas fails the test.

Report each fix with its test name and the exact pytest output lines for 0257 and 0256.
