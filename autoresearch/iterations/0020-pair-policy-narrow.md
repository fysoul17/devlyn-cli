# iter-0020 — Cost-aware pair policy (narrow): e2e → BUILD=Claude + Playwright hygiene

**Status**: Phase A SHIPPED + verdict (`pair_policy_failure_count = 2`); iter-0019.9 fix shipped to clear F9 false signal; **Phase B implementation IN-COMMIT, awaiting paid 9-fixture × 3-arm verification suite (~$30-50, ~3-4h wall)**

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
