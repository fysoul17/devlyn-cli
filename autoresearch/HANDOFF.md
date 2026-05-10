# HANDOFF — for the next session

**Read order on cold start (mandatory)**:
1. **This file** — operating context + active iter + Codex collab protocol
2. [`NORTH-STAR.md`](NORTH-STAR.md) — project goal + 3-layer composition contract + pair-mode policy (round-3 redesign 2026-05-03)
3. [`PRINCIPLES.md`](PRINCIPLES.md) — pre-flight 0 + #1-#7 (every iter cites)
4. [`MISSIONS.md`](MISSIONS.md) — Mission 1 active, hard NO list
5. The active-iter file (currently `iterations/0036-headroom-candidates.md`; design baseline at `iterations/0034-phase-4-cutover.md` § "CLOSURE — SHIPPED 2026-05-04" + `iterations/0035-prelim-tower-defense.md` § "CLOSURE — CLOSED-PRELIM-PASS 2026-05-04" — pre-flight harness-on-greenfield risk now retired)
6. [`DECISIONS.md`](DECISIONS.md) — append-only ship/revert log (most recent entries first to read)

If any file contradicts another, **NORTH-STAR.md wins**, then this file, then PRINCIPLES.md. Open a doc-fix iter on the contradiction.

Last refined 2026-05-10 (iter-0036 headroom work OPEN-PARTIAL: F10/F11/F12/F15 are useful regression fixtures but NOT pair-measurement fixtures; pathBeta scores saturated at bare 94-99 / solo 96-99. Follow-up run `hiddenF10-20260505T123128Z` moved F10 behavior verifiers outside the arm worktree and bare still passed 4/4 in 186s, so F10 is simply too easy, not merely answer-key-contaminated. F17/F18/F19/F20 were rejected/removed after timeout, solo saturation, or hidden-oracle fairness failure. F19 exposed a real hidden-oracle leak: pre-IMPLEMENT `.devlyn/spec-verify.json` included `BENCH_FIXTURE_DIR` verifier command paths, and solo searched for filenames like `exact-success.js`; `run-fixture.sh` now filters those hidden commands out of BUILD_GATE staging while preserving post-run verification. F16 and F20 initially passed headroom after the leak fix, but fairness audit found both passes depended on hidden exact error-shape requirements narrower than the visible spec. After making those contracts explicit, F20 failed at bare 25 / solo 96 and was removed; F16 failed at bare 50 / solo 97. Additional drafts also failed or were invalid: F17 invoice proration bare 28 / solo 96, F18 fulfillment optimizer apparent bare 40 / solo 80 invalid after correcting an unfair `hub` vs `backup` verifier tie-break, and F19 redactor bare 78 / solo 96. A later fair `F17-cli-fare-capping` draft lowered bare to 20 but still failed at solo 92 after 5/5 verifiers, so it was also removed. F21/F23 provided the first fair full-pipeline headroom control set (`20260507-f21-f23-full-pipeline-pair/headroom-gate.json`: both bare 33, solo 66), but later risk-probe diagnostics showed fixture-oracle ambiguity rather than clean pair proof: F21 v13 tied solo and timed out around the window-bound interpretation, and F23 v14 tied solo while exposing rollback hidden-oracle inconsistency plus a scope-widened pair-JUDGE false positive. F16 v15 is now the first clean full-pipeline risk-probe `bare < solo < pair` proof (`20260507-f16-riskprobes-v15-pricing-diagnostic/full-pipeline-pair-gate.json`: 50 -> 75 -> 96, +21, `pair_mode=true`, verifier 4/4, wall ratio 1.28x). Hidden `BENCH_FIXTURE_DIR` verification commands now require `verification_commands[].contract_refs`, and `scripts/lint-fixtures.sh` requires each ref to be an exact substring of `spec.md`; this mechanically blocks hidden oracles from silently requiring contracts absent from the visible spec. F12's pair-discovered duplicate-body oracle gap is now a hidden verifier, but headroom rerun `20260505T183636Z-9986cd3-headroom` still failed at bare 76 / solo 94; F12 is regression/frozen-VERIFY evidence, not a full-pipeline headroom candidate. Frozen VERIFY runner now detects archive-ready state, rejects empty diffs, cleans worktree-matched orphan processes, and `l2_forced` full-pipeline arm is retired because it leaks `--pair-verify` before IMPLEMENT. F12 forced/gated frozen runs proved clean pair verdict lift on the duplicate replay bug; a post-guard rerun proved gated trigger stability but initially missed the HIGH, exposing root cause: JUDGE treated a representative replay verifier as proof of the whole `once` / `body irrelevant` / permanent-id invariant. VERIFY now requires clause-level requirement splitting and code-order counterexample tracing; pair JUDGE is adversarial complement, not duplicate summary. Post-change F12 gated run `20260505T173913Z-9986cd3-frozen-verify` recovered lift: solo `PASS_WITH_ISSUES`, pair `NEEDS_WORK`, `pair_judge=NEEDS_WORK`, `pair_mode=true`, `pair_verdict_lift=true`, with Codex HIGH `duplicate-shape-check-preempts-permanent-replay`. F10 gated frozen run `20260505T230215Z-9986cd3-frozen-verify` also confirmed the explicit `--engine claude` root-guard fix: pair mode fired naturally, solo `PASS_WITH_ISSUES`, pair `NEEDS_WORK`, and `pair_verdict_lift=true`. `frozen-verify-gate.py` now mechanically gates that evidence; the original internal two-run gate PASSes on F12+F10, and the SWE-bench Lite n11 gate PASSes with wall-ratio cap 3. The F10 run exposed and then fixed a metadata-probe cleanup bug: `scripts/codex-shim/codex` now returns `codex-cli unknown (version-probe-skipped)` for `--version` without delegating to Superset-style wrappers that can orphan descendants. Runner summary now reads `verify-merged.findings.jsonl` first so pair HIGHs appear in severity counts. `run-fixture.sh` now kills worktree-matched descendant process groups after timeout and after clean arm exit, because F21/F23 diagnostics exposed orphaned pair judge processes. OPERATIONAL-MILESTONE still holds: L1 solo + CLAUDE.md + AGENTS.md frozen pending real-world feedback; no solo prompt/doc iteration unless user reports a specific failure. **Direction**: 솔로도 그대로 잘 동작하고 페어는 empirically lifts가 있는 phase에만 shipping evidence를 붙인다; full-pipeline L2 now has a clean three-fixture F16+F23+F25 aggregate risk-probe PASS gate, while broad product claims still require more validated fixtures or real-project evidence.)

2026-05-10 addendum: full-pipeline risk-probe evidence now has a three-fixture aggregate PASS gate: `20260510-f16-f23-f25-combined-proof` scores F16 50 -> 75 -> 96, F23 33 -> 66 -> 97, and F25 25 -> 75 -> 99, with average pair/solo wall ratio 1.73x. F29 tenant adjustment auth was rejected after hidden-oracle fairness correction: `20260510-f29-headroom-v2` failed at bare 25 / solo 92, so it is not headroom or pair evidence.

Latest frozen VERIFY check: F11 `20260506T000258Z-9986cd3-frozen-verify` is useful as recall evidence only. Gated pair fired (`pair_mode=true`, no missed trigger) and found MEDIUM/LOW pair-only issues, but solo `PASS` vs pair `PASS_WITH_ISSUES` leaves `pair_verdict_lift=false`, so it is excluded from the passing gate corpus. The same run fixed a runner-summary blind spot: when no `verify-merged.findings.jsonl` exists, `run-frozen-verify-pair.sh` now combines primary and pair judge findings instead of dropping `verify.pair-judge.findings.jsonl`.

SWE-bench bridge added 2026-05-06 after user asked for widely-known benchmark validation: `fetch-swebench-instances.py` fetches Lite/Verified/Full rows from Hugging Face dataset-server into JSONL without extra Python deps; `prepare-swebench-solver-worktree.py` prepares clean local solver worktrees/specs without exposing gold `patch` / `test_patch`; `collect-swebench-predictions.py` converts `<instance_id>/patch.diff` solver logs into official prediction JSONL; `prepare-swebench-frozen-case.py` converts one SWE-bench-style instance JSON plus a fixed candidate patch into `benchmark/auto-resolve/external/swebench/cases/<instance_id>/`; `prepare-swebench-frozen-corpus.py` accepts the official prediction JSONL shape (`instance_id`, `model_name_or_path`, `model_patch`) for bounded batch prep; `run-swebench-frozen-corpus.sh` executes a prepared manifest, gates the produced run ids, and supports `--gate-only-run-ids` to re-gate existing runs without providers; `run-frozen-verify-pair.sh` now accepts `--fixtures-root`, `--base-repo`, and `--prepare-only` so frozen VERIFY can run against external repos checked out at `base_commit`; `test-swebench-frozen-case.sh` validates importer + external patch application without provider calls. This is an accepted external fixed-diff review corpus path, not official SWE-bench solve-rate measurement.

SWE-bench pilot result: after public prediction-source audit found no directly downloadable Lite prediction JSONL, local direct-solver predictions were generated without reading gold patches. `frozen-verify-gate.py --min-runs 11 --max-pair-solo-wall-ratio 3` PASSes on `django__django-11019`, `astropy__astropy-14182`, `django__django-10914`, `astropy__astropy-7746`, `astropy__astropy-14365`, `django__django-11283`, `django__django-11564`, `django__django-11742`, `django__django-11815`, `django__django-12700`, and `django__django-13220`; artifact `benchmark/auto-resolve/results/swebench-lite-proof-gate-n11.json` records average pair/solo wall ratio 1.87x. The latest broader matrix artifact `benchmark/auto-resolve/results/swebench-lite-first25-plus-26-50-bounded-matrix.md` records 48 completed rows: 11 gate rows, 37 excluded/recall/no-lift/failed rows, gate rate 0.229, and 0 trailing non-gate rows; `swebench-frozen-matrix.py` can enforce this as a yield gate with `--min-gate-rate` / `--max-trailing-non-gate`. Later Django rows `django__django-11039`, `django__django-11049`, `django__django-11179`, `django__django-12747`, `django__django-12915`, `django__django-12983`, `django__django-13028`, and `django__django-13033` were no-lift; `django__django-11099`, `django__django-11133`, `django__django-11583`, `django__django-11620`, `django__django-11630`, `django__django-11797`, `django__django-11848`, `django__django-12708`, `django__django-12856`, `django__django-12908`, and `django__django-13158` were recall-only/advisory rows; `django__django-11422` had verdict lift but missed the strict wall-ratio cap; bounded 26-30 partial rows did not extend the gate (`django__django-11905` timeout, `django__django-11964` recall-only advisory, `django__django-11999` recall-only after solo `NEEDS_WORK`); bounded 31-32 retry also did not extend the gate (`django__django-12125` pair timeout at 602s after solo PASS reuse; `django__django-12184` solo PASS at 304s, pair PASS_WITH_ISSUES with pair mode true but timeout at 602s); bounded 33-35 did not extend the gate (`django__django-12284` pair timeout after solo PASS, `django__django-12286` pair timeout/trigger missed after solo PASS_WITH_ISSUES, `django__django-12308` pair-mode recall-only PASS_WITH_ISSUES); bounded 36-38 did not extend the gate (`django__django-12453` no-lift PASS/PASS, `django__django-12470` pair timeout, `django__django-12497` no-lift PASS/PASS); rows 39-40 added one control and one proof (`django__django-12589` no-lift PASS_WITH_ISSUES/PASS_WITH_ISSUES; `django__django-12700` solo PASS -> pair NEEDS_WORK, wall ratio 0.80x); rows 46-50 added four controls plus one proof (`django__django-13220` solo PASS_WITH_ISSUES -> pair NEEDS_WORK, wall ratio 1.62x). Scaling infra now includes `run-swebench-solver-batch.sh` and `swebench-frozen-matrix.py`; provider child stdin is redirected from `/dev/null` so a child cannot consume later manifest rows. The first 21-25 frozen corpus attempt hit local disk exhaustion after generated SWE-bench solver caches/worktrees accumulated; ignored worktrees/caches were removed and the remaining frozen rows were rerun to produce the gate. `run-frozen-verify-pair.sh` now archives/summarizes judge-specific findings files such as `verify.findings.judge-codex.jsonl`, ignores non-finding `severity: PASS` JSONL lines, and preserves pair recall evidence in matrix rows. Django 11019 also exposed and fixed a VERIFY policy bug: high-confidence MEDIUM behavioral regressions are now verdict-binding when they identify concrete regressions against the spec/public contract/existing tests. `frozen-verify-gate.py` now accepts internal pair lift (`pair_judge` stricter than pair primary judge) to avoid stochastic primary-judge confounding. Empty `verification_commands` in imported frozen-review cases no longer stage an empty `.devlyn/spec-verify.json`; `django__django-11001` rerun `swebench-pilot-new2-django-11001-vbind2` confirmed mechanical `PASS` in both arms and no verdict lift.

First30+ follow-up mostly produced controls, with two later proof extensions. `instances-lite-first30.jsonl` identified rows 26-30 as `django__django-11905`, `django__django-11910`, `django__django-11964`, `django__django-11999`, and `django__django-12113`. Solver patches were produced for 11905/11964/11999, while 11910 and 12113 were stopped as long-tail throughput failures. `run-swebench-solver-batch.sh` now creates missing solver roots before redirecting prepare metadata. Bounded frozen VERIFY over the three non-empty predictions used `--timeout-seconds 600`: 11905 solo 431s then pair timeout 603s; 11964 solo `PASS` vs pair `PASS_WITH_ISSUES` with 42 LOW findings; 11999 solo and pair both `NEEDS_WORK`. `swebench-lite-26-30-bounded-gate.{json,md}` FAILs 0/3. Rows 31-32 (`django__django-12125`, `django__django-12184`) have solver patches; the post-reset retry reused 12125's completed solo arm via `--resume-completed-arms` and converted the earlier provider-limit controls into bounded timeout controls. `swebench-lite-31-32-bounded-gate.{json,md}` still FAILs 0/2: 12125 pair timed out at 602s and exceeded the 3x wall-ratio cap; 12184 pair fired but timed out at 602s and only reached `PASS_WITH_ISSUES`. Rows 33-35 (`django__django-12284`, `django__django-12286`, `django__django-12308`) all produced solver patches, but `swebench-lite-33-35-bounded-gate.{json,md}` FAILs 0/3. Rows 36-38 (`django__django-12453`, `django__django-12470`, `django__django-12497`) all produced solver patches, but `swebench-lite-36-38-bounded-gate.{json,md}` FAILs 0/3. Rows 39-40 produced solver patches; `swebench-lite-39-40-gate.{json,md}` FAILs as a two-row tranche because 12589 is no-lift, but row 40 separately PASSes `swebench-lite-39-40-row40-gate.{json,md}` and extends the strict proof corpus. Rows 41-45 produced only controls; rows 46-50 produced one new strict proof (`django__django-13220`) plus four controls. `swebench-lite-first25-plus-26-50-bounded-matrix.{json,md}` includes all bounded rows as controls/proof rather than dropping them. Use resumable small tranches plus gate-only/matrix artifacts rather than one unbounded interactive run.

Latest benchmark status (2026-05-10):

| Surface | Best artifact | Result | What it proves |
|---|---|---|---|
| Frozen VERIFY on internal fixed diffs | `benchmark/auto-resolve/results/20260505T173913Z-9986cd3-frozen-verify`, `benchmark/auto-resolve/results/20260505T230215Z-9986cd3-frozen-verify` | PASS | Pair review can catch verdict-binding issues solo missed when the implementation diff is frozen before pair context appears. |
| Frozen VERIFY on SWE-bench Lite fixed diffs | `benchmark/auto-resolve/results/swebench-lite-proof-gate-n11.{json,md}` | PASS, 11 rows, avg pair/solo wall ratio 1.87x | The fixed-diff review harness has external-corpus evidence under a 3x wall-time cap. |
| SWE-bench selection-bias control matrix | `benchmark/auto-resolve/results/swebench-lite-first25-plus-26-50-bounded-matrix.{json,md}` | 48 completed rows: 11 gate, 37 controls, gate rate 0.229 | The n11 proof is preserved without hiding no-lift, recall-only, wall-ratio-excluded, solo-dominated, or timeout rows. |
| Full-pipeline headroom controls | `benchmark/auto-resolve/results/20260507-f21-f23-full-pipeline-pair/headroom-gate.{json,md}` | INVALIDATED: F21/F23 initially looked like 33 -> 66 headroom | Later verifier replay exposed hidden-oracle bugs. After correction, solo reaches the hidden contracts, so this is oracle-control evidence rather than fair headroom. |
| Full-pipeline pair, standard gated path | prompt-fix through collectfix reruns in `benchmark/auto-resolve/results/` | FAIL | Pair fired after infrastructure fixes but tied or regressed on F21/F23; this path still has no clean pair lift. |
| Full-pipeline pair, risk-probe controls | `benchmark/auto-resolve/results/20260507-f21-riskprobes-v13-windowbound-diagnostic`, `benchmark/auto-resolve/results/20260507-f23-riskprobes-v14-rollback-diagnostic` | INVALID controls | F21 exposed a hidden verifier that rejected a valid later placement; F23 exposed a hidden verifier that rejected a valid later low-priority allocation. Both were corrected and no longer count as proof candidates. |
| Full-pipeline pair, risk-probe proof | `benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.{json,md}` | PASS: F16 50/75/96, F23 33/66/97, F25 25/75/99, avg wall ratio 1.73x | Three-fixture aggregate proof that the harness can produce `bare < solo < pair` under risk probes; still not broad product superiority. |

Next focused run is optional broadening only: pick a visible-contract fixture with fresh headroom evidence, avoid F29's API-auth/idempotency shape unless the solo ceiling is demonstrably lower, and preserve rejected rows instead of hiding them.

---

## 🚦 START-HERE — three things active right now

1. **OPERATIONAL MILESTONE 2026-05-04: L1 solo + CLAUDE.md + AGENTS.md frozen pending user real-world feedback.** User 2026-05-04 wrapped up solo+docs work and committed to validating /devlyn:resolve organically via personal-project usage. Next iter starts only on (a) user real-usage failure report → corrective iter, (b) frozen VERIFY/review pair evidence from fixed diffs, OR (c) explicit user direction to resume full-pipeline L2 work, which itself requires the headroom-benchmark precondition (see point 3). Forbidden until user surfaces a specific failure mode: no iteration on L1 solo skill prompts / CLAUDE.md / AGENTS.md / `_shared/` files. "Looks like it could be cleaner" is drift per CLAUDE.md Goal-locked execution.

2. **iter-0035-prelim CLOSED-PRELIM-PASS 2026-05-04 — pre-flight risk retired.** Hands-free /devlyn:resolve trial on greenfield tower-defense (TypeScript + Vite + Phaser 3 + Vitest + Playwright) PASS in single invocation, 957s harness internal, all 5 phases PASS, surprise PASS on predicted-FAIL Gate (c). 3 Codex rounds (R0 + R-0.5 + R-final). Does NOT close Mission 1 / does NOT open Mission 2 — pre-registered binding upheld. Closure at `iterations/0035-prelim-tower-defense.md` § "CLOSURE — CLOSED-PRELIM-PASS 2026-05-04". **Mission 1 status**: NOT formally CLOSED (full NORTH-STAR test #15 axes — external developer + existing real codebase + shipment acceptance — still missing), but operational milestone reached and pre-flight harness-on-greenfield risk retired. Full iter-0035 evidence will accumulate organically via user usage rather than a discrete trial.

3. **HEADROOM-FIRST RULE for full-pipeline L2 work (binding, user 2026-05-04 directive; mechanically gated 2026-05-05).** Before any full-pipeline L2 pair-mode iter is pre-registered, candidate fixtures must pass `python3 benchmark/auto-resolve/scripts/headroom-gate.py --run-id <run-id>`: at least two fixtures, each with bare scores <= 60 and solo scores <= 80, both clean. `run-full-pipeline-pair-candidate.sh` now enforces that order by running `bare` + `solo_claude` first and spending `l2_gated` only after headroom passes; `full-pipeline-pair-gate.py` then requires clean bare/solo/l2 artifacts, captured `pair_mode=true`, same-judge `l2_gated - solo_claude >= +5`, at least two fixtures, and optional pair/solo wall-ratio cap. iter-0036 F10/F11/F12/F15 FAILED headroom (pathBeta: bare 94-99 / solo 96-99), corrected F16/F20 failed after hidden exact error-shape contracts were made visible, and later fair drafts failed by solo ceiling or disqualifier, so do not use their full-pipeline scores as pair evidence. F21/F23 are now invalidated oracle controls, not fair headroom fixtures. Frozen VERIFY/review is the measured exception because the implementation diff is fixed before pair context appears: `run-frozen-verify-pair.sh` runs that path, and `frozen-verify-gate.py` currently PASSes on distinct internal fixtures F12 `20260505T173913Z-9986cd3-frozen-verify` plus F10 `20260505T230215Z-9986cd3-frozen-verify`, and on an eleven-run SWE-bench Lite pilot (`django__django-11019`, `astropy__astropy-14182`, `django__django-10914`, `astropy__astropy-7746`, `astropy__astropy-14365`, `django__django-11283`, `django__django-11564`, `django__django-11742`, `django__django-11815`, `django__django-12700`, `django__django-13220`) with artifacts at `benchmark/auto-resolve/results/swebench-lite-proof-gate-n11.{json,md}`. The SWE-bench first25 plus bounded 26-50 matrix preserves the 37 non-gate rows, including no-lift, recall-only/advisory, one wall-ratio-excluded lift row, one solo-mechanical-dominated row, and bounded timeout rows. The SWE-bench gate enforces `--max-pair-solo-wall-ratio 3` for that artifact.

**Mission 2 (parallel-fleet substrate)**: still BLOCKED on full iter-0035 PASS (or accumulated-real-usage equivalent the user explicitly accepts as #15 evidence). Hard NO list unchanged.

Everything below this fold supports those three.

---

## ⛔ Hard operating rules (binding)

### Rule 1 — Pair-review IS the work

Every non-trivial claim must be Codex-verified at the time of writing. Don't trust paraphrases; open the cited file:line. R-final BEFORE commit when results surprise you. Recent rounds caught (a) round-2 burden-reversal on solo-ceiling claims, (b) iter-0033c IMPLEMENT-leak diagnosis, (c) NORTH-STAR stale anchors at multiple line ranges.

### Rule 2 — Cost framing is BANNED

Memory `feedback_no_cost_talk.md` (HARD). Never use "paid run", "model invocation cost", "spendy", "$X-Y", or any cost-coded equivalent. Effectiveness × accuracy × reasonable wall-time are the axes.

### Rule 3 — Verify before claim

Every cited file:line opened at citation time. Stale HANDOFF references caused fabrication risk in past iters — verify, don't paraphrase from prior context.

### Rule 4 — Explain simply (Korean, decision-maker view)

Plain Korean. Lead with conclusion + options + recommendation. Drop internal labels (iter numbers OK in artifacts; P1-P7 / α-ε / etc. NOT in user-facing summaries). Define technical terms inline.

### Rule 5 — Greenfield interface, NOT mechanisms

The 2-skill redesign deletes skill surface area while preserving `build-gate.py` mechanisms, `spec-verify-check.py`, state discipline, one-spec-at-a-time pattern. Any redesign edit must justify why a learned mechanism is being changed (not just relocated).

### Rule 6 — Round-3 measurement-gated pair policy (added 2026-05-03)

Pair-mode is gated by per-phase measurement evidence, not by architectural default. Ship only after pre-registered L1-vs-L2 evidence shows quality lift, no wall regression, no hard-floor regression, no phase-contamination leak. "No evidence pair needed" is **not** the same as "evidence solo wins" — honest label is "unmeasured".

---

## 🤝 Codex pair-collab protocol (mandatory for non-trivial work)

Per `feedback_codex_collaboration_not_consult.md`:

- **Multi-round, not one-shot.** R0 (design) + R0.5 (push back on adopted/contested items) + R-final (post-test interpretation when surprised). Round-3 pair-redesign 2026-05-03 used 3 rounds × 3 levels (R0+R0.5+R-final each round) to reach convergence after user rejected R-final twice.
- **Position-stating, not verdict-asking.** State position with evidence; Codex pushes back; iterate.
- **Convergence is the stop.** Not "Codex agreed." Codex must read codebase directly and form independent verdicts; don't just package context for him.
- **Per-round prompt shape**: rich evidence + falsification ask + my response to prior round. Use:
  ```bash
  bash config/skills/_shared/codex-monitored.sh \
    -C /Users/aipalm/Documents/GitHub/devlyn-cli \
    -s read-only \
    -c model_reasoning_effort=xhigh \
    "<prompt>"
  ```
  Output goes to file: `... > /tmp/codex-<topic>/response.log 2>&1`. Never pipe wrapper output (`| tail`, `| grep` etc); wrapper refuses pipe-stdout (iter-0009 contract).
- **Codex reads codebase directly, makes own decisions.** Per user direction 2026-05-03: "codex에게 context만 제공하는게 아니라 직접 코드베이스를 읽어서 스스로 결정할수 있도록." Use `-s read-only` so Codex can `Read`/`Grep`/`Glob` independently. Provide problem statement + falsification ask + your draft conclusion; let Codex verify against actual code.
- **Verify before claim.** Every cited file:line opened at citation time on YOUR side too — Codex's citations may be stale across rounds.

---

## 🧠 What we now know empirically (TL;DR)

### Pair-mode evidence summary (post round-3)

| Surface | Evidence | Verdict |
|---|---|---|
| Codex BUILD/IMPLEMENT (`--engine auto` route) | iter-0020: L2-L1 = −3.6 on 9-fixture suite | **FALSIFIED** — do not pair on IMPLEMENT |
| Pair-VERIFY-JUDGE on frozen diff (verify-only mode) | iter-0033c smoke 1c-fixed-diff: solo PASS 0 findings vs pair BLOCKED 1 CRITICAL on same F2 diff | **deliberation_lift exists** when leak structurally impossible |
| Pair-VERIFY-JUDGE on full-pipeline (gated triggers) | iter-0033c suite: 0/6 lifts ≥+5, mean Δ −2.0, IMPLEMENT-leak from `--pair-verify` parse-time awareness | **CLOSED FAIL** — current trigger design wrong + IMPLEMENT-leak |
| PLAN-pair (Claude proposer + Codex critic, structural firewall) | iter-0022 infra-only — never measured with real models | **UNMEASURED** — iter-0033d is the first measurement |
| ideate spec-audit / PROJECT coherence | Zero measurement | **UNMEASURED** — iter-0033e stub queued |
| CLEANUP residual audit | F4 Playwright artifact leak history but no pair measurement | **UNMEASURED** — folded into VERIFY finding axis if iter-0033d ships |

### Root cause of iter-0033c failure (Codex R-final-suite, 328s)

Per `gates.json` + state.json inspection across all l2_gated arms: pair_judge sub-verdict was `null` on every l2_gated fixture (gated never fired). Yet l2_gated scores regressed. Diagnosis: `--pair-verify` flag parse at PHASE 0 propagated pair-awareness through to IMPLEMENT subagent prompt (`run-fixture.sh:291` benchmark prompt + parse-time skill state). IMPLEMENT reasoned differently when "pair will verify" was in context — over-defensive code, additional unnecessary tests, file-list divergence between solo and l2 arms. **The leak, not the JUDGE, killed the score.**

iter-0033d's structural firewall makes this leak impossible: PLAN runs pair, output is clean `.devlyn/plan.md` only, IMPLEMENT subagent prompt cannot reference pair metadata (lint Check 15 enforces, pre-IMPLEMENT validator hard-fails on reserved tokens).

---

## 🧭 STANDING USER DIRECTIVES

Block 1 is **strictly user-verbatim**. Never re-summarize Block 1.

### Block 1 (2026-04-28 — North Star + 5/6 principles + Codex pair + 산으로 + docs continuous)

> 한가지만 더. 지금 하고있는 것들이 북극성의 목표를 향해서 no xxxx, worldclass xxx 5대 원칙들을 바탕으로 계속 개선을 해나가고 있는게 맞지? 그냥 오로지 점수를 위해서 하는게 아니고 말이야? 확실하게 해주고 항상 codex cli gpt 5.5 와 함께 compenion 으로서 pair 로 논의하고 최선의 결과에 도달할 수 있도록 끝까지 연구하고 개선해줘. 산으로만 가지마. 이제는 됐다 싶을때까지 계속 돌아. 하면서 계속 docs는 업데이트 해주고, 50% 이상 context가 차면 compact 하고 handoff 를 통해서 지금 내가 얘기한것 토씨하나 틀리지 않고 그대로 각인하고 계속 진화시켜나가.

### Block 2 (2026-04-29 evening — six rapid-fire directives)

> 우리 subscription 으로 하는거니까 무료니 얼마 드니 그런거 하지마 앞으로 메모리에 박아.

> L2 는 분업이 아니라 pair 협업을 기준으로 가자.

> 빌드도 협업이어야 할거 같은데??

> 효율과 정확성, 그리고 reasonable 한 속도라고. 무조건 빨라 오래걸려도 괜찮아가 아니라.

> consult 라기보다는 협업모드야. 조언이 아니라. 최적의 결론을 낼때까지. pair 도 반드시 하는게 아니라, 비교해봐야해. pair 로 했을때와 혼자 했을때 크게 차이가 없다면 혼자 하는게 나을수도 있기 때문에.

> 원래 설계에 가장 많은 시간을 쏟고 가장 정확하고 확실한 context engineering을 해야한다고 생각해. build 는 오롯이 plan 에 잡힌 내용들을 정확하고 최선으로 구현하면 되는거고. 검증단계들은 혹시나 만에 하나 잘못 구현하거나 개선할 가치가 있거나, 기술부채를 남겼거나, 클린업을 덜했거나 등등의 케이스를 위해서 존재하는게 아닐까?

> 앞으로 이런거 설명할때 반드시 쉽게 설명해. 쉽고 간결하게. 결정하는 사람 입장에서.

### Block 3 (2026-04-29 architecture compromise)

PLAN은 non-negotiable invariants + acceptance contract을 만든다. BUILD는 그 안에서 *constrained design judgment*를 수행한다. EVAL/CRITIC은 BUILD의 judgment를 대체하지 않는 독립 품질 레이어다. (Codex framing, user-adjudicated.)

### Block 4 (2026-04-29 → 2026-04-30 — engineer-quality + cost-ban + variance + plain Korean)

> 기존 bare case가 틀린거라면 그걸 수정해야해. 북극성을 보자고. 유저가 하나부터 끝까지 다 하는게 목적이 아니야. 유저는 계획하고 실행하면 나머지는 처음부터 끝까지 완벽하게 클린업과 문서화, 기술부채 제거 등을 완벽하게 다 해야해. 소프트웨어 엔지니어링을 생각해보자고.

> 비용이고 뭐고 그냥 신경쓰지말라고 몇번얘기해.

> 점수가 신뢰가 있나? +5 라는게 의미가 정말 있나? 4.5나 5.2나 크게 차이가 없을수도 있을것 같은데?

> 미션1이 팀으로 가는거고 이건 미래에 하는거고, 일단은 혼자서 단일로 하는 케이스도 충분히 만들어져야 한다고 했잖아. 그건 왜 뛰어넘지?

> 좀 쉽게 설명해줄래?? / 무슨얘기인지 쉽게 설명하고 / 아니 좀 쉽게 설명하라니까

### Block 5 (2026-04-30 — 2-skill redesign + multi-LLM evolution)

> 유저 입장에서는 사실 ideate 와 build 두개만 있으면 되지 않나? build 안에 마지막에 verify 가 들어가면 되지 않아?

→ Locked 2-skill design. VERIFY = fresh-subagent final phase of `/devlyn:resolve`.

> build 가 적합하지 않을수도 있는게, 반드시 ideate이 존재하는게 아니라, 기존에 이미 있던 내용에 대해서 수정/개선 요구, 혹은 디버그 요구 등이 있을수도 있어. 그래서 더 적당한 이름이 필요.

→ Renamed `/build` → `/devlyn:resolve`. Free-form goal mode for non-spec-first invocations.

> resolve 스킬은 우리가 지금까지 계속 진화시키고 있던, 여러 LLM 들을 섞어서 논의하는 (claude+codex 부터) 방향도 해야하고, 이후에는 pi agent 를 통해서 여러 다른 LLM도 사용할 수 있다. 특히 우리의 no xxxx, worldclass xxx의 원칙을 반드시 지켜야 한다.

→ Multi-LLM evolution direction binding. Pair-mode is measurement-gated per phase; pi-agent future swap-in via adapter system. no-xxx / worldclass principles bind multi-LLM coordination layer.

> 근데 ideate가 없어도 단독으로도 동작해야하잖아?

→ Confirmed: `/devlyn:resolve` standalone-capable via free-form mode + `--spec` mode (handwritten specs from any source). `/devlyn:ideate` is OPTIONAL.

### Block 6 (2026-05-03 — round-3 pair-redesign, NEW)

> 단순 사용자가 평소대로 resolve 만 하면 다 솔로가 아니라, **최대한의 성능과 효율을 내는 페어 모드여야해**. (풀 파이프라인이라고 하는 정의가 달라져야겠지? 거부된 풀 파이프라인이 아니라 --verify-only 가 풀 파이프라인이 된다던가, 우리의 결정에 따라서. **필요없는 옵션들은 클린업**)

> **계획과 설계가 모든 파이프라인중에 가장 중요해.** 그래서 이부분은 여러 LLM들이 (지금은 둘이지만, 나중에는 늘어날수있음) **페어로 논의하고 최종적으로 최상의 결론이 날때까지 라운드를 이어 나가는게 맞지 않아?** 첫 단추가 잘못 끼이면 뒤에 아무리 둘이서 논의하고 북치고 장구쳐도 안된단말이지. 우리 원칙들을 잘 지키면서 **context pollution, context 부족 등 이슈가 없이** 매우 명확하고 클린하게 spec을 작성하는것이 이후에 Resolve 할때 오류를 최소화 할 수 있는것이지.

> 잠시. **deterministic은 정확하게 무슨뜻이고**, cleanup, verify judge 를 비롯해서 **특히! ideate가 solo 가 더 낫다는 증거가 있나?** 특히 ideate은 **똑같이 plan 을 넘어 설계 단계일텐데, 이거야 말로 가장 중요한 스탭이고 이거야말로 여러 LLM이 유저와 면밀하게 검토해서 가장 정확한 방향의 북극성을 만드는 역할을 할텐데** (특히 프로덕트 전체 그림을 보고 일관되게 그림을 그리는 용도) 이걸 solo로 하는게 더 나은게 맞는거야?

> 새로운 context window 에서 진행할수 있도록 명확하게 모든 context를 pollution 없이 원칙들과 함께 HANDOFF를 클린업하고 재작성해줘. 처음부터 끝까지 멈추지 않고 진행될수 있도록. codex cli gpt 5.5 로 페어로 협의해서 최고의 결과를 얻을수 있도록. **codex에게 context만 제공하는게 아니라 직접 코드베이스를 읽어서 스스로 결정할수 있도록.**

### Memory directives (auto-loaded; cite, do not duplicate)

Critical at `~/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/memory/`:

- `project_2_skill_harness_redesign_2026_04_30.md` — full redesign decision record + multi-LLM evolution clause.
- `feedback_no_cost_talk.md` — HARD rule: no cost framing.
- `feedback_l2_pair_collaboration.md` — L2 = pair 협업 (not 분업).
- `feedback_pair_vs_solo_empirical.md` — pair fires per-phase ONLY where measurement shows lift.
- `feedback_codex_collaboration_not_consult.md` — Codex is partner; multi-round dialogue; reads codebase directly.
- `feedback_explain_simply.md` — plain Korean + concise + decision-maker-framed.
- `feedback_codex_cross_check.md` — reason independently first; send Codex evidence + falsification ask.

**Conflict rule**: if HANDOFF and a memory file disagree, stop before editing and ask the user.

---

## 📍 Branch + project state (verify before editing)

- **Branch**: `main` (origin/main).
- **HEAD**: see `git log -1` — most recent ships are policy-direction commit (round-3 pair-redesign + iter-0033c CLOSED + iter-0033d/e files) and `5397863` (compare.py fix). Prior milestone: `2b9d269` (iter-0033c smokes + infra), `ee27148` (iter-0033c full suite results + 3-bucket Gate 4), `3528579` (iter-0033 C1 close-out), `5378c89` (iter-0033b' F6 N=3 variance), `7669696` (iter-0033b TAP carrier), `2638891` (carrier fix), `3bc86dd` (NEW resolve archive port), `75e08c3` (iter-0033a F9 NEW bake).
- **Iter family closure**: iter-0033a + iter-0033 (C1) + iter-0033b + iter-0033b' + iter-0033c all CLOSED. iter-0033d PRE-REGISTERED. iter-0033e QUEUED-STUB.
- **Mission 1 active** ([MISSIONS.md](MISSIONS.md)). Hard NOs binding.
- **Safety tag**: `pre-merge-2026-04-30` at `1129db6`.

### Cold-start sanity check (run before any edit; ~30s)

```bash
# 1. On main, no detached HEAD.
git status

# 2. Lint passes.
bash scripts/lint-skills.sh   # expect "All checks passed."

# 3. Mirror parity for the 2-skill product surface + shared kernel.
diff -q config/skills/devlyn:resolve/SKILL.md .claude/skills/devlyn:resolve/SKILL.md
diff -q config/skills/devlyn:ideate/SKILL.md .claude/skills/devlyn:ideate/SKILL.md
diff -q config/skills/_shared/runtime-principles.md .claude/skills/_shared/runtime-principles.md

# 4. Active iter file present.
ls autoresearch/iterations/0035-real-project-trial.md

# 5. iter-0034 SHIPPED + iter-0035 STUB on disk.
grep -q "^status: CLOSED-PASS / SHIPPED" autoresearch/iterations/0034-phase-4-cutover.md && echo "0034 SHIPPED ✓"
grep -q "^status: STUB" autoresearch/iterations/0035-real-project-trial.md && echo "0035 STUB ✓"

# 6. CLAUDE.md / AGENTS.md carry the canonical principles block (7 + 3).
grep -q "## Core principles" CLAUDE.md && echo "CLAUDE principles ✓"
grep -q "## Core principles" AGENTS.md && echo "AGENTS principles ✓"

# 7. PRINCIPLES.md self-contradiction fixed (line 72 flexible why-chain).
grep -q "until it reaches the violated invariant" autoresearch/PRINCIPLES.md && echo "PRINCIPLES flexible-why ✓"

# 8. Codex CLI available.
command -v codex && codex --version 2>&1 | head -1
```

If any unexpected output, do NOT proceed. Surface to user.

---

## 🚧 iter queue (post OPERATIONAL-MILESTONE 2026-05-04)

Sequence: iter-0033a/b/b'/C1 PASS → iter-0033c CLOSED FAIL (VERIFY-pair full-pipeline) → iter-0033d/f/g CLOSED-DESIGN (PLAN-pair firewall asymptotic; Codex grep found 0 empirical introspection) → iter-0034 ✅ SHIPPED (Phase 4 cutover + canonical principles refocus, commit `edc6425`) → iter-0035-prelim ✅ CLOSED-PRELIM-PASS (pair-verified hands-free greenfield tower-defense, surprise PASS, does NOT close Mission 1) → **OPERATIONAL-MILESTONE 2026-05-04 (current)**: solo+docs frozen pending user real-usage feedback; full iter-0035 STUB held for organic close; iter-0036+ full-pipeline L2 work has F21/F23 headroom PASS and is now blocked on l2_gated quality no-lift/regression.

Historical iter detail lives in `autoresearch/iterations/*` + `autoresearch/DECISIONS.md`. Below is only what binds the next session.

### iter-0035 (NEXT — real-project trial, Mission 1 terminal gate)

- **Spec**: [iterations/0035-real-project-trial.md](iterations/0035-real-project-trial.md) — STUB. Pre-registration deferred to the session that runs the trial (cannot pre-register without project + task + developer choice).
- **Definition** (NORTH-STAR test #15, verbatim): a developer who has not tuned the harness picks a real (not fixture) feature/bug from a real (not test) codebase, runs `/devlyn:resolve "<spec or goal>"` end-to-end, and the output ships without human prompt-engineering rescue.
- **Pass criteria**: (a) no human edits to skill prompts mid-run, (b) no manual phase re-runs, (c) produced code passes the project's existing test suite + the developer's spec acceptance check, (d) wall-time within budget for the layer the user paid for.
- **Why this is the terminal gate**: 9-fixture suite confirms the harness behaves as designed against known cases (necessary). #15 confirms the harness serves real users on day one (sufficient). Without #15, Mission 1 could ship a benchmark-tuned harness that fails real users.

#### Hand-off contract — what the session running the trial MUST do

1. **Read first**: this HANDOFF (cold-start sanity check) → `NORTH-STAR.md` (test #15 wording) → `MISSIONS.md` (Mission 1 unblock criteria) → `iterations/0035-real-project-trial.md` STUB → recent `DECISIONS.md` entries (iter-0034 SHIPPED context).
2. **Pick the project** with the user — not the devlyn-cli repo, not a benchmark fixture. Candidates: a small open-source project the developer hasn't contributed to, a fresh side-project with a real bug/feature in flight, a non-trivial library the developer maintains.
3. **Pick the task** with the user — real bug or feature, with an acceptance check the developer would normally accept (existing test suite passes + their own check).
4. **Pre-register** in `iterations/0035-real-project-trial.md`: NEW hypothesis, the four NORTH-STAR #15 sub-criteria as gates (a–d), predicted directions filled BEFORE the run, risk register including (a) BUILD_GATE framework auto-detection misses, (b) test-suite running cost, (c) Codex/Claude availability mid-run.
5. **Run hands-free** — `/devlyn:resolve "<spec or goal>"`. Single invocation, no prompt-engineering rescue. If the run halts, that is data — do NOT re-prompt or edit skill prompts mid-run.
6. **Codex pair-collab** — R0 on pre-reg before the run; R-final on raw results after. Same wrapper contract as the iter-0034 sessions (see "Codex pair-collab protocol" section above).
7. **Decision tree on outcome**:
   - **PASS**: Mission 1 closes. Mission 2 (parallel-fleet substrate) opens — see MISSIONS.md "Mission 1 unblocks Mission 2 only when".
   - **FAIL**: classify which gate broke + which phase produced it (PLAN / IMPLEMENT / BUILD_GATE / CLEANUP / VERIFY) and queue the corrective iter (iter-0036+). DO NOT silently re-run.
8. **Closure** — iter file frontmatter `STUB` → `CLOSED-PASS` or `CLOSED-FAIL` with the failure-mode classification. HANDOFF rotates. DECISIONS appends.

#### Definition of "done" for the trial session

- All 4 gates have raw evidence cited (project name, task description, test command output, wall-time, git diff).
- iter-0035 closure committed.
- HANDOFF refreshed; DECISIONS appended.
- If PASS: Mission 1 closes; HANDOFF reflects Mission 2 opening with MISSIONS Mission 2 substrate iter as new active iter.
- If FAIL: corrective iter queued with concrete failure-mode classification.

### iter-0036+ — L2 candidate priority (by measurement difficulty + empirical grounding)

Per iter-0033g closure §H + user direction "L1 stays solid + L2 ships per-phase where empirically lifts":

1. **VERIFY-pair frozen-diff (verify-only mode)** — iter-0033c-fdfd already showed `deliberation_lift` (F2 EACCES finding solo missed, pair caught). Frozen diff = no leak surface. Cleanest measurement target. Highest priority L2 candidate.
2. **PROJECT-pair (ideate)** — iter-0033e queued; needs defect-class oracle first; if oracle is built, no leak surface (PROJECT outputs are read-only spec corpus).
3. **PLAN-pair** — research-only. Re-enters scope when (a) container/sandbox infrastructure justified by other product needs, OR (b) empirical probe demonstrates subagent introspection in production.
4. **Multi-LLM via pi-agent** (Block 5) — Mission 2/3 territory; preserved as future direction; NORTH-STAR's `expected.schema.json` + `_shared/adapters/<model>.md` already hold the contract.

### iter-0033e (QUEUED-STUB, not pre-registered)

- **Spec**: [iterations/0033e-project-coherence-stub.md](iterations/0033e-project-coherence-stub.md).
- **Candidate**: ideate PROJECT coherence audit (cross-spec defect detection in `plan.md + N child specs`).
- **Blocked on**: (1) defect-class oracle definition with scriptable detectors; (2) iter-0034 Phase 4 cutover SHIP; (3) ≥3 real PROJECT corpus runs for oracle calibration.
- **Promotion path**: when blocked-on items resolve, promote to L2 candidate #2 above.

### Post-Phase-4 follow-up queue

- F3/F6/F7 fixture-rotation (RUBRIC two-shipped-version saturation rule; iter-0033 (C1) was first cycle).
- VERIFY MECHANICAL test-diff silent-catch scan (Codex R3 §3 architectural gap; deferred until N≥2 evidence).
- ship-gate.py reframe (+5 floor → categorical reliability gate).
- NORTH-STAR ops test #15 real-project trial (Mission 1 terminal gate).
- iter-0030 phase B — S2-S6 shadow tasks (5 fixtures × 6 files = 30 files). Independent of Phase 4 sequencing.
- ideate spec-audit decision (iter-0033e PROMOTE or kill).

---

## 🧹 Outstanding housekeeping (NOT in active iter scope)

### Worktree triage (deferred per user 2026-04-30)

4 worktrees at `.claude/worktrees/agent-*` — Claude Code Agent transient artifacts. Three are dirty; force-removing them = data loss.

| worktree | HEAD | dirty? | recommended |
|---|---|---|---|
| agent-a244e4e9 | `5f80aac` (NOT in main, "docs updated") | clean | safe to remove |
| agent-a67b4d4d | `1c663f7` (in main, "v1.15.0") | `bin/devlyn.js` +200 lines (doctor subcommand WIP) | save patch first |
| agent-a86d4c87 | `2732cd5` (NOT in main, "phase 1 build complete") | untracked: EVAL-FINDINGS.md, done-criteria.md, benchmark/ | archive first |
| agent-abe3d351 | `83a1759` (NOT in main, "fix round 1 clean") | staged + deleted + modified | save patch first |

User decision deferred to a future session. NOT in any current iter.

### Phase 4 cutover deletions (SHIPPED iter-0034 commit `edc6425`, archived for reference)

15 user skills deleted: `/devlyn:auto-resolve`, `/devlyn:browser-validate`, `/devlyn:clean`, `/devlyn:design-ui`, `/devlyn:discover-product`, `/devlyn:evaluate`, `/devlyn:feature-spec`, `/devlyn:implement-ui`, `/devlyn:preflight`, `/devlyn:product-spec`, `/devlyn:recommend-features`, `/devlyn:review`, `/devlyn:team-resolve`, `/devlyn:team-review`, `/devlyn:update-docs`. Plus `workflow-routing` standards skill deleted (Subtractive). 3 moved to `optional-skills/`: `/devlyn:reap`, `/devlyn:design-system`, `/devlyn:team-design-ui`. `bin/devlyn.js DEPRECATED_DIRS` extended with 18 colon-name entries so `npx devlyn-cli` upgrades force-remove stale legacy skills from downstream installs.

---

## 📋 Mission 1 hard NO list

- ❌ No worktree-per-task substrate (Mission 2).
- ❌ No parallel-fleet smoke / N≥2 simultaneous runs.
- ❌ No resource-lease helper / SQLite leases / port pools / queue metrics.
- ❌ No cross-vendor / qwen / gemma infrastructure (until adapter shipped + measured).
- ❌ No "while I'm here" cross-mission additions.

---

## 📖 Open question — extracting each model's max capability per official guides

**Binding references** (re-read at the start of any iter that touches prompt content or adapters):

- Anthropic Opus 4.7 prompt-engineering best practices: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices>
- OpenAI GPT-5.5 prompt guidance: <https://developers.openai.com/api/docs/guides/prompt-guidance?model=gpt-5.5>

iter-0029 shipped initial adapter files at `_shared/adapters/{opus-4-7, gpt-5-5}.md` — small per-engine deltas reflecting each guide's distinct guidance (Opus 4.7: literal interpretation, self-check pattern, less imperatives; GPT-5.5: outcome-first, decision rules over absolutes, validation tools over self-belief). These adapters are prepended to canonical phase prompts at runtime.

**Standing rule**: any iter that touches an adapter file or canonical phase prompt MUST cite both official guides as part of acceptance. "I think this is better" is not a justification; "guide section X.Y says Z" is.

---

## ⏭️ End of HANDOFF

Current status: **OPERATIONAL-MILESTONE 2026-05-04**. L1 solo (`/devlyn:resolve` + `/devlyn:ideate`) + CLAUDE.md (169 lines) + AGENTS.md (104 lines) frozen pending user real-world feedback. User 2026-05-04 wrapped up solo+docs work and committed to validating the harness organically via daily usage on personal projects. Mission 1 NOT formally CLOSED (full NORTH-STAR test #15 axes still missing — external developer + existing real codebase + shipment acceptance) but operational milestone reached and pre-flight harness-on-greenfield risk retired (iter-0035-prelim CLOSED-PRELIM-PASS 2026-05-04, surprise PASS).

**Active iter at HEAD: iter-0036 OPEN-PARTIAL.** Continue only on:
- (a) User real-usage failure report → corrective iter (failure mode → smallest-unit fix → re-validate via user usage);
- (b) Explicit user direction to scale frozen VERIFY/review evidence → continue the SWE-bench Lite/Verified fixed-diff pilot;
- (c) Explicit user direction to resume full-pipeline L2 work → continue from the clean two-fixture F16+F23 risk-probe PASS; current next step would be broadening beyond the small suite without fixture-oracle ambiguity.

Prior milestones: iter-0035-prelim CLOSED-PRELIM-PASS 2026-05-04 (closure at `iterations/0035-prelim-tower-defense.md` § "CLOSURE — CLOSED-PRELIM-PASS 2026-05-04"); iter-0034 SHIPPED 2026-05-04 commit `edc6425`. Full iter-0035 STUB at `iterations/0035-real-project-trial.md` remains as design document for if/when user wants a discrete formal trial; expected close path is organic accumulation rather than single-trial.

**Direction (user-confirmed 2026-05-03)**: 솔로도 그대로 잘 동작하고 페어는 더욱 더 잘 동작하게 — L1 stays solid + L2 ships per-phase where empirically lifts. L2 candidate priority post-cutover: VERIFY-pair frozen-diff > PROJECT-pair > PLAN-pair (research-only) > multi-LLM via pi-agent (Mission 2/3).

**Next session entry point**: active iter-0036 remains open-partial. SWE-bench Lite fixed-diff evidence now has an eleven-row strict PASS gate and a 48-row matrix (`swebench-lite-proof-gate-n11.{json,md}`, `swebench-lite-first25-plus-26-50-bounded-matrix.{json,md}`); further blind sequential Lite expansion should be yield-gated, not automatic. Full-pipeline L2 now has a clean three-fixture aggregate risk-probe PASS gate: `20260510-f16-f23-f25-combined-proof` scores F16 50 -> 75 -> 96 (+21, wall 1.28x), F23 33 -> 66 -> 97 (+31, wall 2.25x), and F25 25 -> 75 -> 99 (+24, wall 1.65x), with average pair/solo wall ratio 1.73x under the 3.0 cap. F23 was recovered by strengthening `probe-derive.md` so all-or-nothing probes must prove rollback through mutable state, not pre-detectable availability shortcuts; F25 was recovered by tightening cart/pricing risk probes. Treat F21 as an oracle control. Treat F26-F29 as reject/control rows: F26 failed by solo ceiling, F27/F28 failed because bare solved them 4/4, and F29 failed after fairness correction at bare 25 / solo 92. F22 exact-error rerun failed by ceiling (bare 94 / solo 98), F9 failed by bare disqualifier, and F24 `settlement-payout` was rejected/deleted because solo solved it 4/4. The next full-pipeline evidence step is optional broadening beyond the small clean suite, not proof recovery. iter-0035 STUB at `iterations/0035-real-project-trial.md` remains as design document if user later wants a discrete formal trial.

**Forbidden under this branch** (per iter-0033g closure §G + memory lesson `project_iter0033g_asymptotic_firewall_lesson_2026_05_03.md`):
- Do NOT open iter-0033h with another firewall architecture attempt. If user later wants to revisit PLAN-pair, the unblock conditions are documented in `config/skills/devlyn:resolve/SKILL.md` PHASE 1 + `iterations/0033g-pair-plan-impl-pmo.md` § "CLOSURE" §H.
- Do NOT delete iter-0033c-compare.py / build-pair-eligible-manifest.py / iter-0033f-* / iter-0033g-* assets — they preserve closed-iter replay + design archive; CLAUDE.md goal-lock forbids tangential cleanup.
- Do NOT degrade L1 solo behavior in any future iter — iter-0034 R5 path applies (revert smallest unit, re-smoke; 2x fail = surface to user).
- Do NOT skip Codex pair-collab steps. Reasoning independently first + Codex multi-round dialogue is the contract per memory `feedback_codex_collaboration_not_consult.md`.
- Do NOT surface trivial questions to user mid-pipeline. Pair with Codex first; surface only genuinely strategic ambiguity with options + recommendation. Hands-free pipeline rule (CLAUDE.md).
- Do NOT bypass any of CLAUDE.md `## Core principles` (the 7 + 3). The user reminder (repeated multiple times): "no xxxx 원칙들 잊지말고".
- Do NOT pre-register iter-0035 without user-supplied project + task + developer — it is by definition a real-project trial requiring real input.
- Do NOT iterate on L1 solo skill prompts / CLAUDE.md / AGENTS.md / `_shared/` files unless user reports a specific failure mode from real usage. User 2026-05-04 directive: solo + docs frozen at OPERATIONAL-MILESTONE; "could be cleaner" is drift.
- Do NOT claim broad full-pipeline L2 pair-mode beyond the measured surface. `full-pipeline-pair-gate.py` now PASSes on the fair two-fixture F16+F23 headroom set, which proves the harness can produce `bare < solo < pair` on a small clean suite; it is still not evidence of general pair superiority across arbitrary user tasks.

Multi-LLM evolution direction (Block 5) binds `/devlyn:resolve` (Claude + Codex today, pi-agent tomorrow) under no-xxx / worldclass / measurement-gated principles.
