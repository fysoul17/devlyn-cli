---
iter: "0033a"
title: "F9 fixture redesign — 2-skill contract (ideate → resolve, no preflight)"
status: PROPOSED
type: redesign-Phase-3.5 — fixture resync to match shipped 2-skill skill bodies
shipped_commit: TBD
date: 2026-04-30
mission: 1
parent: redesign-2-skill (NORTH-STAR.md product surface, 2026-04-30 lock)
gates: iter-0034-Phase-4-cutover (paired with iter-0033 C1 + iter-0033c)
codex_r05: 2026-04-30 (256s — sequencing flip to FIRST; smokes expanded; arm-specific artifact check; ship-gate.py rename; real path shape; transcript fingerprint; OLD F9 baseline retired)
---

# iter-0033a — F9 fixture redesign for 2-skill contract

## Why this iter exists (PRINCIPLES.md pre-flight 0)

Codex R0 on iter-0033 (2026-04-30, 494s) surfaced that the 2-skill redesign Phases 1-3 SHIPPED skill bodies but did NOT sync benchmark fixtures. F9 still encodes the OLD 3-skill novice contract:

- Old: `/devlyn:ideate` (emits `docs/VISION.md` + `docs/ROADMAP.md` + `docs/roadmap/phase-1/<id>.md`) → `/devlyn:auto-resolve` (implements) → `/devlyn:preflight` (audits).
- New (NORTH-STAR.md product surface, 2026-04-30 lock): `/devlyn:ideate` (emits `docs/specs/<id>-<slug>/spec.md` + `spec.expected.json`) → `/devlyn:resolve --spec <path>` (implements + verifies internally; VERIFY is the fresh-subagent final phase, replacing preflight).

F9 cannot run on the NEW skill chain without redesign — its `expected.json:64-67` requires `docs/VISION.md`, `docs/ROADMAP.md`, `docs/roadmap/**`, none of which the new ideate emits. This iter aligns F9 with the shipped 2-skill design.

