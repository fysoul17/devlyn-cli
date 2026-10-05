# F9 — Notes (2-skill contract, post iter-0033a)

## Purpose

**Load-bearing for the novice-user contract.** The suite ship-gate requires
F9 to pass (variant arm margin ≥ +5) on every shipped version. If F9 fails,
the "type `/devlyn:ideate` and ship worldclass software" promise is not being
met.

Renamed 2026-04-30 (iter-0033a) from the `-to-preflight` legacy id to match
the shipped 2-skill product surface: `/devlyn:ideate` → `/devlyn:resolve --spec`.
The pre-rename copy is preserved at `fixtures/retired/F9-e2e-ideate-to-preflight/`
for recovery if the OLD 3-skill chain ever needs replay.

## What the variant arm does (2-skill chain)

A novice-simulating prompt (`task.txt` is identical to what the user typed)
is delivered to a fresh Claude session. The session has the new 2-skill kit
installed. The pipeline arm is expected to:

1. Recognize this is a vague idea, not a spec → invoke `/devlyn:ideate`.
2. Ideate produces `docs/specs/<id>-<slug>/spec.md` + `spec.expected.json`
   and announces `spec ready — /devlyn:resolve --spec <emitted-path>`.
3. Run `/devlyn:resolve --spec <emitted-path>` (PLAN → IMPLEMENT → BUILD_GATE
   → CLEANUP → VERIFY in one skill). VERIFY is the fresh-subagent final
   phase, replacing the standalone `/devlyn:preflight` skill from the
   3-skill era.

The variant prompt explicitly instructs this chain so the test isn't about
Claude inventing the chain — it's about the new tools being usable end-to-end
when invoked.

## What the bare arm does

Same raw task delivered as a direct prompt with anti-skill rules. Bare
implements `gitstats` using its own judgment. Bare does NOT produce any
`docs/specs/**` artifacts (and isn't expected to).

## Why margin ≥ +5 is required (vs L0 / bare)

The pipeline's whole value prop is that it trades some bare-case tokens for
quality uplift on novice flows. If this fixture can't show ≥ +5 margin
vs L0, we're paying pipeline cost without delivering on the novice promise.

**OLD-vs-NEW comparison is NOT measured here.** OLD `/devlyn:ideate` was
replaced in iter-0032 (the new ideate is the only ideate at HEAD). Calling
the OLD F9 chain (`/devlyn:ideate` → `/devlyn:auto-resolve` → `/devlyn:preflight`)
at HEAD would invoke NEW ideate against OLD auto-resolve — a broken hybrid.
The harness refuses `--resolve-skill old` on F9 with a hard error.

## Scoring notes

- The variant's `docs/specs/<id>-<slug>/spec.md` + `spec.expected.json` ARE
  part of the judge's evaluation. The judge sees the full product (code +
  spec + tests), not just the diff to `bin/cli.js`.
- Bare doesn't produce spec files, so bare's judge payload is code+test only.
  This asymmetry is INTENTIONAL — the fixture tests total-output quality,
  not per-file quality.

## Skill-driven artifact check (out-of-band, NOT in expected.json)

Per Codex R0.5 §B: `expected.json.verification_commands` apply to ALL arms
(see `run-fixture.sh:472`). A `docs/specs/**` check in expected.json would
punish the bare arm (which doesn't run ideate). Skill-driven artifact
verification lives in `scripts/check-f9-artifacts.py`, which runs AFTER
the per-fixture verification block and asserts every non-bare skill arm
(`variant`, `solo_claude`, `l2_gated`, `l2_risk_probes`, `l2_forced`)
produced:

- `docs/specs/<id>-<slug>/spec.md` exists.
- `docs/specs/<id>-<slug>/spec.expected.json` exists.
- transcript contains `/devlyn:resolve --spec` exactly once.
- transcript does NOT contain `/devlyn:auto-resolve` or `/devlyn:preflight`.

## Failure modes detected

- **Pipeline skips ideate.** Variant invokes `/devlyn:resolve` directly on
  the raw idea → free-form classifier kicks in → spec quality is shallow.
  Caught by `scripts/check-f9-artifacts.py`: `docs/specs/**` files missing.
- **Bare over-engineers.** Without a skeleton, bare builds too much,
  touches wrong files, adds deps. Caught by spec constraints (no new deps,
  forbidden empty catch).
- **Variant chains the OLD names.** If the variant transcript contains
  `/devlyn:auto-resolve` or `/devlyn:preflight`, the prompt-following gate
  fails. iter-0033a's harness change ensures the variant prompt names only
  the 2 surviving skills.
- **Spec emit path divergence.** If the new ideate refactors away from
  `<spec-dir>/<id>-<slug>/spec.md`, the harness check fails (path-shape
  regression smoke #4 of iter-0033a catches it before benchmark runs).

## Rotation trigger

F9 is the last fixture we rotate — it's the anchor. If it saturates
(variant consistently > 95), the whole suite needs a harder novice-flow
anchor before we retire this one.

## Current pair-evidence status

Rejected as pair-lift evidence until reworked. `20260512-f9-e2e-headroom`
measured bare 60 / solo_claude 90 with a +30 solo-over-bare margin, and
`check-f9-artifacts.py` passed for bare (exempt) and solo_claude. The headroom
gate still failed because bare headroom was 0 < 5, solo_claude exceeded 80, and
bare carried a judge disqualifier. Keep F9 as the novice-flow anchor, but do not
spend pair arms on it as pair evidence until the fixture is reworked and clears
a fresh headroom gate.
