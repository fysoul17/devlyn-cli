# iter-0020 — Cost-aware pair policy (narrow): e2e → BUILD=Claude + Playwright hygiene

**Status**: **CLOSED 2026-04-29 as FAILED-EXPERIMENT-REVERTED-POLICY** per Codex GPT-5.5 deep North-Star verdict after the 9-fixture × 3-arm paid suite returned ship-gate FAIL (L1-L0 = +4.4 below floor +5; L2-L1 = -3.6). Phase A + Phase B implementation history below is preserved as historical record; the **CLOSE-OUT (Phase 1, 2026-04-29)** block at the bottom of this file documents the rollback decision, the diff (17 files, +199/-813, net -614), and the iter-0021 inverted-pair experiment that replaces it.

## Why this iter exists (NORTH-STAR ops test #6 + Codex R3 hard acceptance)

iter-0019 5-fixture smoke gave L2-L1 = +1.0 (FAIL +5 floor). Pair-mode wasn't paying for itself on the average. NORTH-STAR test #6 says L2 must beat L1 by ≥+5 on **pair-eligible / high-value fixtures**, not on flat suite avg — so the question was *which* fixtures fail pair-routing AND should narrow.

Codex R3 locked iter-0020 hard acceptance: ships ONLY with all 5 — (1) per-fixture-class routing table, (2) ≥1 routing decision differing, (3) deterministic short-circuit/abort enforced **in code (not prompt-only)**, (4) `coverage.json` proving exercise, (5) recorded rollback condition.

## Phase A verdict (with iter-0019.9 fix applied to F9)

`pair_policy_failure_count = 2`:

| Fixture | category | L2 score | L1 score | L2-L1 | wall_ratio | Verdict |
|---|---|---|---|---|---|---|
| F1-cli-trivial-flag | trivial | data | data | +1 | 1.08× | OK (no premium) |
| F2-cli-medium-subcommand | medium | data | data | -1 | 1.34× | OK (no premium) |
| **F4-web-browser-design** | stress | 99 | 100 | -1 | 0.79× | **FAIL: L2 has 1 CRITICAL** (`test-results/.last-run.json` out-of-scope) |
| F6-dep-audit-native-module | stress | data | data | +7 | 1.11× | OK (pair WINS) |
| **F9-e2e-ideate-to-preflight** | e2e | 71 ⚠DQ | 92 | **-21** | 1.84× | **FAIL: L2 silent-catch DQ + format mismatches** (verdict from iter-0019.9 F9 re-run) |

F4 and F9 fail for DIFFERENT reasons:
- F4: Codex BUILD added `test-results/.last-run.json` (Playwright artifact) outside spec scope. Behavior tests passed; only output hygiene leaked. **Prompt-fixable** per Codex Phase B Q4 verdict — narrow `<quality_bar>` bullet about tooling artifacts.
- F9: Codex BUILD on novice-flow regresses 21 points + introduces silent-catch DQ in `safeReaddir`. The "no silent catches" rule is already explicit in `phase-1-build.md:55,60` and `CLAUDE.md:130`; Codex still emitted one. **Treat as not-prompt-fixable until disproven** per Codex Phase B Q3 — narrow routing defense to Claude BUILD for `category=e2e`.

## Codex pair-review trail

