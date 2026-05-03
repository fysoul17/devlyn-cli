---
iter: "0033d"
title: "PLAN-pair vs solo-PLAN — first L1-vs-L2 measurement on `/devlyn:resolve`"
status: CLOSED-DESIGN / NO IMPLEMENT
verdict: design-iter — 18+ leak surfaces enumerated; implementation deferred to iter-0033f-pair-plan-impl with consolidated firewall design
type: measurement — NEW Phase 4 cutover gate (replaces iter-0033c which closed FAIL); CLOSED as design-iter per Codex R0/R0.5/R0.6 + principles-decision pair convergence on option B (defer-as-design-iter)
shipped_commit: TBD
closed_commit: TBD
closed_date: 2026-05-03
date: 2026-05-03
mission: 1
gates: iter-0034-Phase-4-cutover (sole gate; iter-0033a + iter-0033 C1 + iter-0033c all closed)
codex_r0_round3: 2026-05-03 (293s — verdict "유저 반박이 맞습니다"; round-2 ideate-solo verdict was burden-reversal; widened pair candidate set to ideate spec audit + PROJECT coherence + PLAN audit + VERIFY/JUDGE + CLEANUP-as-VERIFY-axis; PLAN-pair iter-0020-falsified framing in SKILL.md:80 is overreach (iter-0020 falsified Codex-BUILD, not PLAN-pair); honest "unmeasured" labels replace "solo wins"; PLAN-pair = first measurement priority)
codex_r05_round3: 2026-05-03 (230s — locked PLAN-pair-first sequence; PROJECT-coherence measurement design TBD via defect-class oracle (deferred to iter-0033e stub); NORTH-STAR carries both meta-policy + current-active state; ship-validated language tightened; commit shape compare.py-fix-first-then-policy)
codex_r0_firewall: 2026-05-03 (295s — REJECT: 6 PUSHBACK + 1 EVIDENCE-NEEDED + 1 AGREE-with-changes. Verdict "I would not ship this design as-is. The blockers are structural, not cosmetic." Caught: Q1 live state leak (pipeline.state.json + SKILL.md self-leak + WORK_DIR=...-${ARM} + Codex env asymmetry); Q2 reserved-token list (missing pair_plan/pair_judge/critic/debate/gpt-5-5/etc., over-blocking accepted_invariants/model_stamps which are legitimate iter-0022 schema content); Q3 cap-3 needs telemetry + early stop; Q4 Check 15 must scan SKILL.md/adapters/CLAUDE.md/.claude/skills mirror, not just implement.md+run-fixture.sh; Q5 smokes must run in mktemp; Q6 Gate 8b unimplementable — claude -p doesn't persist subagent prompts + archive_run.py doesn't archive plan.debate.json; Q7 byte-identical prompts insufficient — no existing arm-invisible selector pattern; Q8 F9 ENGINE_CLAUSE applied to both ideate AND resolve must split.)
codex_r05_firewall: 2026-05-03 (292s — STILL REJECT: 5 PUSHBACK + 3 AGREE. AGREE rate up 13%→38%. New surfaces: Q1 PLAN timing side-channel via state.phases.plan.duration_ms + RESULT_DIR/--debug-file still arm-named; Q2 token list still over-blocks debate/critic/proposer (legitimate domain words) and under-blocks pair mode/cross-model/deliberation/round_num/wall_seconds/codex_critic_finding_ids; Q4 6-char deterministic hash brute-forceable + arm-named result/debug paths bigger leak than salt; Q5 archive recursive **/.harness-internal/*.json risks sweeping .devlyn/runs/** — use explicit moves; Q8 wall estimate 12-14h low → 10-12h impl + 6h suite ≈ 19h total because anon migration touches judge.sh, result layout, timing.json, compare scripts, F9 checks, archive/mirror/lint, process-argv.)
codex_r06_firewall: 2026-05-03 (242s — STILL REJECT: 7 PUSHBACK + 1 AGREE. AGREE rate dropped back 38%→13%. New surfaces: Q1 also scrub started_at/completed_at + state.rounds.pair_plan must be removed entirely; Q2 settings.json still arm-distinguishing (CODEX_BLOCKED vs CODEX_REAL_BIN/MONITORED); Q3 token list — `.harness-internal`/pair_rounds/rounds.pair_plan/plan_mode/pair critic missing; Q4 anon-map.json runtime visibility leak (--debug-file argv reveals result-root shape — write anon-map ONLY after child exit); Q5 archive lifecycle conflict — pre-IMPLEMENT validator deletes .devlyn/.harness-internal/, then PHASE 6 archive has nothing to archive; Q6 validator must hard-fail on full IMPLEMENT-visible state + generated IMPLEMENT prompt + .claude/settings.json canonical hash + no state.rounds.pair_plan + no live anon-map + no mode-control env/config diff. Verdict: "Do not start the 11h implementation block yet. This does not need a fundamental redesign, but it does need R0.7 with a small hardening delta.")
codex_principles_decision: 2026-05-03 (195s — independent verdict on option B (defer-as-design-iter). Verdict: B, runner-up "A reduced — R0.7 once more then B if no convergence." Rationale: AGREE 13%→38%→13% is non-monotonic = NOT converging; iter-0009 / iter-0022 precedent shows R1/R2 keep finding new criticals (current state more like R1/R2 entry than convergence); option C is real disqualification (residual leaks documented violates pre-flight #0 "go/no-go impossible to fake"); option D is not auto-disqualified by no-workaround (iter-0022 infra-only precedent exists) but #2/#4/#6 weak inside current 0033d; PRINCIPLES #2 forbids in-place rename of pre-registered iter — close current 0033d as CLOSED-DESIGN and pre-register fresh impl iter; precedent iter-0033b → iter-0033b' for same pattern.)
user_adjudication: 2026-05-03 (option B chosen after Claude+Codex independent convergence on B; "쉽게 설명" simplified summary; user "B" reply.)
---

# iter-0033d — PLAN-pair vs solo-PLAN measurement

## Why this iter exists (PRINCIPLES.md pre-flight 0)

iter-0033c closed FAIL. Phase 4 cutover deletes `/devlyn:auto-resolve`; without a validated L2 surface on NEW `/devlyn:resolve`, we ship Phase 4 with L2 unproven and the multi-LLM contract degraded.

User direction (2026-05-03): "**계획과 설계가 모든 파이프라인중에 가장 중요해.** 첫 단추가 잘못 끼이면 뒤에 아무리 둘이서 논의하고 북치고 장구쳐도 안된단말이지." Pair-mode investment belongs upstream (PLAN), not just downstream (VERIFY).

iter-0033c suite traced score regression to **upstream pair-awareness leakage** at orchestrator parse time (Codex R-final-suite Q2). PLAN-pair architecture has structural firewall — IMPLEMENT consumes only `.devlyn/plan.md` (clean contract artifact), never sees pair metadata. Different attack surface.

**User-visible failure being closed**: shipping Phase 4 with "two first-class user groups" NORTH-STAR commitment but zero validated L2 surface. Codex CLI users would get a harness whose pair-mode mechanics are documented but never measured.

## Mission 1 service (PRINCIPLES.md #7)

PLAN-pair measurement is single-task scope (one fixture at a time, no parallel-fleet). Mission 1 hard NOs untouched.

## Hypothesis

PLAN-pair (Claude proposer + Codex critic, structured HIGH/CRITICAL findings only, ≤3 rounds) produces a `.devlyn/plan.md` that leads to better IMPLEMENT outcomes than solo-Claude PLAN, **without IMPLEMENT seeing any pair metadata** (firewall mechanism makes leakage structurally impossible).

> Pair-PLAN improves the final implementation on high-value fixtures without leaking pair metadata or exhausting repair-loop budget.

### Falsifiable predictions (BEFORE run)

- Pair-PLAN wall ≈ 2× solo PLAN wall.
- Fix-loop iterations drop by ~50% (PLAN catches issues that would otherwise surface in VERIFY → fix-loop).
- Net run wall ≤ 1.5× solo baseline.
- Quality: pair-PLAN final implementation score ≥ solo-PLAN on every fixture (no regression worse than −3); ≥3/6 pair-eligible fixtures show material win (+5 score lift OR categorical rescue).

## Architecture (the structural firewall)

**Three-layer defense** (Codex round-2 R-final + round-3 R0.5):

1. **Two artifacts**: `.devlyn/plan.md` (clean contract — IMPLEMENT input only) + `.devlyn/plan.debate.json` (full transcript — staged out-of-worktree until IMPLEMENT completes, then copied to run archive). IMPLEMENT prompt is hard-coded to read ONLY `.devlyn/plan.md`.

2. **Schema separation**: `pipeline.state.json` exposes only `state.plan.contract_path` (the clean plan.md location) to IMPLEMENT. Debate path is NEVER in live state. New field `state.rounds.pair_plan` (capped at 3) — distinct from `state.rounds.global` (BUILD_GATE/VERIFY fix-loops).

3. **Pre-IMPLEMENT validator**: orchestrator hard-fails IMPLEMENT spawn if `.devlyn/plan.md` is missing, malformed, or contains reserved metadata tokens (`accepted_invariants`, `model_stamps`, `planning_mode`, `pair-plan`, `plan.debate`, `claude_draft_sha256`, `codex_draft_sha256`, `<round\s*\d+>`). Lint rule `lint-skills.sh` Check 15 (NEW): `references/phases/implement.md` must NOT reference debate artifacts or pair-plan metadata. Same lint rule applies to benchmark prompts in `run-fixture.sh`.

**Convergence rule** (Codex round-2 R0.5):
- Asymmetric proposer/critic: Claude proposes plan.md → Codex critiques structured HIGH/CRITICAL findings → Claude revises plan.md → Codex re-critiques.
- Stop when Codex emits **0 HIGH/CRITICAL** findings, OR `state.rounds.pair_plan == 3`, OR `wall_seconds > pair_plan_wall_budget`.
- At cap with unresolved HIGH/CRITICAL: BLOCKED PLAN, do NOT leak known-bad plan to IMPLEMENT.

**Codex availability**: missing → solo-Claude PLAN downgrade with `engine downgraded: codex-unavailable` banner per existing `_shared/engine-preflight.md` contract.

## Method

### Pre-suite smokes (cheap, gate the suite)

- **Smoke 1a (firewall validator)**: synthetic `.devlyn/plan.md` containing each reserved metadata token → pre-IMPLEMENT validator must hard-fail with the matched token name. ~10s.
- **Smoke 1b (Codex availability)**: `command -v codex` fail-fast at top of `scripts/run-iter-0033d.sh`. <1s.
- **Smoke 1c (lint)**: `bash scripts/lint-skills.sh` Check 15 — assert NO reserved metadata tokens in `references/phases/implement.md` or any benchmark prompt. <5s.
- **Smoke 1d (round-cap)**: synthetic plan with persistent Codex HIGH (mock) → orchestrator must hit cap-3 and emit `BLOCKED:plan-pair-unresolved`. ~30s.

### Suite arms

Per fixture in `{F2, F3, F4, F6, F7, F9}` (pair-eligible set, frozen from iter-0033c manifest):

| arm | description |
|---|---|
| `solo_plan` | `--engine claude` (no pair); equivalent to current solo_claude L1 baseline |
| `pair_plan` | structural firewall + Codex critic in PLAN; IMPLEMENT consumes only `.devlyn/plan.md` |

**Same HEAD, same env, same IMPLEMENT engine** (Claude). Only PLAN differs. Benchmark prompts are **byte-identical across arms** (Codex R-final round-2 lock); plan-mode selection is harness-internal, never appears in `.devlyn/plan.md`, live state consumed by IMPLEMENT, or IMPLEMENT prompts.

### Wall budget estimate

- Solo PLAN per fixture: ~5-10 min
- Pair PLAN per fixture (~3 rounds): ~10-20 min
- IMPLEMENT + BUILD_GATE + VERIFY same as iter-0033c (~5-30 min depending on fixture)
- Suite total: ~6 hr serial (Mission 1, no parallel-fleet)

## Acceptance gates (pre-registered)

| Gate | Threshold | Source |
|---|---|---|
| 1a firewall validator smoke | reserved-token plan.md → hard-fail with matched-token error | round-2 R-final + round-3 R0.5 |
| 1b Codex availability | hard `command -v codex` fail-fast | round-2 |
| 1c lint Check 15 | NO reserved tokens in implement.md OR benchmark prompts | round-2 R-final |
| 1d round-cap smoke | persistent HIGH → BLOCKED:plan-pair-unresolved at cap-3 | round-2 R0.5 |
| 2 No-regression | every fixture: `(pair_plan − solo_plan) ≥ −3` | NORTH-STAR test #6 |
| 3 Material wins (SHIP-BLOCKER) | ≥3/6 fixtures show `+5` score lift OR categorical rescue | round-2 R0.5 (tightened from ≥2/6) |
| 4 Hard-floor | zero new disqualifier on previously-clean l1; zero new HIGH/CRITICAL `design.*`/`security.*` on previously-clean l1; zero pair-induced timeout | iter-0033c 3-bucket carryover |
| 5 Aggregate wall | `aggregate(pair_plan_wall) / aggregate(solo_plan_wall) ≤ 1.5×` | round-2 R0.5 |
| 6 Per-fixture wall ceiling | NO fixture `pair_plan_wall / solo_plan_wall > 2.0×` UNLESS categorical rescue | round-2 R-final + round-3 R0.5 |
| 7 Hold-zone | `1.5× < aggregate wall ≤ 1.7×` = HOLD/root-cause; do NOT ship Phase 4 | round-2 R-final |
| 8 Firewall artifact contract | for every fixture: `.devlyn/plan.md` exists; `.devlyn/plan.debate.json` is in run archive (not live state); IMPLEMENT prompt log shows zero reserved tokens | round-3 R0.5 |

**Ship-blockers**: 1a, 1b, 1c, 1d, 2, 3, 4, 8.
**Quality gates**: 5, 6, 7 (failure → root-cause iter; Phase 4 holds).

## Phase 4 cutover dependency

iter-0034 Phase 4 cutover **gates on iter-0033d ALL ship-blockers PASS**:
- ALL ship-blockers PASS → Phase 4 ships PLAN-pair as first product L2 surface; OLD `/devlyn:auto-resolve` deletion proceeds; NORTH-STAR amends "shipped pair surface = PLAN".
- Any ship-blocker FAIL → Phase 4 ships solo-PLAN only; NORTH-STAR records L2 as "research-only, no shipped pair surface yet"; `--engine` and `--pair-verify` flags removed (still no pair product).

## Implementation scope (this iter)

### Ships in this iter

1. **`/devlyn:resolve` SKILL.md edits**:
   - PHASE 1 PLAN body: add proposer/critic mechanism (Claude proposes → Codex critiques structured HIGH/CRITICAL → Claude revises; ≤3 rounds; firewall outputs `.devlyn/plan.md` clean + `.devlyn/plan.debate.json` debate-only).
   - PHASE 0: REMOVE `--pair-verify`, `--engine` flag parsing (Codex round-2 R0.5 verdict). Update flag table.
   - PHASE 2 IMPLEMENT body: explicit "consumes ONLY `.devlyn/plan.md` + spec; reserved-token validator runs pre-spawn".
   - Strike "PLAN pair-mode is iter-0020-falsified" overreach at line 80.
2. **`references/state-schema.md` edits**: add `state.plan.contract_path`, `state.rounds.pair_plan` (capped at 3); document firewall contract.
3. **`scripts/lint-skills.sh` Check 15 (NEW)**: scan `references/phases/implement.md` and benchmark prompts in `run-fixture.sh` for reserved metadata tokens; fail with matched-token list.
4. **`benchmark/auto-resolve/scripts/run-fixture.sh`**: add `solo_plan` and `pair_plan` arms (mirror solo_claude env shape); DELETE `l2_gated` and `l2_forced` arms; benchmark prompt body byte-identical across solo_plan and pair_plan (only harness-internal arm name differs); skill invocation no longer carries `--engine` or `--pair-verify`.
5. **`benchmark/auto-resolve/scripts/judge.sh`**: ARMS_PRESENT discovery includes `solo_plan` and `pair_plan`; remove `l2_gated`/`l2_forced` from list.
6. **`benchmark/auto-resolve/scripts/run-iter-0033d.sh`** (NEW orchestrator): smoke 1a-d → suite per-fixture interleaved (solo_plan then pair_plan) → judge per fixture → manifest reuse from iter-0033c → `iter-0033d-compare.py` emits gate table.
7. **`benchmark/auto-resolve/scripts/iter-0033d-compare.py`** (NEW): 8-gate evaluator with the thresholds above.
8. **`.claude/skills/` mirror sync** of all skill changes.
9. **Codex pair-collab**: R0 (BEFORE implementation) on the firewall mechanism + lint Check 15 + run-iter-0033d.sh design; R-final-smoke (AFTER smokes) if surprises; R-final (AFTER suite) on raw numbers.

### Does NOT ship in this iter

- Pair-mode in any phase other than PLAN.
- Pair-mode in `/devlyn:ideate` (deferred to iter-0033e stub).
- pi-agent abstraction (Mission 2/3 territory).

## Codex pair-review plan

- **R0** (BEFORE implementation): firewall mechanism design + smoke 1a-d shapes + run-iter-0033d.sh structure. Falsification ask: any leak surface I missed? Any reserved-token category missing? Is round-cap-3 the right ceiling?
- **R-smoke** (AFTER smokes 1a-d): if any smoke fails, root-cause iter before suite.
- **R-final** (AFTER suite): raw numbers + 8-gate verdict.

## Risk register

| Risk | Mitigation |
|---|---|
| Firewall leak (e.g. orchestrator inlines `pair_rounds_used` into IMPLEMENT prompt for completeness) | Pre-IMPLEMENT validator + lint Check 15 + smoke 1a synthetic test |
| Codex critic over-constrains plan (raises spurious HIGH from sandbox-only premise) | Critic findings must cite spec/expected.json/code evidence; speculative defensive expansion stays in debate archive only |
| Pair PLAN wall blowup (>2× per fixture) | Gate 6 catches per-fixture; Gate 5 catches aggregate; round-cap-3 hard limit |
| Round-cap-3 hits with unresolved HIGH | BLOCKED:plan-pair-unresolved verdict; no leak to IMPLEMENT; counts as fixture failure |
| Codex unavailable | Existing `engine downgraded: codex-unavailable` banner; solo-Claude PLAN proceeds |
| Score regression on quality axis (over-defensive plan → over-defensive code) | Gate 2 (no-regression −3) + Gate 4 (zero new HIGH/CRITICAL) |
| Lint Check 15 over-matches legitimate plan content | Reserved-token list is restrictive (not regex on `pair`/`codex`); only metadata-shape tokens |

## Principles check

- **#0 pre-flight**: ✅ closes user-visible failure (Phase 4 cutover with unproven L2).
- **#1 no overengineering**: ✅ measurement + minimum firewall (3-layer); no speculative abstractions.
- **#2 no guesswork**: ✅ predictions filled BEFORE run; gates pre-registered.
- **#3 no workaround**: ✅ structural firewall (artifact + schema + validator), not silent strip.
- **#4 worldclass**: ✅ Gate 4 enforces zero new HIGH/CRITICAL.
- **#5 best practice**: enforced via existing CRITIC findings in VERIFY (carryover).
- **#6 layer-cost-justified**: ✅ Gates 5/6/7 measure wall budget; Gate 3 measures quality lift.
- **#7 mission-bound**: ✅ Mission 1 single-task scope.

## Why this is not score-chasing (PRINCIPLES.md #0)

This iter cannot move benchmark margins on its own; it validates a measurement that the cutover needs. Real shipping decision (Phase 4 cutover with PLAN-pair as first product L2 surface) — case (b) of pre-flight 0.

## Deliverable execution order (NOT EXECUTED — superseded by closure below)

1. ~~R0 with Codex on firewall mechanism + smokes + orchestrator design.~~ DONE — produced REJECT with structural leak surfaces (see closure §A).
2. ~~SKILL.md + state-schema edits + lint Check 15 + run-fixture.sh + judge.sh edits + run-iter-0033d.sh + iter-0033d-compare.py.~~ NOT STARTED.
3. ~~`.claude/skills/` mirror sync; lint-skills.sh PASS.~~ NOT STARTED.
4. ~~Smokes 1a-d (~1 min total).~~ NOT STARTED.
5. ~~R-smoke if any smoke fails.~~ N/A.
6. ~~Suite (~6 hr).~~ NOT STARTED.
7. ~~R-final on raw numbers.~~ N/A.
8. ~~Update HANDOFF.md + DECISIONS.md + iter-0033d closure verdict.~~ DONE for closure (this section).
9. ~~iter-0034 Phase 4 cutover (gated on iter-0033d ALL ship-blockers PASS).~~ STILL BLOCKED — now gated on iter-0033f-pair-plan-impl outcome.

---

## CLOSURE — design-iter, no implementation, hand-off to iter-0033f

This iter began as a measurement iter and converged into a firewall-design discovery iter. Three rounds of Codex pair (R0/R0.5/R0.6, ~13 min Codex wall total) enumerated structural leak surfaces the original spec assumed away. The Claude+Codex independent recommendation (option B per principles-decision) is to close this iter as `CLOSED-DESIGN / NO IMPLEMENT`, preserve the design learnings here, and pre-register a fresh impl iter (iter-0033f-pair-plan-impl) that adopts all R0/R0.5/R0.6 fixes from line one.

### Why CLOSED-DESIGN, not in-place re-pre-registration

PRINCIPLES.md #2 forbids retroactive prediction edits. Rewriting this iter's frontmatter to absorb 18+ post-hoc design changes would violate that. iter-0033b → iter-0033b' precedent shows the clean pattern: close the original at its own scope, open the new one with fresh prereg.

### A. Leak surfaces caught (cumulative across R0+R0.5+R0.6)

The original 3-layer firewall (artifact split + schema separation + reserved-token validator) does NOT close these. iter-0033f must close all of them OR explicitly accept residuals with documented inference impact.

#### Live state / observable side-channels (PHASE 2 IMPLEMENT visibility)

1. **`pipeline.state.json` itself is IMPLEMENT-readable.** `state.rounds.pair_plan`, `state.phases.plan.{started_at, completed_at, duration_ms, engine, model, round}` all leak pair-mode signal. Original spec proposed `state.plan.contract_path` exposure — itself a leak. Fix direction: move pair-plan tracking entirely OUT of `pipeline.state.json` into `.devlyn/.harness-internal/pair-plan.json`; scrub PLAN phase fields to canonical defaults BEFORE IMPLEMENT spawn; pre-IMPLEMENT validator asserts scrubbed values. Top-level `state.started_at` is itself a timing leak when paired with `state.phases.plan.completed_at`.
2. **`SKILL.md` is IMPLEMENT-readable.** Current `config/skills/devlyn:resolve/SKILL.md:80` ("PLAN-pair is unmeasured at HEAD…") and `:145-148` (pair VERIFY triggers) tell the IMPLEMENT subagent that pair-mode exists upstream. Fix direction: cleanse all PHASE 0/1/2/3/4/5/6 bodies of pair-mode mention; move mechanism description to a NEW `references/pair-plan-mechanism.md` referenced ONLY by the orchestrator's runtime PHASE 1 prompt body, NEVER by IMPLEMENT.

#### Filesystem path / env / argv leaks

3. **`WORK_DIR=...-${ARM}`** at `benchmark/auto-resolve/scripts/run-fixture.sh:96` exposes arm via `pwd`. Fix: anonymize via `bench-{run_id}-{anon}` where `anon = sha256(secret_salt + run_id + fixture + arm)[:12]`.
4. **`RESULT_DIR`** at `run-fixture.sh:89` and **`--debug-file`** path at `run-fixture.sh:474` carry arm name into IMPLEMENT-visible argv. Fix: result dir + debug file under same anon.
5. **`anon-map.json` runtime visibility** — `--debug-file` argv reveals result-root path shape even if anon. Fix: write anon-map ONLY after child exit (parent-memory-only during run).
6. **`.claude/settings.json` env asymmetry** — `run-fixture.sh:173` writes `CODEX_BLOCKED=1` for solo-arm vs `CODEX_REAL_BIN/CODEX_MONITORED_PATH` for pair-arm. Fix: byte-identical settings between solo_plan and pair_plan; arm decision via single 1-byte signal file deleted before IMPLEMENT spawn.
7. **Process argv leak** — `bin/devlyn.js` and any wrapper that exec's claude must not carry `solo_plan` / `pair_plan` in argv. Validator: `ps -p $CHILD_PID -o command=` post-spawn must not contain arm-name substring.

#### Reserved-token list (multi-iteration churn)

8. **List under-coverage** (R0+R0.5+R0.6 cumulative additions): `pair_plan`, `pair_judge`, `pair-mode`, `pair mode`, `pair-plan`, `plan-pair`, `plan pair`, `PLAN-pair`, `pair_critic`, `pair_consensus`, `cross-model`, `cross model`, `Codex critique`, `Codex found`, `Codex critic`, `Claude draft`, `Claude proposer`, `opus-4-7`, `gpt-5-5`, `gpt-5.5`, `plan.debate`, `plan_debate`, `deliberation`, `codex_critic_finding_ids`, `round_num`, `wall_seconds`, `<round\s*\d+>`, `round 1 of` / `round 2 of` / `round 3 of`, `claude_draft_sha256`, `codex_draft_sha256`, `signed_plan_sha256`, `BLOCKED:plan-pair-unresolved`, `BLOCKED:plan-pair-stuck`, `BLOCKED:plan-leak-detected`, `.harness-internal`, `pair_rounds`, `rounds.pair_plan`, `plan_mode`.
9. **List over-blocking** (must NOT include): `accepted_invariants`, `model_stamps`, `planning_mode` (legitimate iter-0022 schema content per `_shared/pair-plan-schema.md`), `debate`, `critic`, `proposer` (too generic — chess apps, debate apps, etc. legitimately use these as feature-domain language).
10. **Blacklist insufficient alone** — must combine with strict structural plan.md schema (3 sections only: Files to touch / Risks / Acceptance restatement; no extra H2s; no triple-backtick fences with tokens; no HTML comments). Validator = standalone `scripts/validate-plan.py` deterministic script, not prompt prose.

#### Lint Check 15 scope

11. **Scan list expansion** — original draft scanned only `references/phases/implement.md` + benchmark prompt construction in `run-fixture.sh`. Must scan: `config/skills/devlyn:resolve/SKILL.md`, all 5 phase bodies (plan/implement/build-gate/cleanup/verify), `references/free-form-mode.md`, `references/state-schema.md`, `config/skills/devlyn:ideate/SKILL.md`, `_shared/adapters/{opus-4-7, gpt-5-5}.md`, `_shared/runtime-principles.md`, `_shared/engine-preflight.md`, `_shared/codex-config.md`, `CLAUDE.md`, `benchmark/auto-resolve/scripts/run-fixture.sh`. Plus the post-mirror `.claude/skills/` tree. Excluded (legitimate): `_shared/pair-plan-schema.md` (iter-0022 reference), `_shared/codex-monitored.sh` (iter-0009 wrapper), `judge.sh`, `iter-0033c-compare.py`, `build-pair-eligible-manifest.py`.

#### Artifact persistence + archive lifecycle

12. **IMPLEMENT subagent prompt is NOT persisted** — `claude -p` only saves outer `input.md` + final `transcript.txt` + `claude-debug.log`. Per `benchmark/auto-resolve/scripts/check-f9-artifacts.py:138`, intermediate Agent subprompts do not appear in transcripts. Fix: orchestrator at PHASE 2 entry writes the IMPLEMENT prompt as a string variable into `.devlyn/implement.prompt.txt` BEFORE Agent spawn (Agent prompt arg = file contents). Gate 8b can then scan it for reserved tokens.
13. **`archive_run.py` does NOT archive `plan.debate.json`** — current `PER_RUN_PATTERNS` at `_shared/archive_run.py:23-55` predates the iter-0033d concept. Fix: add explicit (NOT recursive glob — would sweep `.devlyn/runs/**`) entries `.harness-internal/pair-plan.json`, `.harness-internal/plan.debate.json`, `implement.prompt.txt`, `validate-plan.log`. Move helper needs small extension to handle dotted prefix.
14. **Pre-delete vs archive lifecycle conflict** — if pre-IMPLEMENT validator deletes `.devlyn/.harness-internal/`, then PHASE 6 archive has nothing to archive. Fix: pre-IMPLEMENT step moves `.harness-internal/*` to OUT-OF-WORKTREE stash (e.g. `${WORK_DIR}/../stash-${anon}/`) then deletes the in-tree dir; PHASE 6 archive moves stash → run archive.

#### Suite-level / cross-arm

15. **Cap-3 round ceiling** — inherited precedent from iter-0022 pair-plan-schema, NOT PLAN-specific evidence. Fix: per-round telemetry to `pair-plan.json`; early-stop when round N produces byte-identical `codex_critic_finding_ids` to round N-1 (Codex repeating itself → `BLOCKED:plan-pair-stuck` at round 2 instead of wasting round 3). Round-3 post-suite analysis: if no fixture rescued by round-3, lower cap to 2 in iter-0033g amendment.
16. **F9 ENGINE_CLAUSE applied to BOTH ideate and resolve** at `run-fixture.sh:321`. Fix: F9 ideate clause hardcoded `--engine claude` (no arm-specific switch); only resolve clause sees the plan-mode signal. Smoke 1a static check.
17. **Smokes must run in `mktemp`** — original draft proposed running smokes 1a/1d in live `.devlyn/`, polluting the same evidence channel the firewall is trying to prove. Fix: `TMPDIR=$(mktemp -d ...); cd $TMPDIR; ...`.
18. **Validator scope** — must hard-fail on (a) `.devlyn/.harness-internal/` exists, (b) plan.md schema-clean, (c) scrubbed plan state values, (d) `$WORK_DIR` + `$RESULT_DIR` free of arm-name strings, (e) full IMPLEMENT-visible `pipeline.state.json` content scan, (f) generated IMPLEMENT prompt scan, (g) `.claude/settings.json` canonical hash matches reference (byte-identical between arms), (h) no live `anon-map.json` or result-mapping accessible to IMPLEMENT, (i) no mode-control env/config difference between arms.

### B. Wall budget (original vs revised, NOT executed)

| | Original prereg | After R0+R0.5+R0.6 |
|---|---|---|
| Implementation | (folded into "scope of this iter") | ~10-12h |
| Smokes 1a-d | ~1 min | ~30 min |
| Mirror sync + lint | (assumed cheap) | ~15 min |
| Suite (6 fixtures × 2 arms) | ~6h | ~6h |
| R-final + closure + commit | (assumed ~30 min) | ~1.25h |
| **Total** | **~6-7h** | **~19h** |

The 3× growth is itself the primary signal that the original prereg scope was incomplete.

### C. Non-monotonic AGREE rate (R0/R0.5/R0.6)

| Round | AGREE / 8 | New surfaces caught | Verdict |
|---|---|---|---|
| R0 | 1 (12.5%) | 6 | NOT CONVERGED — REJECT design |
| R0.5 | 3 (37.5%) | 5 | NOT CONVERGED — REJECT R0.5 design |
| R0.6 | 1 (12.5%) | 7 | NOT CONVERGED — REJECT R0.6 design; "small hardening delta needed" wording but pattern says otherwise |

Codex's "small hardening delta" wording in R0.6 was optimistic; principles-decision pair (independent assessment) called this out: AGREE rate dropping back to 13% AFTER 5 R0.5 fixes adopted is a stronger signal than the wording. Repo precedent (iter-0009 R1 → R2 found pipe-stdout starvation; iter-0022 R0 → R0v2 → R1 → R-final found new blockers each round) supports the "we're at R1/R2 entry, not convergence" reading.

### D. Hand-off contract for iter-0033f-pair-plan-impl

iter-0033f MUST:

1. Pre-register a NEW hypothesis (cannot recycle this iter's hypothesis verbatim — the threat model is materially different post-leak-enumeration).
2. Pre-register NEW gates that incorporate items 1-18 above as ship-blockers.
3. Pre-register NEW wall budget (~19h is the floor; iter-0033f may add 1-2h slack).
4. Cite this closure section directly so the design context survives across sessions.
5. Sequence implementation as: SKILL.md cleanse first → standalone `validate-plan.py` second → expanded Check 15 third → archive_run.py + IMPLEMENT-prompt-persistence fourth → run-fixture.sh anon-WORK_DIR fifth → judge.sh + compare.py anon-aware sixth → orchestrator + smokes seventh → suite eighth.
6. Codex pair-collab budget: at minimum R0 on the implementation plan (against this closure as the design baseline), R-smoke after smokes 1a-d, R-final on suite raw numbers. Plan for additional R0.5/R0.6 if R0 surfaces 3+ blockers.
7. Honest fallback: if R0 on iter-0033f surfaces a new structural blocker class not in items 1-18, escalate to user adjudication BEFORE drafting R0.5 (avoid the same asymptotic-discovery pattern).

### E. What we keep / what we drop from this iter

| | Keep | Drop |
|---|---|---|
| Hypothesis | Direction (PLAN-pair vs solo-PLAN measurement) | Specific phrasing — iter-0033f restates with leak-aware framing |
| Suite | 6 high-value fixtures {F2, F3, F4, F6, F7, F9} | All implementation choices (arms, env, env-var names) |
| Acceptance gates | 8-gate structure (1a-d smokes + 2/3/4 + 5/6/7 + 8) | All threshold values restate; Gate 8 expanded per items 12-14 |
| Architecture | "Structural firewall" framing | The ORIGINAL 3-layer firewall (artifact + schema + validator) — replaced with N-layer per items 1-18 |
| Wall estimate | (none — original was ~6h) | Replaced with ~19h floor |

### F. Why this is principles-aligned closure

- **#1 No overengineering / Subtractive-first** — closing now stops further surface accretion (R0.6 added 7 new fixes; R0.7 likely adds more). The 18+ leak enumeration IS the deliverable; not adding scaffolding to maybe-eventually-measure.
- **#2 No guesswork** — pre-registration #2 honored by closing the original prereg at its own scope; iter-0033f pre-registers fresh.
- **#3 No workaround** — root-cause analysis surfaced the original threat model was incomplete (not workaround-able by adding more validators on top); fix is acknowledge incomplete + redesign with full surface mapped.
- **#4 Worldclass production-ready** — not shipping a half-baked firewall that would mis-attribute iter-0033f outcomes (was-it-the-pair-or-was-it-the-leak).
- **#5 Best practice** — iter-decomposition (design-iter → impl-iter) is the proven pattern in this repo (iter-0033b → iter-0033b').
- **#6 Layer-cost-justified** — paying ~13 min Codex wall to enumerate 18 surfaces vs paying 19h to maybe-discover them mid-implementation.
- **#7 Mission 1** — single-task scope preserved.
- **pre-flight #0** — closes "is the iter-0033d firewall design ready for measurement?" → answer: NO, with documented evidence. Phase 4 cutover stays blocked but on a clearer gate (iter-0033f-pair-plan-impl outcome).

### G. Pointers

- Codex R0 dialog: `/tmp/codex-iter0033d-r0/{prompt.md, response.log}` (in /tmp; will be lost on reboot — distillation in §A above is canonical).
- Codex R0.5 dialog: `/tmp/codex-iter0033d-r0/{r05-prompt.md, r05-response.log}`.
- Codex R0.6 dialog: `/tmp/codex-iter0033d-r0/{r06-prompt.md, r06-response.log}`.
- Codex principles-decision: `/tmp/codex-iter0033d-r0/{principles-decision-prompt.md, principles-decision-response.log}`.
- Next iter file: `iterations/0033f-pair-plan-impl.md` (PRE-REGISTERED stub at this commit; full pre-reg drafted in next session that picks up impl).
