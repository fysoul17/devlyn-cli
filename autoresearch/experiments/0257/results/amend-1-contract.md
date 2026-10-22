# Fix contract: 0257 amendment 1 — run on any host Claude account

You are the implementation executor. Work only in `autoresearch/experiments/0257/` of the worktree you were started
in (`/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-amend-1`).

Hard limits:
- Never commit, push, tag, open a PR, or run `git add`. Root reviews and commits.
- Edit only `0257/driver.py`, `0257/run_cell.py`, `0257/test_apparatus.py` and `0257/README.md`. Never edit
  `0257/DESIGN.md`, `0257/registration.md`, `0257/results/`, or any other experiment (0222, 0256, … are frozen
  history; import them unchanged).
- No network, no Docker, no model calls. Tests run offline with fakes, as the existing ones do.
- Never read or print credential files or keychain output.
- Follow the repository's CLAUDE.md principles: smallest change, no workaround, no silent fallback, explicit errors.

## Why

The owner's host switches its Claude login between two of the owner's accounts when usage fills (three times on
2026-10-22). The registered apparatus stops on any account change, so a multi-week run cannot finish. The owner
decided (2026-10-22): "아무 계정 다 써 가능한거" — use whichever account is logged in. Costs are read from
tokens and wall time, not window points, so readings do not depend on the account. Window points do: the
driver's block reserve compares a cell's before/after window readings, which is only meaningful within one account.

## Change

1. **No account stop.** `driver.py` no longer stops or holds on an account/organization that differs from
   `runtime['account']`, before or after renewal. `runtime['account']` is no longer read by 0257 code. A renewal is
   still accepted only when the expiry advances; an account change across a renewal is logged as an event
   (`account_changed`, with the before and after fingerprints), not a stop.
2. **Each cell records its accounts.** `run_cell.py` gets its own `snapshot_auth(runtime)`, identical to 0222's
   (`0222/run_cell.py`) except that it returns the current fingerprints instead of comparing them with
   `runtime['account']`; `preflight` uses it instead of `base.snapshot_auth`. `assessment_snapshot` drops the
   comparison with `venue['account']` and `runtime['account']` and returns the assessor's fingerprints. The record
   gains `claude_account_before` (the dispatch account, from the venue) and `claude_account_after` (the account
   whose token read `claude_limits_after`, read from the same keychain credential in the same step), plus
   `assessor_account`. Every other check, error and STOP stays as it is.
3. **Window estimates stay within one account.** In `driver.py`, `delta` (or `estimates`) counts a cell's window
   change only when `claude_account_before == claude_account_after`. A verdict that lacks both fields predates
   this amendment, when an account change stopped the run, so it counts as one account. A verdict with only one of
   the two fields is malformed and raises.
4. **README.md:** the `driver.py` row says "any host account; per-cell account fingerprints" instead of "account
   stop".

## Tests (replace the account-stop test; keep every other test)

- A driver `ready` with a credential account different from `runtime['account']` does not raise and proceeds.
- A renewal that advances the expiry onto a different account proceeds and logs `account_changed`; one that does
  not advance still holds.
- `estimates` ignores a cell whose before and after accounts differ, counts one whose accounts match, counts a
  legacy verdict with neither field, and raises on a verdict with only one field.
- `preflight` with a different account than `runtime['account']` dispatches, and the record carries
  `claude_account_before`, `claude_account_after` and `assessor_account`.

## Done means

- `python3 -m pytest -q autoresearch/experiments/0257` and `python3 -m pytest -q autoresearch/experiments/0256` pass
  offline (report the exact output lines); `python3 -m py_compile` is clean on the edited files.
- Your final message lists each changed function, the tests added or replaced, and the test output. Do not claim
  anything you did not run.