- **R0 pre-design** (43k tokens, 85s): rejected my Options A/B/C, prescribed **Option D** (no-code preflight first; pre-register `pair_policy_failure_count` metric; iter-0020 closes if count=0). Adopted in full.
- **R-phaseA** (68k tokens, 201s) on Phase A data: confirmed F9 false-signal mechanism; verdict Option α (patch iter-0019.9 first); Q3 = `browser=true → BUILD=Claude` (later refined in Phase B scope ask to "F4 prompt-fixable, F9 routing").
- **Phase B scope** (150k tokens, 191s): verdict Option C narrowly — `category=e2e → BUILD=Claude` routing + Playwright/output-hygiene prompt for F4. Do NOT add browser=true to routing rule (over-narrows: F6 stress passes). Provided concrete coverage.json schema.
- **R1 design** (53k tokens, 103s): "Not sufficient as written." 3 blockers: E3 not code-enforced (need actual `select_phase_engine.py` script), archive_run.py missing coverage.json pattern, mirror discipline (auto-mirror covers it). Q-answers: `fixture_class: null` (not omission), gate on BENCH_WORKDIR co-set, new `coverage_report.py`, "do not leave in final diff" wording. All adopted.
- **R2 diff review** (55k tokens, 112s): substantively yes with 4 small fixes — hard-fail on missing state, pipeline-state.md canonical schema block missing new fields (split-brain), SKILL.md PHASE 0 add fixture_id population, stale docstring text in select_phase_engine.py. Q4 keep `not_applicable` and `selected_but_observed_engine_diverged` (load-bearing). Q5 sufficient if suite-aggregator script proves ≥1 fired per route. **Q6 main miss**: no automated suite-level aggregator — adopted, wrote `iter-0020-aggregate-coverage.py`.

## Implementation (10 edits, 3 new files)

### New files (3)

1. **`config/skills/devlyn:auto-resolve/scripts/select_phase_engine.py`** (~155 LOC) — code-enforced per-phase engine selector. Reads `state.source.fixture_class`; applies routing table + per-fixture-class overrides (`e2e → claude`); writes `state.route.engine_overrides.<phase>` if override fires; prints engine name. Hard-fails on missing state.
2. **`config/skills/devlyn:auto-resolve/scripts/coverage_report.py`** (~190 LOC) — emits `.devlyn/coverage.json` per Codex schema (Q5). Per-fixture buckets: `applicable_fired` / `applicable_missed` / `not_applicable`. Per-fixture invariant: `all_applicable_routes_exercised` true when no `applicable_missed`.
3. **`autoresearch/scripts/iter-0020-aggregate-coverage.py`** (~110 LOC) — suite-level aggregator (Codex R2 Q6). Walks all per-fixture coverage.json files; verdict PASS iff every changed route fired ≥1× across the suite AND no router bugs (`applicable_missed` empty everywhere). Exit 0/1.

### Edits to existing files (7)

4. **`benchmark/auto-resolve/scripts/run-fixture.sh`** — export `BENCH_FIXTURE_CATEGORY` (from `metadata.json:category`) + `BENCH_FIXTURE` next to existing `BENCH_WORKDIR` export. 3 lines.
5. **`config/skills/devlyn:auto-resolve/SKILL.md`** PHASE 0 step 4 — populate `state.source.fixture_class` and `state.source.fixture_id` from envs (gated on BENCH_WORKDIR co-set). 1 paragraph.
6. **`config/skills/devlyn:auto-resolve/SKILL.md`** PHASE 1 BUILD — invoke `select_phase_engine.py --phase build --engine <flag>` BEFORE spawn; use printed engine. 1 paragraph rewrite of "Engine: BUILD row" line.
7. **`config/skills/devlyn:auto-resolve/SKILL.md`** PHASE 5 — add coverage_report.py invocation between terminal_verdict and archive. 1 step + renumber follow-on.
8. **`config/skills/devlyn:auto-resolve/scripts/archive_run.py`** — add `coverage.json` to `PER_RUN_PATTERNS`. 3 lines.
9. **`config/skills/devlyn:auto-resolve/references/engine-routing.md`** — new "Per-fixture-class BUILD overrides (iter-0020)" section with table (e2e → Claude), rationale, and rollback condition. ~12 lines.
10. **`config/skills/devlyn:auto-resolve/references/phases/phase-1-build.md`** `<quality_bar>` — narrow Playwright/output-hygiene bullet ("no test-results/, no playwright-report/, no .last-run.json, no reporter HTML") with iter-0020 attribution to F4. 1 line + parenthetical.
11. **`config/skills/devlyn:auto-resolve/references/pipeline-state.md`** — canonical schema block adds `fixture_class`, `fixture_id`, `route.engine_overrides`. Plus "Source" / "Route" semantic docs for the new fields. ~24 lines.

