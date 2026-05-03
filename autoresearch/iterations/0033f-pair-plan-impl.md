---
iter: "0033f"
title: "PLAN-pair vs solo-PLAN — implementation iter (CLOSED-DESIGN; design baseline hand-off to iter-0033g)"
status: CLOSED-DESIGN / NO IMPLEMENT
type: implementation — Phase 4 cutover gate; CLOSED as design-iter per Codex R0 + R0.5 + principles-decision pair convergence on option 2 (close + open iter-0033g with parent-memory-only architecture from line one)
shipped_commit: TBD (this closure commit)
date: 2026-05-03
mission: 1
gates: iter-0034-Phase-4-cutover (sole gate; now blocked on iter-0033g impl)
design_baseline: iterations/0033d-pair-plan-measurement.md §"CLOSURE — design-iter" §A items 1-18 PLUS this file's CLOSURE §A' items 19-20 + sub-classes (Codex R0/R0.5)
parent_design_iter: iter-0033d (Codex R0+R0.5+R0.6 + principles-decision pair → option B)
codex_r0_iter0033f: 2026-05-03 (414s, 184k tokens — NEW STRUCTURAL CLASS verdict; item 19 RESULT_DIR sidecar leak via --debug-file argv parent dir; transcript /tmp/codex-iter0033f-r0/response.log)
codex_r0_5_iter0033f: 2026-05-03 (214s, 104k tokens — NEW STRUCTURAL CLASS verdict; item 19 fix incomplete + item 20 WORK_DIR/.. stash leak; transcript /tmp/codex-iter0033f-r0.5/response.log)
codex_principles_decision: 2026-05-03 (~150s — independent verdict AGREE OPTION 2; reasoning: iter-0033b → iter-0033b' / iter-0033d → iter-0033f precedent; PRINCIPLES.md #2 "in-place re-pre-registration forbidden"; pattern-incremental fix is the asymptotic anti-pattern user explicitly forbade; transcript /tmp/codex-iter0033f-principles/response.log)
user_adjudication: 2026-05-03 — option A (block + go) on R0 (item 19); option 2 (close + open iter-0033g) on R0.5+ after asymptotic pattern materialization
revisions:
  - 2026-05-03 R0 absorption — item 19 added; Codex Q1-Q7 absorptions (later superseded by closure)
  - 2026-05-03 CLOSED-DESIGN — closure section appended; status changed; hand-off to iter-0033g
---

# iter-0033f — PLAN-pair implementation (full firewall design adopted from iter-0033d closure §A + §A' item 19)

## Why this iter exists (PRINCIPLES.md pre-flight 0)

iter-0033d (PLAN-pair measurement) closed as design-iter on 2026-05-03 after Codex R0+R0.5+R0.6 enumerated 18+ structural leak surfaces the original 3-layer firewall did not close. iter-0033f R0 (Codex, 414s, 184k tokens, 2026-05-03) found item 19 (RESULT_DIR sidecar-content leak via `--debug-file` argv parent dir) and was escalated to user per closure §D step 7 anti-asymptotic guard; user picked option A (block + go) on 2026-05-03 same day, so item 19 is now part of this iter's locked design baseline (§A' addendum below). Phase 4 cutover stays blocked on a measured PLAN-pair vs solo-PLAN comparison.

**Scope of this iter**: implement the 19-surface firewall (closure §A items 1-18 + this file's §A' item 19), then run the measurement suite. The 19 surfaces are NOT optional features — each is a ship-blocker. The deliverable is (a) the firewall, (b) the suite verdict, (c) the inference about whether PLAN-pair earns the L2 layer cost.

## §A' addendum — item 19 (RESULT_DIR sidecar leak, added 2026-05-03 post-R0)

Codex R0 found this class. iter-0033d closure §A items 3-7 anonymize the path STRINGS in `WORK_DIR`/`RESULT_DIR`/`--debug-file`/argv but do NOT scrub the SIBLING FILE CONTENTS the path points to. The leak:

- `benchmark/auto-resolve/scripts/run-fixture.sh:273` writes `PROMPT_FILE="$RESULT_DIR/input.md"` BEFORE child spawn. Prompt body contains `${ENGINE_CLAUSE}` which can be `--engine claude --pair-verify` (today's `l2_forced` arm; tomorrow's `pair_plan` arm body would carry pair-mode flags).
- `run-fixture.sh:390-398` writes `$RESULT_DIR/timing.json` BEFORE child spawn with raw `"arm": "..."` and `"work_dir": "..."` JSON fields.
- `run-fixture.sh:468-474` exec's child with `--debug-file "$RESULT_DIR/claude-debug.log"`. Child claude has the directory path in its argv → `dirname` reveals `$RESULT_DIR` → child can read `input.md` and `timing.json` siblings → child knows it's in the `pair_plan` arm.

**Mechanism fix (item 19)**: relocate sidecars OUT of `--debug-file`'s parent directory.

- New layout: `${RESULT_DIR}/claude-debug.log` is the ONLY file the child's argv-reachable parent dir contains during execution. Prompt body and timing-meta move to `${RESULT_DIR}/../sidecars-${anon}/` (sibling of debug-dir, NOT under it).
- `run-fixture.sh` PROMPT_FILE path becomes `${SIDECAR_DIR}/input.md`; timing-meta becomes `${SIDECAR_DIR}/timing.json`.
- After child exit, sidecars move INTO the result dir for archival (the leak window is only DURING child execution).
- Pre-spawn validator: `find "$(dirname "$DEBUG_FILE")" -mindepth 1 -maxdepth 1` returns ONLY `claude-debug.log` (or empty). Any other file → fail-fast with `BLOCKED:result-dir-sidecar-leak`.

**Threat model**: child argv-reachable filesystem (already covered by §A items 3-7 path anon, but extended here to directory contents).

## Mission 1 service (PRINCIPLES.md #7)

Single-task scope (one fixture at a time, no parallel-fleet). Mission 1 hard NOs untouched. Anonymized `WORK_DIR`/`RESULT_DIR` + sidecar relocation are the only structural changes to the bench substrate; do NOT introduce a worktree-per-task model.

## Hypothesis (NEW — cannot recycle iter-0033d verbatim per PRINCIPLES #2)

