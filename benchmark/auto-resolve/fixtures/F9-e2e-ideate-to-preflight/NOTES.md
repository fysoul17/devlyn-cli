# F9 — Notes

## Purpose

**Load-bearing for the novice-user contract.** The suite ship-gate requires
F9 to pass (margin ≥ +5) on every shipped version. If F9 fails, the "type
`/devlyn:ideate` and ship worldclass software" promise is not being met.

## What the variant arm does

A novice-simulating prompt (`task.txt` is identical to what the user typed)
is delivered to a fresh Claude session. The session has our skills installed.
The pipeline arm is expected to:

1. Recognize this is a vague idea, not a spec → invoke `/devlyn:ideate`.
2. Ideate produces `docs/VISION.md`, `docs/ROADMAP.md`, and
   `docs/roadmap/phase-1/1.1-gitstats.md` (or similar).
3. Run `/devlyn:auto-resolve` on the generated spec.
4. Run `/devlyn:preflight` for verification.

The variant arm's prompt explicitly instructs this chain so we're not
relying on Claude to invent it. That's fair because the novice contract is
about the TOOLS being available + discoverable; the user in this benchmark
is already primed to use them.

## What the bare arm does

Same raw task delivered as a direct prompt. Bare implements `gitstats`
using its own judgment. Bare does NOT produce VISION/ROADMAP documents
(and isn't expected to).

## Why margin ≥ +5 is required

The pipeline's whole value prop is that it trades some bare-case tokens for
quality uplift on novice flows. If this fixture can't show ≥ +5 margin,
we're paying pipeline cost without delivering on the novice promise.

## Scoring notes

- The variant's `docs/VISION.md` + `ROADMAP.md` + spec files ARE part of
  the judge's evaluation. The judge sees the full product (code + docs +
  roadmap state), not just the diff to `bin/cli.js`.
- Bare doesn't produce roadmap files, so bare's judge payload is
  code+test only. This asymmetry is INTENTIONAL — the fixture tests
  total-output quality, not per-file quality.

## Failure modes detected

- **Pipeline skips ideate.** Variant goes straight to auto-resolve with a
  vague spec → downstream implementation is weak. Caught by judge:
  `docs/roadmap/` files missing.
- **Bare over-engineers.** Without a skeleton, bare builds too much,
  touches wrong files, adds deps. Caught by spec constraints.
- **Pipeline ships "done" but preflight was a no-op.** If `.devlyn/PREFLIGHT-REPORT.md` exists but shows no commitment audit, something is broken upstream.

## Rotation trigger

F9 is the last fixture we rotate — it's the anchor. If it saturates
(variant consistently > 95), the whole suite needs a harder novice-flow
anchor before we retire this one.
