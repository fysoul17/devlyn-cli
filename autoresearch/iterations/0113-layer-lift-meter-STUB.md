---
id: "0113-layer-lift-meter"
title: "Layer-lift meter — one fixed instrument for L1−L0 (harness over bare) and L2−L1 (pair over solo), per model, minimal wall/tokens"
kind: instrument
status: APPARATUS-FROZEN r12 2026-09-03 (A-12 minimal panel: L1/L2 ×1, lanes 1, δ 6/20, task-granular drain) — next = one-command drain (smoke-3 → 72 cells → score)
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
| Reps | L0 ×4, L1 ×1, L2 ×1; lanes = 1, identical for all arms (wall comparability by symmetry). **A-12 (2026-09-03)** supersedes the registered L1 ×2 / L2 ×2 / lanes 2 — see § "A-12" below. Same on the full panel |
| Score per (task, arm, rep) — two channels | `f_tree` = hidden oracle on the final worktree (always recorded, diagnostic). **Primary `f_ship`** = `f_tree` for terminal PASS / PASS_WITH_ISSUES; **valid product BLOCKED terminals ⇒ `f_ship = 1`** (the harness declined to ship; hands-free contract); registered infrastructure / availability / attestation failures ⇒ infra-invalid, replaceable. `wall_ms`; tokens per model id |
| Estimands | reps averaged within task; `d1_t = f_L0(t) − f_L1(t)`, `d2_t = f_L1(t) − f_L2(t)`; **Δ1 = mean d1 (harness lift), Δ2 = mean d2 (pair lift)**; bootstrap **stratified within class** (resample 3 tasks per class, average the 4 class means; the panel fixed the class mixture) |
| Efficiency — wall AND tokens (NORTH-STAR names both) | `N1_wall = ceil(median wall_L1 / median wall_L0)`, `N1_tok = ceil(tokens_L1 / tokens_L0)` (tokens = OUTPUT tokens summed over all models incl. the codex receipt — the vendor-comparable generation cost; full breakdown recorded; registered assumption, falsified by a NORTH-STAR metric amendment). `E1_x = mean[best-of-N1_x L0 − f_L1]` where best-of = min `f_ship` over pre-indexed L0 reps. **Monotone top-up rule (fixed, not retuning)**: base reps first; if the best-of-4 E CI upper < 0 the leg is already `INEFFICIENT` (more cheaper-arm reps can only lower its best) — stop; otherwise run pre-indexed L0 reps 5…N1 and score exact best-of-N1. Same for E2 with L1 reps 3…M2. Top-up reps are efficiency-only, excluded from Q1/Q2. No `BOUNDED` states |
| Materiality | δ = 6/20 (**A-12**; supersedes the registered 3/20 / 0103 precedent — the harness arm costs ≈ 15× bare in wall and output tokens (smoke-1/2), so only a large quality lift can make the layer out-earn bare; at 12 tasks × 1 harness rep, ±3/20 is narrower than the attainable CI, making `NULL` unreachable and every honest outcome `INCONCLUSIVE`) |
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

### RE-FROZEN (2) — `FREEZE-0113-SOL: FREEZE n=0` (r7 after A-10; `freeze-r7-sol.log`; 08:28 KST)

`registered-params.json` sha256 `ba9bc790429126fbc110eecf02eeb48cb445481d03c1d898a84084590f252c44` embedded in both scripts; normalized `apparatus_sha256` `a831f2d34f716965c9b47a3cad05ece07c194c9377f736097b7d60763d55a717`; seals 8/8; self-tests 21/21 + 16/16. Supersedes the earlier freeze digests. Freeze ledger: r1 11 → r2 5 → r3 3 → r4 FREEZE → A-9 r5 1 → r6 FREEZE → A-10 r7 FREEZE.

### Smoke-1 (2026-09-03 10:10–10:29 KST, `~/.local/share/nx01/iter0113/smoke-1/`) → `SMOKE-0113: FAIL` — one apparatus defect (A-11) + one infra row

