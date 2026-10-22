# Fix round 3 for 0257 amendment 1

Same limits as `results/amend-1-contract.md` (edit only `0257/driver.py`, `0257/run_cell.py`, `0257/test_apparatus.py`;
no git actions, no network, no credentials). Keep every uncommitted amendment-1 change; apply only this fix.
Review records: `results/amend-1-r2-astra.md`, `results/amend-1-r2-grok.md`.

Defect: `Driver.ready` checks the reserve (caps 85/70, block estimate) on the account logged in at that moment. If
the login switches before `run_cell.preflight` snapshots credentials, the cell is dispatched on an account whose
reserve was never checked (e.g. seven-day 90%); `preflight` only refuses at 100%.

Fix: bind dispatch to the account `ready` approved.
- `ready` remembers the fingerprints of the credential whose windows it evaluated when it returns True.
- `dispatch` passes them to `cell.run` (and to `cell.regrade`, whose assessor reserve `ready` also checked) as an
  explicit keyword argument; the CLI entry points of `run_cell.py` keep working without it.
- In `run_cell`, when the argument is given, `preflight` (and the regrade path before assessing) compares it with
  the account it snapshots. On a difference it does not dispatch: the same not-dispatched path and return code as
  other preflight refusals, reason `account changed after reserve check`, no verdict, no STOP. The driver's existing
  "not dispatched → sleep and call `ready` again" loop then rechecks the reserve on the new account.

Tests: a switch between `ready` and `preflight` is not dispatched and the next `ready` evaluates the new account; a
matching account dispatches as before; the regrade path refuses on a switch the same way. Report the exact pytest
output lines for 0257 and 0256.
