---
iter: "0022"
title: "PLAN-pair infrastructure — schema + idgen + lint + preflight + auto-resolve input contract"
status: shipped
type: infrastructure (no real provider/model invocations; iter-0023 will be the measurement pilot)
shipped_commit: 8fcc509
date: 2026-04-29
mission: 1
---

# iter-0022 — PLAN-pair infrastructure

## Why this iter exists (PRINCIPLES.md pre-flight 0)

**This iter exists to make the next behavior change (iter-0023 measurement pilot) impossible to fake.** iter-0021 calibration showed L1-L0 = +4.4 (below the +5 Mission 1 floor) and identified Scope as L1's only negative axis (−4 across F2 + F4). User-adjudicated direction post 3-round Codex dialogue (2026-04-29 evening): test PLAN-pair architecture as the L2 redesign rather than chase the +0.4 scope delta directly.

**Decision this iter unlocks**: iter-0023 measures whether pair PLAN materially improves Codex BUILD over solo PLAN on F2 + F3 (the two fixtures with strongest L1 underperformance signal). iter-0023 must run a real provider/model preflight followed by Arm A (control: solo PLAN + Codex BUILD) vs Arm B (test: pair PLAN + Codex BUILD). Without iter-0022's infrastructure, iter-0023 has no schema, no canonical IDs, no lint, no orchestrator, and no auto-resolve hook to bind plan invariants into BUILD/EVAL/CRITIC.

This is **the LAST attribution-infrastructure iter** before behavior change (iter-0023 = real model calls). PRINCIPLES.md:22 holds: a measurement-only iter is allowed only as the last attribution run before a cost/policy/correctness decision.

## Mission 1 service (PRINCIPLES.md #7)

Serves Mission 1 gate 1 (L1 vs L0 quality) **indirectly**: this iter does NOT move L1-L0. Its output is the substrate iter-0023 needs to read whether PLAN-pair architecture lifts L2 categorically. If iter-0023 returns `plan_capture_with_lift`, L2 product surface re-opens with empirical justification; if `plan_omission` or `plan_capture_no_lift`, L2 stays disabled per iter-0020 closeout and Mission 1 must close on the L1-only path. Either outcome is mission-bound.

Mission 1 hard NOs untouched (no worktree, no parallel-fleet, no resource-lease, no run-scoped state migration, no queue metrics, no multi-agent coordination beyond `pipeline.state.json`, no cross-vendor / model-agnostic infrastructure). User-adjudicated 2026-04-29: "Mission 내용은 무시. 그건 나중에 미래에 할일." iter-0022's D4 (`pair-plan-preflight.sh`) writes Claude+Codex orchestration code but does NOT execute real model calls in iter-0022 — `--dry-run` is the only supported mode this iter; `--no-dry-run` exits 65 explicitly with a contract-violation message. The non-dry-run path lands in iter-0023 along with the measurement pilot.

## Hypothesis (predicted, written before D5 implementation)

H1 (predicted): D2 idgen produces deterministic registries — same inputs → byte-identical SHA — when `--generated-at` is pinned. Confirmed in lint Check 13.

H2 (predicted): F2 registry contains the silent-catch-return-fallback invariant ID derived from `expected.json:forbidden_patterns[0]`, AND the test-fidelity:mock-swap invariant from oracle `--list-categories`. Confirmed: F2 registry has both at `forbidden_pattern__silent_catch_returning_a_fallback_value_violates_no_silent_c__bin_cli_js` and `test-fidelity:mock-swap`.

