---
iter: "0033g"
title: "PLAN-pair PMO architecture — CLOSED-DESIGN per anti-asymptotic hard stop + big-picture pivot to Phase 4 cutover"
status: CLOSED-DESIGN / NO IMPLEMENT
type: design — meta-strategic pivot iter; anti-asymptotic hard stop fired exactly as pre-registered; Claude+Codex independent big-picture review converged on option VI (ship Phase 4 cutover with L1 solo + label L2 PLAN-pair research-only until threat model empirically validated OR container infra justified)
shipped_commit: TBD (this closure commit)
date: 2026-05-03
mission: 1
gates: iter-0034-Phase-4-cutover (no longer gated on PLAN-pair measurement; L1 solo evidence sufficient per iter-0033 (C1) PASS 5/5 headroom fixtures + suite-avg L1−L0 +6.43)
design_baseline:
  - iterations/0033d-pair-plan-measurement.md §"CLOSURE" §A items 1-18 (preserved as design archive)
  - iterations/0033f-pair-plan-impl.md §"CLOSURE" §A' items 19-24 (preserved as design archive)
  - iter-0033g §"CLOSURE" §A'' items 25-28 (this closure — added below)
parent_design_iters: iter-0033d (Codex R0+R0.5+R0.6 → option B) + iter-0033f (Codex R0+R0.5 + Claude/Codex principles-pair → option 2)
codex_r0_iter0033g: 2026-05-03 (470s, 130k tokens — NEW STRUCTURAL CLASS verdict; items 25-28: parent-process argv inspection, /dev/fd/1 derivation, /tmp/iter0033g-runtime.* enumeration, detached descendants outside checked PGID; transcript /tmp/codex-iter0033g-r0/response.log)
codex_bigpicture_review: 2026-05-03 (~7 min, 259k tokens — independent verdict BIG-PICTURE RECOMMENDATION VI; KILLER FINDING: codex grep across 6mo benchmark logs found ZERO actual subagent introspection (only 1 blocked operational `pgrep -af codex`); threat model empirically theoretical not observed; transcript /tmp/codex-bigpicture-2026-05-03/response.log)
user_adjudication: 2026-05-03 — option VI (close iter-0033g + Phase 4 cutover solo + PLAN-pair research-only) confirmed; "솔로도 그대로 잘 동작하고 페어는 더욱 더 잘 동작하게 하는 방향" — L1 stays solid + L2 ships per-phase where empirically lifts
anti_asymptotic_hard_stop_fired: YES — pre-reg said "if R0 finds NEW STRUCTURAL CLASS (item 25+), close iter-0033g as design-iter immediately + escalate to user. NO R0.5 in-place revision." R0 found items 25-28; user adjudicated option VI (broader pivot than just iter-0033h). The hard stop worked exactly as designed — broke the asymptotic pattern.
revisions:
  - 2026-05-03 PRE-REGISTERED — PMO architecture from line one
  - 2026-05-03 CLOSED-DESIGN — closure section appended; status changed; broader hand-off to Phase 4 cutover (NOT iter-0033h)
---

# iter-0033g — PLAN-pair implementation, parent-memory-only architecture

## Why this iter exists (PRINCIPLES.md pre-flight 0)