Given the 19-surface firewall fully implemented (anon `WORK_DIR`/`RESULT_DIR`/`--debug-file` + scrubbed `pipeline.state.json` + cleansed `SKILL.md` + standalone `validate-plan.py` + IMPLEMENT-prompt persistence + archive lifecycle stash + expanded lint Check 15 + byte-identical `.claude/settings.json` + early-stop round-cap telemetry + **§A' item 19: RESULT_DIR sidecars relocated outside `--debug-file` parent dir**), PLAN-pair (Claude proposer + Codex critic, structurally firewalled from IMPLEMENT subagent) on the 6-fixture pair-eligible suite `{F2, F3, F4, F6, F7, F9}` produces:

- **(a) Quality lift**: `(pair_plan − solo_plan) ≥ +5` judge-score on ≥50% of fixtures.
- **(b) Wall efficiency**: per-fixture `pair_plan_wall / solo_plan_wall ≤ 2.0×` (≤ 3.0× ceiling only for fixtures with categorical rescue).
- **(c) Firewall holds**: `validate-plan.py` + Gate 8 expanded scan find ZERO IMPLEMENT-visible pair-mode signal across all 12 runs (6 fixtures × 2 arms).
- **(d) Hard-floor**: zero new HIGH/CRITICAL `design.*`/`security.*` findings on `pair_plan` vs previously-clean `solo_plan`.
- **(e) No regression**: per-fixture `(pair_plan − solo_plan) ≥ −3` axes (Gate 2).
- **(f) Round-cap discipline**: per-round telemetry present + `BLOCKED:plan-pair-stuck` when round N findings byte-equal N−1 (Gate 6).

**Falsification → Phase 4 decision mapping** (exhaustive over the (a-f) outcome space):

| Outcome | Phase 4 decision | Rationale |
|---|---|---|
| (a)P (b)P (c)P (d)P (e)P (f)P | SHIP PLAN-pair | hypothesis confirmed end-to-end |
| (a)P (c)F | SHIP solo only + new firewall iter | lift attributable to leak; mis-attribution |
| (a)P (d)F | BLOCK Phase 4 + follow-up regression-source iter | lift exists but introduces hard-floor regression |
| (a)F (b)P (c)P (d)P (e)P (f)P | SHIP solo only + L2-PLAN labeled research-only | solo PLAN sufficient; L2 doesn't earn layer cost |
| (a)F (c)F | SHIP solo only + new firewall iter | lift never measured cleanly; redo |
| (a)F (d)F | SHIP solo only + new regression-source iter | pair fails on both axes; investigate before next |
| (e)F (any) | SHIP solo only + ROOT-CAUSE iter | regression on previously-clean fixture is a hard veto |
| (b)F (no categorical rescue) | SHIP solo only | wall over-runs L2 layer-cost budget |
| (b)F (with categorical rescue ≤ 3.0×) | conditional SHIP — categorical-rescue bucket only | layer-cost justified for the rescue path only |
| (f)F | BLOCK Phase 4 + round-cap fix iter | round-cap mechanism broken; can't trust pair telemetry |

(Gate 7 `attribution causality` is data-gathering — does not change Phase 4 decision; informs iter-0033g+ design space.)

### Predicted directions (PRINCIPLES #2 — filled BEFORE run)

| | Direction | Confidence | Rationale |
|---|---|---|---|
| (a) Quality lift on ≥3/6 fixtures | LIFT | LOW-MEDIUM | iter-0033c-fdfd showed `deliberation_lift` exists when leak is structurally impossible (sandbox-only F2 EACCES finding). Suggests pair-JUDGE-style critique CAN surface unique findings; PLAN-side is a different surface but the prior is positive. Counter: PLAN is upstream of evidence; Codex-critic without IMPLEMENT runtime context may produce abstract critique that doesn't translate to IMPLEMENT-improvement. |
| (b) Wall ≤ 2.0× on majority, ≤ 3.0× on outliers | YES | MEDIUM | iter-0022 PLAN-pair infra showed cap-3 round termination is rare; PLAN tokens are small vs IMPLEMENT. Per-fixture pair-PLAN wall ≈ 1.3-1.7× solo-PLAN wall typical (Codex Q4 corrected: per-fixture, NOT total-bench-diluted). |
| (c) Firewall holds (zero leak) | YES | MEDIUM | Lowered from MEDIUM-HIGH per Codex Q3 after item 19 found in R0. 19-surface enumeration is now the design-baseline — implementation closes each by mechanism. Risk = item-20+ class. Mitigation: Codex R0.5 (this round) + R-smoke + R-final all probe for new class; user-adjudication escalation if found. |
| (d) Zero new HIGH/CRITICAL on pair_plan | YES | MEDIUM | Codex critic in PLAN tends to flag missing acceptance / tighten scope, not introduce design.*/security.* problems. Risk = "over-defensive plan → over-defensive code → false-positive design findings". Gate 4 with 3-bucket carry-forward isolates `pair_sandbox_only` as LOG, not FAIL. |
| (e) No per-fixture regression ≥ −3 | YES | MEDIUM | iter-0033c L2-gated arm showed mean Δ −2.0 from leak (now firewalled); without leak, regression should narrow. |
| (f) Round-cap fires correctly | YES | MEDIUM-HIGH | Mechanism is deterministic byte-equal hash compare; failure mode is implementation bug, not behavioral. Smoke 1c (iv) probes determinism. |

## Suite (carried from iter-0033d, FROZEN)

- **Fixtures**: `{F2, F3, F4, F6, F7, F9}` (pair-eligible set, frozen from iter-0033c manifest).
- **Arms**: `solo_plan` (`--engine claude` no pair) + `pair_plan` (full firewall + Codex critic in PLAN; IMPLEMENT consumes only `.devlyn/plan.md`).
- **Same**: HEAD, env (anon `WORK_DIR` + `RESULT_DIR` + `--debug-file`), IMPLEMENT engine (Claude). Only PLAN differs.
- **Anonymization**: `anon = sha256(secret_salt + run_id + fixture + arm)[:12]`. Salt rotated per `run_id` (closure §A item 3). `solo_plan` and `pair_plan` get distinct anons under same `run_id`. `anon-map.json` written ONLY after child exit (closure §A item 5).
- **§A' item 19 sidecar relocation**: prompt + timing-meta live in `${RESULT_DIR}/../sidecars-${anon}/` during child execution; merged into result dir post-exit. `--debug-file` parent dir contains ONLY `claude-debug.log` during the run.
- **Anon collision detection**: orchestrator builds the full anon map BEFORE first child launch; if two distinct (fixture, arm) pairs collide on a 12-char hash, fail-fast and extend hash length to 16. Probability for 12 entries × 12 hex chars ≈ 7e-12, but check is cheap.

## Architecture (the 19-layer firewall — closure §A + §A' item 19)

The original 3-layer firewall (artifact split + schema separation + reserved-token validator) does NOT close the 19 surfaces. iter-0033f implements the full N-layer firewall:

1. **Live-state firewall** (§A items 1-2): pair-plan tracking moved out of `pipeline.state.json` into `.devlyn/.harness-internal/pair-plan.json`; PLAN phase fields scrubbed to canonical defaults BEFORE IMPLEMENT spawn; `SKILL.md` PHASE bodies cleansed of pair-mode mention; mechanism description in `references/pair-plan-mechanism.md` consumed ONLY by orchestrator runtime PHASE 1 prompt body.
2. **Path/env/argv firewall** (§A items 3-7 + §A' item 19): anon `WORK_DIR` + `RESULT_DIR` + `--debug-file`; out-of-tree `anon-map.json` (parent-memory only during run); byte-identical `.claude/settings.json` between arms (1-byte signal file deleted before IMPLEMENT spawn); `ps -p $CHILD_PID -o command=` post-spawn must not contain arm-name; **(item 19)** `--debug-file` parent dir contains ONLY `claude-debug.log` during child execution; sidecars relocated to `${RESULT_DIR}/../sidecars-${anon}/` and merged post-exit.
3. **Token firewall** (§A items 8-10): standalone `scripts/validate-plan.py` (deterministic schema + reserved-token blacklist + over-block exemption list); strict 3-section plan.md schema (Files to touch / Risks / Acceptance restatement; no extra H2; no triple-backtick-with-tokens; no HTML comments).
4. **Lint firewall** (§A item 11): `scripts/lint-skills.sh` Check 15 expanded to scan `SKILL.md`, all 5 phase bodies, `references/{free-form-mode,state-schema}.md`, `devlyn:ideate/SKILL.md`, `_shared/adapters/*`, `_shared/{runtime-principles,engine-preflight,codex-config}.md`, `CLAUDE.md`, `run-fixture.sh`, plus `.claude/skills/` mirror. Excluded: `_shared/pair-plan-schema.md`, `_shared/codex-monitored.sh`, `judge.sh`, `iter-0033c-compare.py`, `build-pair-eligible-manifest.py`.
5. **Persistence firewall** (§A items 12-14): orchestrator writes IMPLEMENT prompt to `.devlyn/implement.prompt.txt` BEFORE Agent spawn (Gate 8b scans it); `archive_run.py` PER_RUN_PATTERNS adds explicit (NOT recursive glob) entries `.harness-internal/pair-plan.json`, `.harness-internal/plan.debate.json`, `implement.prompt.txt`, `validate-plan.log`; pre-IMPLEMENT moves `.harness-internal/*` to OUT-OF-WORKTREE stash `${WORK_DIR}/../stash-${anon}/`, deletes in-tree dir; PHASE 6 archive moves stash → run archive. SIGINT/SIGTERM trap added so Ctrl-C mid-stash recovers cleanly (move-back if stash exists but run not archived).
6. **Cross-arm firewall** (§A items 15-18): per-round telemetry to `pair-plan.json`; early-stop when round N produces byte-identical canonical `codex_critic_finding_ids` to round N-1 (`BLOCKED:plan-pair-stuck` at round 2 instead of wasting round 3) — canonical normalization rule = `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` after stripping per-round timestamps and de-duplicating finding ids; mirrors existing `pair-plan-schema.md` canonical style + `pair-plan-lint.py:61-70` duplicate-key rejection. F9 ENGINE_CLAUSE hardcoded `--engine claude` for ideate, only resolve clause sees plan-mode signal; smokes 1a-d run in `mktemp -d` (NOT live `.devlyn/`); validate-plan.py hard-fails on full §A item 18 a-i scope.

## Method

### Pre-suite smokes 1a-d (in `mktemp -d`, gate the suite)

| smoke | what it tests | pass criterion |
|---|---|---|
| **1a** | F9 ENGINE_CLAUSE static check (closure §A item 16) | F9 ideate clause hardcoded `--engine claude`; only resolve clause sees plan-mode signal. `grep -n "ENGINE_CLAUSE" run-fixture.sh` matches expected pattern; arm-name absent from ideate clause. |
| **1b** | Codex CLI availability + monitored-shell wrapper integrity | `command -v codex` PASS; `codex-monitored.sh -s read-only "echo ok"` returns clean. Hard-fail if absent — `pair_plan` arm cannot run. |
| **1c** | validate-plan.py determinism + scope (per Codex Q2 — not only plan.md, but full §A item 18 a-i input set) | invoke against (i) clean canonical plan.md → PASS; (ii) plan.md with each §A item 8 reserved-token → FAIL with that token cited; (iii) plan.md with §A item 9 over-block tokens (`accepted_invariants`, `model_stamps`, `planning_mode`, `debate`, `critic`, `proposer`) → PASS (allow-listed); (iv) full §A item 18 a-i conditions: presence of `.devlyn/.harness-internal/`, plan.md schema, scrubbed state values, `$WORK_DIR`/`$RESULT_DIR` arm-string scan, full state.json IMPLEMENT-visible scan, IMPLEMENT prompt scan, settings.json hash match, no live anon-map, no env diff between arms — each probe independently FAIL-able; (v) Gate 6 canonical hash determinism: same finding-id list yields byte-identical hash across 100 invocations. |
| **1d** | Anon path + sidecar absence + byte-identical settings + IMPLEMENT prompt persistence + hard-cap timer (mini end-to-end on F2 only, both arms, no judge) | (i) `WORK_DIR`/`RESULT_DIR`/`--debug-file` paths contain anon hash, NOT arm name; (ii) `sha256(.claude/settings.json)` byte-identical between arms; (iii) `ps -p $CHILD_PID -o command=` post-spawn does NOT contain `solo_plan`/`pair_plan`; (iv) `.devlyn/implement.prompt.txt` present + non-empty post-spawn; (v) post-run, `.harness-internal/` archived to `runs/<run_id>/`; **(vi) §A' item 19**: `find "$(dirname "$DEBUG_FILE")" -mindepth 1 -maxdepth 1` during child execution returns ONLY `claude-debug.log`; sidecars present in `${RESULT_DIR}/../sidecars-${anon}/`; (vii) `run-iter-0033f.sh` writes start-timestamp at boot and aborts with `BLOCKED:hard-cap-exceeded` if (now − start) ≥ 24h. Smoke runs the REAL `run-fixture.sh --anon` path with `mktemp -d` as RESULT_ROOT (per Codex Q6 — no hand-built approximation). |

If any smoke fails → R-smoke with Codex (against §A + §A' as design baseline) → fix → re-run smokes. If R-smoke surfaces NEW structural class (item 20+) → escalate to user BEFORE attempting fix (closure §D step 7 — anti-asymptotic guard).

### Suite

6 fixtures × 2 arms = 12 runs, serial, on a single workstation. Same HEAD, anon paths, anon `anon-map.json` written post-child-exit. Total wall ~6h.

### Wall budget (post-R0.5; ~21h floor + 3h slack ceiling)

| stage | budget |
|---|---|
| Implementation (steps 3.1 → 3.7) including item 19 sidecar relocation + Gate 6 normalization + hard-cap timer | ~11-13h |
| Smokes 1a-d (in mktemp, real `run-fixture.sh --anon` path) | ~30 min |
| Mirror sync (`bin/devlyn.js -y`) + lint (twice — pre-smokes + post-R-smoke-fix-pre-suite) | ~30 min |
| Suite (6 fixtures × 2 arms, serial) | ~6h |
| R-final + closure write + commit | ~1.5h (includes Codex pair rounds if R-final surfaces a blocker — Codex Q5) |
| **Floor** | **~21h** |
| **Hard-cap** | **24h, mechanically enforced by `run-iter-0033f.sh` start-timestamp + abort check** |

**Hard-cap enforcement (Codex Q5)**: `run-iter-0033f.sh` writes `${ITER_RESULTS_DIR}/.iter-start-epoch` at boot. Every per-arm invocation checks `(now − start) ≥ 86400` and aborts with `BLOCKED:hard-cap-exceeded` if true. If hit, iter-0033f closes as design-iter (option B precedent) + escalate to user. Anti-asymptotic guard now mechanical, not policy-only.

## Acceptance gates (pre-registered, ALL ship-blockers cite closure §A items + §A' item 19)

| Gate | Threshold | Source / item(s) |
|---|---|---|
| **1a** | F9 ENGINE_CLAUSE smoke PASS | closure §A item 16 |
| **1b** | Codex CLI + monitored-shell smoke PASS | iter-0033c Gate 1b carry-forward |
| **1c** | validate-plan.py determinism + scope smoke PASS (probes (i)-(v)) | closure §A items 8, 9, 10, 18 |
| **1d** | Anon-path + sidecar absence + byte-identical settings + IMPLEMENT-prompt persistence + hard-cap timer smoke PASS (probes (i)-(vii)) | closure §A items 3, 4, 5, 7, 12, 14 + §A' item 19 + Codex Q5 hard-cap |
| **2. No regression vs solo_plan** | every fixture: `(pair_plan − solo_plan) ≥ −3` axes | NORTH-STAR test #6 carry-forward |
| **3. Quality lift on pair-eligible (SHIP-BLOCKER)** | `(pair_plan − solo_plan) ≥ +5` on ≥50% of fixtures (≥3/6) | iter-0033d hypothesis (a); iter-0033c Gate 3 carry-forward (promoted to ship-blocker per Codex R0.5) |
| **4. Hard-floor (3-bucket Gate 4 carry-forward)** | zero `pair_plan` disqualifier on previously-clean `solo_plan` fixtures; zero `pair_plan` CRITICAL/HIGH `design.*`/`security.*` on previously-clean `solo_plan`. **3-bucket classification**: `mechanical_failed` → FAIL; `target_env_reproduced` → FAIL; `pair_sandbox_only` → LOG (counted toward Gate 7 attribution). | PRINCIPLES #4 + iter-0033c-fdfd 3-bucket policy |
| **5. Wall efficiency** | per-fixture `pair_plan_wall / solo_plan_wall ≤ 2.0×`; `≤ 3.0×` ceiling only for fixtures with categorical rescue (pair_plan catches disqualifier solo_plan missed). | iter-0033c Gate 5 carry-forward (per-fixture wall, not phase-1-only) |
| **6. Round-cap discipline (canonical normalization rule, NEW per §A item 15 + Codex Q2)** | `pair-plan.json` per-round telemetry present on every `pair_plan` run; if round N produces canonical-byte-identical hash to N−1 (canonicalization = `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` after timestamp strip + finding-id de-dup), status MUST be `BLOCKED:plan-pair-stuck` (NOT continue to round N+1). Round-3 ceiling enforced. Suite-level: if no fixture rescued by round-3, post-suite analysis recommends lower cap to 2 in iter-0033g amendment. | closure §A item 15 + Codex Q2 normalization rule |
| **7. Attribution causality (4-class)** | per-fixture: `no_material_lift` / `implementation_confounded` / `tool_or_trigger_lift` / `deliberation_lift`. Recorded for design-space update. NOT pass/fail. | iter-0033c Gate 7 carry-forward + NORTH-STAR test #11 |
| **8. Artifact + leak contract (EXPANDED per §A items 2, 11, 12, 13, 14, 17, 18 + §A' item 19)** | (a) `pipeline.state.json` PLAN phase fields scrubbed to canonical defaults pre-IMPLEMENT; (b) `.devlyn/implement.prompt.txt` present, non-empty, scanned for ALL §A item 8 reserved tokens — ZERO matches; (c) `.harness-internal/{pair-plan.json, plan.debate.json}` archived to `runs/<run_id>/` (explicit, NOT recursive glob); (d) `validate-plan.log` archived; (e) `lint-skills.sh` Check 15 PASSES on full §A item 11 scan list (source + mirror); (f) `.claude/settings.json` SHA-256 byte-identical between arms (recorded in run manifest); (g) no live `anon-map.json` accessible to IMPLEMENT (file does not exist in WORK_DIR during run; written post-child-exit OUTSIDE WORK_DIR); (h) `ps -p $CHILD_PID -o command=` log captured post-spawn, contains NO arm-name substring; (i) full `pipeline.state.json` IMPLEMENT-visible content scan finds ZERO §A item 8 reserved tokens; **(j) §A' item 19**: `--debug-file` parent dir contains ONLY `claude-debug.log` during child execution; sidecars in `${RESULT_DIR}/../sidecars-${anon}/`, merged post-exit; **(k) §A item 2 SKILL cleanse**: `scripts/lint-skills.sh` Check 15 confirms NO §A item 8 reserved tokens in `config/skills/devlyn:resolve/SKILL.md` PHASE 0/1/2/3/4/5/6 bodies; **(l) §A item 17 mktemp**: smokes 1a-d ran from `mktemp -d` (recorded in smoke logs); **(m) §A item 14 stash existence**: pre-IMPLEMENT trace shows `${WORK_DIR}/../stash-${anon}/` exists before IMPLEMENT spawn AND is empty in-tree (`.devlyn/.harness-internal/` absent during run); **(n) §A item 18 i**: env/config diff between arms = ONLY 1-byte signal file content (deleted pre-spawn); all other env vars + config files byte-equal. | closure §A items 2, 11, 12, 13, 14, 17, 18 + §A' item 19 |

**Ship-blockers**: 1a, 1b, 1c, 1d, 2, 3, 4, 6, 8.
**Quality gates** (failure → root-cause iter, not silent skip): 5.
**Data-gathering** (no pass/fail): 7.

If ANY ship-blocker FAILS → Phase 4 ships solo-PLAN only + NORTH-STAR records L2 PLAN-pair as research-only + `--engine`/`--pair-verify` flags removed (carries iter-0033d closure policy).

## Phase 4 cutover dependency

Same as iter-0033d, gated on iter-0033f outcome:
- iter-0033f ALL ship-blockers PASS → Phase 4 ships PLAN-pair as first product L2 surface.
- ANY ship-blocker FAIL → Phase 4 ships solo-PLAN only; NORTH-STAR records L2 as research-only; `--engine` and `--pair-verify` flags removed.

## Implementation scope (this iter)

### Ships in this iter (per closure §D step 5 sequencing + Codex Q4 mirror sync correction)

1. **SKILL.md cleanse** (`config/skills/devlyn:resolve/SKILL.md`): PHASE 0/1/2/3/4/5/6 bodies free of pair-mode mention. Mechanism moved to NEW `config/skills/devlyn:resolve/references/pair-plan-mechanism.md`. (closure §A item 2)
2. **scripts/validate-plan.py** (NEW, standalone, deterministic): schema check (3 H2 sections only) + reserved-token blacklist (closure §A item 8) + over-block exemption (closure §A item 9) + full closure §A item 18 a-i hard-fail conditions + Gate 6 canonical hash function (Codex Q2). CLI accepts (a) `--plan <path>` for plan.md schema, (b) `--state <path>` for `pipeline.state.json` content scan, (c) `--prompt <path>` for `implement.prompt.txt` scan, (d) `--settings-hash <hex>` + `--reference-hash <hex>` for settings.json byte-equality, (e) `--paths <a,b,c>` for arm-string scan, (f) `--env-diff` for arm-arm env diff. (closure §A items 8, 9, 10, 18 + Codex Q2)
3. **scripts/lint-skills.sh Check 15** (NEW section, expanded scan list per closure §A item 11): scans source + mirror, exemptions list applied. (closure §A item 11)
4. **config/skills/_shared/archive_run.py**: PER_RUN_PATTERNS gains explicit entries for `.harness-internal/pair-plan.json`, `.harness-internal/plan.debate.json`, `implement.prompt.txt`, `validate-plan.log`. Stash-aware lifecycle (`${WORK_DIR}/../stash-${anon}/` → `runs/<run_id>/`). SIGINT/SIGTERM trap added: if interrupted with stash dir present but run not archived, archive-on-resume moves stash back into `.devlyn/.harness-internal/` for the resuming session to handle (Codex Q6 Ctrl-C recovery). (closure §A items 13, 14 + Codex Q6)
5. **Orchestrator (`config/skills/devlyn:resolve/SKILL.md` PHASE 2 entry mechanism + `references/phases/implement.md`)**: writes IMPLEMENT prompt to `.devlyn/implement.prompt.txt` BEFORE Agent spawn (per Codex Q4 sequencing — must come before smoke 1d). (closure §A item 12)
6. **`benchmark/auto-resolve/scripts/run-fixture.sh`**: anon `WORK_DIR`/`RESULT_DIR`/`--debug-file` (sha256 hash); byte-identical `.claude/settings.json` between arms (1-byte signal file pre-IMPLEMENT-spawn); `ps -p $CHILD_PID -o command=` post-spawn validator; F9 ENGINE_CLAUSE ideate-clause hardcoded `--engine claude`; **§A' item 19**: relocate `PROMPT_FILE` (was `$RESULT_DIR/input.md`) and `timing.json` (was `$RESULT_DIR/timing.json`) to `${RESULT_DIR}/../sidecars-${anon}/`; pre-spawn validator confirms `--debug-file` parent dir contains ONLY `claude-debug.log`; post-exit merge moves sidecars back into `$RESULT_DIR` for archival. `--anon` is mandatory for `solo_plan`/`pair_plan` arms (hard-fail if missing); legacy arms (`bare`/`variant`/`solo_claude`/`l2_gated`/`l2_forced`) keep arm-named WORK_DIR for iter-0033c re-runnability (Codex Q4). (closure §A items 3, 4, 5, 6, 7, 16 + §A' item 19)
7. **`benchmark/auto-resolve/scripts/judge.sh` + `benchmark/auto-resolve/scripts/iter-0033f-compare.py` (NEW, cites closure §D step 5 + iter-0033c-compare.py:230-255 for 3-bucket impl per Codex Q7)**: anon-aware (resolve fixture/arm via out-of-tree anon-map.json written post-child-exit). 3-bucket Gate 4 carry-forward.
8. **`benchmark/auto-resolve/scripts/run-iter-0033f.sh` (NEW, cites closure §D step 5/6 per Codex Q7)**: orchestrator + smokes 1a-d (in `mktemp -d` per closure §A item 17). R-smoke trigger if any smoke fails. **Hard-cap timer**: writes `${ITER_RESULTS_DIR}/.iter-start-epoch` at boot; per-arm wrapper aborts if `(now − start) ≥ 86400` (Codex Q5). Anon-collision detection: builds full anon map BEFORE first spawn; fail-fast on duplicate.
9. **Mirror sync sequencing (Codex Q4)**: `bin/devlyn.js -y` + `bash scripts/lint-skills.sh` runs (a) ONCE before smokes 1a-d, (b) AGAIN after any R-smoke fix BEFORE suite kickoff, (c) NEVER between suite arms (frozen).
10. **Suite execution**: 6 fixtures × 2 arms, serial, ~6h.
11. **R-final on raw numbers + closure verdict + commit**.

### Does NOT ship in this iter

- iter-0034 Phase 4 cutover (separate iter, gated on this one).
- iter-0033e PROJECT-coherence pair (separate stub, gated on this + defect-class oracle).
- F8 fixture (reporting-only, excluded from pair-eligible set).
- Pair-mode for any phase OTHER than PLAN.
- Cross-vendor adapter (pi-agent / qwen / gemma) — Block 5 future direction, not this scope.
- Deletion of `iter-0033c-compare.py` or `build-pair-eligible-manifest.py` — preserves closed-iter replay; CLAUDE.md goal-lock forbids tangential cleanup (Codex Q7).

## Codex pair-collab plan (per closure §D step 6)

- **R0** (DONE 2026-05-03, 414s, 184k tokens, output `/tmp/codex-iter0033f-r0/response.log`): NEW STRUCTURAL CLASS verdict — item 19 found. User picked option A; this revision absorbs item 19 + Codex Q1-Q7.
- **R0.5** (NEXT, this revision): Codex re-verifies item 19 fix + Q1-Q7 absorptions. Falsification ask: any item-20+ class? Are Q1-Q7 fixes complete? Output to `/tmp/codex-iter0033f-r0.5/`. Verdict: CONVERGED → step 3.1 (SKILL.md cleanse); NOT CONVERGED with revisions only → revise + re-send R0.6; NEW STRUCTURAL CLASS (item 20+) → user adjudication.
- **R0.6** (conditional): if R0.5 surfaces revisions only, NOT new class.
- **R-smoke**: after smokes 1a-d on the actual implementation. Codex reads smoke logs + validate-plan.py output; falsification ask: did any smoke pass for the wrong reason?
- **R-final**: after suite raw numbers. Codex reads compare.py output + per-fixture state.json + IMPLEMENT-prompt scans; falsification ask: is gate 3 PASS attributable to deliberation lift OR leak/confound? Is any LOG-classified Gate 4 case actually a sandbox-only false-positive?

Per `feedback_codex_collaboration_not_consult.md`: position-stating not verdict-asking; multi-round; convergence is the stop. Per `feedback_codex_cross_check.md`: reason independently first; send rich evidence + falsification ask.

## Risk register (carry-forward + new + Codex Q6 absorptions)

| Risk | Mitigation |
|---|---|
| (CARRY) Firewall leak — IMPLEMENT subagent reasons differently due to pair-mode signal | Gate 8b scans `.devlyn/implement.prompt.txt` for §A item 8 tokens; Gate 8a scrubs `pipeline.state.json`; Gate 8j scans `--debug-file` parent dir; validate-plan.py hard-fails on §A item 18 a-i. |
| (CARRY) Critic over-constrains plan → plan loses information needed for IMPLEMENT | Gate 4 catches via design.* hard-floor; Gate 7 attribution flags `tool_or_trigger_lift` vs `deliberation_lift`. |
| (CARRY) Wall blowup — pair-PLAN > 3.0× solo-PLAN with no categorical rescue | Gate 5; if exceeded, fail-fast and root-cause. |
| (CARRY) Round-cap unresolved — Codex repeats itself across rounds, wasting wall | Gate 6 canonical-byte-identical-finding-ids early-stop (closure §A item 15) with explicit normalization rule. |
| (CARRY) Codex unavailable mid-suite | Gate 1b hard-fail; do not proceed without Codex CLI. |
| (CARRY) Score regression on previously-clean fixture | Gate 4 (3-bucket); LOG/FAIL classification per fdfd policy. |
| (CARRY) Check 15 over-match (false positives on legitimate `proposer`/`critic`/`debate` content) | §A item 9 over-block exemption list applied in validate-plan.py + Check 15. |
| (NEW) Implementation slips beyond ~21h floor | **Hard-cap mechanically enforced at 24h** (`run-iter-0033f.sh` start-timestamp + per-arm abort check). If exceeded, close iter-0033f as design-iter (option B precedent) and escalate to user. Anti-asymptotic guard. |
| (NEW) Unforeseen leak surface (item 20+) discovered mid-implementation | Pause + Codex R-pause; if surface is structural class, escalate to user BEFORE drafting fix. Anti-asymptotic per closure §D step 7. |
| (NEW) `--anon` refactor breaks iter-0033c re-runnability | `--anon` is MANDATORY for new `solo_plan`/`pair_plan` arms; legacy arms (bare/variant/solo_claude/l2_gated/l2_forced) keep arm-named WORK_DIR. Smoke 1d covers anon-mode; existing iter-0033c re-runs use legacy mode. (Codex Q4) |
| (NEW) Mirror sync drift between source and `.claude/skills/` post-impl | Mirror+lint runs (a) before smokes, (b) after R-smoke fix before suite. Lint Check 6 (existing) catches divergence. (Codex Q4) |
| (NEW) `.harness-internal/` stash lifecycle race — child writes during pre-IMPLEMENT scrub window OR Ctrl-C between stash + archive | Pre-IMPLEMENT step uses `mv` (atomic on same filesystem), not `cp`+`rm`. Stash dir is `${WORK_DIR}/../stash-${anon}/` — outside WORK_DIR. `archive_run.py` SIGINT/SIGTERM trap moves stash back into `.devlyn/.harness-internal/` if interrupted before archive. Validator in IMPLEMENT prompt scan also catches if missed. (Codex Q6) |
| (NEW, BYPASS-PROTECTED) Validate-plan.py false-positive on legitimate plan content (e.g. fixture spec mentions `pair`) | §A item 9 over-block exemption + per-fixture override file `benchmark/auto-resolve/fixtures/<F>/validate-plan.allow.json` if a fixture genuinely needs a normally-blocked token. **Bypass guard (Codex Q7)**: any override is reported as residual inference impact in Gate 7 attribution + flagged in `compare.py` output as `validate-plan.allow.json:<F>` — NOT a silent allow. Smoke 1c probes (i)-(v) to confirm scope. |
| (NEW Codex Q6) Codex critic nondeterminism across reruns | Persist every round prompt + output in `.harness-internal/plan.debate.json` (round_num, prompt_sha256, response_sha256, finding_ids, model, cli_version, reasoning_effort). Rerun-interpretation policy: same input + nondeterministic output = log + treat as variance, NOT firewall failure. R-final ask: did pair_plan arms with rerun show variance > +/-2 score? If yes, iter-0033g caveats. |
| (NEW Codex Q6) mktemp smoke 1d drift from production WORK_DIR shape | Smoke 1d invokes the REAL `run-fixture.sh --anon` path with `mktemp -d` as RESULT_ROOT (not a hand-built approximation). Smoke logs record actual paths used so post-hoc shape comparison is possible. |
| (NEW Codex Q6) Anon hash collision across (fixture, arm) pairs in same run | Orchestrator builds full 12-entry anon map BEFORE first child spawn; fail-fast on duplicate; auto-extend hash to 16 hex chars on retry. Probability for 12 entries × 12 hex chars ≈ 7e-12; check is ~10ms. |

## Principles check

- **#0 pre-flight**: ✅ closes user-visible failure (Phase 4 cutover with unproven L2 surface). Closes iter-0033d "is firewall ready for measurement" as YES (firewall is implemented; measurement runs).
- **#1 no overengineering / Subtractive-first**: ⚠️ now-substantial implementation (~12h post-item-19, multiple files) BUT each piece is justified by an iter-0033d §A item OR §A' item 19 OR Codex R0 absorption (no speculative additions). Subtractive-first applied: SKILL.md PHASE bodies SHRINK by cleanse; mechanism description moves to single new reference file (net surface ≈ flat); legacy arm-named WORK_DIR pattern preserved (per Codex Q4 backward compat). Did NOT delete iter-0033c-compare.py / build-pair-eligible-manifest.py — Codex Q7 explicitly rejects as tangential cleanup.
- **#2 no guesswork**: ✅ predictions filled BEFORE run (above table); gates pre-registered with thresholds + cite §A items + §A' item 19. NEW hypothesis (not recycled from iter-0033d). 4-falsification table replaced with exhaustive Phase-4-decision mapping (Codex Q3).
- **#3 no workaround**: ✅ structural firewall (anon paths + scrubbed state + standalone validator + IMPLEMENT prompt persistence + archive lifecycle stash + sidecar relocation); not silent strip / not config-level skip. validate-plan.allow.json bypass-guarded, NOT silent allow (Codex Q7).
- **#4 worldclass production-ready**: ✅ Gate 4 with 3-bucket carry-forward enforces zero new HIGH/CRITICAL on `pair_plan` arm vs previously-clean `solo_plan`.
- **#5 best practice**: enforced via existing CRITIC findings in VERIFY (carryover) + structural validator at PHASE 2 entry.
- **#6 layer-cost-justified**: ✅ Gates 5, 6 measure wall budget; Gate 3 measures quality lift (ship-blocker). ~21h infra cost for L2 layer is itself a layer-cost data point — if L2 fails Gate 3, layer-cost argument falsifies and Phase 4 ships solo-only.
- **#7 mission-bound**: ✅ Mission 1 single-task scope. Anonymized WORK_DIR is bench-substrate change ONLY; no parallel-fleet, no worktree-per-task model.

## Why this is not score-chasing (PRINCIPLES.md #0)

This iter measures whether multi-LLM pair-mode in PLAN improves IMPLEMENT outcomes vs solo, AFTER the firewall closes the leak surfaces that contaminated iter-0033c attribution. The measurement is the deliverable. Benchmark margin movement is downstream of the measurement, not the goal. The Phase-4-decision mapping above explicitly enumerates outcomes that REJECT the L2 PLAN-pair surface — score-chasing is incompatible with pre-registered REJECT cases.

## Deliverable execution order

1. **Pre-registration drafted** (this file). ✅
2. **Codex R0** on this pre-reg vs closure §A. Verdict: NEW STRUCTURAL CLASS (item 19). User adjudication option A. ✅
3. **Pre-reg revised** with item 19 + Codex Q1-Q7 absorptions (this revision). ✅
4. **Codex R0.5** on revised pre-reg. Verdict: CONVERGED → step 5; revisions-only → R0.6; NEW item-20+ class → user adjudication.
5. **Implementation steps 3.1 → 3.7** per §"Ships in this iter" sequencing. One-line phase report per step.
6. **Mirror sync** (`bin/devlyn.js -y`) + lint (`bash scripts/lint-skills.sh`) BEFORE smokes.
7. **Smokes 1a-d** in `mktemp -d`. Any fail → R-smoke + fix + re-mirror+lint + re-run smokes.
8. **Suite** (6 fixtures × 2 arms, serial, ~6h). Run via `run_in_background` Bash with HANDOFF state continuity.
9. **Compare** (`iter-0033f-compare.py`) → emit per-fixture verdicts + 3-bucket Gate 4 + Gate 7 attribution.
10. **R-final** on raw numbers. Falsification ask per Codex pair-collab plan above.
11. **Closure verdict** appended to this file. Update `HANDOFF.md` + `DECISIONS.md`.
12. **Commit** per repo conventions. iter-0034 Phase 4 cutover unblocked (or recorded research-only) per ship-blocker outcome.

## Pointers

- **Design baseline (load-bearing)**: `iterations/0033d-pair-plan-measurement.md` § "CLOSURE — design-iter, no implementation, hand-off to iter-0033f", especially §A items 1-18.
- **Design baseline addendum**: this file's "§A' addendum — item 19 (RESULT_DIR sidecar leak)" section + CLOSURE §A' items 19-20 + sub-classes below.
- **Codex round transcripts** (in /tmp at iter-0033d close, may be purged): `/tmp/codex-iter0033d-r0/`. Distillation in iter-0033d §A is canonical.
- **Codex R0 transcript** (this iter): `/tmp/codex-iter0033f-r0/{prompt.md, response.log}` — 414s, 184k tokens, NEW STRUCTURAL CLASS verdict at line 5351.
- **Codex R0.5 transcript**: `/tmp/codex-iter0033f-r0.5/{prompt.md, response.log}` — 214s, 104k tokens, NEW STRUCTURAL CLASS verdict at line 2290.
- **Codex principles-decision transcript**: `/tmp/codex-iter0033f-principles/{prompt.md, response.log}` — AGREE OPTION 2 verdict at line 3132.
- **Sibling stub** (PROJECT-coherence pair, separate measurement): `iterations/0033e-project-coherence-stub.md`.
- **Successor iter**: `iterations/0033g-pair-plan-impl-pmo.md` (parent-memory-only architecture from line one).

---

## CLOSURE — design-iter, no implementation, hand-off to iter-0033g (2026-05-03)

This iter began as the implementation iter for PLAN-pair (consuming iter-0033d closure §A as locked design baseline). After Codex R0 found item 19 (RESULT_DIR sidecar leak), user adjudicated option A (block + go), and the pre-reg was revised to absorb item 19 + Codex R0 Q1-Q7. R0.5 then found (a) item 19 fix incomplete (sidecar dir name still derivable from `--debug-file` parent + `transcript.txt` not relocated), (b) NEW item 20 (WORK_DIR/.. stash leak — child can `cd ..` from `$WORK_DIR` and read stash dir contents).

Pattern recognition: each Codex round produces ≥1 new structural class. This is the iter-0033d asymptotic pattern user explicitly forbade ("iter-0033d처럼 asymptotic 패턴 빠지지 말 것"). Claude+Codex independent principles-decision pair (option 1 vs option 2 vs option 3) BOTH converged on option 2 (close + open iter-0033g with parent-memory-only architecture from line one). User adjudicated option 2.

### Why CLOSED-DESIGN, not in-place re-pre-registration

PRINCIPLES.md #2 forbids retroactive prediction edits. This iter's pre-reg was already revised once after R0 (item 19 absorbed) and would need a second materially-different revision after R0.5 (parent-memory-only architecture replacing the sidecar/stash design — not a small revision). iter-0033b → iter-0033b' and iter-0033d → iter-0033f precedents show the clean pattern: close the original at its own scope, open the new one with fresh prereg. Same situation, same answer.

### A'. Leak surfaces enumerated post iter-0033d closure (cumulative R0 + R0.5)

The iter-0033d closure §A items 1-18 enumerate the surfaces the original 3-layer firewall did NOT close. iter-0033f's revised "anon paths + sidecar relocation" architecture closes 1-18 but did NOT close the following additional classes (iter-0033g must close all of these from line one):

#### Path-derivable disk artifacts during child execution (root cause: any disk path the child can derive from its env/argv/cwd is a leak surface)

**19. `RESULT_DIR` sidecar files reachable via `dirname --debug-file`** (Codex R0 2026-05-03). `benchmark/auto-resolve/scripts/run-fixture.sh:273` writes `PROMPT_FILE="$RESULT_DIR/input.md"` (containing arm-aware ENGINE_CLAUSE) BEFORE child spawn. `:390-398` writes `$RESULT_DIR/timing.json` with raw `"arm"` and `"work_dir"` JSON. `:468-474` exec's child with `--debug-file "$RESULT_DIR/claude-debug.log"`. Child has the directory in argv → `dirname` reveals `$RESULT_DIR` → siblings readable. Iter-0033f revised plan tried "relocate sidecars to `${RESULT_DIR}/../sidecars-${anon}/`" but R0.5 found this still parent-reachable (one `dirname` + `cd ..` step). FIX DIRECTION (iter-0033g): pair-mode artifacts NEVER on disk during child execution; held in parent bash variables; written to disk POST-CHILD-REAP into a path the child has no env/argv/derive-from-env path to.

**20. `WORK_DIR/..` stash leak — child can `cd ..` from inside `$WORK_DIR`** (Codex R0.5 2026-05-03). iter-0033f revised plan moved `.harness-internal/*` to `${WORK_DIR}/../stash-${anon}/`. But child starts INSIDE `$WORK_DIR` (`run-fixture.sh:449`) and ALSO receives `BENCH_WORKDIR="$WORK_DIR"` env (`:467`), so `cd ..; ls; cat stash-*/pair-plan.json` reveals stash contents. The stash contains the very pair-mode telemetry the firewall is hiding. FIX DIRECTION (iter-0033g): same as item 19 — parent-memory-only during child execution.

#### Codex Q2 sub-classes flagged for iter-0033g architecture (must close from line one)

**21. `transcript.txt` (live child stdout/stderr in `$RESULT_DIR`)** (Codex R0.5 Q1). `run-fixture.sh:475` redirects child stdout/stderr into `$RESULT_DIR/transcript.txt` during execution. Child cannot read its own stdout normally, but if the child introspects via `/dev/fd/1` → `readlink` → derived path, it can read prior transcript content. Probability: low for normal claude behavior, BUT iter-0033g must address by either (a) redirecting transcript outside child-derivable paths, OR (b) accepting as residual with documented inference impact in pre-reg.

**22. `claude-debug.log` content leakage** (Codex Q2). The debug log itself is downstream of the child's own behavior, but if claude logs its own prompt body, the prompt's ENGINE_CLAUSE ends up readable mid-execution. iter-0033g pre-reg must explicitly assert: debug log content scanned post-run for arm-revealing tokens (already partly covered by Gate 8b on `implement.prompt.txt`, but `claude-debug.log` is a distinct surface).

**23. Process-group descendants persist after parent `wait`** (Codex Q2). The current runner backgrounds child in its own process group (`set -m` + `exec`) and waits on `CHILD_PID`. If child spawns descendants that detach + outlive parent's `wait`, post-exit merge of sidecars into result dir could happen WHILE descendants are still alive — reopening the leak window. iter-0033g must enforce: post-reap merge only after process-group quiescence confirmed (`pkill -0 -- -PGID` returns no processes).

**24. `/tmp/.../${run_id}/${anon}` paths where `run_id` or `anon` is derivable from child's env/argv before child quiescence** (Codex Q2). Even moving artifacts to `/tmp` doesn't help if the path uses `run_id` (in `BENCH_WORKDIR=bench-{run_id}-{anon}`) or `anon` (in `--debug-file $RESULT_DIR/claude-debug.log` where RESULT_DIR contains anon). Child can construct the path from its own env. FIX DIRECTION: artifact storage path uses a SECRET (random per-run UUID, NOT derived from anon/run_id, NEVER passed to child).

### B. Convergence record

| round | wall | tokens | verdict | new classes |
|---|---|---|---|---|
| R0 | 414s | 184k | NEW STRUCTURAL CLASS | item 19 |
| R0.5 | 214s | 104k | NEW STRUCTURAL CLASS | item 19 fix incomplete + item 20 |
| principles-decision | ~150s | 130k | AGREE OPTION 2 | n/a — process verdict |

Pattern: 1 new class per round (decreasing from iter-0033d's 6+5+7, but qualitatively same — every Codex pass finds a class iter-0033f's architecture cannot close). User direction binding: "iter-0033d처럼 asymptotic 패턴 빠지지 말 것".

### C. Hand-off contract for iter-0033g-pair-plan-impl-pmo

iter-0033g MUST:

1. Pre-register a NEW hypothesis (cannot recycle iter-0033d / iter-0033f hypotheses verbatim — the threat model is materially different post-classes-19-24 enumeration).
2. **Architecture: parent-memory-only during child execution** — pair-mode artifacts (pair-plan.json, plan.debate.json, sidecars, anon-map, etc.) live in PARENT bash variables ONLY while child is alive. Disk write happens ONLY after child reap + process-group quiescence confirmed (`pkill -0 -- -PGID` empty). Disk path uses parent-only secret UUID (random `uuidgen`, NEVER passed to child env or argv).
3. Pre-register NEW gates that incorporate iter-0033d §A items 1-18 AND iter-0033f §A' items 19-24 as ship-blockers from line one.
4. Cite iter-0033d closure §A AND iter-0033f closure §A' directly so the design context survives across sessions.
5. Sequence implementation as: SKILL.md cleanse → standalone validate-plan.py (parent-memory-aware CLI: `--in-memory-pair-plan-json`) → expanded Check 15 → archive_run.py with parent-memory-write contract → run-fixture.sh refactor (parent-memory state machine + post-quiescence merge) → judge.sh + compare.py anon-aware → orchestrator + smokes (in mktemp + REAL run-fixture.sh path) → suite.
6. Codex pair-collab budget: at minimum R0 on the implementation plan (against iter-0033d §A + iter-0033f §A' as combined design baseline), R-smoke after smokes, R-final on suite raw numbers. ANTI-ASYMPTOTIC HARD STOP: if R0 surfaces a NEW structural class (item 25+), close iter-0033g as design-iter immediately + escalate to user. NO R0.5 attempt under in-place revision.
7. Wall budget: ~22h floor (~12-14h impl due to parent-memory state machine complexity + 0.5h smokes + 0.5h mirror+lint + 6h suite + 1.5h R-final/closure + 0.5h commit). Hard-cap 28h mechanically enforced.

### D. What we keep / what we drop from iter-0033f

| | Keep | Drop |
|---|---|---|
| Design baseline | iter-0033d §A items 1-18 + iter-0033f §A' items 19-24 | "anon paths + sidecar relocation" architecture (architecturally insufficient) |
| Hypothesis | Direction (PLAN-pair vs solo-PLAN measurement) | iter-0033f's specific phrasing — iter-0033g restates with parent-memory-only framing |
| Suite | 6 high-value fixtures {F2, F3, F4, F6, F7, F9} | All implementation choices (arms env, env-var names, paths) |
| Gates | 8-gate structure carry-forward | Threshold values restate; Gate 8 expanded per items 19-24 |
| Wall estimate | (none — iter-0033f was ~21h floor) | Replaced with ~22h floor |

### E. Why this is principles-aligned closure (Claude + Codex independent convergence on option 2)

- **#1 No overengineering / Subtractive-first** — closing now stops further pre-reg accretion (R0+R0.5 already spent ~10h on now-stale framing). Net surface: option 2 < option 1 (delete + restart vs patch + patch).
- **#2 No guesswork / "in-place re-pre-registration forbidden"** — pre-reg already revised once after R0; revising AGAIN after R0.5 is exactly the in-place re-pre-registration pattern. iter-0033b → iter-0033b' / iter-0033d → iter-0033f precedent IS the canonical fix.
- **#3 No workaround** — option 1 ("fix-then-codex-then-fix") is pattern-incremental. Option 2 acknowledges the asymptotic pattern + breaks it via fresh-iter. Pattern-level break is the root-cause fix.
- **#4 Worldclass production-ready** — clean-design-from-line-one gives stronger leak-zero guarantee than two-revision-deep patch.
- **#5 Best practice** — iter-decomposition (design-iter → impl-iter) is the proven pattern (iter-0033b → iter-0033b', iter-0033d → iter-0033f).
- **#6 Layer-cost-justified** — option 1 risks R0.6 finding item 25 → another revise → R0.7 → asymptote. Option 2 caps cost at "1-2h iter-0033g pre-reg + Codex R0 fresh". Bounded vs unbounded.
- **#7 Mission-bound** — single-task scope preserved.
- **pre-flight #0** — closes "is the iter-0033f firewall design ready for measurement?" → answer: NO, with documented evidence. Phase 4 cutover stays blocked but on a clearer gate (iter-0033g impl outcome).
- **User direction (binding)** — "iter-0033d처럼 asymptotic 패턴 빠지지 말 것". Option 2 breaks the pattern; option 1 stays in it.

### F. Pointers

- Codex R0 dialog: `/tmp/codex-iter0033f-r0/{prompt.md, response.log}`.
- Codex R0.5 dialog: `/tmp/codex-iter0033f-r0.5/{prompt.md, response.log}`.
- Codex principles-decision dialog: `/tmp/codex-iter0033f-principles/{prompt.md, response.log}`.
- Next iter file: `iterations/0033g-pair-plan-impl-pmo.md`.