H3 (predicted): F3 registry contains the silent-catch invariant AND the real-HTTP-server-helper-class invariant (which maps to `test-fidelity:mock-swap` per Codex R0v2 catch — F3's `tests/server.test.js` uses `createServer`/`listen` which are REAL_PATTERNS). Confirmed: F3 registry has `forbidden_pattern__silent_catch_returning_fallback__server_index_js` and `test-fidelity:mock-swap`.

H4 (predicted): pair-plan-lint catches all 4 acceptance categories — `missing_required_id`, unresolved-with-final, mismatched-stamps, source-sha-drift. Confirmed via mutation tests against the F2 sample-pass plan.

H5 (predicted): pair-plan-preflight.sh `--dry-run` produces `verdict.json` that validates inline schema and outputs `verdict: "advance"` on F2 and F3 (oracle entries → solo stub captures half → pair stub captures all → lift > 0). Confirmed: F2 lift=3, F3 lift=3, both verdict=advance. Synthetic test bundle (no oracle entries) returns `verdict: "abort"` with reason "lift <= 0" — this is correct semantics: a fixture with zero oracle invariants does not benefit from pair planning.

## Method

Five deliverables built in dependency order, each gated by HANDOFF acceptance criteria. Codex pair-review trail: R0 design (cross-cutting), R0v2 design corrections, ship-gate close-out.

### Deliverable 1 — `pair-plan-schema.md` schema doc

`config/skills/_shared/pair-plan-schema.md` (~210 lines) defines the canonical shape of `pair-plan.json` and `canonical_id_registry.json`. Mirrored to `.claude/skills/_shared/pair-plan-schema.md`. Registered in `scripts/lint-skills.sh` Check 6. The doc is self-contained — a fresh session implements D2-D5 from D1 alone.

Two SHA contracts pinned:
- **Contract A — raw file bytes** for `source.{spec_sha256, expected_sha256, rubric_sha256, canonical_id_registry_sha256}` and registry's `generated_from.*_sha256`. Computed `sha256(open(p, "rb").read())`.
- **Contract B — canonical pre-stamp** for `model_stamps.{claude,codex}.signed_plan_sha256`: load plan, replace `model_stamps` value with `{}`, `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`, UTF-8, sha256. Both stamps sign byte-identical canonical bytes; lint enforces equality.

Slug rules pinned:
- `forbidden_patterns[i]`: `forbidden_pattern__<sanitize(description, 60)>__<sanitize(files[0], 30)>`. Collision handling: first occurrence keeps bare slug, subsequent collisions get `__i<index>` suffix.
- `verification_commands[i]`: `verification__<sha8(canonical_compact_json(verification_obj))>` — full-object hash, reorder-stable, exit_code/stdout-aware (per Codex R0 critique #4).

Final-plan coverage rule: `plan_status == "final"` requires every `required_invariants[].id` to appear in `accepted_invariants[].id` ∪ `rejected_alternatives[].conflicts_with_ids[]` ∪ `escalated_to_user[].id` ∪ `unresolved[].id`. Draft / blocked plans are NOT subject to coverage (allows preflight to compare solo-vs-pair when solo is incomplete).

### Deliverable 2 — `pair-plan-idgen.py` + oracle `--list-categories` + F2/F3 snapshots

`benchmark/auto-resolve/scripts/pair-plan-idgen.py` (~280 lines). Reads `expected.json` + `metadata.json` from a fixture dir, plus per-oracle category enums via `--list-categories`. Emits sorted-by-id registry JSON. Path-trap: `builtins.open` and `os.open` wrappers raise `AssertionError` on any path containing `/results/` (HANDOFF mandatory acceptance test, defends against iter-0020 result leakage into registry source-of-truth). Verified: legitimate fixture paths pass; both `/tmp/x/results/y` and `os.open` of same fail with assertion.

Oracle scripts patched to expose stable category enums via `--list-categories`:
- `oracle-test-fidelity.py`: 4 categories (test-file-deleted, test-file-renamed, mock-swap, assertion-regression).
- `oracle-scope-tier-a.py`: 2 categories (lockfile-deletion, tier-a-violation umbrella covering 5 path-glob groups + 2 basename rules — split rejected per Codex R0 Q1).
- `oracle-scope-tier-b.py`: 1 category (scope-unmatched). `tier-b-reachable` (info-positive) deliberately omitted from registry.

`--list-categories` is a standalone subcommand (no `--work` / `--scaffold` required), and category output embeds NO line numbers (Codex R0 Q8 — line numbers shift on script edits, breaking determinism).

`metadata.json` field `pair_plan_oracle_categories` (NEW per fixture, 7 entries each) controls per-fixture allowlist. F2 includes `test-fidelity:mock-swap` (Codex R0 critique #2: every fixture inherits `fixtures/test-repo/tests/cli.test.js` via `run-fixture.sh:64 cp -R`, and that file uses `execFileSync` ∈ REAL_PATTERNS).

Snapshots committed:
- `benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/expected-pair-plan-registry.json` (19 invariants)
- `benchmark/auto-resolve/fixtures/F3-backend-contract-risk/expected-pair-plan-registry.json` (18 invariants)

Both snapshots show byte-identical SHA across two consecutive runs with `--generated-at` pinned (verified via lint Check 13).

### Deliverable 3 — `pair-plan-lint.py` + sample fixtures

`benchmark/auto-resolve/scripts/pair-plan-lint.py` (~270 lines). Validates a `pair-plan.json` against its registry. Resolves registry path via `source.canonical_id_registry_path` (override with `--registry`). Strict-keys JSON loading (rejects duplicate keys via `object_pairs_hook`). Path resolution tries (a) absolute, (b) git-root ancestor of plan dir, (c) cwd, (d) plan-dir — covers temp-file mutation tests, repo-relative refs, and absolute paths.

Sample fixtures:
- `benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/pair-plan.sample-pass.json` — exit 0, ok=true.
- `benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/pair-plan.sample-fail.json` — exit 1, error code `missing_required_id` (silent-catch invariant dropped).

Mutation tests (in-session): unresolved>0 + plan_status=final → exit 1 + `unresolved_with_final_status`; mismatched stamps → exit 1 + `stamp_sha_disagree`; spec_sha256 drift → exit 1 + `source_sha_drift`. All 4 HANDOFF lint acceptance categories satisfied.

### Deliverable 4 — `pair-plan-preflight.sh` + synthetic test bundle

`autoresearch/scripts/pair-plan-preflight.sh` (~370 lines). Stages blind input bundle (deterministic alias = sha8(fixture+run_id)), generates registry via D2, produces solo + pair plans via inline Python stubs (dry-run only in iter-0022; `--no-dry-run` exits 65), lints both, computes `verdict.json` with inline schema validation. Output dir layout matches HANDOFF.md:280 spec.

Solo stub: accepts every expected.json-derived invariant + half of oracle-derived (deterministic by even-index sort), drops the rest into `unresolved[]` with `plan_status: "draft"`. Pair stub: accepts every invariant, `plan_status: "final"`, both stamps sign matching canonical pre-stamp sha. Verdict policy: `advance` iff both lints pass AND pair captures every required id AND lift > 0.

Synthetic test bundle: `autoresearch/scripts/test-fixtures/synthetic-preflight/{spec.md, expected.json, metadata.json, task.txt}` — minimal fixture (1 forbidden_pattern, 1 verification_command, 0 oracle entries). Preflight runs end-to-end against it without any provider/model subprocess.

End-to-end smoke (in-session):
- Synthetic: `verdict: "abort"` (no oracle entries → lift 0) — correct semantics.
- F2: `verdict: "advance"`, `pair_minus_solo_lift: 3`, `pair_caught_count: 19`, `solo_caught_count: 16`.
- F3: `verdict: "advance"`, `pair_minus_solo_lift: 3`, `pair_caught_count: 18`, `solo_caught_count: 15`.

### Deliverable 5 — `/devlyn:auto-resolve` input contract change

Per Codex R0 Round 2 critique #5 ("D5 minimality is not enough if PHASE 0 only"), the change extends across 5 files (~+50-65 lines net):

- `config/skills/devlyn:auto-resolve/SKILL.md` PHASE 0 step 1 — adds `--plan-path <path>` flag and JSON-payload form `{spec_path, plan_path}`.
- `config/skills/devlyn:auto-resolve/SKILL.md` PHASE 0 step 3 — initializes `state.plan = {mode, path, registry_path, lint_at}`.
- `config/skills/devlyn:auto-resolve/SKILL.md` PHASE 0 new step 4.5 — runs `pair-plan-lint.py` when `state.plan.mode == "pair"`; failure → terminal `BLOCKED:plan-invalid` (no fallback to legacy_none).
- `config/skills/devlyn:auto-resolve/references/pipeline-state.md` — adds `plan` field to canonical schema + new `### Plan` semantics section. Registered in lint Check 6 (Codex R0 Round 2 critique #2 — file was edited but not in critical-path mirror list; if the runtime arm read `.claude/skills/.../pipeline-state.md` it would silently miss the new field. Now mirrored and gated).
- `config/skills/devlyn:auto-resolve/references/phases/phase-{1-build,2-evaluate,3-critic}.md` — one `<plan_invariants>` block each. BUILD treats `accepted_invariants[].operational_check` as binding constraints; EVAL audits against each entry and emits findings (`criterion_ref = id`, severity from invariant); CRITIC enumerates every accepted_invariant id and confirms upheld-in-diff or surfaces a finding.

`legacy_none` invocation contract is unchanged: any string-form `<pipeline_config>` (the existing 9-fixture suite shape) sets `state.plan.mode = "legacy_none"` and the new step 4.5 + per-phase `<plan_invariants>` blocks are explicit no-ops. No regression risk for the legacy hot path.

Metric tagging: per-arm scores and `--perf` artifacts MUST stamp `plan_mode = state.plan.mode` so iter-0023 aggregation never mixes `pair` runs with `legacy_none` runs (measurement integrity per HANDOFF acceptance).

## Findings (what was actually built)

**Files added — 13 in `config/`+`benchmark/`+`autoresearch/` (plus 2 mirror copies under `.claude/skills/`)**
- `config/skills/_shared/pair-plan-schema.md` (+ mirror under `.claude/skills/_shared/pair-plan-schema.md`)
- `benchmark/auto-resolve/scripts/pair-plan-idgen.py`
- `benchmark/auto-resolve/scripts/pair-plan-lint.py`
- `benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/expected-pair-plan-registry.json` (19 invariants)
- `benchmark/auto-resolve/fixtures/F3-backend-contract-risk/expected-pair-plan-registry.json` (18 invariants)
- `benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/pair-plan.sample-pass.json`
- `benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/pair-plan.sample-fail.json`
- `autoresearch/scripts/pair-plan-preflight.sh`
- `autoresearch/scripts/test-fixtures/synthetic-preflight/spec.md`
- `autoresearch/scripts/test-fixtures/synthetic-preflight/expected.json`
- `autoresearch/scripts/test-fixtures/synthetic-preflight/metadata.json`
- `autoresearch/scripts/test-fixtures/synthetic-preflight/task.txt`
- `autoresearch/iterations/0022-pair-plan-infrastructure.md` (this file)

**Files modified — 12 in source tree (plus 6 mirror copies under `.claude/skills/`)**
- `.gitignore` — added `__pycache__/` + `*.pyc` patterns (Python bytecode caches regenerated by idgen / lint / preflight; previously untracked, would noise commits per Codex R-final P2 catch)
- `benchmark/auto-resolve/scripts/oracle-test-fidelity.py` — `--list-categories` flag + 4-category enum
- `benchmark/auto-resolve/scripts/oracle-scope-tier-a.py` — `--list-categories` flag + 2-category enum
- `benchmark/auto-resolve/scripts/oracle-scope-tier-b.py` — `--list-categories` flag + 1-category enum
- `benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/metadata.json` — `pair_plan_oracle_categories` (7 entries)
- `benchmark/auto-resolve/fixtures/F3-backend-contract-risk/metadata.json` — `pair_plan_oracle_categories` (7 entries)
- `config/skills/devlyn:auto-resolve/SKILL.md` — PHASE 0 step 1 (`--plan-path` flag), step 3 (state.plan init), new step 4.5 (Plan validate)
- `config/skills/devlyn:auto-resolve/references/pipeline-state.md` — `plan` field + new `### Plan` semantics section
- `config/skills/devlyn:auto-resolve/references/phases/phase-1-build.md` — `<plan_invariants>` block
- `config/skills/devlyn:auto-resolve/references/phases/phase-2-evaluate.md` — `<plan_invariants>` block
- `config/skills/devlyn:auto-resolve/references/phases/phase-3-critic.md` — `<plan_invariants>` block
- `scripts/lint-skills.sh` — Check 6 adds `_shared/pair-plan-schema.md` + `pipeline-state.md` to mirror list; new Check 13 (idgen determinism)

Mirror copies under `.claude/skills/`: `_shared/pair-plan-schema.md` (new) + `devlyn:auto-resolve/SKILL.md` + `references/pipeline-state.md` + `references/phases/phase-{1-build,2-evaluate,3-critic}.md` (1 new + 5 modified = 6 mirror updates total).

**Lint**: 12 + 1 = 13 checks PASS post-mirror.

**Path-trap acceptance test (Codex R0v2 confirmed mandatory)**: in-process `builtins.open` and `os.open` wrappers raise `AssertionError` on `/results/` paths. Verified at runtime with both legitimate (passes) and forbidden (asserts) paths.

## What this iter unlocks

iter-0023 measurement pilot. Specifically:

1. **Negative-screen step**: iter-0023 runs `pair-plan-preflight.sh` (non-dry-run mode — to be added in iter-0023) against F2 + F3 with real Claude + Codex draft + merge rounds. The dry-run stubs from iter-0022 will be swapped for `claude -p` and `codex-monitored.sh` invocations behind the same orchestrator skeleton. Pair plan must capture every must-hit canonical ID for both fixtures or the preflight FAILs with verdict `plan_omission`.

2. **Measurement pilot**: if preflight PASSes, iter-0023 runs Arm A (control: solo PLAN + Codex BUILD + solo CRITIC + solo EVAL on F2 + F3) vs Arm B (test: pair PLAN + Codex BUILD + solo CRITIC + solo EVAL). Same git baseline, same Codex BUILD invocation, same downstream phases. Only PLAN differs.

3. **Pre-registered acceptance** (HANDOFF.md:359-362; do not edit during iter-0023 execution):
   - Arm B beats Arm A by ≥ +5 on judge-axis-sum on at least one of {F2, F3}, AND no fixture regresses by > -3.
   - Arm B has 0 forbidden_pattern DQ on F2 (the iter-0020 silent-catch failure must not recur).
   - Arm B has 0 mock-swap oracle hits on F3 (the iter-0020 test-fidelity failure must not recur).

4. **Outcome attribution labels** (pre-registered): `plan_omission` (preflight FAIL), `plan_capture_no_lift` (preflight PASS but Arm B ≤ Arm A — pair PLAN wrote IDs but Codex BUILD violated anyway → confirms BUILD has constrained-judgment latitude), `plan_capture_with_lift` (preflight PASS + Arm B > Arm A — PLAN-pair architecture validated for next-iter L2 ship discussion).

iter-0023 BLOCKED until the 7-item HANDOFF.md:340-346 checklist clears against this iter's commit.

## Principles check

### Pre-flight 0 — not score-chasing
**Status: ✅ PASS.** Removes the explicit go/no-go decision for iter-0023 (does PLAN-pair architecture causally rescue Codex BUILD on iter-0020 failure classes?). No real provider/model invocations, no judge change, no fixture set change.

### 1. No overengineering
✅ PASS. Each deliverable cites the exact HANDOFF acceptance gate it closes. No speculative abstractions: oracle category enum reuses the existing `type` enum (umbrella `tier-a-violation` instead of 5-way split per Codex R0 Q1); registry locator field added rather than synthesizing path from hash (Codex R0 Round 2 #1); `oracle_contract_sha256` dropped to avoid duplicating `canonical_id_registry_sha256` (subtractive-first wins). D5 minimum across 5 files documented as the smallest set that makes pair invariants binding rather than validated-then-ignored (Codex R0v2 #5).

### 2. No guesswork
✅ PASS. H1-H5 hypotheses all stated with predicted direction before implementation. Each acceptance gate has a concrete file/SHA/exit-code check. Lint Check 13 mechanically enforces idgen determinism going forward; no "I tested it once and it seemed deterministic" hand-waving.

### 3. No workaround
✅ PASS. No `any`, no silent catches, no hardcoded values. Path-trap on `/results/` is a defensive write of a load-bearing invariant, NOT a workaround for a shaky upstream contract: it backs the HANDOFF rule that registries derive only from authoritative sources. The single intentional exception (synthetic preflight returning `abort` — "fixture has 0 oracle entries → no lift possible") is the correct semantic, not a fallback.

### 4. Worldclass production-ready
✅ PASS. iter-0022 ships zero variant-arm CRITICAL/HIGH (no real arm runs this iter; the contract-text changes preserve `legacy_none` behavior unchanged). Lint passes 13/13. The path-trap defends iter-0023 measurement integrity against a real attack path (registry contamination from prior iter results).

### 5. Best practice
✅ PASS. Idiomatic Python (argparse with default-None + post-validation; `pathlib.Path`; `subprocess.run(check=True)`; `json.dumps(sort_keys=True)`; `hashlib.sha256` raw bytes; `copy.deepcopy` before canonical mutation). Idiomatic bash (`set -euo pipefail`, `trap`, single-quoted heredocs for embedded Python, no piped wrappers per CLAUDE.md). No hand-rolled regex slugger when a single `re.sub` does it; no manual JSON canonicalization beyond the documented compact form.

### 6. Layer-cost-justified
✅ PASS. iter-0022 is iteration-loop infrastructure (R0 design pair-review + R1 ship-gate review), not auto-resolve hot-path code. The pair-review cost (R0: 421s xhigh ~150k tokens; R0v2: 205s xhigh ~98k tokens) is amortized over iter-0023+ measurement runs that affect every future PLAN-pair decision. The L2-product surface itself remains gated; iter-0022 only builds the substrate, with `--no-dry-run` deliberately disabled until iter-0023.

### 7. Mission-bound
✅ PASS. Serves Mission 1 gate 1 indirectly via iter-0023 measurement. Mission 1 hard NOs untouched: no worktree, no parallel-fleet, no resource-lease, no run-scoped state migration, no queue metrics, no qwen/gemma cross-vendor, no aggregate-margin chasing. User adjudicated 2026-04-29 that the multi-agent-coordination textual conflict in Codex R0 critique #1 is out-of-band ("Mission 내용은 무시. 그건 나중에 미래에 할일.") — iter-0022 writes orchestration code without executing real model coordination this iter, so the spirit of the rule is preserved.

## Codex pair-review trail (this iter)

### R0 — design draft (2026-04-29, ~150k tokens xhigh, 421s)
Verdict: **NOT CONVERGED.** 5 blocking critiques + Q1-Q8 answers.
- #1 Mission-scope conflict surfaced for user adjudication — resolved by user "Mission 내용은 무시."
- #2 F2 must include `mock-swap` (every fixture inherits `fixtures/test-repo/tests/cli.test.js` via run-fixture.sh:64 cp -R; that file uses `execFileSync` ∈ REAL_PATTERNS). Adopted.
- #3 Source SHA contract: my P4 conflated canonical-form (pair-plan stamps) with raw-bytes (file-content shas). HANDOFF :217 vs :257 are TWO contracts. Adopted: schema doc separates them with explicit "How to compute" subsections.
- #4 P3 verification slug `index+sha8(cmd)` ignored exit_code/stdout assertions and broke on reorder. Adopted: full-object canonical hash; index in `source_ref` only. Forbidden_pattern collision handling defined now (description+files[0], `__i<index>` suffix on collision), not "if it happens later."
- #5 D5 PHASE-0-only edit leaves plan validated-then-ignored — BUILD/EVAL/CRITIC don't read `state.plan`. Adopted: schema + 3 phase prompts + state docs all amended (~50-65 lines net across 5 files).

### R0v2 — design corrections (2026-04-29, ~98k tokens xhigh, 205s)
Verdict: **CLOSE TO CONVERGED, 2 remaining gaps.**
- Gap 1: registry locator underspecified — my P4-revised had only `canonical_id_registry_sha256` (a hash, not a pointer). Fixed: schema doc adds `source.canonical_id_registry_path`; lint resolves registry from that field with `--registry` override. Naming standardized on `canonical_id_registry.json` everywhere (HANDOFF.md:280's `canonical-ids.json` deprecated; schema doc explicitly notes this).
- Gap 2: D5 edits `pipeline-state.md` but Check 6's critical-path mirror list omitted it. Fixed: added to lint-skills.sh:130.
- Side question (user-asked, parked): "specific implementation missions" benchmark — wait until Mission 1 closes. RUBRIC.md:3 freeze contract makes mid-Mission fixture-set changes invalid for L1-L0 calibration. Backlog: Mission-1.5 candidate when L1 stabilizes at +5+ floor.

R0v2 declared close enough to converged that adopting both gaps in-place + proceeding to implementation was the right move (diminishing returns from another R0 round). R1 below covers ship-gate diff review.

### R1 — ship-gate diff review (2026-04-29, ~161k tokens xhigh, 489s)
Verdict: **NOT CONVERGED**, 5 blocking + 3 polish, all adopted.

- B1 — idgen path-trap blocked own writes (over-broad). Fixed by gating trap on read-mode `open()` / read-flag `os.open()`; writes to `/results/` are legitimate (preflight output) and now pass.
- B2 — pair-plan-lint shallow on `accepted_invariants[]` shape. Fixed by new `check_accepted_invariants_shape` enforcing `id, source_refs, operational_check, authority`.
- B3 — `plan_status` not enum-validated; arbitrary strings passed. Fixed by `PLAN_STATUS_VALID = {"final", "blocked", "draft"}` enum check (and `PLANNING_MODE_VALID` for symmetry).
- B4 — phase prompt severity contract conflated registry severity (`disqualifier|hard|flag|warn`) with findings severity (`CRITICAL|HIGH|MEDIUM|LOW`). Fixed by explicit decoupling in phase-2-evaluate.md / phase-3-critic.md and a new "Severity decoupling (registry vs findings)" section in pair-plan-schema.md.
- B5 — lint contradicted schema doc on registry shape (sort + unknown-fields). Fixed by new `check_registry_shape` enforcing both rules.
- P1 — naming claim too broad ("canonical_id_registry.json everywhere"). Fixed in schema doc to distinguish runtime artifact name from committed snapshot name.
- P2 — iter file file counts stale. Fixed (this section).
- P3 — preflight verdict validator KeyError on missing `verdict` field. Fixed via `verdict_doc.get("verdict")`.

### R-final — R1 absorption verification (2026-04-29, ~77k tokens xhigh, 160s)
Verdict: **7/8 confirmed, 1 falsified.** P2 caught a residual `__pycache__/pair-plan-idgen.cpython-314.pyc` artifact that got regenerated when lint Check 13 ran idgen twice; the iter file's "13 added" count was correct only after pycache removal. Adopted: added `__pycache__/` + `*.pyc` to `.gitignore`, removed stray pycache directory, and updated iter file modified-count to include `.gitignore`. Worktree now clean: 12 tracked-file mods + 9 untracked entries (which expand to 13 newly-added files when `autoresearch/scripts/` and `synthetic-preflight/` directories are committed).

## Drift check (산으로?)

- **Removes a real user failure?** No, but unblocks the explicit go/no-go decision for iter-0023 (PLAN-pair architecture viability). The user-visible failure being attacked is the iter-0020 Codex BUILD failure class (silent-catch DQ on F2, mock-swap on F3). iter-0023 resolves whether pair PLAN rescues that — iter-0022 makes that resolution measurable.
- **Expands scope beyond infrastructure?** No. iter-0022 ships zero behavior change for `legacy_none` invocations (the entire current 9-fixture suite). The new pair-mode path is opt-in via `--plan-path`. The `--no-dry-run` switch on the preflight orchestrator is explicitly refused this iter.
- **Sets up a multi-iter measurement chain?** Yes, intentionally. iter-0022 is the LAST attribution-infrastructure iter before behavior change (PRINCIPLES.md:22). iter-0023 IS the behavior change.
- **"While I'm here" cross-mission additions?** None. F2/F3 `pair_plan_oracle_categories` field added to existing `metadata.json` only — fixture metadata enrichment, not a new fixture, not a scoring change (RUBRIC.md:3 freeze respected).

## Cumulative lessons

1. **Pair-review IS the work.** Codex R0 caught 5 load-bearing design errors I would have shipped: F2 mock-swap omission (run-fixture.sh:64 evidence I had not opened), source-SHA contract conflation (HANDOFF :217 vs :257 distinction I had blurred), verification-slug instability (reorder-broken), forbidden_pattern collision-handling deferred, D5 minimality leaving plan validated-then-ignored. Each was reasoned independently, evidence-cited by Codex, and adopted in R0v2. iter-0021's R-final fabrication-rescue lesson held: every claim demands direct file verification at citation time.

2. **Subtractive-first beat additive instinct twice this iter.** (a) Dropping `oracle_contract_sha256` rather than adding a third synonym field once `canonical_id_registry_sha256` was sufficient. (b) Choosing `metadata.json` allowlist over machine-evaluated `applies_when` predicate — the simpler explicit form survived without losing meaningful filtering.

3. **Codex's "info-positive" omission rule sharpened registry shape.** `tier-b-reachable` is reachable-via-imports = positive context, not invariant violation. Including it would have forced every plan to enumerate `tier-b-reachable` as `accepted` despite there being nothing to violate. Omitting it kept the registry semantics tight.

4. **Path-trap is an architectural assertion, not paranoia.** HANDOFF mandated it for measurement integrity; the implementation gates BOTH `builtins.open` and `os.open` (catches anything that bypasses Python file abstractions) and verifies via in-process tests that BOTH legitimate fixture paths work AND `/results/` paths assert. The cost was ~25 lines for a real attack-path defense (registry contamination from iter-0020 results that would invalidate iter-0023 measurement).

5. **Synthetic test bundle's `abort` verdict is correct semantics.** A fixture with 0 oracle entries can't show a pair-vs-solo lift because there's nothing for solo to drop. Documenting this as expected behavior (rather than tweaking the stub to produce artificial lift) preserved the verdict semantics for real fixtures (F2/F3 produce `advance` correctly).

6. **`--no-dry-run` exits 65 makes the iter-0022 / iter-0023 boundary mechanical.** Anyone trying to run real PLAN-pair calls today gets a clear exit code + message pointing to iter-0023. The contract isn't just textual — it's enforced.

## Falsification record (in-session smoke tests)

- D2 idgen `--generated-at` fixed: F2 sha = F2 sha (deterministic). F3 sha = F3 sha. ✓
- D2 path-trap: legitimate fixture path passes; `/results/` path raises AssertionError on both `open` and `os.open`. ✓
- D2 F2 registry contains silent-catch invariant: ✓ (`forbidden_pattern__silent_catch_returning_a_fallback_value_violates_no_silent_c__bin_cli_js`).
- D2 F3 registry contains mock-swap invariant: ✓ (`test-fidelity:mock-swap`).
- D3 sample-pass: exit 0, ok=true. ✓
- D3 sample-fail: exit 1, error code `missing_required_id`. ✓
- D3 unresolved-with-final mutation: exit 1, error code `unresolved_with_final_status`. ✓
- D3 stamp-mismatch mutation: exit 1, error code `stamp_sha_disagree`. ✓
- D3 spec-sha-drift mutation: exit 1, error code `source_sha_drift`. ✓
- D4 synthetic preflight: end-to-end exit 0, verdict `abort` (no oracle entries → lift 0). ✓
- D4 F2 preflight: exit 0, verdict `advance`, lift=3, both lints pass. ✓
- D4 F3 preflight: exit 0, verdict `advance`, lift=3, both lints pass. ✓
- D5 lint Check 6: source ↔ installed mirror parity for all 4 changed files + 2 new files. ✓
- Ship gate Check 13 (idgen determinism): F2 sha stable across two runs. ✓

Total: 13 acceptance gates closed. Real provider/model invocations: 0.
