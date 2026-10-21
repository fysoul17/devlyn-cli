# Fix round 2: 0256 apparatus

Same hard limits as `autoresearch/experiments/0256/results/build-contract.md`. Round-2 reviews:
`/private/tmp/claude-501/-Users-aipalm-Documents-GitHub-devlyn-cli/39734701-88f7-45dd-bd5a-f5397ef89eed/scratchpad/0256/c2-astra.out`
and `c2-grok.out`. Fix every item with a test that fails before and passes after (observe the failure first), minimal
changes only.

1. **record_usage.py: conflicting terminal copies are conservative.** Whenever two terminal copies of one message id
   disagree — within one session or across a folded parent/child — the session is UNKNOWN and every counter of that
   message contributes its minimum across copies to the lower bound. Test across a folded parent/child conflict
   (inputs 9 and 2 → bound 2, UNKNOWN).
2. **record_usage.py: folded placeholders.** When child folding merges into an owner-session placeholder created by an
   id-bound event row, the placeholder takes the model of the terminal assistant copy; nothing calls a method on None.
   Test the combined shape (event placeholder + folded child assistant) yielding correct totals.
3. **decide.py: paired witness evidence is mandatory.** For every witness that reproduces on a B cell, the paired A cell
   (same task, configuration, replicate) must have an explicit `true` or `false` entry for that witness in
   `decisions['witnesses']`; a missing entry is a named gap, so the panel is NOT_FINISHED. Apply the same requirement
   symmetrically for witnesses reproducing on A cells (needed for the severe-subset comparison). Test with a real-shaped
   loader input.
4. **run_cell.py: regrade telemetry.** Before a regrade records new telemetry, remove any inherited
   `claude_limits_after` and `claude_limits_after_error`; a failed query leaves only the new error. Test from a record
   that already carries an old `claude_limits_after`.
5. **driver.py: expired or near-expiry tokens reach renewal.** Read `expiresAt` from the keychain first. When the token
   is within the renewal window or already expired, go straight to the renewal step without calling the profile
   endpoint; check account and organization fingerprints only after the renewal, against the renewed token. Test with a
   profile call that returns 401 for the old token.
6. **driver.py: renewal never kills the driver.** Catch `subprocess.TimeoutExpired` (and `OSError`) from the renewal
   command, then recheck the keychain exactly as after a normal attempt: an advanced expiry with matching fingerprints
   proceeds; otherwise a hold for the owner, as DESIGN says (the expiry stays recorded as attempted). Test both.
7. **run_cell.py / driver.py: transient network faults are holds.** Any `OSError` (including `TimeoutError`) from the
   preflight's profile, usage or Codex-limit queries returns "not dispatched" (rc 3) with the reason; in the driver,
   such faults from `credential()` or window queries are holds. Test a `TimeoutError` from `urlopen` in preflight and in
   the driver.

Done means: `python3 -m pytest -q autoresearch/experiments/0256` passes, pyflakes clean, and a final message listing
each item with its test name and the before/after observation.
