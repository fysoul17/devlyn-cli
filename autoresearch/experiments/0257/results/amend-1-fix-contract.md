# Fix round 1 for 0257 amendment 1

Same limits as `results/amend-1-contract.md` (edit only `0257/driver.py`, `0257/run_cell.py`, `0257/test_apparatus.py`;
no git actions, no network, no credentials). Your uncommitted amendment-1 changes are in the worktree; keep them.

Defect: `grade` sets `claude_limits_after_error` and no `claude_account_after` when the after-window read fails
(HTTP 429 from the usage endpoint is common; SMOKE verdicts already show it). Such a verdict has
`claude_account_before` without `claude_account_after`, and `driver.estimates` raises `incomplete Claude account
pair`. That crashes the driver on a legitimate verdict. The contract's "raise on only one field" rule was wrong.

Fix in `estimates`:
- Both account fields present and equal, or both absent (legacy, pre-amendment): count the window change as before.
- Both present and different: skip.
- `claude_account_before` present, `claude_account_after` absent, and `claude_limits_after` absent: skip (no after
  reading).
- Any other combination (`claude_account_after` without `claude_account_before`, or `claude_limits_after` present
  without `claude_account_after` on a verdict that has `claude_account_before`): raise as malformed.

Also state in your final message why you changed `credential`'s near-expiry branch from `expiry - time.time() <= 300`
to `expiry <= time.time()`, and add a test showing the behavior it is needed for (or revert it if nothing needs it).

Tests: add the failed-after-read case (skipped, no raise) and keep the existing ones. Report the exact pytest
output lines for 0257 and 0256.