iter-0033d closed as design-iter (18 leak surfaces enumerated). iter-0033f attempted implementation with anon-paths + sidecar-relocation architecture; closed as design-iter after Codex R0+R0.5 found 6 more classes (items 19-24) that the architecture could not close (root cause: any disk path the child can derive from its env/argv/cwd is a leak surface; relocation-to-siblings doesn't help because siblings are reachable via `dirname` or `cd ..`). Claude+Codex independent principles-decision pair AGREE option 2: close + open iter-0033g with parent-memory-only architecture from line one.

**Scope of this iter**: implement the parent-memory-only architecture closing all 24 surfaces (iter-0033d §A items 1-18 + iter-0033f §A' items 19-24), then run the measurement suite. The 24 surfaces are NOT optional features — each is a ship-blocker. The deliverable is (a) the firewall, (b) the suite verdict, (c) the inference about whether PLAN-pair earns the L2 layer cost.

## §0. Architecture — parent-memory-only (PMO)

The root cause of all 24 leak surfaces: pair-mode artifacts ON DISK during child execution. ANY disk path child can reach via `dirname`, `cd ..`, env-var-derive, or argv-derive is a leak surface.

**PMO contract** (binding, line-one):

1. **During child execution, NO pair-mode artifact exists on disk anywhere child can reach.** Pair-mode artifacts (`pair-plan.json`, `plan.debate.json`, IMPLEMENT-prompt audit copy, anon-map, timing-meta with `arm` field, sidecar prompt) live in PARENT bash variables ONLY.
2. **Disk write happens ONLY after**: (a) child reaped, (b) process-group quiescence confirmed (`pkill -0 -- -PGID` returns no processes after a 2s settle window — closes Codex Q2 item 23 process-descendants).
3. **Disk write target is a path the child has no way to derive**: `${SECRET_RUNTIME_DIR}/${run_id}/${anon}/`, where `SECRET_RUNTIME_DIR=$(mktemp -d /tmp/iter0033g-runtime.XXXXXX)` is a parent-only random path created at orchestrator boot, NEVER passed to child env or argv.
4. **Child's reachable filesystem during execution**: ONLY `$WORK_DIR` (which contains the codebase + `.devlyn/criteria.generated.md` if free-form mode + `.devlyn/spec-verify.json` carrier — no pair-mode signal in either), `$RESULT_DIR/claude-debug.log` (the only file in `--debug-file`'s parent dir — lone file, no siblings), and standard system paths (`/usr`, `/tmp/<random-claude-temp>`, etc.).
5. **`transcript.txt` (closes item 21)**: child stdout/stderr redirected to `${SECRET_RUNTIME_DIR}/transcript.${anon}.txt` (parent-only path) instead of `$RESULT_DIR/transcript.txt`. Child's `/dev/fd/1` readlink resolves to a path child cannot otherwise derive.
6. **`claude-debug.log` content (closes item 22)**: post-run scan asserts `claude-debug.log` content does NOT contain ANY iter-0033d §A item 8 reserved tokens. Failure → fail-fast (this is a child-side leak that PMO cannot prevent prospectively, only detect retrospectively; Gate 8 records as ship-blocker).
7. **Process-group quiescence (closes item 23)**: parent waits on `CHILD_PID`, then `sleep 2`, then `pkill -0 -- -PGID`; if any process remains, escalate to `BLOCKED:process-group-not-quiescent` and dump remaining processes for diagnosis.
8. **No `run_id`/`anon` in path under child-derivable space (closes item 24)**: `WORK_DIR` becomes `bench-${SECRET_PARENT_HASH}-${anon}` where `SECRET_PARENT_HASH = sha256(uuid + run_id)[:12]` is parent-only; child sees the path but cannot reverse it to `run_id`. `SECRET_RUNTIME_DIR` (the artifact storage) uses `/tmp/iter0033g-runtime.XXXXXX` (mktemp) — not derivable from any child-visible value.

The PMO architecture closes items 19-24 as a CATEGORY (not individually). Items 1-18 (iter-0033d §A) close via the same mechanisms iter-0033d/f planned (cleansed SKILL.md, scrubbed pipeline.state.json, standalone validate-plan.py, expanded lint Check 15, stash-aware archive_run.py with PMO write-target, byte-identical .claude/settings.json, F9 ENGINE_CLAUSE split, mktemp smokes), but with the artifact-storage path replaced by `SECRET_RUNTIME_DIR`.

## Mission 1 service (PRINCIPLES.md #7)

Single-task scope (one fixture at a time, no parallel-fleet). Mission 1 hard NOs untouched. PMO architecture is bench-substrate change ONLY; does NOT introduce a worktree-per-task model.

## Hypothesis (NEW — not recycled from iter-0033d/f per PRINCIPLES #2)

Given the 24-surface firewall fully implemented via parent-memory-only architecture (PMO contract §0 above), PLAN-pair (Claude proposer + Codex critic, structurally firewalled from IMPLEMENT subagent) on the 6-fixture pair-eligible suite `{F2, F3, F4, F6, F7, F9}` produces:

- **(a) Quality lift**: `(pair_plan − solo_plan) ≥ +5` judge-score on ≥50% of fixtures.
- **(b) Wall efficiency**: per-fixture `pair_plan_wall / solo_plan_wall ≤ 2.0×` (≤ 3.0× ceiling only for fixtures with categorical rescue).
- **(c) Firewall holds**: `validate-plan.py` + Gate 8 expanded scan find ZERO IMPLEMENT-visible pair-mode signal across all 12 runs (6 fixtures × 2 arms). Specifically: child's reachable filesystem (cwd + cwd/.. + dirname-of-argv-paths + env-var-paths) contains ZERO pair-mode artifacts during execution.
- **(d) Hard-floor**: zero new HIGH/CRITICAL `design.*`/`security.*` findings on `pair_plan` vs previously-clean `solo_plan`.
- **(e) No regression**: per-fixture `(pair_plan − solo_plan) ≥ −3` axes (Gate 2).
- **(f) Round-cap discipline**: per-round telemetry present + `BLOCKED:plan-pair-stuck` when round N findings byte-equal N−1 (Gate 6).

**Falsification → Phase 4 decision mapping** (exhaustive over (a-f) outcome space):

| Outcome | Phase 4 decision | Rationale |
|---|---|---|
| All PASS | SHIP PLAN-pair | hypothesis confirmed end-to-end |
| (a)P (c)F | SHIP solo only + new firewall iter | lift attributable to leak; mis-attribution |
| (a)P (d)F | BLOCK Phase 4 + follow-up regression-source iter | lift exists but introduces hard-floor regression |
| (a)F + (c)(d)(e)(f) all PASS + (b) PASS | SHIP solo only + L2-PLAN labeled research-only | solo PLAN sufficient; L2 doesn't earn layer cost |
| (a)F + (c)F | SHIP solo only + new firewall iter | lift never measured cleanly; redo |
| (a)F + (d)F | SHIP solo only + new regression-source iter | pair fails on both axes |
| (e)F (any) | SHIP solo only + ROOT-CAUSE iter | per-fixture regression on previously-clean fixture is a hard veto |
| (b)F (no categorical rescue) | SHIP solo only | wall over-runs L2 layer-cost budget |
| (b)F (categorical rescue ≤ 3.0×) | conditional SHIP — categorical-rescue bucket only | layer-cost justified for the rescue path only |
| (f)F | BLOCK Phase 4 + round-cap fix iter | round-cap mechanism broken; can't trust pair telemetry |
| (a)P (c)P (d)P (e)P (f)P (b) categorical only | SHIP PLAN-pair on rescue bucket only + research-only on rest | conditional ship |

(Gate 7 attribution causality is data-gathering only — does not change Phase 4 decision; informs iter-0033h+ design space.)

### Predicted directions (PRINCIPLES #2 — filled BEFORE run)

| | Direction | Confidence | Rationale |
|---|---|---|---|
| (a) Quality lift on ≥3/6 fixtures | LIFT | LOW-MEDIUM | iter-0033c-fdfd showed `deliberation_lift` exists when leak is structurally impossible. PLAN-side is a different surface; prior is positive but PLAN-pair without IMPLEMENT runtime context may produce abstract critique. |
| (b) Wall ≤ 2.0× majority, ≤ 3.0× outliers | YES | MEDIUM | iter-0022 PLAN-pair infra showed cap-3 round termination is rare; PLAN tokens are small vs IMPLEMENT. PMO state machine adds ~constant overhead per arm (process-group quiescence wait + post-reap merge), should not dominate. |
| (c) Firewall holds (zero leak) | YES | MEDIUM-HIGH | PMO architecture closes items 19-24 as CATEGORY (every disk artifact moved to SECRET_RUNTIME_DIR — child has no env/argv/derive path to it). Risk = items 25+ class. Mitigation: Codex R0 (this round, post-pre-reg-write) probes; if NEW class found, anti-asymptotic hard stop fires (close iter-0033g, escalate). NO R0.5 in-place revision. |
| (d) Zero new HIGH/CRITICAL on pair_plan | YES | MEDIUM | Codex critic in PLAN tends to flag missing acceptance / tighten scope, not introduce design.*/security.* problems. Gate 4 with 3-bucket carry-forward isolates `pair_sandbox_only` as LOG. |
| (e) No per-fixture regression ≥ −3 | YES | MEDIUM | iter-0033c L2-gated arm showed mean Δ −2.0 from leak (now firewalled by PMO); without leak, regression should narrow. |
| (f) Round-cap fires correctly | YES | MEDIUM-HIGH | Mechanism deterministic byte-equal canonical hash compare; failure mode = implementation bug, not behavioral. Smoke 1c probes determinism. |

## Suite (carry-forward from iter-0033f, FROZEN)

- **Fixtures**: `{F2, F3, F4, F6, F7, F9}` (pair-eligible set, frozen from iter-0033c manifest).
- **Arms**: `solo_plan` (`--engine claude` no pair) + `pair_plan` (PMO firewall + Codex critic in PLAN; IMPLEMENT consumes only `.devlyn/plan.md`).
- **Same**: HEAD, env (PMO `WORK_DIR`/`RESULT_DIR`), IMPLEMENT engine (Claude). Only PLAN differs.
- **Anonymization**: `anon = sha256(secret_salt + run_id + fixture + arm)[:12]` for short-string display only. Path uses `SECRET_PARENT_HASH = sha256(uuid + run_id)[:12]` (parent-only; not anon, not derivable from child).
- **Anon collision detection**: orchestrator builds full anon map BEFORE first child spawn; fail-fast on duplicate; auto-extend hash to 16 hex chars on retry.

## Architecture (24-surface firewall via PMO — closure §A + §A' + items 25+ proactively flagged)

The original 3-layer firewall (artifact split + schema separation + reserved-token validator) does NOT close items 1-24. iter-0033f's anon-paths + sidecar-relocation architecture does NOT close items 19-24. iter-0033g uses PMO architecture (§0 above) which closes items 19-24 as a category.

1. **Live-state firewall** (iter-0033d §A items 1-2): pair-plan tracking IN PARENT MEMORY ONLY (not in `pipeline.state.json` or any disk file during child execution); PLAN phase fields scrubbed to canonical defaults BEFORE IMPLEMENT spawn; `SKILL.md` PHASE bodies cleansed of pair-mode mention; mechanism description in `references/pair-plan-mechanism.md` consumed ONLY by orchestrator runtime PHASE 1 prompt body.
2. **Path/env/argv firewall** (iter-0033d §A items 3-7 + iter-0033f §A' items 19-20, 24): `WORK_DIR=bench-${SECRET_PARENT_HASH}-${anon}` (parent hash derivable only from parent's secret UUID); `RESULT_DIR` contains ONLY `claude-debug.log` during child execution (no sidecars); child env free of `run_id` / `anon` derivation; `BENCH_WORKDIR=$WORK_DIR` env still required by `spec-verify-check.py` but cannot derive pair-mode signal because no pair-mode artifacts exist in `$WORK_DIR/..` either; byte-identical `.claude/settings.json` between arms (1-byte signal file deleted before IMPLEMENT spawn); `ps -p $CHILD_PID -o command=` post-spawn must not contain arm-name.
3. **Token firewall** (iter-0033d §A items 8-10): standalone `scripts/validate-plan.py` (deterministic schema + reserved-token blacklist + over-block exemption list); strict 3-section plan.md schema; in-memory pair-plan-json validated via `--in-memory` CLI mode (parent passes JSON via stdin, no disk write).
4. **Lint firewall** (iter-0033d §A item 11): `scripts/lint-skills.sh` Check 15 expanded scan list; PMO addendum: also lint `run-fixture.sh` for any `> "$RESULT_DIR/"` redirect (must be allowlisted to `claude-debug.log` only).
5. **Persistence firewall** (iter-0033d §A items 12-14 + iter-0033f §A' item 21 transcript): IMPLEMENT prompt held in PARENT memory; written to `${SECRET_RUNTIME_DIR}/implement.prompt.txt` AFTER child reap + process-group quiescence; child stdout/stderr redirected to `${SECRET_RUNTIME_DIR}/transcript.${anon}.txt` (NOT `$RESULT_DIR/transcript.txt`). `archive_run.py` reads from `SECRET_RUNTIME_DIR` (passed via env from orchestrator) to merge into `runs/<run_id>/`; secrets dir cleaned up after merge.
6. **Cross-arm firewall** (iter-0033d §A items 15-18): per-round telemetry held in PARENT memory (parent bash array of round records); early-stop when round N produces byte-identical canonical hash to round N-1 (canonicalization = `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` after timestamp strip + finding-id de-dup; finding-id derivation rule: `sha1(round_num + finding.text.strip())[:12]` — Codex Q2 item flagged finding-id stability, this rule fixes it); F9 ENGINE_CLAUSE hardcoded `--engine claude` for ideate; smokes run in `mktemp -d` with REAL `run-fixture.sh --pmo` path; validate-plan.py hard-fails on full §A item 18 a-i scope.
7. **Process-group firewall** (iter-0033f §A' item 23): post-`wait` quiescence check (`pkill -0 -- -PGID` after 2s settle); failure → `BLOCKED:process-group-not-quiescent` with process dump.
8. **Debug-log content firewall** (iter-0033f §A' item 22): post-run scan of `claude-debug.log` for iter-0033d §A item 8 reserved tokens; ANY match → ship-blocker (cannot be retroactively scrubbed from a paid run; treat as inference void).

## Method

### Pre-suite smokes 1a-e (in `mktemp -d`, REAL `run-fixture.sh --pmo` path)

| smoke | what it tests | pass criterion |
|---|---|---|
| **1a** | F9 ENGINE_CLAUSE static check (iter-0033d §A item 16) | F9 ideate clause hardcoded `--engine claude`; only resolve clause sees plan-mode signal. arm-name absent from ideate clause. |
| **1b** | Codex CLI availability + monitored-shell wrapper integrity | `command -v codex` PASS; `codex-monitored.sh -s read-only "echo ok"` returns clean. |
| **1c** | validate-plan.py determinism + scope (covers iter-0033d §A items 8-10, 18 + Codex Q2 normalization rule + finding-id derivation) | invoke against (i) clean canonical plan.md → PASS; (ii) reserved-token plan → FAIL with token cited; (iii) over-block tokens → PASS (allow-listed); (iv) full §A item 18 a-i → each FAIL-able; (v) Gate 6 canonical hash determinism (100 invocations, byte-identical); (vi) finding-id derivation determinism (same finding text → same id across runs). |
| **1d** | PMO firewall — child's reachable filesystem contains ZERO pair-mode artifacts during execution (mini end-to-end on F2 only, both arms, no judge) | (i) `$WORK_DIR/..` listing during child execution: NO `stash-*`, NO `sidecars-*`, NO `pair-*` directories; (ii) `dirname --debug-file`'s parent dir contains ONLY `claude-debug.log` after child writes it (poll-until-exists); (iii) `find $WORK_DIR -name 'pair-*' -o -name 'plan.debate*' -o -name 'pair-plan.json'` during execution returns EMPTY; (iv) `ps -p $CHILD_PID -o command=` post-spawn does NOT contain `solo_plan`/`pair_plan`/`pair_critic`; (v) `sha256(.claude/settings.json)` byte-identical between arms; (vi) `BENCH_WORKDIR` env value passed to child does NOT contain `solo_plan`/`pair_plan`/raw `run_id`; (vii) post-reap, `pkill -0 -- -PGID` returns empty (process-group quiescent); (viii) post-merge, `claude-debug.log` content scanned for §A item 8 reserved tokens — ZERO matches. |
| **1e** | Hard-cap timer + anon collision detection | (i) `run-iter-0033g.sh` writes `.iter-start-epoch` at boot; per-arm wrapper aborts if `(now − start) ≥ 28h`; (ii) orchestrator builds full 12-entry anon map BEFORE first spawn; if collision injected (test fixture), fail-fast + auto-extend hash. |

If any smoke fails → R-smoke with Codex (against iter-0033d §A + iter-0033f §A' as combined design baseline) → fix → re-run smokes. **ANTI-ASYMPTOTIC HARD STOP**: if R-smoke surfaces a NEW STRUCTURAL CLASS (item 25+) → close iter-0033g as design-iter immediately + escalate to user. NO R-smoke-revision attempt. iter-0033h opens fresh.

### Suite

6 fixtures × 2 arms = 12 runs, serial, on a single workstation. Same HEAD, PMO architecture, secret-runtime-dir per-run. Total wall ~6h.

### Wall budget (~22h floor + 4h slack ceiling = 26h soft / 28h hard-cap)

| stage | budget |
|---|---|
| Implementation (PMO state machine in run-fixture.sh + secret-runtime-dir lifecycle + process-group quiescence + archive_run.py PMO contract + validate-plan.py in-memory CLI + finding-id derivation + all from iter-0033f impl scope) | ~12-14h |
| Smokes 1a-e (in mktemp, REAL run-fixture.sh --pmo path) | ~45 min |
| Mirror sync (`bin/devlyn.js -y`) + lint (twice — pre-smokes + post-R-smoke-fix-pre-suite) | ~30 min |
| Suite (6 fixtures × 2 arms, serial) | ~6h |
| R-final + closure write + commit | ~2h (includes Codex pair rounds if R-final surfaces a blocker) |
| **Floor** | **~22h** |
| **Hard-cap** | **28h, mechanically enforced by `run-iter-0033g.sh` start-timestamp + abort check** |

**Hard-cap enforcement**: `run-iter-0033g.sh` writes `${ITER_RESULTS_DIR}/.iter-start-epoch` at boot. Every per-arm invocation checks `(now − start) ≥ 100800` (28h × 3600) and aborts with `BLOCKED:hard-cap-exceeded` if true. If hit, iter-0033g closes as design-iter (option 2 precedent) + escalate to user.

## Acceptance gates (pre-registered, ALL ship-blockers cite iter-0033d §A items + iter-0033f §A' items)

| Gate | Threshold | Source / item(s) |
|---|---|---|
| **1a** | F9 ENGINE_CLAUSE smoke PASS | iter-0033d §A item 16 |
| **1b** | Codex CLI + monitored-shell smoke PASS | iter-0033c Gate 1b carry-forward |
| **1c** | validate-plan.py determinism + scope smoke PASS (probes (i)-(vi)) | iter-0033d §A items 8, 9, 10, 18 + Codex Q2 normalization |
| **1d** | PMO firewall smoke PASS (probes (i)-(viii)) | iter-0033d §A items 3-7, 12, 14 + iter-0033f §A' items 19-23 |
| **1e** | Hard-cap timer + anon collision smoke PASS | iter-0033f Codex Q5 hard-cap + Q6 anon-collision |
| **2. No regression vs solo_plan** | every fixture: `(pair_plan − solo_plan) ≥ −3` axes | NORTH-STAR test #6 carry-forward |
| **3. Quality lift on pair-eligible (SHIP-BLOCKER)** | `(pair_plan − solo_plan) ≥ +5` on ≥50% of fixtures (≥3/6) | iter-0033c Gate 3 ship-blocker carry-forward |
| **4. Hard-floor (3-bucket Gate 4 carry-forward)** | zero `pair_plan` disqualifier on previously-clean `solo_plan`; 3-bucket: `mechanical_failed` → FAIL; `target_env_reproduced` → FAIL; `pair_sandbox_only` → LOG | PRINCIPLES #4 + iter-0033c-fdfd |
| **5. Wall efficiency** | per-fixture `pair_plan_wall / solo_plan_wall ≤ 2.0×`; `≤ 3.0×` ceiling for categorical rescue | iter-0033c Gate 5 carry-forward |
| **6. Round-cap discipline (canonical hash + finding-id derivation rule)** | `pair-plan.json` per-round telemetry present (in PARENT memory during run, written post-reap); canonical hash function spec'd; finding-id = `sha1(round_num + finding.text.strip())[:12]` — Codex R0.5 Q2 fix | iter-0033d §A item 15 + Codex R0.5 Q2 |
| **7. Attribution causality (4-class)** | per-fixture: `no_material_lift` / `implementation_confounded` / `tool_or_trigger_lift` / `deliberation_lift` | iter-0033c Gate 7 carry-forward |
| **8. PMO firewall + artifact contract (EXPANDED — closes iter-0033d §A items 2, 11, 12, 13, 14, 17, 18 + iter-0033f §A' items 19-24)** | (a) `pipeline.state.json` PLAN phase fields scrubbed to canonical defaults pre-IMPLEMENT; (b) `implement.prompt.txt` (post-merge in run archive) scanned for §A item 8 tokens — ZERO matches; (c) `pair-plan.json` + `plan.debate.json` (post-merge in run archive) present + non-empty; (d) `validate-plan.log` archived; (e) `lint-skills.sh` Check 15 PASSES on full §A item 11 scan list (source + mirror); (f) `.claude/settings.json` SHA-256 byte-identical between arms; (g) NO disk artifact for pair-mode existed during child execution (smoke 1d (i)(iii) live evidence); (h) `ps -p $CHILD_PID -o command=` log captured post-spawn, NO arm-name; (i) `BENCH_WORKDIR` env value sent to child does NOT contain `run_id`/raw arm; (j) `--debug-file` parent dir contained ONLY `claude-debug.log` during execution (smoke 1d (ii)); (k) SKILL.md PHASE 0/1/2/3/4/5/6 bodies free of pair-mode tokens (Check 15 enforces); (l) smokes ran from `mktemp -d`; (m) post-reap `pkill -0 -- -PGID` returned empty (process-group quiescent — closes item 23); (n) `claude-debug.log` content scanned for §A item 8 reserved tokens — ZERO matches (closes item 22); (o) `transcript.${anon}.txt` lived in SECRET_RUNTIME_DIR, NOT `$RESULT_DIR` (closes item 21); (p) `WORK_DIR/..` listing during child execution had NO `stash-*` / `sidecars-*` / `pair-*` (closes item 20); (q) `SECRET_RUNTIME_DIR` path NOT derivable from any child env/argv (closes item 24). | iter-0033d §A items 2, 11, 12, 13, 14, 17, 18 + iter-0033f §A' items 19-24 |

**Ship-blockers**: 1a, 1b, 1c, 1d, 1e, 2, 3, 4, 6, 8.
**Quality gates** (failure → root-cause iter, not silent skip): 5.
**Data-gathering** (no pass/fail): 7.

If ANY ship-blocker FAILS → Phase 4 ships solo-PLAN only + NORTH-STAR records L2 PLAN-pair as research-only + `--engine`/`--pair-verify` flags removed.

## Phase 4 cutover dependency

Same as iter-0033d/f, gated on iter-0033g outcome:
- iter-0033g ALL ship-blockers PASS → Phase 4 ships PLAN-pair as first product L2 surface.
- ANY ship-blocker FAIL → Phase 4 ships solo-PLAN only; NORTH-STAR records L2 as research-only.

## Implementation scope (this iter)

### Ships in this iter (sequenced; one-line phase report per step)

1. **SKILL.md cleanse** (`config/skills/devlyn:resolve/SKILL.md`): PHASE 0/1/2/3/4/5/6 bodies free of pair-mode mention. Mechanism in NEW `references/pair-plan-mechanism.md` (orchestrator-only). (iter-0033d §A item 2)
2. **scripts/validate-plan.py** (NEW, standalone, deterministic, in-memory aware): schema check + blacklist + over-block exemption + §A item 18 a-i + Gate 6 canonical hash + finding-id derivation. CLI accepts `--in-memory` (read JSON from stdin) so parent can validate without disk write. (iter-0033d §A items 8, 9, 10, 18 + Codex Q2)
3. **scripts/lint-skills.sh Check 15** (NEW section): scans source + mirror; PMO addendum: also lint `run-fixture.sh` for `> "$RESULT_DIR/"` redirects (allowlisted to `claude-debug.log` only). (iter-0033d §A item 11)
4. **config/skills/_shared/archive_run.py**: PMO contract — reads from `SECRET_RUNTIME_DIR` env (set by orchestrator) to merge `pair-plan.json`, `plan.debate.json`, `implement.prompt.txt`, `validate-plan.log`, `transcript.${anon}.txt` into `runs/<run_id>/`; secrets dir cleaned post-merge. SIGINT/SIGTERM trap: archive-on-resume if interrupted (Codex Q6). (iter-0033d §A items 13, 14 + iter-0033f §A' items 19-24)
5. **Orchestrator (`config/skills/devlyn:resolve/SKILL.md` PHASE 2 entry mechanism + `references/phases/implement.md`)**: holds IMPLEMENT prompt in PARENT memory; passes to Agent via prompt arg; writes audit copy to `${SECRET_RUNTIME_DIR}/implement.prompt.txt` AFTER Agent return. (iter-0033d §A item 12)
6. **`benchmark/auto-resolve/scripts/run-fixture.sh`** (PMO state machine + secret-runtime-dir lifecycle + process-group quiescence): `--pmo` mode is mandatory for `solo_plan`/`pair_plan` arms. State machine: (i) parent boot creates `SECRET_RUNTIME_DIR=$(mktemp -d /tmp/iter0033g-runtime.XXXXXX)`; (ii) prompt + timing held in parent vars (NOT written to `$RESULT_DIR`); (iii) child stdout/stderr redirected to `${SECRET_RUNTIME_DIR}/transcript.${anon}.txt`; (iv) `WORK_DIR=bench-${SECRET_PARENT_HASH}-${anon}` (parent hash = `sha256(uuid + run_id)[:12]`); (v) `--debug-file $RESULT_DIR/claude-debug.log` (parent dir lone-file); (vi) post-`wait`, `sleep 2`, `pkill -0 -- -PGID` quiescence check; (vii) post-quiescence merge: parent vars + secret-runtime files → `$RESULT_DIR` for archival (read by `archive_run.py`); (viii) F9 ENGINE_CLAUSE ideate-clause hardcoded `--engine claude`. Pre-iter-0033g arms (bare/variant/solo_claude/l2_gated/l2_forced) keep legacy non-PMO path for iter-0033c re-runnability. (iter-0033d §A items 3-7, 16 + iter-0033f §A' items 19-24)
7. **`benchmark/auto-resolve/scripts/judge.sh` + `benchmark/auto-resolve/scripts/iter-0033g-compare.py` (NEW)**: anon-aware (resolve fixture/arm via post-merge anon-map.json); 3-bucket Gate 4 carry-forward; cites iter-0033c-compare.py:230-255 for 3-bucket impl. PMO addendum: judge.sh reads transcript from `$RESULT_DIR/transcript.${anon}.txt` (post-merge location) — never from `SECRET_RUNTIME_DIR` directly.
8. **`benchmark/auto-resolve/scripts/run-iter-0033g.sh` (NEW)**: orchestrator + smokes 1a-e (in `mktemp -d` per iter-0033d §A item 17). R-smoke trigger if any smoke fails. **Hard-cap timer**: writes `.iter-start-epoch` at boot; per-arm wrapper aborts on overrun (28h cap). Anon-collision detection: builds full anon map pre-spawn; fail-fast on duplicate.
9. **Mirror sync sequencing**: `bin/devlyn.js -y` + `bash scripts/lint-skills.sh` runs (a) ONCE before smokes 1a-e, (b) AGAIN after any R-smoke fix BEFORE suite kickoff, (c) NEVER between suite arms (frozen).
10. **Suite execution**: 6 fixtures × 2 arms, serial, ~6h.
11. **R-final on raw numbers + closure verdict + commit**.

### Does NOT ship in this iter

- iter-0034 Phase 4 cutover (separate iter, gated on this one).
- iter-0033e PROJECT-coherence pair (separate stub, gated on this + defect-class oracle).
- F8 fixture (reporting-only, excluded from pair-eligible set).
- Pair-mode for any phase OTHER than PLAN.
- Cross-vendor adapter — Block 5 future direction.
- Deletion of `iter-0033c-compare.py` / `iter-0033f-compare.py` if any / `build-pair-eligible-manifest.py` — preserves closed-iter replay; CLAUDE.md goal-lock forbids tangential cleanup.
- Migration of pre-iter-0033g arms (bare/variant/solo_claude/l2_gated/l2_forced) to PMO — backward compat preserves iter-0033c re-runnability.

## Codex pair-collab plan

- **R0** (NEXT, after pre-reg commit): Codex reads this pre-reg + iter-0033d §A + iter-0033f §A' directly. Falsification ask: any leak class not in items 1-24? Any gate threshold under-specified? PMO architecture sufficient? Verdict: CONVERGED → step 5 (impl); revisions-only → user adjudication BEFORE R0.5 (anti-asymptotic hard stop); NEW STRUCTURAL CLASS (item 25+) → close iter-0033g as design-iter immediately + escalate to user.
- **R-smoke**: after smokes 1a-e on the actual implementation. Codex reads smoke logs + validate-plan.py output; falsification ask: did any smoke pass for the wrong reason?
- **R-final**: after suite raw numbers. Codex reads compare.py output + per-fixture state.json + IMPLEMENT-prompt scans; falsification ask: is gate 3 PASS attributable to deliberation lift OR leak/confound? Is any LOG-classified Gate 4 case actually a sandbox-only false-positive?

**ANTI-ASYMPTOTIC HARD STOP** (binding): if R0 finds NEW STRUCTURAL CLASS, close + escalate. NO in-place revision attempt. The threshold for tolerating NEW class found mid-iter-0033g is ZERO — option 2 was specifically chosen to break the asymptotic pattern, and admitting one "small" revision restarts it.

## Risk register (carry-forward + new + Codex Q6 absorptions)

| Risk | Mitigation |
|---|---|
| (CARRY) Firewall leak — IMPLEMENT subagent reasons differently due to pair-mode signal | PMO architecture closes the disk-side category; Gate 8 a-q probes verify all 24 surfaces empty during execution. |
| (CARRY) Critic over-constrains plan → plan loses information needed for IMPLEMENT | Gate 4 design.* hard-floor; Gate 7 attribution. |
| (CARRY) Wall blowup — pair-PLAN > 3.0× solo-PLAN with no categorical rescue | Gate 5 fail-fast + root-cause. |
| (CARRY) Round-cap unresolved — Codex repeats itself | Gate 6 canonical-byte-identical-hash early-stop with finding-id derivation. |
| (CARRY) Codex unavailable mid-suite | Gate 1b hard-fail. |
| (CARRY) Score regression on previously-clean fixture | Gate 4 (3-bucket); LOG/FAIL classification. |
| (CARRY) Check 15 over-match | §A item 9 over-block exemption list. |
| (NEW) Implementation slips beyond ~22h floor | Hard-cap mechanically enforced at 28h. If exceeded, close iter-0033g as design-iter + escalate. |
| (NEW, BINDING) NEW STRUCTURAL CLASS (item 25+) discovered in R0 | **ANTI-ASYMPTOTIC HARD STOP — close iter-0033g as design-iter immediately + escalate to user. NO R0.5 attempt.** |
| (NEW) `--pmo` refactor breaks iter-0033c re-runnability | `--pmo` MANDATORY for new arms; legacy arms (bare/variant/solo_claude/l2_gated/l2_forced) keep non-PMO path. |
| (NEW) Mirror sync drift | Mirror+lint runs (a) before smokes, (b) after R-smoke fix before suite. Lint Check 6 catches divergence. |
| (NEW) `SECRET_RUNTIME_DIR` cleanup leaves orphan dirs in /tmp on Ctrl-C | Orchestrator SIGINT/SIGTERM trap → cleanup `mktemp` dirs. macOS `tmpcleaner` also reaps. |
| (NEW) Process-group quiescence check fails (`pkill -0 -- -PGID` returns processes) | `BLOCKED:process-group-not-quiescent`. Dump remaining processes. Treat as suite-blocker. |
| (NEW, BYPASS-PROTECTED) Validate-plan.py false-positive on legitimate plan content | §A item 9 over-block exemption + per-fixture override file; **bypass guard**: any override reported as residual inference impact in Gate 7 + flagged in `compare.py` output. |
| (NEW Codex Q6) Codex critic nondeterminism across reruns | Persist round prompt+output+CLI/model/config in `pair-plan.json`. Rerun-interpretation policy: same input + nondeterministic output = log + treat as variance. R-final ask: did pair_plan reruns show variance > +/-2? |
| (NEW Codex Q6) mktemp smoke 1d drift from production WORK_DIR shape | Smoke 1d invokes REAL `run-fixture.sh --pmo` path with `mktemp -d` as RESULT_ROOT (not hand-built). |
| (NEW Codex Q6) Anon hash collision | Build full anon map pre-spawn; fail-fast + auto-extend hash to 16 hex chars. |
| (NEW iter-0033f §A' item 22) `claude-debug.log` content scan ship-blocker | Cannot prevent prospectively (child controls debug log content). Detect retrospectively: Gate 8 (n) scans for §A item 8 reserved tokens; ANY match → ship-blocker (run is treated as inference void; cannot retroactively scrub). |

## Principles check

- **#0 pre-flight**: ✅ closes user-visible failure (Phase 4 cutover with unproven L2 surface). Closes iter-0033f "is the iter-0033f firewall ready for measurement?" as NO via PMO redesign.
- **#1 no overengineering / Subtractive-first**: ⚠️ now-substantial implementation (~13h post-PMO, multiple files) BUT each piece is justified by a §A item OR §A' item OR Codex absorption (no speculative additions). Subtractive-first applied: PMO architecture REPLACES iter-0033f's accumulated "anon paths + sidecar relocation + stash relocation" with a single category-level mechanism (parent-memory-only) — net mechanism count drops from ~6 to ~3 (PMO + cleansed SKILL.md + standalone validator). Did NOT delete iter-0033c-compare.py / iter-0033f assets / build-pair-eligible-manifest.py — Codex Q7 explicitly rejects as tangential cleanup.
- **#2 no guesswork**: ✅ predictions filled BEFORE run; gates pre-registered with thresholds + cite §A items + §A' items. NEW hypothesis (not recycled). Anti-asymptotic hard stop forbids in-place re-pre-registration if R0 finds new class.
- **#3 no workaround**: ✅ structural firewall (PMO category fix); not silent strip / not config-level skip. validate-plan.allow.json bypass-guarded.
- **#4 worldclass production-ready**: ✅ Gate 4 with 3-bucket carry-forward enforces zero new HIGH/CRITICAL on `pair_plan` vs previously-clean `solo_plan`.
- **#5 best practice**: enforced via existing CRITIC findings in VERIFY (carryover) + structural validator at PHASE 2 entry.
- **#6 layer-cost-justified**: ✅ Gates 5, 6 measure wall budget; Gate 3 measures quality lift (ship-blocker). ~22h infra cost is itself a layer-cost data point.
- **#7 mission-bound**: ✅ Mission 1 single-task scope. PMO is bench-substrate change ONLY; no parallel-fleet, no worktree-per-task model.

## Why this is not score-chasing (PRINCIPLES.md #0)

This iter measures whether multi-LLM pair-mode in PLAN improves IMPLEMENT outcomes vs solo, AFTER the PMO firewall closes the leak surfaces that contaminated iter-0033c attribution + iter-0033f anon-paths-relocation insufficiency. Measurement is the deliverable. Phase-4-decision mapping above explicitly enumerates outcomes that REJECT the L2 PLAN-pair surface — score-chasing is incompatible with pre-registered REJECT cases.

## Deliverable execution order

1. **Pre-registration drafted** (this file). ✅
2. **Codex R0** on this pre-reg vs iter-0033d §A + iter-0033f §A'. Verdict: CONVERGED → step 3; revisions-only → USER ADJUDICATION (anti-asymptotic — do NOT in-place revise); NEW STRUCTURAL CLASS → close iter-0033g + open iter-0033h.
3. **Implementation steps 3.1 → 3.7** per §"Ships in this iter" sequencing. One-line phase report per step.
4. **Mirror sync** (`bin/devlyn.js -y`) + lint BEFORE smokes.
5. **Smokes 1a-e** in `mktemp -d`. Any fail → R-smoke + fix (only mechanism-fix; if NEW class, anti-asymptotic hard stop) + re-mirror+lint + re-run smokes.
6. **Suite** (6 fixtures × 2 arms, serial, ~6h). Run via `run_in_background` Bash with HANDOFF state continuity.
7. **Compare** (`iter-0033g-compare.py`) → emit per-fixture verdicts + 3-bucket Gate 4 + Gate 7 attribution.
8. **R-final** on raw numbers.
9. **Closure verdict** appended to this file. Update `HANDOFF.md` + `DECISIONS.md`.
10. **Commit** per repo conventions. iter-0034 Phase 4 cutover unblocked (or recorded research-only) per ship-blocker outcome.

## Pointers

- **Design baseline 1**: `iterations/0033d-pair-plan-measurement.md` § "CLOSURE", especially §A items 1-18.
- **Design baseline 2**: `iterations/0033f-pair-plan-impl.md` § "CLOSURE", especially §A' items 19-24.
- **Design baseline 3 (this file)**: §"CLOSURE" §A'' items 25-28 below.
- **Codex round transcripts**: `/tmp/codex-iter0033d-r0/`, `/tmp/codex-iter0033f-r0/`, `/tmp/codex-iter0033f-r0.5/`, `/tmp/codex-iter0033f-principles/`, `/tmp/codex-iter0033g-r0/`, `/tmp/codex-bigpicture-2026-05-03/`.
- **Sibling stub** (PROJECT-coherence pair, separate measurement): `iterations/0033e-project-coherence-stub.md`.
- **Successor iter**: `iterations/0034-phase-4-cutover.md` (PRE-REGISTERED-STUB — Phase 4 cutover ships solo PLAN as default, deletes 14+ legacy skills, labels L2 PLAN-pair research-only).
- **Memory file (lessons)**: `~/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/memory/project_iter0033g_asymptotic_firewall_lesson_2026_05_03.md`.

---

## CLOSURE — design-iter, anti-asymptotic hard stop fired exactly as pre-registered (2026-05-03)

iter-0033g was pre-registered as the implementation iter for PLAN-pair via parent-memory-only (PMO) architecture, replacing iter-0033f's anon-paths + sidecar-relocation design (which CLOSED-DESIGN after R0.5 found items 19-20). A binding **anti-asymptotic hard stop** was written into the pre-reg: "if R0 finds NEW STRUCTURAL CLASS (item 25+), close iter-0033g as design-iter immediately + escalate to user. NO R0.5 in-place revision attempt."

Codex R0 (470s, 130k tokens) returned NEW STRUCTURAL CLASS verdict with items 25-28 (parent-process argv inspection, `/dev/fd/1` derivation, `/tmp/iter0033g-runtime.*` enumeration, detached descendants outside checked PGID). The hard stop fired.

User asked Claude+Codex to do a big-picture strategic review (not just iter-0033h decision). Codex independent big-picture verdict (~7 min, 259k tokens) returned BIG-PICTURE RECOMMENDATION VI: ship Phase 4 cutover with solo PLAN default + label L2 PLAN-pair research-only + defer container infra until empirical threat justifies it. Claude independent analysis converged. User adjudicated option VI: "솔로도 그대로 잘 동작하고 페어는 더욱 더 잘 동작하게 하는 방향" (L1 stays solid + L2 ships per-phase where empirically lifts).

### A''. Leak surfaces enumerated (R0 cumulative — items 25-28)

**25. Parent-process argv inspection.** Child can `ps aux | grep run-fixture.sh` and read parent's `--arm`, `--run-id`, `--fixture` flags directly. Closing requires masking parent argv (e.g. setting `argv[0]` to a generic name, hiding env). Citation: `/tmp/codex-iter0033g-r0/response.log:5547` + `benchmark/auto-resolve/scripts/run-fixture.sh:24-28` (argv parsing).

**26. `/dev/fd/1` readlink reveals SECRET_RUNTIME_DIR.** Child can `readlink /proc/self/fd/1` (or `/dev/fd/1` on macOS) to get its own stdout target path. PMO redirected stdout to `${SECRET_RUNTIME_DIR}/transcript.${anon}.txt`, so readlink reveals SECRET_RUNTIME_DIR mid-execution. Closing requires either (a) keeping stdout in a path child cannot derive even via fd-introspection, OR (b) accepting child can know its own stdout target (which it does in any case). Citation: `/tmp/codex-iter0033g-r0/response.log:5537` + iter-0033g pre-reg §0 item 5.

**27. `/tmp/iter0033g-runtime.*` glob enumeration.** PMO chose a fixed prefix `/tmp/iter0033g-runtime.XXXXXX` for the secret runtime dir. Child can `ls /tmp/iter0033g-runtime.*` and find ALL secret runtime dirs (own arm + sibling arm if running concurrently). Closing requires either (a) random prefix not derivable from any constant, OR (b) serial-only execution + immediate cleanup. Citation: `/tmp/codex-iter0033g-r0/response.log:5549`.

**28. Detached descendants outside the checked process group.** PMO uses `pkill -0 -- -PGID` after 2s settle to verify quiescence. But descendants that detach (`setsid`, double-fork) are outside that PGID and persist post-merge. Closing requires either (a) tracking ALL descendants via process namespace / cgroup (Linux only), OR (b) accepting some risk of detached watchers. Citation: `/tmp/codex-iter0033g-r0/response.log:5541-5543`.

### B. Convergence record

| iter / round | wall | tokens | verdict | new classes |
|---|---|---|---|---|
| iter-0033d R0+R0.5+R0.6 | ~17 min | ~13k+ | NOT CONVERGING (non-monotonic AGREE 12.5%→37.5%→12.5%) | items 1-18 (cumulative 6+5+7) |
| iter-0033f R0 | 414s | 184k | NEW STRUCTURAL CLASS | item 19 |
| iter-0033f R0.5 | 214s | 104k | NEW STRUCTURAL CLASS | item 19 incomplete + item 20 |
| iter-0033g R0 | 470s | 130k | NEW STRUCTURAL CLASS | items 25-28 |
| big-picture review | ~7 min | 259k | RECOMMENDATION VI | n/a — strategic verdict |

Pattern across 5+ Codex rounds (~25 min Codex wall total): each pass produces ≥1 new structural class. The threat model "any disk/process/fd reachable to child" is unbounded for filesystem-only isolation. Container isolation is the only category-level closure — but unjustified per Q2 below.

### C. KILLER FINDING — threat model empirically not observed

Codex big-picture review searched ALL benchmark logs (transcripts, debug logs, judge logs across ~6 months) for evidence of subagents actually doing introspection (`readlink /dev/fd/1`, `ps aux`, `pgrep`, `ls /tmp`, `find /tmp`, `BENCH_WORKDIR`, stash/sidecar names, pair-plan names). Found: ZERO. Only one match — a blocked operational `pgrep -af codex` status check in a debug log (not arm-detection behavior). Citation: `/tmp/codex-bigpicture-2026-05-03/response.log:13010` + `benchmark/auto-resolve/results/20260429T141802Z-b06fffd-iter-0027-f2-n2/F2-cli-medium-subcommand/variant/claude-debug.log:1342`.

iter-0033c's diagnosis ("L2 mean Δ −2.0 from `--pair-verify` parse-time leak") was inference from downstream divergence (file-list divergence between solo and l2_gated arms), NOT direct observation of subagent introspection. The leak hypothesis is plausible but unverified.

**Implication**: 24+ leak surfaces are structurally real but empirically theoretical. Building container infra to close them is overengineering relative to the actual product surface (which doesn't have container isolation between phases).

### D. Hand-off contract for iter-0034 Phase 4 cutover (NOT iter-0033h)

The big-picture pivot replaces "iter-0033h another firewall attempt" with "iter-0034 Phase 4 cutover solo + research-only L2 label". iter-0034 MUST:

1. Ship `/devlyn:resolve` solo PLAN as default (already true at HEAD; iter-0034 mostly deletion work).
2. Delete `/devlyn:auto-resolve` + 14+ legacy skills (per HANDOFF Outstanding housekeeping).
3. Update doc surfaces: README.md, CLAUDE.md, `/devlyn:resolve` SKILL.md (remove "PLAN-pair unmeasured at HEAD" framing — replace with "L2 PLAN-pair research-only until container infra OR threat empirically validated"), NORTH-STAR (Phase 4 done), HANDOFF (Mission 1 progress).
4. Label L2 PLAN-pair as research-only with explicit unblock conditions: (a) container/sandbox infra justified by other product needs, OR (b) empirical probe demonstrates subagent introspection in production.
5. Suite re-run: pre/post Phase 4 cutover should produce identical L1 numbers (solo PLAN behavior unchanged).
6. Real-project trial as Mission 1 terminal gate — Phase 4 ship is necessary but NOT sufficient; the real-project trial is the true gate.

### E. What we keep from iter-0033g (preserved learning)

- **PMO architecture as a research direction**: parent-memory-only is valid for L2 surfaces where leak risk is empirically observed. Re-applicable when needed.
- **Anti-asymptotic hard-stop pattern**: pre-registering a binding "if R0 finds new class, close immediately" rule worked. Should be standard for any iter dealing with adversarial threat models. Codify in PRINCIPLES if pattern recurs.
- **Codex grep methodology**: searching past benchmark logs for evidence of theorized behavior (Codex Q2 in big-picture review) is a powerful epistemic check. Should precede any "build infra to close threat" decision.
- **§A items 1-18 + §A' items 19-24 + §A'' items 25-28**: the full 28-item leak enumeration is preserved as design archive. If we ever build container isolation, this list is the spec for what it must close.

### F. What we drop from iter-0033g

- The PMO implementation scope (validate-plan.py `--in-memory`, archive_run.py PMO contract, run-fixture.sh `--pmo` mode, run-iter-0033g.sh, iter-0033g-compare.py). All un-coded; just text in pre-reg.
- The iter-0033h speculative "next firewall attempt" path. Big-picture pivot makes this obsolete.

### G. Why this is principles-aligned closure (Claude + Codex independent convergence on option VI)

- **#1 No overengineering / Subtractive-first**: option VI deletes 14+ legacy skills (Phase 4 cutover) AND deletes the L2 measurement infra investment (PMO scope abandoned). Most subtractive of all options considered.
- **#2 No guesswork / "in-place re-pre-registration forbidden"**: anti-asymptotic hard stop fired as pre-registered. Big-picture review escalated meta-decision to user adjudication, not in-place revise of iter-0033g.
- **#3 No workaround**: research-only label is honest acknowledgment of measurement boundary. Not a workaround.
- **#4 Worldclass production-ready**: solo PLAN is empirically world-class (iter-0033 (C1) PASS 5/5 headroom fixtures, suite-avg L1−L0 +6.43). Shipping that as default is principled. L2 PLAN-pair is unmeasured — shipping it would be opposite of principle #4.
- **#5 Best practice**: iter-decomposition (3 design-iters → strategic pivot iter) is the proven pattern for adversarial threat-model problems with unclear empirical grounding. The grep-past-logs methodology before building infra is itself best practice.
- **#6 Layer-cost-justified**: option VI honors layer-cost. Container infra (~30h) for unobserved threat = unjustified. Solo Phase 4 cutover = layer-cost-zero (mostly deletion). Future L2 surfaces (VERIFY-pair frozen-diff, PROJECT-pair, multi-LLM via pi-agent) ship per-phase where measurement justifies them.
- **#7 Mission-bound**: Mission 1 single-task scope preserved. Phase 4 cutover stays Mission 1 work. Real-project trial is Mission 1 terminal gate.
- **User direction Block 5 (multi-LLM evolution)**: preserved as future direction; pi-agent adapter is Mission 2/3 territory per NORTH-STAR + MISSIONS hard NO list. Block 5 doesn't require shipping multi-LLM today; it requires not baking single-LLM assumptions. NORTH-STAR's `expected.schema.json` + `_shared/adapters/<model>.md` already hold this contract.
- **User direction Block 6 (페어가 PLAN에서 가장 중요)**: preserved as L2 candidate priority. Block 6 said PLAN is the most important PHASE for pair-mode IF pair-mode ships; it does NOT override layer-cost (Block 5 explicitly: "pair 비교 없이 결정 X"). Honest reading: PLAN-pair is the highest-priority L2 candidate IF measurement infra justifies itself. Currently solo PLAN's empirical floor is +6.43 above L0; lifting that requires either (a) a different L2 surface where measurement is cheaper, OR (b) container infra justified by other needs. Both paths preserve Block 6's intent.

### H. Forward L2 candidate priority (post-Phase-4)

After Phase 4 cutover ships, the next L2 measurement work should follow this priority order (by measurement difficulty + empirical grounding):

1. **VERIFY-pair frozen-diff (verify-only mode)** — iter-0033c-fdfd already showed `deliberation_lift` (F2 EACCES finding solo missed, pair caught). Frozen diff = no leak surface. Cleanest measurement target. iter-0036+ candidate.
2. **PROJECT-pair (ideate)** — iter-0033e queued; needs defect-class oracle first; if oracle is built, no leak surface (PROJECT outputs are read-only spec corpus).
3. **PLAN-pair** — current research-only. Re-enters scope when (a) container infra justified by other product needs, OR (b) empirical probe shows subagent introspection in production.
4. **Multi-LLM evolution via pi-agent** (Block 5) — Mission 2/3 territory; preserved direction, not implementation target during Mission 1.

### I. Pointers

- Codex R0 dialog: `/tmp/codex-iter0033g-r0/{prompt.md, response.log}`.
- Codex big-picture dialog: `/tmp/codex-bigpicture-2026-05-03/{prompt.md, response.log}`.
- Memory lesson file: `~/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/memory/project_iter0033g_asymptotic_firewall_lesson_2026_05_03.md`.
- Next iter file: `iterations/0034-phase-4-cutover.md`.
