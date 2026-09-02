---
id: "0113-layer-lift-meter"
title: "Layer-lift meter — one fixed instrument for L1−L0 (harness over bare) and L2−L1 (pair over solo), per model, minimal wall/tokens"
kind: instrument
status: APPARATUS-FROZEN 2026-09-03 (session 22) — FREEZE-0113-SOL r4 after 3 REVISE rounds; next = smoke gate → quick panel (opus-5)
depends_on: ["0102-executor-quality-discovery-corpus", "0104-model-checkup-loop", "0064-ceiling-instrument", "0073-nodeg-cell"]
---

# iter-0113 — layer-lift meter (층 상승 측정기)

## Why this iter exists (pre-flight 0)

NORTH-STAR § 3-layer contract (`NORTH-STAR.md:149-157`) requires L1 (solo
harness) to beat L0 (bare) and L2 (pair) to beat L1 — on quality AND on
efficiency (wall-time and token cost not worse than `bare-best-of-N`,
N = the wall ratio). Verified 2026-09-02:

- The ceiling 3-arm tranche has arms A = `/devlyn:resolve --pair-verify`
  (executor codex, `run-ceiling-arm.sh:264,:375`), B = bare, C = copycat.
  **There is no L1 arm**, and its parent launcher hardcodes `--model sonnet`
  (`claude-isolation.py:309-310`). L2−L1 was only ever measured on retired
  fixture suites ("PASS (small suite) — NOT broad product superiority").
- The ceiling/nodeg corpus (13 rows) is bare-saturated (0068
  VALID-NEGATIVE; `benchmark/ceiling/README.md:12`). Both honest tranche
  runs were FAIL-pilot for that reason.
- The sealed 0102 discovery corpus (32 tasks, 4 classes × 8, hidden
  oracles, no judge) is the only corpus measured to discriminate at bare
  (sonnet fail mean 39/80, interior 30/32; opus-4-8 0.475; fable-5 0.353;
  opus-5 ~0.30 — DECISIONS 0102.1/0103.1). It has only been run
  bare-to-bare (`mx-driver.py`).

The user's directive (2026-09-02, HANDOFF Block 11): a FIXED meter for
"bare보다 더 나은 하네스, pair로 더더욱 나은 하네스", per model, with minimal
tokens and time. This iter joins the two existing parts; one arm (L1) is
added and one scorer computes the two contract deltas.

**Supersession (stated once)**: ceiling corpus → no-degradation control
only; ceiling tranche A arm → superseded as the L1/L2 instrument; 0112
(session-horizon) → optional module (PARKED); copycat arm C stays in the
ceiling instrument for ops #17 claims and is NOT part of 0113.

## The question (one sentence)

For engine model `M`: does the shipped harness lift `M` over bare, and does
the pair lift the harness — same tasks, same hidden oracles, wall-time and
token efficiency vs best-of-N, in hours not weeks.

## Fixed elements (frozen at registration; never retuned)

