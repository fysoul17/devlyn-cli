# Fix round 1: 0256 apparatus

Same hard limits as `autoresearch/experiments/0256/results/build-contract.md` (work only in
`autoresearch/experiments/0256/`, never DESIGN.md or results/, no commits, offline tests). Reviews:
`/private/tmp/claude-501/-Users-aipalm-Documents-GitHub-devlyn-cli/39734701-88f7-45dd-bd5a-f5397ef89eed/scratchpad/0256/c1-astra.out`
and `c1-grok.out` in the same directory. Fix every item below, each with a test that fails before the fix and passes
after (state in your final message that you observed the failure first). Keep each fix minimal.

1. **decide.py: real verdict statuses.** The grader (`0222/run_cell.py:74-78`) emits `COMPLETE`, `ADJUDICATE` and
   `PRODUCT_INCOMPLETE`; accept exactly those (plus STOP handling as now). Test through `load()` with a real-shaped
   `PRODUCT_INCOMPLETE` verdict file.
2. **decide.py: missing decisions file.** An absent or unreadable decisions path yields NOT_FINISHED with a named gap
   for every panel, never an exception.
3. **decide.py: strict-gain condition.** Whenever `strictly_better` is False, the conditions list `strict_gain`; when it is
   None, it is listed as unknown — for every reading, not only NO_STRICT_GAIN.
4. **Window reset comparison (driver.py `delta` and the split-wait check).** The usage endpoint's `resets_at` jitters by
   sub-seconds on every call (observed today: `2026-10-21T08:59:59.541426+00:00`, `…59.934881…`, `09:00:00.323437…`
   for one unchanged five-hour window). Parse the timestamps; treat two values as the same window when they differ by
   less than 600 seconds; a reset is a change of at least that. Tests with jittered values for both `delta`/`estimates`
   and the split wait; also a test that a reset-crossing sample never enters `estimates`.
5. **driver.py: windows after renewal.** `ready()` must query the windows with the token it just read from the keychain
   (the `credential()` snapshot), not `runtime.auth/claude.json`; add a `claude_limits` variant that takes the access
   token. Test: renewal succeeded, saved file still holds the old token, readiness proceeds.
6. **run_cell.py: image check is a hold, not a verdict.** When the image is missing or its ID differs, write
   `not-dispatched-<name>.json` with the reason and return 3 (as preflight holds do), never a STOP verdict; the driver
   loads the tarball before dispatch as now. Test.
7. **run_cell.py: post-grading telemetry never loses a verdict.** Any exception from the after-grading
   `claude_limits` query (including `TimeoutError`/`OSError`) is recorded as `claude_limits_after_error`; the verdict is
   still written. Test.
8. **record_usage.py: transcript shapes.**
   - Skip assistant rows whose `message.model` is `<synthetic>` (0233 `evidence.py:110` does).
   - Rows of `type` `progress` or `error` without a message id are tool/hook progress, not API attempts: ignore them.
     Rows with subtype `api_retry`, `api_error` or `abort` without a message id still make the session UNKNOWN.
   - A placeholder created for an id-bound retry/progress row must take the model of a later assistant row for that id;
     never call methods on `None`. Test the ordering where the event row precedes the assistant row.
   - Subagents: Claude Code writes native subagent transcripts either under the parent's `sessionId` or with a
     `parentSessionId`/sidechain marker. Fold every transcript session that has no result envelope and whose rows carry
     `parentSessionId` equal to an enveloped session into that parent before comparing; any remaining unenveloped
     session is still a gap. Tests for both shapes, a healthy owner+subagent reconciling to COMPLETE.
   - Usage recording must never raise past `run_cell` (it is recorded, never a stop): confirm the existing guard covers
     `AttributeError`, or widen it.
9. **models_cache.py: container cleanup.** Name the container and reap it unconditionally in `finally`, as 0233's
   `codex_limits` does with `assess.reap`. Test that a timeout still reaps.
10. **Tests the reviewers found vacuous:** the 1,500 s assessor cutoff (exercise `assessment_snapshot` with a
    1,499 s and a 1,501 s token, mocking only `security`/HTTP), the renewal threshold (a token above 300 s but below
    6,300 s holds without renewing; at or below 300 s renews once), and the estimates recomputation.

Done means: `python3 -m pytest -q autoresearch/experiments/0256` passes, pyflakes clean, README updated if a file's
role changed, and a final message listing each item with its test name and the before/after observation.
