# rp-d8 registration amendment 1 — apparatus fix after smoke attempt 1

Written after smoke attempt 1 and before any measured exposure. The
prediction, schedule, grading, decision rules, arms, prompt, token gate and
inputs other than the apparatus code are unchanged; [registration.md](registration.md)
and [registration.json](registration.json) stay as committed.

## What happened

Smoke attempt 1 (run `20261019a`, stage `runtime-smoke.json`) ran the Claude
`high` Y cell and then the Codex `high` Y cell on SM.

- **smoke-claude:** qualified. Owner exit 0, release/pack, P1 and effort
  binding MATCH, COMPLETE usage, delivered (merged PR), archived and deleted
  (404). 67.3 s, 292,009 input, 3,994 output.
- **smoke-codex:** STOP before dispatch, with the reason "rp-d1
  instrumentation failed: EvidenceError". It never launched an engine. Its
  repository had been seeded (an inputs commit and an install commit, no
  PR). It was retained because the STOP had no sealed teardown. It was
  mirrored to `archives/smoke-codex-manual` (refs, pulls, mirror) and
  deleted (404).

The registry recorded attempt 1 as FAILED, which consumes it; the spare pair
(attempt 2) remains.

## Cause

`prepare.installed_binding` in rp-d8 called rp-d7's, which requires an
installed `CLAUDE.md` in every cell because rp-d7 was Claude-only. A Codex
install writes only `AGENTS.md`, so `require()` raised `EvidenceError`. The
error came from a second loaded instance of the rp-d1 `github` module, so rp-d1
`runner.py`'s class-based handler missed it. The message was then replaced by
the class name. The offline tests used Claude-shaped installs for every cell,
and the four apparatus reviews did not catch it.

## Fix (commit `1a101b73`)

- `CLAUDE.md` binding by engine. Claude cells still require the exact managed
  block or the 11-byte `@AGENTS.md` import of the verified package. Codex
  cells accept `CLAUDE.md` absent, or the same exact bytes if present. The
  `AGENTS.md` managed-block binding is unchanged for both.
- One shared `EvidenceError` identity, so the fixed `require()` messages
  reach the slot record. Arbitrary exception payloads stay redacted.
- Regression tests: a Codex-shaped install, a wrong Codex `CLAUDE.md`, a
  Claude install without `CLAUDE.md`, and message propagation. The untouched
  attempt-1 Codex checkout passes the new binding read-only. An audit of the
  other inherited checks found no further Claude-only assumption on g01, g02
  or smoke-codex.
- Offline suites: rp-d8 499, rp-d7 325, rp-d6 277.

Review: Astra ultra and Grok 4.7 both SHIP on the fix ([Astra](results/amend1-r1-astra.md), [Grok](results/amend1-r1-grok.md)).

## Next

Smoke attempt 2 (the registered spare: smoke2-claude, smoke2-codex) runs in
a fresh stage directory with the same run ID and inputs plus
`--smoke-attempt 2`. A second miss stops the run.