| Element | Value |
|---|---|
| Corpus | sealed 0102 candidate (`~/.local/share/nx01/iter0102/freeze/candidate-manifest.json`, tree pinned) |
| Quick panel | 12 tasks = per class (AF/BD/MI/UA) the 3 whose sonnet calibration `q_cal` (`iter0102/calibration/band-verdict.json`) is closest to 1/2 (ties → lexical id). Committed as `panel-quick.json` + calibrator-file digest; `run-lift-panel.py` re-derives and refuses on mismatch (no standalone selector). **Prior-selected: outcome-blind for models disjoint from the registered `claude-sonnet-5` calibrator; calibrator-model claims require a disjoint registered panel.** Full panel = all 32 |
| Arms (the intervention = the product as shipped) | **L0** bare: `mx-driver.py` (opaque workdir, goal-only prompt, `claude -p --model M --strict-mcp-config --allowedTools …`, run-bounded 1800 s). **L1** solo harness: `/devlyn:resolve --goal-file .devlyn/goal.txt --no-pair` (free-form mode — the user's workload shape; `resolve-bootstrap.py:21-24,153-160`), orchestrating CLI `claude -p --model M` (launcher gains a `--model` parameter; the `sonnet` literal is deleted), arm-local `.devlyn/engines.json = {"executor":"claude"}`, devlyn context staged as the ceiling A arm does. **L2** = L1 + `--pair-verify`; pair judge = the EXACT registered Codex model ID under a frozen `CODEX_HOME` (config digest pinned; receipt must agree). Same visible tree + same goal bytes in all arms; harness arms additionally get `git init` + baseline commit |
| Known fixed harness component | SURFACE_CLOSE runs iff source is generated (free-form) and complexity trivial/medium, always `--model claude-sonnet-5` (`SKILL.md:262-264`). It is part of the shipped product and stays; its usage is attributed separately (diagnostic) |
| Attestation (exact sets, no tolerance) | L0: Claude `modelUsage` key set == {M} (0103 rule, `mx-driver.py:124-140`). L1/L2: key set ⊆ {M, `claude-sonnet-5`}, `claude-sonnet-5` admissible ONLY when `state.phases.surface_close` records a run (when M = sonnet-5 the set is {M}); L1 state attests `pair_default_enabled=false` + `user_no_pair` (`state-schema.md:52-58`); L2 codex receipt attests the registered pair ID. Any other model id or missing attestation ⇒ infra-invalid (replaceable), never scored |
| Reps | L0 ×4, L1 ×2, L2 ×2 (lanes = 2, identical for all arms — wall comparability by symmetry). Same on the full panel |
| Score per (task, arm, rep) — two channels | `f_tree` = hidden oracle on the final worktree (always recorded, diagnostic). **Primary `f_ship`** = `f_tree` for terminal PASS / PASS_WITH_ISSUES; **valid product BLOCKED terminals ⇒ `f_ship = 1`** (the harness declined to ship; hands-free contract); registered infrastructure / availability / attestation failures ⇒ infra-invalid, replaceable. `wall_ms`; tokens per model id |
| Estimands | reps averaged within task; `d1_t = f_L0(t) − f_L1(t)`, `d2_t = f_L1(t) − f_L2(t)`; **Δ1 = mean d1 (harness lift), Δ2 = mean d2 (pair lift)**; bootstrap **stratified within class** (resample 3 tasks per class, average the 4 class means; the panel fixed the class mixture) |
| Efficiency — wall AND tokens (NORTH-STAR names both) | `N1_wall = ceil(median wall_L1 / median wall_L0)`, `N1_tok = ceil(tokens_L1 / tokens_L0)` (tokens = OUTPUT tokens summed over all models incl. the codex receipt — the vendor-comparable generation cost; full breakdown recorded; registered assumption, falsified by a NORTH-STAR metric amendment). `E1_x = mean[best-of-N1_x L0 − f_L1]` where best-of = min `f_ship` over pre-indexed L0 reps. **Monotone top-up rule (fixed, not retuning)**: base reps first; if the best-of-4 E CI upper < 0 the leg is already `INEFFICIENT` (more cheaper-arm reps can only lower its best) — stop; otherwise run pre-indexed L0 reps 5…N1 and score exact best-of-N1. Same for E2 with L1 reps 3…M2. Top-up reps are efficiency-only, excluded from Q1/Q2. No `BOUNDED` states |
| Materiality | δ = 3/20 (0103 precedent, `score-cohort.py:186-193`) |
| Decision line (mutually exclusive) | `LIFT` = CI_lower > +δ · `NULL` = CI_lower > −δ ∧ CI_upper < +δ · `HARM` = CI_upper < −δ · else `INCONCLUSIVE`. Efficiency per leg: `EFFICIENT` = E CI_lower > 0 · `INEFFICIENT` = E CI_upper < 0 · else `INCONCLUSIVE`; the terminal E1/E2 is `EFFICIENT` only when wall AND token legs are both `EFFICIENT` (fail-closed) |
| Terminal token | `LIFT-0113: Q1=<…> E1=<…> Q2=<…> E2=<…> M=<model> panel=<quick|full> receipt=<sha>` — quick tokens are panel-scoped screening results; confirmatory layer claims use the full 32 |
| One evaluation per registration | attempts 1..3 only replace infra-invalid rows on byte-identical digests (0102 rule); no retuning; corpus ids never in skill text (thermometer rule); per-task outcomes sealed until the frozen scorer runs |
| Saturation | mean `f_ship_L0` < 0.10 on the panel ⇒ terminal `PANEL_SATURATED` — the run ends; a new registration derives a new panel (no in-run re-derivation) |

## What each verdict means (plain)

- Q1 `LIFT` + E1 `EFFICIENT`: the harness earns its place for M.
- Q1 `LIFT` + E1 `INEFFICIENT`: the harness helps but bare-best-of-N helps
  more per wall/token — an efficiency defect signal (nodeg precedent 8-12×).
- Q1 `NULL`/`HARM`: harness defect signal for M — adapter/prompt/phase
  work, not model work.
- Q2 `LIFT`: the codex pair judge catches oracle-visible defects that M's
  solo VERIFY misses AND the one permitted fix loop repairs them
  (`SKILL.md:352`). Q2 `NULL`: pair-VERIFY measured unnecessary at this
  corpus shape for M. Registered limitation: free-form goals synthesize at
  most a thin `## Verification` section (`free-form-mode.md:35-50`), so the
  pair judge's bullet targets are few — the diagnostic records the bullet
  count per run; a Q2 read is a product read at the user's workload shape,
  not a judge-recall measurement.
- Same meter with M' ⇒ the model checkup (0104) and the harness checkup are
  two columns of one table.

## Predictions (stated BEFORE any run; falsifiers accepted)

- **P-0113-1** (M = claude-opus-5, quick panel): Δ1 point > 0. Falsifier:
  Q1 = `HARM`.
- **P-0113-2**: E1 = `INEFFICIENT` on the wall leg (nodeg wall 8-12× makes
  best-of-N bare a strong baseline). Falsifier: E1 `EFFICIENT`. This is the
  honest expectation and the improvement signal the meter exists to produce.
- **P-0113-3**: the pair fix round changes the shipped diff on ≤ 30 % of
  panel tasks; Q2 ∈ {NULL, INCONCLUSIVE}. Falsifier: Q2 `LIFT`.

## Reuse / new

- **Reuse (byte-identical)**: 0102 corpus + `hidden/oracle.py`;
  `mx-driver.py` (L0 + oracle + ledger + modelUsage); ceiling arm
  `stage_devlyn_context` + claude isolation launcher (arm mode) +
  attribution receipt; `score-cohort.py` bootstrap/terminal shape.
- **New (terra, `benchmark/layer-lift/`)**: `run-lift-panel.py` (panel
  re-derivation check; L0 via mx-driver; L1/L2 via the arm staging with
  executor `claude`, `--no-pair`/`--pair-verify`, `--model M`; lanes 2;
  detached `os.setsid`; one `rows.jsonl` with both score channels;
  top-up scheduling), `score-lift.py` (Δ/E + stratified CI + decision line
  + terminal token; self-test on synthetic ledgers covering every
  point/CI tuple → exactly one token), `panel-quick.json`,
  `registered-params.json`, `scripts.sha256`. Launcher changes: `--model`
  parameter replacing the `sonnet` literal; arm-local executor `claude`.

## Operating tier (HANDOFF hard rule 8)

1. **Smoke gate** (not a prediction): 1 task × 3 arms × 1 rep on a quiet
   account — must show, simultaneously, exact `modelUsage` key sets as
   registered, L1 `user_no_pair` state, SURFACE_CLOSE recorded when it
   ran, L2 codex receipt ID, oracle output for all three arms; records the
   wall/token anchors. Fails ⇒ no panel.
2. **Quick panel**: 12 tasks — 48 L0 + 24 L1 + 24 L2 base runs (+ top-up)
   — the per-release check (hours; fires on every model release AND every
   harness release).
3. **Full panel**: 32 tasks — periodic exam; the only basis for a
   confirmatory layer claim.

Account discipline unchanged (quiet account, writer check, 23:00–01:00 KST
exclusion, detached runs, scorer frozen before rows complete).

## R0 record (2026-09-03, fable adjudication of sol `r0-sol.log`, 815 s; grok skipped — 402 standing)

Sol `R0-0113-SOL: REVISE a=ADOPT b=REVISE c=AMEND d=AMEND e=REVISE` + 4
unlisted. Every byte claim was re-verified by fable before ruling
(SURFACE_CLOSE sonnet literal `SKILL.md:262-264`; launcher `--model sonnet`
`claude-isolation.py:309-310`; flags `resolve-bootstrap.py:21-24,153-160`;
free-form Verification `free-form-mode.md:35-50`; terminal rule
`score-cohort.py:186-193`).

- (a) ADOPT — L2 estimand = deliverable after pair merge + permitted fix
  loop (LAYER-PRODUCT); frozen-diff judge recall stays outside the meter.
- (b) **REVISED, named delta**: sol's exact-set attestation, smoke
  conjuncts, `--model` launcher fix, and deletion of the 1 % tolerance are
  ADOPTED. Sol's switch to `--spec` mode is REJECTED: criterion
  **PRODUCT-AS-SHIPPED INTERVENTION** — free-form `--goal-file` is the
  user's workload shape for fixture-sized goals, PLAN's spec derivation is
  part of the harness value under test, spec mode would also skip
  SURFACE_CLOSE and thereby measure a harness that does not ship, and 32
  hand-authored specs on an unstated-contract corpus add an apparatus and a
  leakage surface. The SURFACE_CLOSE sonnet phase is therefore registered
  as a fixed product component with exact-set attestation, not tolerated
  by percentage. Falsifier sol should hold fable to: the smoke gate must
  show the registered key set exactly; any unexplained model id voids the
  arm design, not the row.
- (c) ADOPT — mutually exclusive decision line at δ = 3/20 (0103 shape);
  stratified within-class bootstrap; 12 retained, 16 not invented.
- (d) ADOPT — monotone top-up rule; `BOUNDED` deleted.
- (e) ADOPT — saturation re-derivation deleted (terminal); copycat removed
  from 0113; `panel.py` folded; P-0113-4 demoted to the smoke gate;
  supersession stated once.
- Unlisted 1 ADOPT — two-channel `f_ship`/`f_tree`, BLOCKED ⇒ 1.
- Unlisted 2 ADOPT with a pin — token legs added; metric pinned to OUTPUT
  tokens (sol's "total tokens" is ambiguous across cache fields; output is
  vendor-comparable). Falsifier: NORTH-STAR metric amendment.
- Unlisted 3 ADOPT — calibrator-separation wording.
- Unlisted 4 ADOPT — exact registered pair ID under frozen `CODEX_HOME`.

## Apparatus record (session 22, 2026-09-03 — pre-freeze amendments, byte-verified by fable)

- **A-1 (b) verified — INHERITS.** Native `Agent` spawns carry no model (`SKILL.md:53`). Micro-runs (`~/.local/share/nx01/iter0113-reg/b-binding.md`, envelopes `b-binding/run1..7.json`): an explicit `model "sonnet"` adds `claude-sonnet-5` to the parent `modelUsage` (the envelope sees subagents); an unpinned subagent stays on M. Finding: claude 2.1.258 adds a CLI-internal session-title call (`claude-haiku-4-5-20251001`, 8–14 output tokens) to every session unless `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`; the launcher already sets it (`claude-isolation.py:248`), the 0102 bare driver did not (it ran on pinned 2.1.226, where the call did not exist).
- **A-2 Same knobs across arms** (named delta from "reuse `mx-driver.py` byte-identical"; criterion ONLY-THE-HARNESS-DIFFERS): one claude binary for all arms (the launcher-resolved direct binary, sha pinned), effort `xhigh` for all arms, L0 env = `scrubbed_env()` + `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` + `DISABLE_AUTOUPDATER=1`; L0 argv otherwise byte-identical to `mx-driver.py:189-210`. The exact-set rule `{M}` then holds with no tolerance.
- **A-3 Launcher**: `claude-isolation.py` gains a required `--model` (arm/judge/canary modes); the `sonnet` literals are deleted; the 8 existing callers pass `--model sonnet` (argv byte-identical); `test-ceiling-harness.sh` PASS.
- **A-4 Attestation per envelope**: parent `modelUsage` == {M}; if `phases.surface_close` ran, `.devlyn/surface-close.output.json` `modelUsage` == {claude-sonnet-5} (== {M} when M is sonnet-5), else that file is absent. L1: `risk_profile.pair_default_enabled == false` ∧ `phases.verify.pair_trigger.skipped_reason == "user_no_pair"` (the schema's field names, `state-schema.md:52,58,71`) ∧ zero codex rollouts under the arm's CODEX_HOME.
- **A-5 L2 pair attestation** (named delta from R0 unlisted-4 "codex receipt attests the pair ID"): the product writes no VERIFY invocation receipt and omits `-m` (`phases/verify.md:212-221`, `_shared/invocation-receipt.py:15-16,160-164`; terra STOP upheld). Criterion MECHANICAL ATTESTATION FROM FROZEN INPUTS: staged `config.toml` = `model = "gpt-5.6-sol"` / `model_reasoning_effort = "max"` (copied from the real `~/.codex/config.toml:1-2` at freeze; digest pinned) ∧ every codex rollout under the arm's opaque CODEX_HOME shows `turn_context.payload.model == gpt-5.6-sol` ∧ ≥ 1 rollout ∧ `state.pair_verify` ∧ `codex-judge.stdout` present ∧ `sub_verdicts.pair_judge` non-null (`"TIMEOUT"` is a valid product outcome, recorded as `pair_timeout`). Codex output tokens = Σ per rollout of the final `token_count` event's `total_token_usage.output_tokens`.
- **A-6 Terminals**: harness `TIMEOUT` (BOUND_H = 3600 s = the ceiling A-arm default, `run-ceiling-arm.sh:12,140`; 0102 bare walls: opus-5 median 1.5 min, max 3.8 min) and `NEEDS_WORK` map to `f_ship = 1/1` like BLOCKED (no shippable result); `f_tree` is still scored.
- **A-7 Apparatus** (`benchmark/layer-lift/`, terra `gpt-5.6-terra`; report `/private/tmp/iter0113-terra/terra-report.md`): `run-lift-panel.py`, `score-lift.py`, `panel-quick.json` (AF2/AF1/AF5, BD2/BD3/BD4, MI5/MI3/MI6, UA2/UA3/UA5), `registered-params.json`, `scripts.sha256`, README. Self-tests 9/9 + 9/9 (fable re-run), ceiling harness suite PASS, seals 8/8. Embedded params pins stay `TBD-FREEZE` until the freeze round closes; `run`/`smoke`/`score` refuse until then.
- **A-8 Window-interruption continuation** (usage capture 03:24 KST: weekly 50 % used, reset 2026-09-07 20:01 KST; 5-hour window 72 %): `run --attempt 1 --resume` schedules ONLY the base cells absent from `rows.jsonl` for the run id, on identical frozen digests (ledger rows re-validated; refuse on drift); rows are atomic — a cell killed at a window boundary (`kill -TERM $(cat driver.pid)`, SIGTERM forwarded to the cell's process group) leaves no row and is re-run from scratch. `--resume` is invalid with attempts 2/3 and with `--smoke`. Self-test `window-interruption-resume` (10/10). No account-usage gate inside the runner: window discipline is the operator's (fable's) rule, recorded in the run log.

### Freeze round 1 record (sol `freeze-r1-sol.log`, 1007 s, `REVISE n=11`; grok 402 → skipped; fable adjudication 2026-09-03 04:00 KST)

ADOPT F-2 (normalized `apparatus_sha256` in params, scripts self-check), F-3 (`staged_intervention_sha256` over skills + CLAUDE.md + AGENTS.md + settings + engines), F-4 (quick panel refuses M == calibrator), F-5 (`classify_cli_result` ported verbatim; missing attestation unscorable; `incomplete` used), F-6 (surface-close `ran` from state only), F-8 (`all_rows_infra_valid` smoke conjunct), F-9 (saturation evaluated before other arms), F-11 (exact-id purity). F-1 KEEP as A-8 with cited failures (0110 m4/m5, 0112 venue, usage 03:24) — trimmed. **F-7 → A-5′ (named delta)**: the pair judge runs `--ignore-user-config --ignore-rules --ephemeral` (`codex-monitored.sh:150-158`), so the staged config is never read and no rollout is ever written — the rollout rule would have failed every L2 row; attestation source = the product-captured `codex-judge.stdout` header (`OpenAI Codex v0.152.1`, `model: gpt-5.6-sol` = the CLI built-in default, `reasoning effort: medium` per `verify.md:233`), codex binary pinned (sha `8194ea31…`); codex tokens = the `tokens used` TOTAL (only mechanical figure; conservative over-count on the L2 side, recorded in the receipt). F-10 AMENDED in text: stratified draws per class = class size in the panel (3 quick / 8 full). **A-6 amended (sol § 7)**: TIMEOUT is symmetric — any arm's bound expiry is a valid outcome with `f_ship = 1/1`, `f_tree` scored, attestation null permitted only there. **A-2 label (sol § 7)**: results are not comparable to historical 0102 fail rates (effort/binary differ); only within-meter deltas are claims. Deleted: `input_tokens_total`, `final_report.md` fallback. Kept with citation: row timestamps (A-8 window placement).

### Freeze round 2 record (sol `freeze-r2-sol.log`, 899 s, `REVISE n=5`; fable adjudication 04:45 KST)

CLOSED F-1/3/4/5/7/8/9/10/11. ADOPT F-2 (launcher inside `apparatus_sha256`), F-6 (`ran` = phase present ∧ not `auto_surface_close_claude_unavailable`; the adjudication-malformed recovery keeps its envelope), **F-12** (the pinned product captures streams separately — codex header + `tokens used` are in `codex-judge.stderr`, real artifact `rs-20260729T151700Z…/codex-judge.stderr:5-14,510-511`; parse stderr only, require both files), **F-13** (TIMEOUT rows carry unknown tokens ⇒ the affected token leg is `INCONCLUSIVE`; quality and wall legs unchanged), F-14 (all selected task seals validated before any launch), F-15/16 (text). Accretion adopted: orphan telemetry, non-attempt-1 history acceptance, duplicate missing-cell scan, redundant run-metadata digests, hardcoded `runner_is_frozen`, consumer-less params prose — deleted; registered diagnostics (`verification_bullets`, `fix_round_ran`, `diff_changed_by_pair`, `pair_timeout`) are now summarized in the verdict (P-0113-3 reads `diff_changed_by_pair`).

### Freeze round 3 record (sol `freeze-r3-sol.log`, 453 s, `REVISE n=3`; fable 05:15 KST)

All r2 items CLOSED except F-13's top-up corner. ADOPT F-17 (unknown-token scan covers every required cheaper-arm rep through N/M, top-ups included), **F-18** (smoke gate gains the registered wall/token-anchor conjunct: positive `wall_ms` and known positive tokens on all three rows — a pair TIMEOUT fails smoke), F-19 (P-0113-3 aggregated by task; `panel_size` = tasks). Sol's independent normalized apparatus digest before this round: `7e967c77…`.

### FROZEN — `FREEZE-0113-SOL: FREEZE` (r4, `freeze-r4-sol.log`, 322 s, 2026-09-03 05:29 KST; rounds 11+5+3→0)

`registered-params.json` sha256 `6713f3df633c70a87d60e5cc151d9d9368d5118dadf87005497db6bcba6824ec` (embedded as `PARAMS_PIN_SHA256` in both scripts); normalized `apparatus_sha256` `a20c93f76035d0f8d17ee61fb746c1afd40a3be1ba40bbcedd89770e1ffa32f5` (sol independently recomputed both); `scripts.sha256` 8/8; self-tests 20/20 + 16/16. Panel = AF2/AF1/AF5, BD2/BD3/BD4, MI5/MI3/MI6, UA2/UA3/UA5. Next = smoke gate (EQ3-AF2 × 3 arms, M = claude-opus-5) → quick panel.

### A-9 post-freeze defect at first use → RE-FREEZE (07:14 KST)

First `run --smoke` (account quiet at 07:12 after the other project's devlyn pipeline finished) was REFUSED by the writer check: it scanned the whole repo tree for `pipeline.state.json` and flagged 12 archived July workspaces (`~/.local/share/nx01/iter0113-reg/writer-check-false-positives.txt`; 435 such files exist in the repo). Registered predicate corrected to the standing rule: live `claude -p`/`codex exec`/`grok -p` processes + the repo-root `.devlyn/pipeline.state.json` only, in-flight iff `phases.final_report.verdict` is null. The root state file of the abandoned 2026-08-25 run was moved to `.stale-20260903` (machine-local, gitignored). Apparatus bytes change ⇒ pins reset, sol re-freeze round required (self-tests inject the writer check, which is why the freeze rounds could not see this).

### RE-FROZEN — `FREEZE-0113-SOL: FREEZE n=0` (r6 after A-9 + F-20; `freeze-r5-sol.log`, `freeze-r6-sol.log`; 07:39 KST)

`registered-params.json` sha256 `227a1bc0b60e3e60db53176da272c11f9ed2410f59000dd88118404f721924e2` embedded in both scripts; normalized `apparatus_sha256` `4101a78a88337d62122f58c7f2803784e659ee7fc0451c8ae76ca70b465b60dd`; seals 8/8; self-tests 20/20 + 16/16. Supersedes the 05:29 freeze digests above.

### A-10 binary pin independent of PATH (08:10 KST) → re-freeze

Second smoke attempt refused `Claude binary path/digest mismatch`: the CLI auto-updated 2.1.258 → 2.1.259 between freeze and launch. Registered fix (0102 `mx-driver.py` PIN precedent): the registered binary is copied to `~/.local/share/nx01/pins/claude-2.1.258-iter0113/claude` (sha unchanged) and every arm launches THAT path — L0 directly, L1/L2 via the launcher's explicit-binary mechanism — so PATH drift (auto-update mid-panel) cannot change the measured binary; the PATH comparison is deleted. The (b) binding evidence stays on 2.1.258 exactly.

## Not in scope

Non-coding axes (intent fidelity / decomposition / collaboration) — 0070a
modules, later. Copycat / moat — ceiling instrument (ops #17). Session
horizon — 0112 module. Cross-vendor bare (codex/grok/gemini) — requires
first showing the panel is not saturated for that engine bare (register
per engine).