## Falsification (synthetic, no model spend)

`select_phase_engine.py` 5 unit tests (T1-T5, all matched 1:1):
- T1 e2e + auto → claude (override fires + state write) ✓
- T2 trivial + auto → codex (default) ✓
- T3 e2e + --engine claude → claude (no override needed) ✓
- T4 e2e + --engine codex → codex (user choice wins) ✓
- T5 real-user (no fixture_class) + auto → codex (default) ✓

`coverage_report.py` 3 scenarios:
- T6 e2e + override fired + observed=claude → applicable_fired=1, all_applicable_routes_exercised=true ✓
- T7 trivial fixture (route not applicable) → not_applicable=1, all_applicable=true ✓ (semantically correct: route is for a different class)
- T8 e2e + class match BUT override didn't fire (router bug sim) → applicable_missed=1, all_applicable=false ✓

`iter-0020-aggregate-coverage.py` 2 scenarios:
- AGG-1 mixed F1/F9 (F1=not_applicable, F9=fired) → VERDICT PASS (route exercised ≥1×) ✓
- AGG-2 only F1 (route never fires across suite) → VERDICT FAIL (exit 1) ✓

## Hard acceptance check (Codex R3 lock)

| # | Requirement | Status |
|---|---|---|
| 1 | Per-fixture-class routing table | ✓ `engine-routing.md` "Per-fixture-class BUILD overrides" |
| 2 | At least one routing decision differing from current | ✓ e2e → Claude (was Codex) |
| 3 | Deterministic short-circuit/abort enforced in code (not prompt-only) | ✓ `select_phase_engine.py` invoked from PHASE 1 |
| 4 | `coverage.json` proving every changed route was exercised | ✓ `coverage_report.py` per-fixture + `iter-0020-aggregate-coverage.py` suite-level. Hard acceptance gate at suite end: aggregator exit 0. |
| 5 | Recorded rollback condition | ✓ `engine-routing.md` table footer: revert if e2e regresses ≥3 axes vs iter-0019.9 baseline (F9 L1=92/verify=1.0/dq=false) |

## Principles 1-6 self-check