User-visible failure this closes: without F9 redesign, the novice-flow load-bearing gate (RUBRIC ship-gate hard floor #2; NORTH-STAR test #1: F9 ≥ +5) is **undefined for the NEW arm**. Phase 4 cutover would ship a harness whose flagship novice scenario was never measured.

## Mission 1 service (PRINCIPLES.md #7)

Mission 1 single-task L1 surface — F9 IS the novice-user contract. No Mission 2 substrate. Hard NOs untouched.

## Hypothesis

Rewriting F9 so the variant arm runs `/devlyn:ideate → /devlyn:resolve --spec <emitted-path>` (no preflight) preserves the **fixture's intent** (vague-idea-to-shipped-feature novice contract) while matching the **shipped skill contract**. The `gitstats` deliverable, verification commands for runtime behavior, and forbidden-pattern checks remain unchanged. What changes: the artifact contract for ideate's emit (paths and filenames).

**Falsifiable predictions (BEFORE run):**

After redesign, four independent smoke checks must pass (Codex R0.5 §B expanded):

1. **Ideate-only smoke**: in a fresh test-repo workdir, run `/devlyn:ideate` from F9's task.txt. Stop after the announce line `spec ready — /devlyn:resolve --spec <path>`. Assert:
   - announced `<path>` exists at the **real path shape** `<spec-dir>/<id>-<slug>/spec.md` (Codex R0.5 — NOT `<id>` only);
   - sibling `spec.expected.json` exists at the same dir;
   - `python3 .claude/skills/_shared/spec-verify-check.py --check <path>` exits 0.
2. **Resolve-only smoke**: from a hand-curated NEW-style spec at the real path shape (e.g. `docs/specs/F9-gitstats-cli/spec.md` + `spec.expected.json`), run `/devlyn:resolve --spec <path>` on a fresh test-repo. Assert:
   - implementation produces `bin/cli.js` with gitstats;
   - verification commands pass;
   - archive at `.devlyn/runs/<run_id>/pipeline.state.json` shows `final_report.verdict ∈ {PASS, PASS_WITH_ISSUES}`;
   - **proves `spec.expected.json` was actually consumed** (Codex R0.5): `state.phases.build_gate.artifacts` references the spec.expected.json path, OR `.devlyn/spec-verify.json` mirrors its `verification_commands` array;
   - `state.source.spec_sha256` matches sha256 of the spec.md.
3. **Full-chain smoke (NEW arm)**: run F9 NEW arm end-to-end (ideate → resolve) via the harness F9 NEW prompt (scope §6). Assert:
   - same outcome as smoke #2;
   - the spec resolve consumed is exactly the one ideate emitted (path match);
   - **transcript fingerprint** (Codex R0.5): transcript contains `/devlyn:resolve --spec <emitted-path>` exactly once; transcript does NOT contain `/devlyn:auto-resolve`; transcript does NOT contain `/devlyn:preflight`.
4. **Path-shape regression smoke** (Codex R0.5 — guards against silent ideate refactor): assert `<spec-dir>/<id>-<slug>/spec.md` shape (id-slug, hyphen-joined) and not legacy `<spec-dir>/<id>/spec.md` shape. If the announce-line discovers a path NOT matching `<id>-<slug>`, smoke fails.

If any smoke fails, iter-0033a does NOT ship — root-cause iter opens for whichever skill failed, then re-run smokes.

## Scope (locked)

### Ships in this iter

1. **`F9-e2e-ideate-to-resolve/`** — rename directory from `F9-e2e-ideate-to-preflight/` (preflight is gone). Spec id, fixture id, results path all update.
2. **`spec.md`** — rewrite Context section to reflect 2-skill chain. Requirements unchanged (gitstats behavior is the deliverable). **Drop entirely** the `[ ]` bullet about `docs/VISION.md` / `docs/ROADMAP.md` / `docs/roadmap/phase-1/*.md` and the variant-only artifact requirement bullet. The fixture's shared `spec.md` Requirements must apply uniformly across all arms (Codex R0.5 — variant-only assertions must NOT live in shared spec).
3. **`expected.json`** — `tier_a_waivers` updated to **union of OLD + NEW** to remain permissive across both `--resolve-skill` modes (open question §1):
   - Add `docs/specs/**` waiver.
   - Keep `docs/VISION.md`, `docs/ROADMAP.md`, `docs/roadmap/**` (permissive — not a constraint, just allowed surface).
   - **Critically (Codex R0.5 §B)**: do NOT add a `verification_commands` entry that checks `docs/specs/**` or `docs/roadmap/**` artifacts — those run for ALL arms (incl. bare) per [run-fixture.sh:472](benchmark/auto-resolve/scripts/run-fixture.sh:472), and bare doesn't run ideate. The legacy `test -f docs/VISION.md && test -f docs/ROADMAP.md && ls docs/roadmap/phase-1/*.md | head -1` was already wrong on this axis (it would punish bare); the redesign DROPS it entirely. Variant/solo_claude ideate-artifact verification moves to the **out-of-band gate** (scope §8).
4. **`task.txt`** — unchanged (vague idea is the user input; that didn't change).
5. **`NOTES.md`** — rewrite the "what variant runs" section. Drop preflight bullet. New chain: ideate → resolve.
6. **Harness update**: `benchmark/auto-resolve/scripts/run-fixture.sh` F9 branch (lines ~250-265):
   - **F9 OLD path retired** (Codex R0.5 §E): there is no usable OLD F9 because OLD `/devlyn:ideate` was replaced in iter-0032; only NEW ideate exists at HEAD. F9 OLD pass would invoke NEW ideate → OLD auto-resolve, a broken hybrid. The harness refuses `--resolve-skill old` on F9 with a hard error citing "F9 OLD baseline is unobtainable post-iter-0032; F9 measures NEW vs L0 only per iter-0033a".
   - **F9 NEW path**: novice prompt chain `/devlyn:ideate ${ENGINE_CLAUSE}` → parse announce line → `/devlyn:resolve --spec <emitted-path> ${ENGINE_CLAUSE}`. No preflight invocation. The transcript fingerprint check in scope §8 enforces this.
7. **`scripts/ship-gate.py` rename** (Codex R0.5 §B): update line 47 hardcoded `F9-e2e-ideate-to-preflight` → `F9-e2e-ideate-to-resolve`.
8. **Out-of-band variant artifact check** (Codex R0.5 §B): add to `scripts/iter-0033-compare.py` (or a small `scripts/check-f9-artifacts.py`) a NEW-arm-specific check that runs AFTER `run-fixture.sh` completes for F9 variant/solo_claude:
   - assert `docs/specs/<id>-<slug>/spec.md` exists in the fixture work-dir;
   - assert `docs/specs/<id>-<slug>/spec.expected.json` exists;
   - assert transcript contains `/devlyn:resolve --spec` exactly once and does NOT contain `/devlyn:auto-resolve` or `/devlyn:preflight`;
   - bare arm exempt from these assertions.
9. **Lint check** additions: `scripts/lint-skills.sh`:
   - F9 fixture id is `F9-e2e-ideate-to-resolve` when NEW skills present;
   - any reference to `F9-e2e-ideate-to-preflight` outside `fixtures/retired/` is a fail (catches missed renames).

### Does NOT ship in this iter

- Other fixtures (F1-F8 already work via spec staging at `docs/roadmap/phase-1/<FIXTURE>.md` regardless of skill version).
- Any change to NEW skill prompts.
- Phase 4 cutover (still gated on iter-0033 + this).
- L2 measurement on F9.

### Subtractive-first check (PRINCIPLES.md #1)

- Could we delete F9 instead of redesigning? **No.** F9 is the novice gate per RUBRIC + NORTH-STAR. Deleting it would silently weaken the suite's most load-bearing measurement.
- Could we keep the OLD F9 contract for "compat"? **No.** That would make Phase 4 cutover (which deletes preflight + auto-resolve) impossible to verify. Two contracts ≠ one truth.
- Net change: rename + ~10 lines of expected.json edits + ~5 lines of NOTES.md edits + a small run-fixture.sh F9 NEW branch. Smaller than original iter-0033 scope.

## Codex pair-review plan

- **R0**: send this design + the redesigned `expected.json` + the F9 NEW prompt block in run-fixture.sh to Codex. Falsification ask: "Does the new artifact contract (`docs/specs/**`) preserve the original fixture intent (vague-idea-to-shipped-feature)? Are the smoke checks #1-#3 sufficient, or am I missing a chain failure mode? Does the spec-id rename break any reference I haven't updated?"
- **R-final** (AFTER smokes): if any smoke surprises, send raw output to Codex.

## Acceptance gate (pre-registered)

| Gate | Threshold | Source |
|---|---|---|
| 1. Ideate smoke | smoke #1 passes (real path shape `<id>-<slug>` + spec.md + spec.expected.json + lint) | hypothesis + Codex R0.5 |
| 2. Resolve smoke | smoke #2 passes (implementation + verification + archive + spec.expected.json consumption proven + spec_sha256 match) | hypothesis + Codex R0.5 |
| 3. Full-chain smoke | smoke #3 passes end-to-end + transcript fingerprint clean | hypothesis + Codex R0.5 |
| 4. Path-shape regression smoke | smoke #4 passes (catches silent ideate refactor) | Codex R0.5 |
| 5. F9 NEW vs L0 (benchmark) | margin ≥ +5 (RUBRIC ship-gate hard floor #2) | NORTH-STAR test #1, RUBRIC |
| 6. Artifact contract — out-of-band F9 variant/solo_claude | `docs/specs/<id>-<slug>/spec.md` + `spec.expected.json` exist; transcript contains `/devlyn:resolve --spec` exactly once; transcript free of `/devlyn:auto-resolve` and `/devlyn:preflight`. Bare arm exempt. | Codex R0.5 §B |
| 7. Artifact contract — pipeline state | `.devlyn/runs/*/pipeline.state.json` archived; `final_report.verdict` non-null; `state.source.spec_path` matches ideate emit path; `source.spec_sha256` matches | iter-0033 Gate 9 mirror |
| 8. ship-gate.py rename | `scripts/ship-gate.py` line 47 references `F9-e2e-ideate-to-resolve`; no remaining `F9-e2e-ideate-to-preflight` references in repo (excluding `fixtures/retired/`) | Codex R0.5 §B |

**Gates 1-4 must pass before any benchmark run** (smokes are cheap; benchmark run is expensive). Gate 5 is the post-benchmark verdict. Gates 6-8 close the artifact + rename contracts.

F9 OLD-vs-NEW comparison is **explicitly not gated** (Codex R0.5 §E): OLD F9 baseline is unobtainable at HEAD post-iter-0032 because OLD ideate was deleted. F9 NEW measurement is against L0 (bare) only.

## Phase 4 cutover dependency

iter-0034 Phase 4 cutover gates on **all three**:
- iter-0033a Gates 1-8 PASS (this iter).
- iter-0033 (C1) Gates 1-9 PASS.
- iter-0033c (NEW L2 vs NEW L1) PASS.

Any failing → root-cause iter, then re-run that step. Sequencing per Codex R0.5 §F: iter-0033a first, then iter-0033, then iter-0033c.

## Why this is not score-chasing (PRINCIPLES.md #0)

Closes a real user-visible failure: without F9 redesign, the novice-user contract is unmeasurable on NEW skills, and Phase 4 ships unverified. Case (a) of pre-flight 0.

## Risk register

| Risk | Mitigation |
|---|---|
| New ideate's announce-line parsing in F9 NEW prompt is fragile | Smoke #1 (and the path-shape smoke #4) is exactly this contract test. Failing the smoke = open root-cause iter. |
| Renaming F9 dir breaks references in scripts/specs | grep-search before rename for `F9-e2e-ideate-to-preflight` across `benchmark/`, `scripts/`, `autoresearch/`, `config/skills/`. Update all (incl. `ship-gate.py:47`). Lint check (scope §9) catches future drift. |
| F9 NEW score < OLD historical baseline | OLD F9 baseline is no longer obtainable at HEAD (Codex R0.5 §E). F9 NEW is measured against L0 only (≥ +5 vs bare). Historical OLD numbers retained for context, not as a regression gate. |
| `expected.json.verification_commands` punishes bare arm if variant-only check leaks in | Codex R0.5 §B: variant artifact check is **out-of-band** in `scripts/check-f9-artifacts.py`, not in `expected.json`. Bare arm exempt by construction. |

## Principles check

- **#0 pre-flight**: ✅ closes user-visible failure (novice contract unmeasurable on NEW).
- **#7 mission-bound**: ✅ Mission 1 single-task novice gate.
- **#1 no overengineering**: ✅ minimum changes — rename + small JSON/MD edits + harness branch.
- **#2 no guesswork**: ✅ smoke checks pre-registered.
- **#3 no workaround**: ✅ root-cause fix (fixture aligned with shipped skill, not skill warped to fit fixture).
- **#4 worldclass**: ✅ artifact contract gate.
- **#5 best practice**: n/a (fixture data, no code idiom).
- **#6 layer-cost-justified**: ✅ L1 measurement only; F9 L2 deferred.

## Open questions (resolved post-R0.5)

1. ~~F9 `tier_a_waivers` keep `docs/roadmap/**`?~~ → **Resolved**: union of OLD + NEW. Permissive waiver is fine.
2. Renaming directory — also retire old name in `fixtures/retired/`? **Decision**: yes; preserves recovery if a future regression suspects OLD F9 contract. Cheap.
3. Does NEW F9 chain need `--spec-dir docs/specs/F9` override? → **Smoke #1 + #4 answers empirically**. Default plan: do NOT override; rely on ideate auto-id-generation. If smokes show announce-line parsing is unreliable, add the override.
4. (Codex R0.5 §B new) Does `spec-verify-check.py --check` actually prove `spec.expected.json` is consumed? → **No** (it validates a JSON fence in spec.md). Smoke #2 adds the consumption proof: `state.phases.build_gate.artifacts` references the file OR `.devlyn/spec-verify.json` mirrors its commands. Without this, schema validation passes while the carrier silently fails.

## Deliverable execution order

1. **R0.5 disposition complete** (this iter). R0 on the original draft was implicit in iter-0033 R0; R0.5 surfaced this fixture-gap.
2. Apply file changes:
   - rename dir + `git mv fixtures/F9-e2e-ideate-to-preflight fixtures/F9-e2e-ideate-to-resolve`;
   - copy old fixture to `fixtures/retired/F9-e2e-ideate-to-preflight/` (open question §2);
   - rewrite spec.md (drop variant-only artifact bullet);
   - rewrite expected.json (union waivers; remove broken VISION/ROADMAP verification command);
   - rewrite NOTES.md;
   - update run-fixture.sh F9 branch (NEW chain only; OLD refused with hard error);
   - update ship-gate.py:47 rename;
   - add `scripts/check-f9-artifacts.py` (out-of-band variant artifact check);
   - add lint checks.
3. Run smokes #1-#4 in `/tmp` test-repos.
4. If any smoke fails → root-cause iter. If all pass → commit fixture + harness changes.
5. **R-final smoke** with Codex on smoke results before benchmark run.
6. Run F9 NEW arm: `bash scripts/run-suite.sh F9-e2e-ideate-to-resolve --resolve-skill new` (single fixture).
7. Verify gates 5-8.
8. **R-final** with Codex on benchmark numbers.
9. Update HANDOFF.md + DECISIONS.md.
10. Hand off to iter-0033 (C1) execution. iter-0033c follows. iter-0034 Phase 4 cutover after all three.