- L0 (opus-5 bare): 5/5 manifestations pass, 50 s, 3,822 output tokens, key set {opus-5} exactly. L1: PLAN PASS → IMPLEMENT PASS → SURFACE_CLOSE `BLOCKED:surface-close-adjudication-out-of-surface` → `BLOCKED` (VERIFY never spawned), 762 s, 61,944 output tokens, parent {opus-5} + surface envelope {sonnet-5} attested; oracle on the tree as left 2/5 failed. L2: 68 turns, then `is_error` "You've hit your session limit · resets 13:10 KST" during VERIFY — infra-invalid (correct classification), 1,052 s, 83,487 output tokens.
- **A-11** (apparatus): the L1 conjunct `phases.verify.pair_trigger.skipped_reason == user_no_pair` cannot exist when VERIFY never spawns; corrected to `pair_default_enabled == false` ∧ (verify absent ∨ `user_no_pair`) ∧ zero rollouts. Re-freeze required (terra fix7 → sol r8).
- Venue: the 5-hour session window (48 % before the smoke, shared with other projects' pipelines on this account) is the binding limit, not the weekly meter (27 % after a denominator shift) — 0110's lesson again. Smoke-2 after 13:10 KST on a quiet account; the quick panel needs night windows + `--resume`.
- Product signal (not yet a claim): bare solved EQ3-AF2 in 50 s; the harness declined to ship after 12.7 min.

### RE-FROZEN (3) — `FREEZE-0113-SOL: FREEZE n=0` (r8 after A-11; `freeze-r8-sol.log`; 12:58 KST)

`registered-params.json` sha256 `52731fd9dab43b526b87d07a862aa0dec2b6666a68abb86c30ebbc7263c0e111` embedded in both scripts; normalized `apparatus_sha256` `1cf69fb8ec73b10683836e65660cf4e4a8d770453df53c0ab0b3fe3fbb01e77b`; seals 8/8; self-tests 22/22 + 16/16. Supersedes earlier freeze digests. Freeze ledger: r1 11 → r2 5 → r3 3 → r4 FREEZE → A-9 r5 1 → r6 FREEZE → A-10 r7 FREEZE → A-11 r8 FREEZE.

### Smoke-2 (2026-09-03 14:43–14:57 KST, `~/.local/share/nx01/iter0113/smoke-2/`, dedicated account) → `SMOKE-0113: FAIL` — venue only, no apparatus defect

- Fired by session 22's launch loop (`smoke-2/launch-loop.sh`) after 30 s machine-wide quiet. L0 (opus-5 bare): 5/5 manifestations pass, 50.6 s, 3,894 output tokens, key set {opus-5}. L1 and L2: PLAN PASS → SURFACE_CLOSE PASS → IMPLEMENT in flight, then `429 rate_limit_error` "You've hit your session limit · resets 08:30 UTC" at 05:56:55Z (L1, 787 s, 59,596 output tokens, 4.78 M cache-read) and 05:57:30Z (L2, 770 s, 60,144 output tokens, 6.16 M cache-read; pair judge never spawned). Both rows `infra_invalid` (registered classification; `terminal BLOCKED:unclassified` is the unscored placeholder). Conjuncts `parent_model_exact` / `surface_close_attested_when_run` / `wall_and_token_anchors` PASS; the other four FAIL as consequences of the two infra rows. Apparatus bytes unchanged (`1cf69fb8…`, params `52731fd9…`); no A-item.
- Venue evidence: the 429's reset (08:30Z) matches the 12:33 KST capture of the dedicated account (session 9 %, resets 08:30Z, weekly 2 %; session-22 scratchpad `usage-post-smoke1.json.raw.json`), not the shared account (session resets 09:09Z, 15 % at 15:16 KST; session-23 `usage-1517.json.raw.json`). Session 23 runs on the shared account (`~/.claude.json` oauthAccount); a pinned-binary opus-5 probe at 15:20 KST returned OK there.
- **Capacity fact (two smokes, two accounts):** two concurrent harness arms of one task consumed ≥ 52 % (smoke-1: 48 % → limit) and ≤ 91 % (smoke-2: 9 % → limit) of a Max-20x 5-hour window ⇒ ≈ 25–45 % per harness cell (~13 min, ~60 k output tokens, 5–6 M cache-read tokens, 3 subagents). The registered quick panel = 48 harness cells + 48 L0 cells ⇒ ≥ 20 five-hour windows (≈ 4–6 days round-the-clock on ONE otherwise-idle account) and ≈ 2.9 M output tokens ≈ one weekly allowance (0110 m6 reached the weekly limit at 3.12 M output tokens). Not runnable as a same-day panel on any account; runnable only as a multi-day exclusive-account drain (≈ 2 harness cells per fresh window, `--attempt 1 --resume` per window). A cell killed by the limit is wasted and re-run.
- Product signal (n=1 per smoke, not a claim): bare solved EQ3-AF2 in 50 s / 3.9 k tokens both times; the harness arm spent 12.5–13 min / 60 k tokens and either declined to ship (smoke-1 L1) or was still in IMPLEMENT (smoke-2). Logged for the 0073 bottleneck ledger (residual + VERIFY).
- Open user decision (recorded, not taken): venue + schedule for the registered panel — HANDOFF START-HERE.

### A-12 minimal quick panel + task-granular window drain (2026-09-03 18:50 KST, user ruling after smoke-2) → re-freeze r9

User ruling (verbatim intent): run with the minimum, on the shared machine login, coexisting with the user's own sessions — no dedicated account. Named deltas from the frozen registration, each with its criterion:

- **Reps** L1 2→1, L2 2→1 (L0 stays 4 — 50 s cells): harness cells 48→24. Criterion CAPACITY-AT-THE-VENUE — one harness cell ≈ 25–45 % of a Max-20x 5-hour window (smoke-1/2 bytes); 24 cells ≈ 12 windows ≈ 2.5 days at one task per window, ≈ half a weekly allowance.
- **Lanes** 2→1 (symmetric for all arms): two concurrent harness cells killed both smokes; serial cells fit one per half-window.
- **Materiality** δ 3/20→6/20: see the Fixed-elements row. Decision line, estimands, bootstrap, predictions P-0113-1..3 unchanged (P-0113-1's falsifier `HARM` now means CI_upper < −6/20).
- **`--task` in non-smoke `--attempt 1 --resume` runs**: the ledger validates against the full panel, only that task's missing base cells are scheduled. Purpose: one task (L0 r1 → L1 → L2 → L0 r2-4, ≈ 30 min) per fresh window, launched by the operator loop. No account-usage gate inside the runner (A-8 stands).
- **Operator loop `benchmark/layer-lift/drain-quick.py`** (unsealed operator tooling, outside `APPARATUS_FILES`; never writes rows or scores): self-detaches (`os.setsid`), gate = no live `claude -p`/`codex exec`/`grok -p` ∧ five-hour usage ≤ 10 % (`usage-capture-0112.py`, quota-free) ∧ outside 23:00–01:00 KST; step 0 smoke (skipped when `smoke/smoke.log` already holds `SMOKE-0113: PASS`) → attempt-1 drain task by task → attempts 2/3 for infra-invalid rows → `score-lift.py score` → `LIFT-0113:`/`NEEDS_TOPUP` line in `drain.log`. Top-ups stay an operator step.
- Dropped from the proposal: "hard tasks first" — the 12 panel tasks are all q_cal ≈ 1/2 by construction, so difficulty ordering has nothing to order; the runner's class-sorted order stands.
- Not changed: launch argv per arm, attestation predicates, smoke conjuncts, panel derivation, corpus seals.

Freeze lane: pins reset to `TBD-FREEZE` → terra fix8 (`terra13.log`, 1430 s; self-tests 24/24 + 16/16 + drain 3/3, seals 8/8, ceiling suite + lint PASS) → sol r9 (`freeze-r9-sol.log`, 487 s) `REVISE n=3`, all ADOPTED by fable (operator-path reachability, the 0110 A6 lesson): **F-21** busy-refused / nonzero task runs were skipped, so missing cells surfaced only at scoring → the task pass repeats until every task is NO-JOBS (cap 3 passes, then STOP; same for attempts 2/3); **F-22** the scorer's registered `PANEL_SATURATED` terminal was not recognized by the drain (`STOP scorer rc=0`, no `drain.done`) → accepted as a terminal; **F-23** the scorer's full output plus the extracted line put two terminal tokens in `drain.log` → scorer output goes to `score.log`, `drain.log` carries exactly one. Sol independently recomputed apparatus `1e314e0d…` and params `56cdc14d…`; runner/scorer/params bytes unchanged by the fixes (drain only). → terra fix9 (`terra14.log`; drain self-test 6/6) → sol r10 (`freeze-r10-sol.log`) `REVISE n=3`, all ADOPTED — every one a reachability corner of the operator path, none touching sealed bytes: **F-24** attempts 2/3 have no resume (A-8) and the runner refuses once a partial attempt-N pass committed rows (`run-lift-panel.py:1407`) → the drain retries attempts 2/3 only on preflight-busy refusals and STOPs naming the pending infra-invalid cells otherwise; **F-25** with all L0 rows saturated the runner refuses every launch (`PANEL_SATURATED: further scheduling refused`, `:1534`) while the scorer gives saturation precedence (`score-lift.py:651`) → that refusal routes straight to scoring; **F-26** re-invoking after `drain.done` scored again and appended a second terminal line → refuse to start when `drain.done` exists. → terra fix10 (`terra15.log`; drain 9/9) → sol r11 (`freeze-r11-sol.log`) `REVISE n=1` ADOPTED: **F-27** STOP diagnostics after a partial attempt listed only previous-attempt infra cells → every STOP names all latest infra-invalid cells, the previous-attempt predicate is kept only for the "run attempt N?" decision. → terra fix11 (`terra16.log`; drain 10/10) → sol r12 `FREEZE n=0`.

### RE-FROZEN (4) — `FREEZE-0113-SOL: FREEZE n=0` (r12 after A-12; `freeze-r12-sol.log`; 2026-09-03 20:05 KST)

`registered-params.json` sha256 `56cdc14de95950c21676e062fec3e9a8b61cfc013965d33d7fdfa7801dbd26be` embedded in both scripts; normalized `apparatus_sha256` `1e314e0dcf4a08e9761921510033d1283cb49e76576f52b51347b35db1f697e4` (sol recomputed both in r9–r12); seals 8/8 (`drain-quick.py` deliberately unsealed operator tooling); self-tests 24/24 + 16/16 + drain 10/10; ceiling suite + lint PASS. Supersedes earlier freeze digests. Freeze ledger: r1 11 → r2 5 → r3 3 → r4 FREEZE → A-9 r5 1 → r6 FREEZE → A-10 r7 FREEZE → A-11 r8 FREEZE → A-12 r9 3 → r10 3 → r11 1 → r12 FREEZE. Next = `drain-quick.py` one command (HANDOFF START-HERE): smoke-3 → 24 harness + 48 L0 cells serially → score.

### A-13 Codex pin independent of PATH + pair model re-pin (2026-09-05 09:52 KST, cold-start blocker) → re-freeze r13

Observed at session-24 cold start: the Codex CLI at the registered nvm path had auto-updated 0.152.1 → 0.153.4 at 09:52 KST (no npm install log → not a manual install), so the frozen preflight refused `Codex binary path/digest mismatch`; under a bare `CODEX_HOME` (what `stage_codex_home` stages) the CLI's default flagship is now `gpt-6-astra` (probe: header shape unchanged, `reasoning effort: medium` with the product's pair-JUDGE flag, `SKILL.md:347`). Same failure class as A-10 (Claude auto-update); the Codex pin had been left on the mutable path. Named deltas, each with its criterion:

- **Pair pin** → snapshot `~/.local/share/nx01/pins/codex-0.153.4-iter0113/codex` (sha256 `b973d440…`), `codex_cli_version` 0.153.4, `model_id` `gpt-6-astra` (= the shipped product's default flagship, `codex-config.md` omit-`-m` rule), `effective_effort` medium unchanged. Criterion PATH-INDEPENDENT PIN (A-10 precedent): every harness arm launches the snapshot via `CEILING_TEST_CODEX_BIN` → `claude-isolation.py:417` → frozen PATH (`:121-123`); launcher metadata `direct_codex` attested per cell like `direct_claude`; preflight validates both pins with one `registered_binary` helper; the PATH-based `resolve_codex_binary`/`codex_probe` path deleted. Production −12 lines, self-tests +21 (the parser fixture follows the registration by design, `:1739`; new `path-independent-codex-pin-refusal`).
- **Seats**: user direction 2026-09-05 — verification trio = fable + codex `gpt-6-astra` (read-only, omit `-m`) + grok 4.6 (402 cleared, probe OK). terra lane = codex `gpt-6-astra` workspace-write.
- Not changed: predictions P-0113-1..3, decision line, δ 6/20, reps, lanes, panel, corpus seals, scorer semantics, drain-quick.py.

Lane: terra r1 (`terra1.log`, 101 s) STOP — correct: the packet claimed the parser fixture was params-independent, but `:1739` validates it against live params → packet r2 → terra r2 (`terra2.log`, 581 s) → seals 8/8, self-tests 25/25 + 16/16 + 10/10, `--derive-panel` byte-identical, lint + nodeg/isolation self-tests PASS (fable re-ran all of them on the same bytes) → parallel freeze review: sol r13 (`sol1.log`, 432 s, codex `gpt-6-astra` read-only) `REVISE n=1` — F-1 C1 reachability PASS (independent resolution → snapshot, different inode from nvm; injected missing/drift pins refuse), F-2 attestation PASS, F-4 subtractive PASS, F-5 outcome-blind PASS, **F-3** = its read-only sandbox could not execute the self-tests (no scratch dir), a verification-environment gap → closed by fable's raw acceptance lines, sol micro `FREEZE n=0` (`sol2.log`); grok r13 (`grok1.log`, 671 s, grok 4.6 static) `FREEZE n=0` with 4 NOTEs — F-1 pin lstat/digest (closed: regular file, `b973d440…`), **F-2 sibling-independence** (the single-file snapshot dropped the bundled `codex-path/rg` / `codex-resources/zsh`; 0144.5 pin precedent copied the full vendor dir) → **accepted fix taken**: pin rebuilt as the full `aarch64-apple-darwin` vendor tree + `provenance.json`, `codex_binary_path` → `…/codex-0.153.4-iter0113/bin/codex` (digest unchanged; params `44f34b2e…`, apparatus unchanged `9a40ae66…`, seals 8/8, self-tests re-run PASS), reachability proved by execution: from the pin with `env -i PATH=/usr/bin:/bin` (no nvm/homebrew) the header reads `v0.153.4 / gpt-6-astra / medium` and the shell tool resolves `rg` to `<pin>/codex-path/rg` (ripgrep 15.2.0); `otool -L` = system libraries only; F-3 executing-seat evidence (closed, same lines as sol F-3); F-4 NOTE — the self-test's parent-PATH `which("codex")` conjunct (`:1821-1824`) is not a reachability proof → deferred to the next apparatus edit (non-blocking; the proof is the probe + per-cell `direct_codex` attestation). Final micro-round on the vendor-tree bytes: sol (`sol3.log`) + grok (`grok3.log`) — see RE-FROZEN (5).

### RE-FROZEN (5) — `FREEZE-0113-A13: FREEZE n=0` ×2 (sol `sol3.log` 142 s, 10:37 KST; grok 4.6 `grok4.log`, 10:46 KST; r13 after A-13, 2026-09-05)

`registered-params.json` sha256 `44f34b2ec98b38cd33d02140cc3ba6da5ab0953471ebe3d536713f85a4781225` embedded in both scripts; normalized `apparatus_sha256` `9a40ae66e23c9065a18fbb5dd652fbf8d8dea2a9767b05781e35611157ae0acf` (sol recomputed both; grok string-level); seals 8/8; self-tests 25/25 + 16/16 + 10/10; lint + nodeg/isolation self-tests PASS. Supersedes the r12 digests. Freeze ledger: r1 11 → r4 FREEZE → A-9 r6 FREEZE → A-10 r7 FREEZE → A-11 r8 FREEZE → A-12 r9 3 → r10 3 → r11 1 → r12 FREEZE → **A-13 r13 sol REVISE 1 (env-only) / grok FREEZE (4 NOTEs) → vendor-tree re-pin → micro sol FREEZE + grok FREEZE**. Deferred NOTE (grok F-4): the test-only parent-PATH `which("codex")` conjunct at `run-lift-panel.py:1821-1824` is not a reachability proof — fold into the next apparatus edit, never alone. Drain LAUNCHED 2026-09-05 10:47 KST (session 24, commit `6db18ab` clean tree): `~/.local/share/nx01/iter0113/quick-1/`, `drain.pid` 58955; first gate read `blocked: supported CLI session is active; five_hour.utilization=25% exceeds 10%` (the user's other sessions — by design it waits). Smoke-3 + panel outcome → next session records here.

## Not in scope

Non-coding axes (intent fidelity / decomposition / collaboration) — 0070a
modules, later. Copycat / moat — ceiling instrument (ops #17). Session
horizon — 0112 module. Cross-vendor bare (codex/grok/gemini) — requires
first showing the panel is not saturated for that engine bare (register
per engine).