1. **No overengineering** — Codex R0 collapsed Options A/B/C into Option D (preflight first). Codex Phase B narrowed Option C from "browser=true OR e2e routing + prompt" to "e2e routing + narrow F4 prompt." 3 new scripts (155+190+110 LOC) but each closes a specific hard-acceptance criterion. ✓
2. **No guesswork** — pre-registered failure metric (Codex R0). Phase A ran. F9 false signal verified via independent file:line grep (R-phaseA Q1). Phase B routing rule justified per fixture (R-Phase-B Q3-Q4 evidence). ✓
3. **No workaround** — F9 routing-as-defense is *not* a workaround for "Codex emits silent catches"; it's a layered defense after the prompt-level "no silent catches" rule already exists at `phase-1-build.md:55` + `CLAUDE.md:130` and Codex still violated it (Codex R-Phase-B Q3 verdict). The `<quality_bar>` Playwright bullet for F4 is the smallest fix at the right layer for that specific class of leak. ✓
4. **Worldclass production-ready** — `select_phase_engine.py` hard-fails on missing state (Codex R2 #1); explicit error messages cite the contract violation; `coverage_report.py` distinguishes router bugs (`applicable_missed`) from non-applicable routes (`not_applicable`). ✓
5. **Best practice** — script-pattern consistency with `archive_run.py` / `terminal_verdict.py` / `spec-verify-check.py` (Codex R1 Q4). Stable schema (Codex R2 #2 + Q3): `fixture_class: null` not omitted. Defense-in-depth at multiple layers (selector + state write + coverage proof + aggregator). ✓
6. **Layer-cost-justified** — Phase A preflight ($25) saved a misdirected $30-50 9-fixture run on stale data. Phase B implementation is code-only ($0). The 9-fixture verification run ($30-50) is the next paid step, gated on user approval. Routing change targets ONLY e2e fixture class — doesn't penalize non-e2e users with extra Claude-vs-Codex deliberation cost. ✓

## Drift check (산으로?)

- **Removes a real user failure?** Yes for benchmark e2e users (F9 measures novice flow); generalization to real-user e2e detection deferred to a future iter when we have user-side evidence (real users without `BENCH_FIXTURE_CATEGORY` env get current Codex BUILD default — no behavior change for them).
- **Expands scope?** Strictly within Codex R0+R-Phase-B scope. Did NOT add browser=true to routing (Codex Q3+Q4: F4 is hygiene-fixable, not routing). Did NOT add prompt accretion for silent-catch (already explicit; accretion is Codex's "not root cause" verdict).

## Rollback condition (recorded)

Revert E1-E11 (or specifically the e2e routing entry) if a future paid suite OR real-project trial gate (NORTH-STAR test #14) shows the e2e fixture-class regressing by **≥3 axes** vs the iter-0019.9 baseline (F9 L1=92 / verify=1.0 / dq=false). Rollback fires per-route, not all-or-nothing — the routing entries in `engine-routing.md` "Per-fixture-class BUILD overrides" are independently revertable.

## What this iter does NOT close

- 9-fixture × 3-arm paid verification suite (~$30-50, ~3-4h wall) is the next paid step. Awaits user cost approval. Will produce trustworthy L1-vs-L0 release-readiness data + verify e2e routing exercised correctly + verify F1-F8 don't regress under the new selector.
- Real-user e2e detection: deferred. iter-0020 ships benchmark-only routing signal; real users currently get Codex BUILD default until a real-user e2e signal is identified.
- F4 → Claude routing: rejected per Codex Q3-Q4. Prompt fix only.
- iter-0019.7 fix-loop enrichment: stays deferred (Codex R3 attribution discipline — measurement-driven decision after iter-0020 9-fixture data).

## What this iter unlocks

- 9-fixture × 3-arm paid verification suite (the canonical release-readiness measurement deferred since iter-0019).
- iter-0019.7 measurement-driven decision (post 9-fixture data).
- iter-0021 dual-judge conditional fire (per HANDOFF queue: only if iter-0020 verdict lands within ±6pt of routing threshold).
- NORTH-STAR test #14 (real-project trial gate) becomes the final stop condition.

---

## CLOSE-OUT (Phase 1, 2026-04-29) — FAILED-EXPERIMENT-REVERTED-POLICY

**Verdict source**: Codex GPT-5.5 deep North-Star consultation (78k tokens, 156s, xhigh) on 2026-04-29 after the 9-fixture × 3-arm paid suite (RUN_ID `20260428T131713Z-91994db-iter-0020-9fixture-verify`, ~$30-50, 5h17m wall) returned ship-gate FAIL.

### Codex North-Star verdict (verbatim)

> "3-layer North Star is still right. The current L2 architecture is wrong. Codex BUILD + Claude review is falsified for this fixture set. Loses to Claude solo on F2/F3/F5/F6, only +1 wins on F4/F7."

**Q-by-Q**:
- Q2 ship: NOT ship as L2 policy. Close iter-0020 as "failed product-policy experiment, useful evidence retained." Keep only independently justified pieces (F4 Playwright hygiene). Rollback the e2e override.
- Q4 next: (1) Product stance NOW: L1 Claude solo = canonical surface; L2 = disabled / research-only. (2) Research experiment: iter-0021 Claude BUILD + Codex CRITIC inverted-pair smoke on F2/F3/F8. (3) Acceptance: L2-inverted must not regress L1 by >1pt + must improve at least one L1 weakness materially + must abort cheaply on F8.
- Q6 user-facing: do NOT sell L2 today.

### 9-fixture data (per-fixture)

| Fixture | category | L2 | L1 | L0 | L2-L1 | L1-L0 | L2/L1 wall |
|---|---|---|---|---|---|---|---|
| F1 trivial-flag | trivial | 98 | 99 | 93 | -1 | +6 | 1.06× |
| F2 cli-subcommand | medium | **83** | 94 | 85 | **-11** | +9 | 0.99× |
| F3 backend-contract | high-risk | **78** | 94 | 95 | **-16** | -1 | 1.23× |
| F4 web-browser | stress(browser) | 96 | 95 | 84 | +1 | +11 | 1.01× |
| F5 fix-loop-red-green | stress | 92 | 96 | 92 | -4 | +4 | 0.75× |
| F6 dep-audit | stress | 97 | 99 | 90 | -2 | +9 | 1.0× |
| F7 out-of-scope-trap | stress | 100 | 99 | 97 | +1 | +2 | 1.32× |
| F8 known-limit | edge | 80 | 80 | 80 | 0 | 0 | 15.0× |
| F9 e2e-novice-flow | e2e | 53 | 53 | 53 | 0 | 0 | 0.33× (API 429 — not run) |
| **Avg** | | **86.3** | **89.9** | **85.4** | **-3.6** | **+4.4** | **2.5×** |

L1-L0 = +4.4 — below NORTH-STAR floor +5 → **L1 release-readiness FAIL**.
L2-L1 = -3.6 — pair-mode regresses solo on average → **L2 release-readiness FAIL**.

### Phase 1 rollback diff

17 files, 199 inserts / 813 deletes (net -614 lines). Subtractive-first applied per Codex R0 Q1 alternative ("delete now" instead of "keep dormant with sunset clause" — keeping dormant scaffolding for hypothetical iter-0021 reuse violated P1 since iter-0021 inverted-pair routes CRITIC, not BUILD). The 199 inserts are dominated by required record-keeping: this CLOSE-OUT block, the `DECISIONS.md` line, the `HANDOFF.md` rotation, and the post-R2 fix-up patches; net behavior change is small.

**Deleted (4 scripts, 626 LOC total)**:
- `config/skills/devlyn:auto-resolve/scripts/select_phase_engine.py` (158 LOC) — code-enforced per-phase BUILD selector
- `config/skills/devlyn:auto-resolve/scripts/coverage_report.py` (183 LOC) — `.devlyn/coverage.json` proof artifact
- `autoresearch/scripts/iter-0020-aggregate-coverage.py` (120 LOC) — suite-level aggregator
- `autoresearch/scripts/iter-0020-failure-count.py` (165 LOC) — Phase A `pair_policy_failure_count` verdict script

**Skill prompt edits** (auto-resolve only — Codex R1 Option β scope):
- `SKILL.md:37` — `<engine_routing_convention>` final line clarified: `--engine claude` is auto-resolve default; `--engine auto` opts into experimental dual-engine routing.
- `SKILL.md:70` — `--engine MODE (auto)` → `--engine MODE (claude)`. Runtime default flipped.
- `SKILL.md:89` — iter-0020 `state.source.fixture_class`/`fixture_id` population paragraph deleted (PHASE 0 no longer asks orchestrator to populate fields).
- `SKILL.md:101` — iter-0020 selector invocation deleted (PHASE 1 BUILD reverts to static engine-routing table).
- `SKILL.md:243` — coverage_report.py invocation deleted from PHASE 5.
- `references/engine-routing.md` — "Per-fixture-class BUILD overrides (iter-0020)" section deleted entirely (option B per Codex R0 F4). "Override behavior" §82 default-claim corrected to per-skill default note.
- `references/pipeline-state.md` — `state.source.fixture_class`, `fixture_id`, `state.route.engine_overrides` schema entries + prose deleted.

**Shared / preflight** (Codex R1 Option β: skill-default-aware semantics, not global flip):
- `_shared/engine-preflight.md` — rule rewritten: skill resolves engine from its own SKILL.md default + user flag; pre-flight fires only when resolved engine is `auto`/`codex`. Per-skill defaults now documented inline (auto-resolve `claude`; ideate / preflight / team-* `auto`).
- `_shared/runtime-principles.md` + `CLAUDE.md` — silent-fallback exception updated to engine-resolved-by-skill semantics; banner text identical.

**Bench harness**:
- `benchmark/auto-resolve/scripts/run-fixture.sh` — variant arm `ENGINE_CLAUSE` flipped from `""` (relied on default) to `"--engine auto"` (explicit-flag pattern survives default flip per Codex R0 F3). BENCH_FIXTURE_CATEGORY + BENCH_FIXTURE exports deleted (no consumer). coverage.json copy block deleted.
- `config/skills/devlyn:auto-resolve/scripts/archive_run.py` — `coverage.json` removed from PER_RUN_PATTERNS.

**Product positioning** (auto-resolve-scoped per Codex R1):
- `CLAUDE.md:22` — Quick Start rewritten to scope the default flip explicitly: auto-resolve defaults to `--engine claude` (its experimental dual-engine mode is disabled per the 9-fixture verdict); ideate / preflight keep `--engine auto` as their default (no measured pair-mode failure on those skills).
- `README.md` — "Bonus — Intelligent Model Routing" section + table deleted; replaced with "Engine selection — Claude solo by default" with quality-floor data citation. Skip-phases line lost the `--engine auto` recommendation.

### Things KEPT (independently justified)

- `phase-1-build.md` `<quality_bar>` Playwright/output-hygiene bullet (F4 evidence — applies to all `--engine auto` BUILD calls regardless of routing).
- `spec-verify-check.py` + `.devlyn/spec-verify.json` carrier mechanism (iter-0019.6/.8/.9) — orthogonal to routing; NORTH-STAR test #14 carrier dimension closure.
- archive_run.py `spec-verify*` patterns.
- `devlyn:ideate` / `devlyn:preflight` / `devlyn:team-resolve` / `devlyn:team-review` SKILL.md `--engine auto` defaults — UNCHANGED. The 9-fixture verdict measured auto-resolve's L2 BUILD-pair architecture only; ideate's CHALLENGE-critic and preflight's AUDIT routing have not been benchmarked. Applying the rollback to skills with no measured failure = scope creep (산으로 가는 work). Per-skill defaults documented in shared engine-preflight.md.

### Codex pair-review trail (Phase 1)

- **R0 pre-rollback** (161k tokens, 214s, xhigh): "Do not apply as drafted — under-corrects in 3 load-bearing places." 7 findings adopted, including delete-vs-dormant decision (chose delete per Q1 alternative).
- **R1 diff review** (116k tokens, 262s, xhigh): "Not sufficient yet. I found real misses." 3 findings adopted: (1) default flip incomplete across 8 sites — adopted Option β (scope to auto-resolve, rewrite shared engine-preflight.md as skill-default-aware) over Option α (flip uniformly); (2) `engine-routing.md:82` "Override behavior" §default claim corrected; (3) `.claude/scheduled_tasks.lock` flagged not for commit (gitignored).
- **R2-1 ship-readiness** (127k tokens, 235s, xhigh): "Not ship-as-drafted yet — 6 commit-blocking findings." All 6 adopted: (a) `.claude/*.lock` added to `.gitignore` (so `git add -A` can't stage `scheduled_tasks.lock`); (b) HANDOFF cold-start sanity check #4 trimmed to runtime-principles.md only (the two iter-0020 script `diff -q`'s referenced deleted files); (c) HANDOFF Phase 2 plan rewritten — instructs designing FRESH inverted-pair scaffolding from scratch, NOT extending deleted `coverage_report.py`/`select_phase_engine.py`; (d) diff stat in 4 places corrected; (e) `pipeline-state.md:108` "engine: ... or `auto` default" corrected to skill-default wording; (f) R2/TBD markers cleaned up.
- **R2-2 ship-readiness re-review** (117k tokens, 264s, xhigh): "Not ship-as-drafted yet — 4 commit-blocking doc drift issues." All 4 adopted: (a) CLAUDE.md:22 + iter-0020:175 over-scoped default flip — rewrote to scope auto-resolve only (Option β), explicit retain ideate/preflight at auto; (b) HANDOFF:230 sanity check #2 expected output corrected (post-Phase-1 commit = clean status, lock file gitignored); (c) HANDOFF:251 sanity check #5b grep relaxed to allow leading whitespace (`^[[:space:]]+- ` vs anchored `^- `); (d) iter-0020:149 prose mention of "187 inserts" updated to match corrected count.
- **R2-3 ship-readiness re-review** (122k tokens, 248s, xhigh): "Not ship-as-drafted yet — 3 remaining doc drift issues." All 3 adopted: this Status header / R2-trail line, HANDOFF Current-state pre-Phase-1 framing prune, and DECISIONS line R2-final wording.
- **R2-final** (32k tokens, 108s, xhigh): "fix that wording and commit; I would not run R2-N+1 for this" — single minor R2-3 trail-wording correction adopted (this bullet itself reflects the fix); ship-readiness PASS.

### Phase 1.5 — skill-creator audit decision

SKIPPED with documented rationale: auto-resolve `SKILL.md` description frontmatter was deliberately NOT touched in this rollback (per HANDOFF Phase 1.4 rule — skill description stays neutral about engine, user supplies `--engine claude` explicitly per CLAUDE.md guidance). Trigger-rate regression risk is therefore not material — skill-creator eval would consume tokens for a defensive check on unchanged surface. Re-run skill-creator eval if and when iter-0021 introduces new SKILL.md description wording.

### Principles 1-6 self-check (close-out)

| # | Principle | Status |
|---|---|---|
| 0 | Pre-flight: removes user failure / forces decision | ✓ Closes iter-0020 as failed-experiment; deletes a paid product surface that loses on 5/8 fixtures while costing 3× |
| 1 | No overengineering / subtractive-first | ✓ 199 inserts / 813 deletes = ratio ~4.1:1 net-deletion. Behavior-change inserts ≈ 25 lines (default-flip wording, explicit-flag for variant, skill-default-aware preflight rewrite, post-R2 fix-up patches); the remainder is required record-keeping (this CLOSE-OUT block, DECISIONS line, HANDOFF rotation). |
| 2 | No guesswork | ✓ Verdict driven by 9-fixture paid data + Codex North-Star synthesis; no retroactive prediction |
| 3 | No workaround | ✓ Codex R1 Option β: per-skill defaults documented in shared engine-preflight.md; runtime default flipped at the skill layer (auto-resolve only). No docs-only hedge. |
| 4 | Worldclass production-ready | ✓ Lint 11/11 PASS post-R1; no CRITICAL/HIGH design.* findings introduced |
| 5 | Best practice | ✓ No MEDIUM unidiomatic-pattern adds; pure subtraction for the deleted scripts |
| 6 | Layer-cost-justified | ✓ Direct apply: rolling back a layer that failed its own L2-vs-L1 contract. ideate / preflight / team-* defaults retained because they have no measured layer-cost failure. |

### What this close-out unlocks

- **iter-0021** — inverted-pair research smoke (Claude BUILD + Codex CRITIC) on F2/F3/F8. Pre-registered acceptance gates per Codex Q4. Awaits user cost approval (~$15-25, ~2-3h wall).
- **NORTH-STAR test #14 (L1 real-project trial)** — runnable as diagnostic now (per Codex Q7), NOT as final stop condition since 9-fixture release gates haven't passed.
- **L1 product stance** — `--engine claude` is the canonical user-facing surface for auto-resolve. Documented as "currently the best measured default but still below release floor" — honest claim boundary preserved.

### Rollback rollback condition (when to revisit)

If iter-0021 inverted-pair (Claude BUILD + Codex CRITIC) ships PASS on its pre-registered gates, the L2 product surface re-enters scope under inverted shape — but with new selectors / new schema, NOT by restoring the iter-0020 e2e BUILD override (which is permanently rejected by the 9-fixture data above).
