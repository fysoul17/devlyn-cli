# HANDOFF — for the next session

**Outer goal lives in [`NORTH-STAR.md`](NORTH-STAR.md). Read that file FIRST — it is the project contract. This HANDOFF is the operating-context layer on top of it.**

**Read this second** in any new conversation continuing the AutoResearch loop. Smallest set of pointers that lets you pick up where 2026-04-28 (post iter-0018.5 SHIP, mid iter-0019 paid 5-fixture × 3-arm smoke run) left off.

---

## 🧭 STANDING USER DIRECTIVE (2026-04-28, 토씨 그대로 각인) — re-apply on EVERY resume

Verbatim from user, never re-summarize, never paraphrase. This is the operating contract for the autoresearch loop until the user revokes it. If context auto-compacts, the FIRST action on resume is to re-load this block into working memory before any other work.

> 한가지만 더. 지금 하고있는 것들이 북극성의 목표를 향해서 no xxxx, worldclass xxx 5대 원칙들을 바탕으로 계속 개선을 해나가고 있는게 맞지? 그냥 오로지 점수를 위해서 하는게 아니고 말이야? 확실하게 해주고 항상 codex cli gpt 5.5 와 함께 compenion 으로서 pair 로 논의하고 최선의 결과에 도달할 수 있도록 끝까지 연구하고 개선해줘. 산으로만 가지마. 이제는 됐다 싶을때까지 계속 돌아. 하면서 계속 docs는 업데이트 해주고, 50% 이상 context가 차면 compact 하고 handoff 를 통해서 지금 내가 얘기한것 토씨하나 틀리지 않고 그대로 각인하고 계속 진화시켜나가.

**Operational decoding** (these rules are derived; the verbatim above is the source of truth):

1. **Every iter is checked against PRINCIPLES.md 1-6 BEFORE ship**, not the score gates alone. If an iter raises margins but violates principle 1/3/4/6, it does NOT ship — it gets reframed. "점수만 위해서 하는게 아니다."
2. **Score is a downstream signal, not the goal**. The goal is L0→L1→L2 layer-cost-justified pipeline that gives non-context-engineering users worldclass-production-ready software hands-free. If iter X improves score but doesn't move the user-facing layer contract, it's "산으로 가는" work — flag it and reconsider scope.
3. **Codex GPT-5.5 companion pair-review is mandatory on every non-trivial iter.** Pattern in CLAUDE.md "Codex companion pair-review" section. Reason independently first → send rich evidence + falsification ask → surface pushback transparently → user adjudicates. Skip the pair-review only on text-only doc edits (HANDOFF, DECISIONS) where there is no behavior change to falsify.
4. **Loop until "됐다" — don't stop at "good enough."** No premature termination. Each iter ends with: "what's the next falsifiable hypothesis that closes a remaining gap to the North Star?" If the answer is "none," only then stop. Otherwise continue.
5. **Docs update is continuous, not at the end.** HANDOFF + DECISIONS + iteration files + memory entries get updated as work happens, not in a final pass. Cold-start resumability is a hard requirement.
6. **Context-budget protocol**: when conversation context exceeds ~50%, immediately (a) update HANDOFF with current state + verbatim of this directive block intact, (b) trigger compaction, (c) on resume re-read NORTH-STAR → this directive → HANDOFF Cold-Start block → resume work. The verbatim Korean text in the blockquote above must survive every compaction unmodified.

If a future session finds this block missing or summarized, that is a violation — restore it from git history (the verbatim is logged on every commit that touches HANDOFF.md from 2026-04-28 onward).

---

## ⚠️ COLD-START CRITICAL CONTEXT (read FIRST in a new session)

**Last shipped**: `50f26b9` iter-0019.A (SKILL audit + runtime-principles propagation + preflight Round 2). Working tree clean except `?? .claude/` (gitignored install dir).

**Three iter SHIPPED 2026-04-28 since last cold-start**:
- iter-0019.6 acceptance — F9/variant.verify_score=1.0 (mechanical output-contract gate works) — `e6de5ef`
- iter-0019.6.1 — F9 cmd #5 unsatisfiable contract bug fix — `da3eef5`
- iter-0019.A — runtime-principles.md + preflight PHASE 3.5 ROUND 2 + lint Check 12 — `50f26b9`

### NEXT CONCRETE ACTION — iter-0019.8: real-user contract carrier

**Goal**: give real `/devlyn:auto-resolve` users the iter-0019.6 mechanical output-contract gate. Currently `spec-verify-check.py` is a deliberate silent no-op when `.devlyn/spec-verify.json` is absent (Codex R-verdict Q6 caught this — benchmark fixtures get the JSON via `run-fixture.sh:208-219`, real users do not). Without iter-0019.8, all iter-0019.6 work is benchmark-only (NORTH-STAR test #14 trap).

**Scope** (single iter, sub-agent prompt edits + ideate template — code-only, no paid suite):
1. `auto-resolve/SKILL.md` PHASE 0 PARSE: when `source.type == "spec"` and the spec contains a `## Verification` section, parse the section and write `.devlyn/spec-verify.json` BEFORE PHASE 1 BUILD spawns. When `source.type == "generated"`, BUILD writes the section to `.devlyn/criteria.generated.md` and PHASE 0 (round 2 onward) reads it the same way.
2. `auto-resolve/references/phases/phase-0-parse.md` (or wherever PARSE prompt body lives) — add the JSON-emission contract: parse `## Verification` markdown bullets matching shape `cmd: ... → exit_code: N, stdout_contains: [...], stdout_not_contains: [...]` and emit canonical JSON shape matching `benchmark/auto-resolve/fixtures/F*/expected.json` `verification_commands` array.
3. `ideate/references/templates/item-spec.md` — add `## Verification` section template with 1-3 example bullets so ideate-generated specs ship with verifiable contracts.
4. `auto-resolve/references/findings-schema.md` — confirm `correctness.spec-literal-mismatch` is documented as the canonical rule_id (already added in iter-0019.6 — verify only, don't duplicate).
5. Falsification: dry-run on a small synthetic spec (`docs/roadmap/phase-1/test-iter-0019-8.md`) with `## Verification` section → confirm `.devlyn/spec-verify.json` materializes correctly + BUILD_GATE picks it up + spec-verify-check.py fires. Cost ~$0 (Claude-only synthetic). NO paid 9-fixture suite.

**Step-by-step sequence (mirror iter-0019.A discipline)**:

1. **Design draft + Codex pair-review Round 1** — propose PHASE 0 contract + ideate template diff; ask Codex for falsification on edge cases (multi-cmd specs, missing `## Verification`, ideate-generated criteria path).
2. **Adopt findings** + draft skill prompt edits.
3. **Codex pair-review Round 2** on actual diff before commit.
4. **Mirror** via `node bin/devlyn.js -y`.
5. **Lint** — confirm Check 6 + Check 12 still PASS post-edit.
6. **Synthetic dry-run** falsification.
7. **Iter file** + DECISIONS append + HANDOFF rotate + memory + atomic commit.

### Do NOT

- ❌ Run iter-0020 9-fixture paid suite (blocked by iter-0019.8 + iter-0019.7 measurement decision)
- ❌ Edit `_shared/runtime-principles.md` content without mirroring CLAUDE.md `:section=NAME:` blocks — **lint Check 12 will fail**. CLAUDE.md is the source of truth; runtime-principles is the mirror.
- ❌ Edit CLAUDE.md `runtime-principles:section=NAME:` blocks without re-syncing runtime-principles.md AND re-running `node bin/devlyn.js -y`
- ❌ Bundle iter-0019.8 with iter-0020 or iter-0019.7 (Codex R3 attribution-clarity rule)
- ❌ Re-introduce iter-0019.7 silent-catch BUILD_GATE helper before iter-0019.8 ships — Codex R-halt confirmed that ordering is score-chasing. Order is **0019.8 → measure → 0019.7 only if data demands**.
- ✅ OK: design iter-0019.8 in `autoresearch/iterations/0019-8-real-user-contract.md`; pair-review with Codex before code lands

### How to verify state on resume (cold-start sanity check, ~30s)

Paste these in order; expected output noted:

```bash
# 1. Branch + commit chain
git log --oneline -8
# Expected top: 50f26b9 autoresearch(iter-0019.A): SKILL audit ...

# 2. Working tree clean
git status --short
# Expected: only `?? .claude/`

# 3. Lint full pass
bash scripts/lint-skills.sh
# Expected: all 11 checks (1-10 + 12) PASS, "All checks passed."

# 4. Mirror parity
diff -q config/skills/_shared/runtime-principles.md .claude/skills/_shared/runtime-principles.md
# Expected: silent (no diff)

# 5. Confirm next iter file does not exist yet
ls autoresearch/iterations/0019-8-*.md 2>/dev/null
# Expected: empty (next session creates it)

# 6. Confirm runtime-principles markers (anchored to line-start, not prose mentions)
grep -cE '^<!-- runtime-principles:section=' CLAUDE.md
# Expected: 8 (4 sections × 2 markers)
grep -cE '^<!-- runtime-principles:section=' config/skills/_shared/runtime-principles.md
# Expected: 8
```

If any of these unexpectedly fails, the branch state has drifted — investigate before starting iter-0019.8 work.

### Read-order on cold start

1. `autoresearch/NORTH-STAR.md` — what we are optimizing (3-layer L0/L1/L2 contract, 14 operational tests, real-project trial gate test #14).
2. **This file** — operating context.
3. `autoresearch/PRINCIPLES.md` — pre-flight 0 + 6 principles.
4. `CLAUDE.md` — session-level runtime contract (Subtractive-first, Goal-locked, No-workaround, Evidence — these 4 sections are mirrored in `_shared/runtime-principles.md` for sub-agents).
5. `autoresearch/DECISIONS.md` — append-only ship/revert log.
6. `autoresearch/iterations/0019-A-skill-audit-runtime-principles.md` — most recent iter, full data + Codex 7-round trail + lessons.
7. `config/skills/_shared/runtime-principles.md` — runtime contract sub-agents consume.
8. `config/skills/devlyn:preflight/SKILL.md` PHASE 3 + 3.5 — newest preflight mechanism.

---

## Current state

**Branch**: `benchmark/v3.6-ab-20260423-191315`. 28 commits ahead of origin after iter-0019.4 / .5 / .6 / .6.1 / .6-acceptance / .A + iter-0019 part 2 + CLAUDE.md audit proposal + CLAUDE.md subtractive-first/goal-locked + handoff pivot/rotate commits.

**iter-0019.A SHIPPED 2026-04-28**: SKILL audit + runtime-principles propagation + preflight Round 2. Code-only iter, no paid suite. lint 11/11 + new Check 12 PASS (CLAUDE.md ↔ `_shared/runtime-principles.md` per-section excerpt parity: markers + topology + content). Auto-resolve `<harness_principles>` + phase-1/2/3 + fix-loop + DOCS now consume runtime-principles. Preflight has new PHASE 3.5 ROUND 2 CRITIQUE (5 deterministic triggers, 240s wall-budget abort, single round runtime). preflight emits `principle.*` rule_ids per code-auditor overlay table; browser-auditor narrow scope. ideate untouched. 7 Codex review rounds, all findings adopted (~640k tokens read).

**iter-0019.6 ACCEPTANCE GATE PASSED 2026-04-28T01:01Z** (RUN_ID `20260427T235114Z-da3eef5-iter-0019-6-acceptance`, paid ~$5-10, wall ~70min). F9/variant.verify_score=1.0 (5/5), disqualifier=false, score=88 (vs iter-0019's 74, +14 lift). Mechanism trace: BUILD round 0 PASS (557s) → BUILD_GATE round 1 fired 2 CRITICAL `correctness.spec-literal-mismatch` (`topAuthors` vs `authors`, exit 1 vs 2 — exact iter-0018.5 failure mode) → fix_loop_round_1 PASS (399s, triggered_by=build_gate) → BUILD_GATE round 1 re-run PASS (5s) → EVALUATE PASS_WITH_ISSUES (3 LOW only). Convergence in 1 fix-loop round. **iter-0019.6 status: SHIPPED-VERIFIED** (DECISIONS.md line `0019.6 | SHIPPED-VERIFIED`). Codex R-verdict: ship-as-PASS (138k tokens, 256s, xhigh) with namespace correction adopted (residual judge findings on ranked format + exact stderr are non-DQ, queued for iter-0020+ gate-vocabulary enrichment).

Side data (NOT acceptance, context for iter-0020): F9/L1=73⚠DQ silent-catch (NOT codex contamination — settings.json clean per Codex Q3), F9/L0=70⚠DQ; L2-L1=+15 (iter-0019 was -7, swing partly L1 falling, partly L2 rising via iter-0019.6 mechanism); L1-L0=+3 (1-fixture smoke read, NOT the L1 release gate). Wall L2/L1/L0 = 2632s/1369s/70s.

Asymmetry note: variant arm copied pre-edit CLAUDE.md at startup (commit `660871c` subtractive-first/goal-locked landed mid-suite); load-bearing iter-0019.6 metric (F9/variant.verify_score) is uncontaminated.

**iter-0019 SUITE COMPLETE 2026-04-28T04:06Z** (RUN_ID `20260427T155638Z-c08130f-iter-0019-smoke`). All 15 arm runs + 5 judge re-runs (after iter-0019.4 mapfile fix) successful. Suite avg V=91.8 / L1=90.8 / L0=81.2. **L1 partial / directional only** (L1-L0=+9.6 across 5-fixture smoke; full 9-fixture run is iter-0020 scope; release-readiness language forbidden until then per NORTH-STAR.md:83). **L2 FAILS NORTH-STAR test #6** (L2-L1=+1.0 < +5 floor) — pair-mode compression risk realized. 2 variant hard-floor DQs (F2, F9 silent-catch) → release-readiness NOT IMPLIED. F4 L1=100 beats L2=99 (Codex R3 tool-attribution hypothesis CONFIRMED). F9 L1=81 beats L2=74 by 7 points. solo_claude enforcement clean on all 5 fixtures (Bypass A surface open but never exercised). iter-0018.5 F9 prompt fold-in DEAD (verify=0.4 across all arms).

**iter-0019 follow-up patches LANDED 2026-04-28**:
- iter-0019.4 (`5e035d1`): judge.sh mapfile → Bash 3.2 portable while-read (mapfile is Bash 4+; macOS /bin/bash 3.2 silently failed all 5 judge invocations in the iter-0019 paid run). Re-judged all 5 fixtures post-fix to extract scores.
- iter-0019.5 (`2269787`): close CODEX_REAL_BIN env-var leak into solo_claude — bypass surface CLOSED. Codex R1 caught (during iter-0019 mid-suite); surface was open all suite long but never exercised, hardening preemptively for iter-0020's 9-fixture run.
- iter-0019.6 (`3a6db4f`): F9 mechanical output-contract enforcement — verdict bind option (a). Adds `.devlyn/spec-verify.json` staging + `scripts/spec-verify-check.py` BUILD_GATE invocation that mirrors post-run verifier semantics, emits canonical CRITICAL `correctness.spec-literal-mismatch` findings on exit/contains/not-contains mismatch. Routes through existing PHASE 2.5 fix-loop. Prompt-only iter-0018.5 fold-in was empirically dead — this is the iter-0008 lesson at second mechanism scope.

**NEXT (queued, not yet run)**: iter-0019.8 (real-user contract carrier — auto-resolve PHASE 0 emits `.devlyn/spec-verify.json` from spec `## Verification` + ideate template generates the section). See "NEXT CONCRETE ACTION" block at top. Code-only iter, ~no paid spend. Then iter-0019.7 measurement-driven decision, then iter-0020 (9-fixture L0/L1/L2 paid run).

**HEAD chain** (newest first):
```
50f26b9  autoresearch(iter-0019.A): SKILL audit — runtime-principles propagation + preflight Round 2 + principle overlay
45addc1  autoresearch(handoff): pivot to [A] SKILL audit; iter-0019.7 deferred per Codex R-halt
e6de5ef  autoresearch(iter-0019.6 acceptance): SHIPPED-VERIFIED + iter-0020 unblock
660871c  CLAUDE.md: subtractive-first + goal-locked execution rules
2e247ca  autoresearch(handoff): log iter-0019.6.1 + acceptance suite in-flight
da3eef5  autoresearch(iter-0019.6.1): drop F9 cmd#5 unsatisfiable stdout_not_contains
4b1e9fc  autoresearch(handoff): rotate cold-start to iter-0019.6 acceptance gate
3a6db4f  autoresearch(iter-0019.6): F9 mechanical output-contract enforcement
2269787  autoresearch(iter-0019.5): omit CODEX_REAL_BIN from solo_claude env
b5f0f97  autoresearch(iter-0019 part 2): verdict + pre-flight 0 + real-project trial gate
5e035d1  autoresearch(iter-0019.4): judge.sh mapfile -> bash 3.2 portable
34e6341  autoresearch(handoff): cold-start-resilient HANDOFF rewrite for context-clear continuity
d6faef1  autoresearch: queue CLAUDE.md install-time identity + minimization audit
c08130f  autoresearch(iter-0019 part 1): solo_claude L1 arm + 3-arm schema + CODEX_BLOCKED enforcement
60b27b2  autoresearch(iter-0018.5): BUILD/EVAL prompt fold-ins for F5 / F9 failure modes
5fd781a  autoresearch(iter-0018): measurement integrity + report-shape lock + iter-0016 final readout
5d9ba0d  autoresearch: surface 5+1 principles in CLAUDE.md outer-goal block + lock README queue to HANDOFF
3bc6f45  autoresearch: lock North Star + 3-layer perf contract + iter queue rewrite
27d1636  autoresearch(iter-0017): run-suite.sh auto-mirror config/skills -> .claude/skills
775f761  autoresearch: HANDOFF rewrite for fresh-context resume post iter-0014
20f6f07  autoresearch(iter-0014): state-writes-per-phase + archive path
... (earlier chain in DECISIONS.md)
```

Working tree clean except untracked `.claude/` install dir (gitignored content + worktrees + scheduler lock — see iter-0017 NOTE).

iter-0007 verdict realized. iter-0008 REJECTED. **iter-0009 → iter-0014 + iter-0017 + iter-0018 + iter-0018.5 + iter-0019 part 1 all SHIPPED to commit**. iter-0019 part 2 (paid run + verdict + iter file) is in flight. iter-0016 5-fixture suite completed 2026-04-27T13:58Z (RUN_ID `20260427T121636Z-27d1636-iter-0016-verify`); iter-0018 locked the readout into docs; iter-0018.5 closed F5/F9 prompt issues; iter-0019 part 1 added `solo_claude` L1 arm + `CODEX_BLOCKED` enforcement + 3-arm judge/compile schema and the paid smoke run is in progress.

**Next iteration QUEUE** (post-iter-0018.5 + iter-0019 part 1, rewritten 2026-04-28):

0. **iter-0019 part 2 — verdict + iter file** (✅ **SHIPPED 2026-04-28**, commit `b5f0f97`). Bind: follow-up action **(a) F9 mechanical enforcement** = iter-0019.6 (also SHIPPED, see below). See `autoresearch/iterations/0019-l1-claude-arm.md` for full data + principles check. **PRECOMMIT (Codex R2, 2026-04-28, kept for historical reference)**: this run's verdict was allowed to lead to exactly ONE of three follow-up actions, no fourth option. Pick before reading the data. Track which one this verdict commits to in the iter file under "What this iter unlocks":
   - (a) **Mechanically enforce F9 output contract** — if F9 variant verify_score < 0.6 OR judge spec axis < 22 (i.e. iter-0018.5 prompt fold-in did not hold), the next iter is harness-side enforcement (e.g. EVAL bash gate that diffs actual output bytes against spec literal, fails CRITICAL on mismatch — not prompt-only). User-visible failure removal.
   - (b) **Implement cost-aware pair policy in iter-0020** — if L1 vs L0 + L2 vs L1 attribution is clean enough to make a router decision (per-fixture margins + wall ratios), iter-0020 lands the per-phase decision-mode taxonomy with **deterministic short-circuit + wall budget abort**, not as design discussion. Routing policy change.
   - (c) **Disable or narrow L2 where it fails L1 cost-adjusted** — if any fixture shows variant_over_solo < +5 with wall_ratio_variant_over_solo > 2.0, the next iter is to *remove* the pair phase for that fixture class, not to optimize it. User-visible cost reduction.
   No "iter-0020-prep" / "iter-0019.6 measurement-improvement" / "more attribution" iter is allowed before one of (a)/(b)/(c) lands. **Pre-flight 0 (PRINCIPLES.md) gates this.** If the verdict pass cannot map to (a)/(b)/(c), the loop has gone 산으로; surface to user before continuing.

   When `report.md` + `summary.json` appear in `results/20260427T155638Z-c08130f-iter-0019-smoke/`:
   - **Run `bash /tmp/iter0019-verdict-greps.sh` first** — staged 2026-04-28 with Codex R0 contamination-detection greps (CODEX_BLOCKED hits, real-codex side-channel via `~/.codex/sessions/.../session_meta.cwd` matching solo_claude paths, pipeline.state.json engine field per phase). This is the load-bearing check; if any solo_claude run shows session_meta.cwd hits or `[codex-monitored] start` in transcript, **L1 data is contaminated** and iter-0019 verdict must say so.
   - Read the 3-arm scores: per-fixture `arms.{variant, solo_claude, bare}.score`, suite `scores_avg_by_arm`, pairwise `margins` and `wall_ratios`. Schema lives in `compile-report.py` (post iter-0019 part 1) — see "Schema cheat-sheet" below.
   - Verify `solo_claude` arm produced findings (no `CODEX_BLOCKED` enforcement bypass): each `arms.solo_claude.{score, wall_s, files_changed}` should be populated; `findings_by_arm[solo_claude]` should be a list (possibly empty).
   - Read against NORTH-STAR.md operational tests: L1 vs L0 margin (`margins_avg.solo_over_bare`) ≥ +5 floor / +8 preferred? F9 ≥ +5? wall ratio L1/L0 reasonable?
   - Specific watchpoints: F5 is NOT in this 5-fixture set (set is F1+F2+F4+F6+F9), so iter-0018.5 F5 surgical-scope fix is verified in iter-0020's full 9-fixture run. Did F9 spec-compliance fix hold? (variant spec axis should be ≥ 22 not 16 — read judge.json breakdowns.)
   - Write `autoresearch/iterations/0019-l1-claude-arm.md` with full principles 1-6 check + Codex R-final cross-check + tool-vs-deliberation attribution preview (which fixtures' lifts came from which arm).
   - Update DECISIONS.md with `0019 | DATA | <verdict>` line.
   - Update HANDOFF.md "Current state" + cumulative lessons.
   - Commit. Do NOT bundle prompt edits or the iter-0019.5 / iter-0020 work.

0.5. **iter-0019.5 — close `CODEX_REAL_BIN` env-var leak into solo_claude** (✅ **SHIPPED 2026-04-28**, commit `2269787`). Bypass surface was OPEN through iter-0019 paid run but never exercised (data confirmed clean across all 5 solo_claude runs). Hardening landed preemptively for iter-0020's 9-fixture L0/L1/L2 run. Codex R0/R1 (pre-data falsification on iter-0019 enforcement) caught: `run-fixture.sh:126-131` unconditionally writes `CODEX_REAL_BIN=<absolute-path-to-real-codex>` into `.claude/settings.json` env, including for ARM=solo_claude. Orchestrator can call `Bash("$CODEX_REAL_BIN exec ...")` and bypass BOTH shim (PATH lookup not used) AND wrapper (codex-monitored.sh not invoked). The codex node binary itself does NOT honor CODEX_BLOCKED, so this is a real bypass class. **Fix**: when ARM=solo_claude, omit `CODEX_REAL_BIN` from the env dict (or set to empty/poison). Shim's BLOCKED check fires before needing CODEX_REAL_BIN, so removing it doesn't break shim; if CODEX_BLOCKED is somehow unset later, shim now fails closed instead of delegating. Lands AFTER iter-0019 part 2 verdict commits, BEFORE iter-0020. Separate commit. Falsification: re-run a single solo_claude fixture and confirm `CODEX_REAL_BIN` absent from settings.json env block; lint passes. The current 5-fixture suite's verdict pass uses post-hoc artifact detection (Codex Q2 greps) to determine if bypass A actually fired — if it did, iter-0019 numbers are documented as suspect and re-run is needed.

0.6. **iter-0019.6 — F9 mechanical output-contract enforcement** (✅ **SHIPPED 2026-04-28**, commit `3a6db4f`, BOUND from iter-0019 verdict option (a)). Design B (Codex R5 verdict adopted in full): normalized `.devlyn/spec-verify.json` staged by `run-fixture.sh` (verification_commands only — no tier_a_waivers / forbidden_patterns / scope oracles); `config/skills/devlyn:auto-resolve/scripts/spec-verify-check.py` invoked by BUILD_GATE Agent every round, mirrors post-run verifier semantics (combined stdout+stderr, 60s per-cmd timeout); emits canonical schema `correctness.spec-literal-mismatch` CRITICAL findings concatenated onto `build_gate.findings.jsonl`; routes through existing PHASE 2.5 fix-loop. Out of scope: forbidden_patterns silent-catch (separate enforcement), mutating verification commands (read-only-only). Unit-falsified: 3 staged commands (1 pass / 1 missing-contains / 1 exit-code-mismatch) produced exactly 2 CRITICAL findings + correct results.json evidence. **Acceptance gate (NOT YET RUN)**: re-run iter-0019 paid suite limited to F9 only (~$5-10, ~30-45min) and confirm F9/variant verify_score ≥ 0.6 + no spec-failure DQ. See "NEXT CONCRETE ACTION" block at top of this HANDOFF.

1. **iter-0020 — Pair-vs-solo policy formalization + tool-vs-deliberation attribution**. Per-phase decision-mode mapping per `NORTH-STAR.md`. Adds wall-time abort + `coverage.json` checklist-coverage artifact (every checklist ID with `pass/fail/na` + evidence path + touched-file scope, per Codex R3 Q4). **Critical instrumentation**: separate measurement of tool/phase lift (browser_validate, build_gate, security-review native firings) vs model-deliberation lift (second-model EVAL/CRITIC/JUDGE producing different conclusions). F4 may be tool-attributed not pair-attributed (per Codex R3 Q5 hypothesis); F5/F9 in iter-0016 were excluded as evidence per iter-0018 verdicts but iter-0019's data may rehabilitate them. After iter-0020 lands, run a **full 9-fixture L0/L1/L2 suite** to obtain canonical L2-vs-L1 numbers (this is where the 9-fixture run lives, not iter-0019). Do NOT bundle CLAUDE.md audit work (see High-priority queued).

   **HARD ACCEPTANCE — Codex R3 (2026-04-28)**: iter-0020 ships only if it changes an executable routing policy, not just reports attribution. The iter must produce ALL FIVE: (1) a per-fixture-class phase routing table, (2) at least one routing decision that differs from current behavior, (3) a deterministic short-circuit or abort rule enforced in code (not prompt-only), (4) `coverage.json` proving every changed route was exercised, (5) a recorded rollback condition. **Aggregate score movement alone is non-acceptance evidence.** If after data lands the conclusion is "current routing was already correct, no change needed", iter-0020 closes as "data confirms; no behavior change shipped" — that is also a valid pre-flight 0 outcome (the data forced a specific decision).

2. **iter-0021 — Dual-judge — REFRAMED to conditional, NOT permanent default (Codex R3, 2026-04-28)**. Original plan was `pair_consensus` for JUDGE phase to fix self-judgment bias (~5.6pt). Pre-flight 0 audit + Codex R3 verdict: dual-judge is "harness self-knowledge" work — legitimate ONLY when bad measurement can cause a wrong user-facing decision. **New scope**: iter-0021 fires ONLY IF iter-0020's verdict lands within ±6pt of a routing-decision threshold (i.e. the 5.6pt self-judgment inflation could plausibly flip a per-fixture pair-vs-solo decision). Otherwise iter-0021 closes as "measurement polish — not user-failure-removing." The judge.sh 3-arm schema from iter-0019 part 1 remains a prerequisite either way. Reframed iter file should record: which threshold was at risk, what dual-judge sidecar measured, what the arbitration rule produced.

3. **iter-0022 — Cost retune** (only if iter-0020 short-circuits + iter-0019 data show wall ratio still over budget after pair gates active). Otherwise close as "not needed." Cost/wall time = direct user harm, so this passes pre-flight 0 by definition when data demands it (Codex R3).

4. Old queue items (iter-0015 shim defer, stream-json, F9 timeout adjustment, N=1 ship-gate floor, F6 chronic slowness, stuck-execution abort) renumber/recycle as the queue rotates.

### Schema cheat-sheet (post iter-0019 part 1)

`summary.json` (suite-level, written by `compile-report.py`):

```
{
  "fixtures_total": int,
  "fixtures_scored": int,
  "variant_avg": float | null,        // legacy — equals scores_avg_by_arm.variant
  "bare_avg":    float | null,        // legacy — equals scores_avg_by_arm.bare
  "margin_avg":  float | null,        // legacy — equals margins_avg.variant_over_bare
  "hard_floor_violations": int,
  "margin_ge_5_count": int,
  "gated_fixtures": int,
  "wall_ratio_variant_over_bare_avg": float | null,    // legacy
  "arms_present": {"variant": bool, "solo_claude": bool, "bare": bool},
  "scores_avg_by_arm": {"variant": float | null, "solo_claude": float | null, "bare": float | null},
  "margins_avg": {
    "variant_over_bare":   float | null,
    "solo_over_bare":      float | null,    // L1 vs L0 — NORTH-STAR test #1 gate
    "variant_over_solo":   float | null     // L2 vs L1 — NORTH-STAR test #6 gate
  },
  "wall_ratio_avg_by_pair": { same triple },
  "rows": [ ... ]
}
```

Per-row (per-fixture):
```
{
  "fixture": "F2-cli-medium-subcommand",
  "category": "medium",
  "arms": {
    "variant":     {"score": int, "wall_s": int, "verify_score": float, "files_changed": int, "timed_out": bool, "disqualifier": bool, "critical_findings": [..]},
    "solo_claude": {... same shape ...},
    "bare":        {... same shape ...}
  },
  "margins":      {"variant_over_bare": int|null, "solo_over_bare": int|null, "variant_over_solo": int|null},
  "wall_ratios":  {"variant_over_bare": float|null, "solo_over_bare": float|null, "variant_over_solo": float|null},
  "winner": "variant" | "solo_claude" | "bare" | "tie" | null,
  // Legacy fields below — kept so ship-gate.py + history readers still parse pre-iter-0019 shape:
  "variant_score", "bare_score", "margin", "variant_disqualifier", "variant_dq_judge",
  "variant_dq_deterministic", "variant_wall_s", "bare_wall_s", "wall_ratio_variant_over_bare",
  "variant_verify_score", "bare_verify_score", "variant_files_changed", "bare_files_changed",
  "critical_findings_variant", "critical_findings_bare"
}
```

`judge.json` (per-fixture, written by `judge.sh`):
```
{
  "a_score", "b_score", "c_score" (if 3-arm),    // raw blind scores
  "a_breakdown", "b_breakdown", "c_breakdown",   // 4-axis Spec/Constraint/Scope/Quality + notes
  "winner": "A" | "B" | "C" | "tie",
  "_blind_mapping": {"A": "<arm>", "B": "<arm>", "C": "<arm>", "seed": int},
  "_judge_cli", "_judge_model",
  "scores_by_arm": {"variant": int, "solo_claude": int, "bare": int},
  "findings_by_arm": {<arm>: [...], ...},
  "disqualifiers_by_arm": {<arm>: {"disqualifier": bool, "reason": str}, ...},
  "margins": {"variant_over_bare", "solo_over_bare", "variant_over_solo"},
  "winner_arm": "<arm>",
  // Legacy 2-arm fields (variant_score, bare_score, margin) preserved
}
```

Pre iter-0019 runs (e.g. iter-0016 results dir) lack `arms{}`/`margins{}`/`wall_ratios{}`/`scores_by_arm` — `compile-report.py` post iter-0019 part 1 falls back to legacy `variant_score`/`bare_score` so re-compile works against old data. Verified 2026-04-27 by re-compiling iter-0016 with the new code.

### High-priority queued: CLAUDE.md install-time identity + minimization audit (post iter-0019)

User direction 2026-04-28. Two coupled concerns surfaced after the iter-0019 design pass:

**(1) Install-time identity gap (load-bearing for benchmark validity).** `bin/devlyn.js` installs `CLAUDE.md` to the user's project root via `fs.copyFileSync(claudeMdSrc, claudeMdDest)` where `claudeMdSrc = path.join(__dirname, '..', 'CLAUDE.md')` (lines 387-391, post-iter-0017 audit). The benchmark variant arm uses `$REPO_ROOT/CLAUDE.md` (per `run-fixture.sh:71`). For variant scores to predict end-user experience, the **shipped package's CLAUDE.md must be byte-identical to the repo CLAUDE.md** — otherwise we measure something different from what the user runs. Verification work:
- Confirm `package.json` `files[]` list explicitly includes `CLAUDE.md` (npm pack inclusion).
- Run `npx devlyn-cli` in a temp dir, diff installed vs `$REPO_ROOT/CLAUDE.md`. Must be silent.
- Add lint Check 11 enforcing this identity before any ship.
- If a CLAUDE.md edit happens between commits and a release, the package SHA must update.

**(2) Minimization opportunity (universal rules vs skill-specific rules).** Current CLAUDE.md ≈ 138 lines covering: outer goal, 5+1 principles, Quick Start (auto-resolve / ideate / preflight), Karpathy 4, Error Handling Philosophy, Codex invocation, Codex companion pair-review, Working Mode, Skill Boundary Policy, Native Claude Code Skills, Bare-Case Guardrail, No-Workaround Bar, Communication Style, Commit Conventions, Design System. Several sections are autoresearch-loop concerns (NOT runtime guidance for end users): "Codex companion pair-review" (iteration-loop only — not all users do meta-review), "Bare-Case Guardrail" + "Skill Boundary Policy" (auto-resolve internals), "Working Mode" / "Native Claude Code Skills" (skill-call mechanics).

End users hit different surfaces:
- **modal: auto-resolve** (run, walk away). Doesn't need to know about iteration-loop pair patterns.
- **secondary: ideate, preflight**. Same — skill internals not load-bearing.
- **occasional: /resolve, /review, /clean, plain prompting, single-task**. CLAUDE.md is the global background — pollution here drags every short interaction.

User direction (verbatim, Korean): keep universal applicable rules ("no overengineering, no workaround, no guesswork, worldclass production-ready, best practice, layer-cost-justified") in CLAUDE.md; lazy-load skill-specific rules; CLAUDE.md must NOT pollute non-auto-resolve workflows. Even small CLAUDE.md changes shift benchmark numbers — A/B falsification gate required before ship.

**Plan**: queued as a separate iter (probably iter-0020 or 0020.5 depending on iter-0019 verdict timing). Codex GPT-5.5 deep cross-check expected on the prune decision. Output:
- New `autoresearch/iterations/00NN-claude-md-minimization.md` with full diff plan + benchmark gate.
- Possibly a new `PRINCIPLES.md` principle if a "context-pollution" rule emerges.
- Lint Check 11 (install-time identity).
- A/B benchmark gate: re-run iter-0019 smoke (5 fixtures × 3 arms) under pruned CLAUDE.md and compare margins. Ship only if no fixture regresses by ≥5.

**HARD GATE — Codex R3 + pre-flight 0 (2026-04-28)**: claim (1) install-time identity is **proven user harm** (silent CLAUDE.md drift breaks the predictability of benchmark numbers for end users) — proceed. Claim (2) minimization is **plausible but unproven harm**. Pre-flight 0 forbids starting the minimization iter on assertion alone. Required pre-iter measurement: pick 5–10 representative non-auto-resolve user prompts (single-task /resolve invocations, plain "edit this file" asks, brief code questions) and run them under the CURRENT CLAUDE.md. Score response quality against expected behavior. Re-run under a candidate-minimized CLAUDE.md. **Ship the minimization iter only if measurable degradation appears in the current state**, OR if a measurable improvement appears after pruning. If both runs are indistinguishable, the minimization claim is style work — close the iter as "no measurable pollution; current CLAUDE.md is fine; reopen if a future user-prompt category surfaces evidence." Identity-gap iter (item 1) is NOT gated by this — it removes a known divergence regardless of perceptible UX.

Do NOT bundle with iter-0020 pair-policy work — Codex R3 attribution-clarity rule. Either before or after, never combined.

**Codex R3 explicit warning**: do NOT bundle judge-mechanics changes + L1 arm + pair policy in the same iter — attribution becomes muddy. Sequence above keeps measurement and behavior changes separate.

**Cost estimate iter-0019 → 0021**: ~4-5 hours wall + 2-3 paid runs (~$30-60 total). iter-0019 paid (4-fixture × 3-arm smoke, ~$20-30); iter-0020 includes a full 9-fixture L0/L1/L2 paid run (~$30-50); iter-0021 reuses iter-0020's data for a re-judge sidecar (no new paid arm runs).

**Cost estimate iter-0016 → 0021**: ~3-4 hours wall + 2-3 paid suite runs ($30-60 total) before release-decision data lands.

---

## iter-0016 final readout (5-fixture partial — F1/F3/F7/F8 deferred to iter-0019)

RUN_ID `20260427T121636Z-27d1636-iter-0016-verify`. Completed 2026-04-27T13:58Z. Results dir `benchmark/auto-resolve/results/20260427T121636Z-27d1636-iter-0016-verify/`. Suite ran 5 of 9 fixtures (F2/F4/F5/F6/F9) per scope decision; F1/F3/F7/F8 deferred to iter-0019's L0+L1+L2 9-fixture run.

### Headline numbers

| Fixture | V score | B score | Margin | V wall | B wall | Wall ratio | Notes |
|---|---|---|---|---|---|---|---|
| F2 | 95 | 78 | **+17** | 1201s **TO** | 156s | 7.7× | Bare DQ silent-catch. Variant CRITIC killed at watchdog but quality high. |
| F4 | 99 | 78 | **+21** | 1012s | 177s | 5.7× | Bare missed italic CSS, added out-of-scope test-results file. browser=true. |
| F5 | 95 | 96 | **−1** | 770s | 45s | **17×** | Both spec=25/constraint=25/quality=21. Variant lost on scope=24 vs bare=25 (variant added `completed=` field to roadmap frontmatter). |
| F6 | 97 | 87 | +10 | 876s | 82s | 10.7× | Bare rethrows non-ENOENT, breaks createReadStream constraint. |
| F9 | 83 | 72 | +11 | 1393s | 87s | 16.0× | **Both arms verify=0.4, spec=16/13** — wrong `Error:` prefix, wrong exit 2, wrong JSON top-level shape, unranked authors. Bare DQ silent-catch. |

**Suite avg variant 93.8 / bare 82.2 / margin +11.6** (above the +8 NORTH-STAR preferred). 0 hard-floor violations. **SHIP-GATE FAIL** — only 4/5 fixtures ≥ +5 against absolute 7/9 floor (5-fixture run cannot pass a 7-of-9 absolute gate).

### Honest claim boundary (Codex R3 + R4 lock language)

- **L2 vs L0 (5-fixture partial)**: PASS on quality margin (+11.6 > +8 preferred), 0 hard-floor violations. FAIL on volume rule (5 fixtures only).
- **L2 vs L1**: **UNKNOWN**. L1 arm does not exist yet. iter-0019 must land before any L2-vs-L1 claim.
- **Release readiness**: NOT IMPLIED by these numbers. L2-vs-L1 compression risk (Codex R4): if L1 lands at, say, +9 vs L0, L2's effective lift over L1 is only +2.6 — below the +5 floor for L2 vs L1 in NORTH-STAR.md operational test #6. We do not know yet which side of that floor we are on.
- **Cross-vendor**: not measured. Per NORTH-STAR.md operational test #11, model-agnostic axis is de-prioritized.

### Per-fixture diagnoses (Codex R4 verdicts)

- **F2** — variant +17 despite watchdog timeout. CRITIC killed mid-phase (state writes confirmed: build/build_gate/evaluate populated, critic phase started but verdict=-/duration=0). F2 timeout=1200s too tight for full 4-phase pipeline + inter-phase gaps. Bump to 1500-1800s candidate for iter-0019 fixture metadata.
- **F4** — variant +21, the largest L2 lift. **Plausibly tool-attached** (browser_validate + native security-review on browser=true) per Codex R3, not pair-deliberation-attached. iter-0020 must instrument tool-vs-deliberation attribution before claiming pair lift here.
- **F5** — variant −1 on scope. Codex R4 verdict: "**root cause is surgical-change failure, not pairing is inherently waste**. The waste signal is real (17× wall for no quality gain), but the actionable fix is BUILD policy: stricter scope boundary, no opportunistic metadata edits, audit must explicitly reject unrelated file/frontmatter/status changes." → iter-0019 BUILD prompt fold-in.
- **F6** — variant +10, bare hits two CRITICAL findings (non-ENOENT rethrow, createReadStream constraint violation). Genuine pair lift on constraint discipline.
- **F9** — both arms verify=0.4 spec=16/13. Same output contract failure across L0 and L2: missing `Error:` prefix, wrong exit 2, wrong JSON shape, unranked authors. Codex R4 verdict: "measurement/report integrity adjacent because both arms failed the same output contract. **Do not use F9 for pair-policy conclusions until fixed.**" → iter-0018 spec/pipeline diagnosis required.

### What iter-0014/0017 protocol confirmed (positive)

- iter-0014 state-writes-per-phase: F2 variant `phases.{build, build_gate, evaluate, critic}` populated even on watchdog kill. Pre-iter-0014 would have shown only `evaluate`. Causality attribution to CRITIC was possible because of this.
- iter-0012 `WATCHDOG_FIRED` sentinel: F2 variant `result.json.timed_out=true`, `invoke_exit=124`.
- iter-0017 auto-mirror: `[suite] mirrored 26 committed skill(s)` at suite startup.
- F4 variant `phases.{browser_validate, build, build_gate, evaluate}` — browser_validate phase visible (not exercised in F1-only iter-0014 falsification gate).

### Open observability gap

F2 variant: 678s of inter-phase time unaccounted by per-phase `duration_ms` (sum of `build+build_gate+evaluate+critic` durations = 523s; arm wall = 1201s). Phase 1.4/1.5 routing not measured by current state-write protocol. iter-0019 or iter-0020 BUILD/EVAL prompt fold-in may close this; defer if not load-bearing.

## North Star refinement (2026-04-27, post-iter-0017)

User clarified the project goal in two passes during this session:

1. **3-layer performance contract**: L0 bare → L1 solo harness → L2 pair harness. Single-LLM users (Opus alone, GPT-5.5 alone) are first-class — they get L1, which must beat L0. Multi-LLM users get L2, which must beat L1. **De-prioritized**: cross-vendor "model-agnostic" axis (Qwen / Gemini / Gemma); not the North Star.
2. **Efficiency is first-class at every layer**: each layer must beat `previous-layer-best-of-N` where N is the wall-time ratio. "Pair is slower but more thoughtful" is rejected — if L2 takes 17× the wall-time of L0 at verify-tie, the user could have run bare-best-of-17 and likely gotten a better result.

Codex GPT-5.5 R1 + R2 review concurred with the L0 / L1 / L2 framing and contributed:

- Release gate numbers (suite avg margin ≥ +8 preferred / ≥ +5 floor; F9 ≥ +5; 7/9 fixtures ≥ +5; zero variant DQ/CRITICAL/HIGH/timeouts).
- Per-phase decision-mode taxonomy (`solo` / `pair_critic` / `pair_consensus`) and the table now in `NORTH-STAR.md`.
- Pushback on EVAL = unconditional pair (would recreate F5/F6 waste): made it **gated solo → escalate to pair_critic only on signals**.
- Pushback on full profile-neutral runtime abstraction (`engine-roles.json` + dispatcher): **overengineering** since model-agnostic is no longer the North Star. Keep policy in text only; provider names stay inline in SKILL.md PHASE blocks.
- Iteration-loop pair vs auto-resolve pair: **same vocabulary, different thresholds** (iter-loop tolerates more pair because cost is amortized over harness improvements; auto-resolve must be aggressively gated because every pair call is paid by the user on every run).

`PRINCIPLES.md` gained a sixth principle, "Layer-cost-justified," that operationalizes the efficiency contract. Iteration files now must enumerate principles 1–6.

## What was just shipped (iter-0017)

Full data in `iterations/0017-run-suite-auto-mirror.md`.

Single-file diff, +33 lines, in `benchmark/auto-resolve/scripts/run-suite.sh`.
Adds an auto-mirror block right after the run banner that replicates
`bin/devlyn.js`'s `cleanManagedSkillDirs` + `copyRecursive` semantics for the
skills tree only — no `CLAUDE.md` copy, no `.gitignore` mutation, no
`settings.json` writes, no agent-pack install. Per-skill staging dir +
atomic `mv` keeps Ctrl-C from leaving a managed skill missing. UNSHIPPED list
inline (4 entries; comment points at `bin/devlyn.js:299`). Skipped only in
`--judge-only`; runs in `--dry-run` so suite-setup verification covers the
mirror path.

Falsified locally: marker injection + drift simulation + dry-run produced
`[suite] mirrored 26 committed skill(s)` stamp; marker propagated; drift
removed; user-installed skills preserved (verified with synthetic
`.claude/skills/fake-user-skill/`); UNSHIPPED workspace dirs absent in
`.claude/skills/`. Lint 10/10. Zero model spend.

Codex GPT-5.5 R0 (84s, 41k tokens) verdict: M2 (inline shell) over M1
(`bin/devlyn.js -y` — too broad) and M3 (rsync — macOS variance). All R0
recommendations adopted verbatim.

## What was shipped before that (iter-0014)

Full data in `iterations/0014-state-writes-per-phase.md`.

6-file diff, +138/-21, no new files, no new abstractions. Two bugs closed in one iter, both surfaced from iter-0013's F1 successful run:

1. **State-writes-per-phase contract drift.** `pipeline-state.md:165-171` requires per-phase `phases.<name>.{started_at, round, triggered_by}` (orchestrator) at start and `{verdict, completed_at, duration_ms, artifacts}` (phase agent) at end. Pre iter-0014 F1 runs populated only `phases.evaluate`.
2. **Archive script path bug** (Codex iter-0014 R0 finding). SKILL.md ran `python3 scripts/{archive_run.py, terminal_verdict.py}` from work_dir, but those scripts live at `.claude/skills/devlyn:auto-resolve/scripts/`. Silent failure → artifacts piled in `.devlyn/`, never moved to `.devlyn/runs/<run_id>/`.

Edits:

- `config/skills/devlyn:auto-resolve/SKILL.md` — new `<state_write_protocol>` block; per-phase one-line reminders for PHASE 1/1.4/1.5/2/3/4; PHASE 5 detailed write directive; fixed script paths to `.claude/skills/devlyn:auto-resolve/scripts/`.
- `references/phases/phase-1-build.md` / `phase-2-evaluate.md` / `phase-3-critic.md` — explicit final-state-json write line listing all required fields.
- `autoresearch/iterations/0014-state-writes-per-phase.md` (new).
- `autoresearch/HANDOFF.md` (this file, updated again now).

Falsification gate (RUN_ID `iter0014-verify-20260427T092859Z`):

| Phase | verdict | started_at | completed_at | duration_ms | engine | artifacts |
|---|---|---|---|---|---|---|
| `build` | PASS | 2026-04-27T09:29:50Z | 2026-04-27T09:33:22Z | 212000 | codex | `{}` |
| `build_gate` | PASS | 2026-04-27T09:34:30Z | 2026-04-27T09:34:35Z | 5000 | bash | `{findings_file, log_file}` |
| `evaluate` | PASS | 2026-04-27T09:34:40Z | 2026-04-27T09:35:30Z | 50000 | claude | `{findings_file, log_file}` |
| `final_report` | PASS | 2026-04-27T09:35:45Z | 2026-04-27T09:35:50Z | 5000 | bash | `{}` |

elapsed=610s under 900s budget; verify_score=0.8; archive ran (`.devlyn/runs/ar-20260427T092945Z-f221066a9098/` populated).

---

## Decided next step — recommended

**Recommendation: full-suite verification run under iter-0014** (filed as iter-0016 below). Concrete pain check: confirm F2/F4/F5/F6/F9 also benefit from per-phase state writes + archive fix, and surface any CRITIC/DOCS observability gaps that the F1-only verify (fast route) didn't exercise. Cost: ~1 hour wall, ~$10-20 spend.

If user prefers not to spend on a suite run: pick from the queue below by current pain. Option A (shim distribution, iter-0015) stays deferred per Karpathy #2 unless production regression observed.

---

## Critical gotcha — sync gap (now self-healing)

**As of iter-0017, `run-suite.sh` auto-mirrors `config/skills/` → `.claude/skills/`** at the top of every invocation (skipped only in `--judge-only`). Manual mirror via `node bin/devlyn.js -y` is no longer required before benchmarks.

**Still useful before a commit / lint pass**:

```bash
diff -rq config/skills/ .claude/skills/ 2>&1 | grep -v "Only in"
```

Expected: silence (UNSHIPPED_SKILL_DIRS legitimately have `Only in config/skills/...` lines per `bin/devlyn.js:299` exclusion list). If non-empty, either run `bash benchmark/auto-resolve/scripts/run-suite.sh --dry-run F1` (cheapest sync) or `node bin/devlyn.js -y` (full installer).

iter-0014 specifically modified: `SKILL.md`, `phase-1-build.md`, `phase-2-evaluate.md`, `phase-3-critic.md`. Those four are mirror-parity-checked by lint Check 6. Lint enforces the equivalence at commit time even though run-suite handles it at run time.

---

## Cross-judge sidecar — iter-0006-full data still relevant

`benchmark/auto-resolve/results/20260426T034926Z-1ac7594-iter-0006-full/cross-judge-summary.json` has Opus 4.7 dual-judge data over the same sanitized prompts. Pearson(margins)=0.988, winner_agree=6/9, sign_agree=7/9. Mild self-judgment bias signal (~5.6pt — GPT-5.5 inflates variant scores relative to Opus). Permanent dual-judge in `judge.sh` queued as iter-0019.

---

## What is shipped vs queued (post iter-0014 SHIP)

### Shipped on this branch (chronological)

`DECISIONS.md` is canonical. Quick map:

- iter 0001 — skill scope-first + trivial-fast routing
- iter 0002 — F6/F7 spec annotation
- iter 0003 — process-group watchdog
- iter 0004 — outer claude -p MCP isolation
- iter 0005 REVERTED
- iter 0006 REVERTED (per iter-0007 verdict)
- iter 0007 — F6 isolation experiment, conclusive
- iter 0008 REJECTED (prompt-level contract empirically dead)
- iter 0009 SHIPPED — wrapper + PATH shim. F2 BUILD ran 399.9s through wrapper without watchdog kill; F6 +60-pt recovery.
- iter 0010 SHIPPED — production rollout of wrapper-form to ideate / preflight / team-resolve / team-review; lint Check 10 added; shim shipping deferred per Codex R1 ship-blocker.
- iter 0011 SHIPPED — Codex Option D: Check 10 evasion-shape close (pattern broadened to invocation-class `codex exec[[:space:]]+\S`) + priming-token scrub in shared docs. Falsification canary 6/6.
- iter 0012 SHIPPED — `run-fixture.sh` `timed_out` derivation switched to WATCHDOG_FIRED Bash sentinel (vs `elapsed >= timeout`).
- iter 0013 SHIPPED — F1 metadata.timeout 480→900s after Codex-corrected reframe and 465s clean discriminator.
- **iter 0014 SHIPPED** — state-writes-per-phase observability + archive script path. D4-lite design (universal block + per-phase reminders + prompt-body strengthening) per Codex R0; archive bug found via Codex grepping `archive_run.py`.
- **iter 0017 SHIPPED** — `run-suite.sh` auto-mirror `config/skills/ → .claude/skills/`. Codex GPT-5.5 R0 picked M2 (inline shell mirror) over M1 (`bin/devlyn.js -y`, too broad — touches CLAUDE.md, .gitignore, project + global settings, agent packs) and M3 (rsync, macOS variance). Per-skill staging dir + atomic `mv` for Ctrl-C safety. Falsified locally with marker injection + drift simulation + user-skill-preservation test; lint 10/10; zero model spend.
- **iter 0016 (5-fixture suite)** — F2/F4/F5/F6/F9 ran post iter-0014/0017; suite avg variant 93.8 / bare 82.2 / margin +11.6 / wall ratio 11.4×. SHIP-GATE FAIL (volume rule: 4/5 ≥ +5 against absolute 7/9 floor). 0 hard-floor violations. F2 +17 (variant TO at 1200s but quality high), F4 +21 (largest L2 lift, plausibly tool-attached), F5 −1 (variant added `completed=` to roadmap frontmatter — surgical-scope failure not pair waste), F6 +10 (genuine constraint lift), F9 +11 but both arms verify=0.4 spec=16/13 (pipeline-level spec-compliance failure, not pair vs solo). Final readout in `iter-0016` results + `iterations/0018-measurement-integrity.md`.
- **iter 0018 SHIPPED** — Measurement integrity + report-shape lock. Added `wall_ratio_variant_over_bare` per-row + `wall_ratio_variant_over_bare_avg` aggregate to `summary.json` and report.md. Locked iter-0016 final readout into HANDOFF.md + NORTH-STAR.md operational test #13 (L2-vs-L1 compression risk, "release not implied" honest-claim language). Classified F5 as surgical-scope failure (iter-0019 BUILD prompt fold-in) and F9 as pipeline spec-compliance failure (iter-0019/0020 BUILD/EVAL prompt fold-in). CLAUDE.md gained Codex companion pair-review section distinguishing iteration-loop pair from auto-resolve pair (same vocabulary, different thresholds). Diagnostic-only — zero paid runs, lint 10/10.
- **iter 0018.5 SHIPPED** — BUILD/EVAL prompt fold-ins for F5 (spec-frontmatter ban) + F9 (literal-verification rule + EVAL `correctness.{exit-code,spec-string,json-shape,format}-mismatch` + `scope.frontmatter-edit` rule_ids). 4 bullets total across `phase-1-build.md` + `phase-2-evaluate.md` `<quality_bar>` blocks. Codex R0 Q4/Q5/Q7 verdicts adopted verbatim; split from iter-0019 to keep attribution clean. Text-only — zero paid runs, lint 10/10. Behavior claim is iter-0019's job (F5 variant scope should return to 25, F9 variant spec should reach ≥22).

### Queued (next hypotheses, ordered, post iter-0017)

1. **iter-0015 — shim distribution to user installs** (long-deferred per Karpathy #2). Design fail-open shim + `devlyn doctor activate` (NOT npm post-install) + idempotent settings.json merge. Revisit when production regression observed.
2. **iter-0016 — full-suite verification under iter-0014/0017**. Run F2/F4/F5/F6/F9 and confirm state-write protocol + archive fix carry over. May surface CRITIC/DOCS phase observability gaps on `standard` route. Now safer post iter-0017 (auto-mirror closes one of the two stale-skill failure modes).
3. **iter-0018 — `claude -p --output-format stream-json`** for variant arm. Would make transcript flush incrementally and survive SIGTERM partial output. Optional; not pressing once F1 budget is right.
5. **iter-0019 — permanent dual-judge in judge.sh** (`memory/project_dual_judge_2026_04_26.md`).
6. **iter-0020 — silent-catch fixture spec**. F2 spec language allows BUILD output with `catch { return fallback }`; tighten.
7. **iter-0021 — F9 wall-time regression**. Both iter-0006 single-fixture F9 attempts took >30 min. Bump F9 metadata.timeout to 5400s.
8. **iter-0022 — single-fixture ship-gate hard-floor bug**. Ship-gate currently passes catastrophic regression on N=1 because 7/9 floor not applied at N=1.
9. **iter-0023 — F6 chronic slowness investigation**.
10. **iter-0024 — auto-resolve stuck-execution abort criteria** (skill guardrail G5).
11. **5-Why operationalization in CLAUDE.md** (codex round 2 Karpathy #1 expansion).
12. **DOCS Job 2 wider verification** (long-queued).
13. **Held-out fixture set** (don't build until 3+ fixtures improve with no intuitive mechanism).
14. **Adversarial-ask layer** (long-term).

### Deferred (user-direction, awaiting explicit user call)

- Multi-LLM orchestration modes (3 modes + extensibility) — `memory/project_orchestration_modes_2026_04_26.md`.
- Benchmark cross-mix arms — `memory/project_benchmark_cross_mix_2026_04_26.md`.

---

## Decisions locked in the 2026-04-27 → 2026-04-28 session (compressed)

These are the load-bearing conclusions a fresh session must inherit. Each links to the canonical doc — read those when you need detail.

1. **3-layer performance contract** — L0 bare → L1 solo harness → L2 pair harness. Each layer beats `previous-layer-best-of-N` on quality AND wall-time efficiency. (`NORTH-STAR.md` operational tests #1-13.)

2. **Two first-class user groups** — single-LLM users (Opus alone, GPT-5.5 alone) and multi-LLM users (Claude + Codex). Both must beat their respective baselines. iter-0019 ships `solo_claude` (L1-claude) arm; `solo_codex` deferred (no non-Claude orchestrator path).

3. **Efficiency is first-class at every layer** — "slower but more thoughtful" is rejected. PRINCIPLES.md gained principle #6 "Layer-cost-justified."

4. **Model-agnostic axis is de-prioritized** — user direction. Vocabulary is profile-neutral (`solo`/`pair_critic`/`pair_consensus`) but no runtime engine-swap dispatcher. Cross-vendor fixtures remain a deferred memo.

5. **Per-phase decision-mode taxonomy** (iter-0020 target — text-only landing, no runtime engine-swap):
   - ROUTE = solo, BUILD = solo Codex, BUILD_GATE = solo deterministic
   - EVAL = gated solo → escalate to pair_critic on signals (NOT unconditional pair — would recreate F5/F6 waste)
   - CRITIC = pair_critic with checklist-coverage short-circuit
   - DOCS = solo, JUDGE = pair_consensus, FINAL_REPORT = solo
   Short-circuit rule for CRITIC: skip second model if 0 CRITICAL/HIGH AND no uncertainty/coverage flags AND **checklist coverage met** (deterministic anti-overconfidence guard, NOT vibe confidence).

6. **iter-0016 readout (5-fixture partial, locked)** — variant 93.8 / bare 82.2 / margin +11.6 / wall ratio 11.4× / SHIP-GATE FAIL (only 4/5 ≥ +5 against 7/9). 0 hard-floor. **L2 vs L0 only — L2 vs L1 unknown.** F2 +17 (TO 1201s), F4 +21 (plausibly tool-attached not pair-attached), F5 −1 (BUILD added `completed=` to roadmap frontmatter — surgical-scope failure not pair waste, fixed in iter-0018.5), F6 +10, F9 +11 with both arms verify=0.4 spec=16/13 (pipeline spec-compliance failure, fixed in iter-0018.5).

7. **F4 lift attribution unknown** — plausibly tool-attached (browser_validate + native security-review fired on `browser=true`) not pair-deliberation-attached. Pair > solo is **UNPROVEN**. iter-0020 must instrument tool-vs-deliberation attribution before claiming pair lift.

8. **Release-blocking gates** — `NORTH-STAR.md` operational tests:
   - L1 vs L0: suite avg ≥ +8 preferred / ≥ +5 floor, F9 ≥ +5, ≥ 7/9 fixtures, 0 variant DQ/CRITICAL/HIGH/timeouts, wall ratio ≤ 5.0 soft ceiling.
   - L2 vs L1: L1 must pass first (release-blocker). L2 must not regress any fixture by ≥ −3. L2 must beat L1 by ≥ +5 on **pair-eligible/high-value fixtures** (NOT flat suite avg). L2 efficiency: `L2-best-of-M` must lose to L2.
   - **No release-readiness language** until iter-0020's full 9-fixture L0/L1/L2 paid run delivers L2-vs-L1 numbers.

9. **CLAUDE.md install-time identity gap** — `bin/devlyn.js:568-572` copies `$REPO_ROOT/CLAUDE.md` to `<cwd>/CLAUDE.md` at install; benchmark variant arm reads same file. For variant scores to predict end-user experience, byte-identity required. No tooling enforces this yet. Lint Check 11 + CI gate planned. Full audit + minimization plan in `autoresearch/iterations/PROPOSAL-claude-md-minimization.md` (queued post iter-0019, do NOT bundle with iter-0020).

10. **iter-0019 R0 design pushbacks** (locked into iter-0019 part 1 commit `c08130f`):
    - Q1: B over A — `CODEX_BLOCKED=1` env enforced in shim + monitored.sh (defense in depth), NOT just `--engine claude` flag (iter-0008 proved prompt-only constraints insufficient).
    - Q2: F1+F2+F4+F6+F9 (added F6 for constraint-discipline coverage; kept F1 fast-route sentinel).
    - Q3: F2 timeout 1200→1500s. NOT 1800. If 1500 still TO, treat inter-phase gap as the bug.
    - Q6: same judge prompt scores all 3 arms (no separately-calibrated calls). 3-arm randomized A/B/C blind mapping. Schema in `judge.sh` + `compile-report.py`.
    - Q7: split iter-0018.5 (prompt-only) from iter-0019 (arm + schema) for attribution clean.

11. **Codex companion pair-review pattern** (iteration-loop only, NOT runtime skill behavior) — `bash config/skills/_shared/codex-monitored.sh -C <repo> -s read-only -c model_reasoning_effort=xhigh "<prompt>"`. **Never pipe** the wrapper output. Reason independently FIRST, then send Codex rich evidence + falsification prompt, then surface pushback transparently. CLAUDE.md "Codex invocation" section has the operating contract.

## How to resume cleanly in a new session

1. **Read `autoresearch/NORTH-STAR.md` first.** Outer goal + L0/L1/L2 contracts + per-phase decision-mode taxonomy. Ground truth.
2. **Read `autoresearch/HANDOFF.md` second** (this file) — start with the "⚠️ COLD-START CRITICAL CONTEXT" block at the top. Operating context layered on top of the goal.
3. **Read `autoresearch/PRINCIPLES.md`** if you'll be writing an iteration file (principles 1–6 must be checked).
4. **Read `autoresearch/iterations/PROPOSAL-claude-md-minimization.md`** if a question about CLAUDE.md, install-time identity, or context pollution comes up — it's the queued audit work.
5. **Check the running suite first** before any edit:
   ```bash
   ps -p $(grep SUITE_PID /tmp/iter-0019-logs/pid.txt | cut -d= -f2) -o pid,etime
   ```
   If it's alive, follow the "Do NOT do these things" list above. If it's done, follow iter-0019 part 2 in the queue.
6. `cd /Users/aipalm/Documents/GitHub/devlyn-cli && git status && git log --oneline -10` — confirm branch state matches the HEAD chain above (top of "Current state" section).
7. `diff -rq config/skills/ .claude/skills/ 2>&1 | grep -v "Only in"` — must be silent. As of iter-0017 `run-suite.sh` self-heals at start of every invocation, so this is belt-and-suspenders.
8. `bash scripts/lint-skills.sh` — must pass all 10 checks before any commit.
9. **All Codex collaboration goes through the local CLI**, never MCP. Pattern: `bash config/skills/_shared/codex-monitored.sh -C /Users/aipalm/Documents/GitHub/devlyn-cli -s read-only -c model_reasoning_effort=xhigh "<prompt>"`. Never pipe the wrapper output (`| tail`, `| head`, `| grep` without `--line-buffered`) — pipe-stdout is refused per iter-0009. Output too large goes to `~/.claude/projects/.../tool-results/<id>.txt` automatically; read that file with `Read` rather than re-running.
10. Reason independently first; consult Codex with rich evidence; never delegate the decision (`feedback_user_directions_vs_debate.md`).
11. **If iter-0019 background suite is still running** (PID 93465, log `/tmp/iter-0019-logs/suite.log`): do NOT interrupt. iter-0019 part 2 (verdict + iter file + commit) is the next step once it completes.

---

## Don't lose these decisions / lessons (cumulative)

1. **CLAUDE.md stays clean of conditional rules.** 5-Why is Karpathy #1 expansion, not a new top-level rule.
2. **RUBRIC.md does not change** during a benchmarking window.
3. **Don't build held-out fixtures yet.** Trigger: 3+ fixtures improve with no intuitive mechanism.
4. **Don't blanket-kill `codex-mcp-server` processes.** Iter 0003's narrow watchdog is the right scope.
5. **The four oracles are tools, not the loop.** The loop is iteration files + DECISIONS.md + benchmarks.
6. **`claude-debug.log` is metadata-only.** For "did codex run?", use `~/.codex/sessions/` + `pipeline.state.json`.
7. **Single-fixture falsification gate is necessary but not sufficient** for full-suite ship — but **single-fixture isolation IS sufficient for causality attribution** when comparing two HEADs (iter-0007 proved this).
8. **Don't pass `--accept-missing` to ship-gate when all 9 fixtures exist.**
9. **Self-judgment bias** is real (~5.6pt). Permanent dual-judge queued as iter-0019.
10. **Universal contract rules over-fit single failure modes.** iter-0006 banned a category to prevent a specific shape; the category is broader than the shape. Apply skill guardrails G1-G5 (`memory/project_skill_guardrails_2026_04_26.md`) before merging any contract change.
11. **Read your own data carefully.** Codex Round 16 caught a CSV column-order misread; iter-0014 R0 caught a wrong knock-on-bug claim by reading `archive_run.py` itself.
12. **User directions ≠ debate prompts.** When user says "we're going X direction," ask codex for best practice + improvements, NOT "should we?". Surface codex pushback transparently. (`feedback_user_directions_vs_debate.md`)
13. **`zsh -c source <snapshot>` overrides parent PATH.** Project-scope `$WORK_DIR/.claude/settings.json env.PATH` override is the only reliable way to inject PATH into Bash dispatches inside `claude -p`. (iter-0009.)
14. **`[ -p /dev/stdout ]` is the portable POSIX test for "stdout is a pipe."** Used in iter-0009 wrapper.
15. **Cross-model GAN earned its keep at every iter from iter-0009 onward.** Continue dual-model practice. iter-0014 R0 caught a separate archive bug I'd missed entirely.
16. **Static gate suffices when mechanism is unchanged** (iter-0010 lesson). Text-only changes that ride on a proven mechanism don't need a benchmark gate; lint check + canary is the right scope.
17. **Pattern-priming applies even to descriptive text** (iter-0010/0011 lesson). Phrases like "passes args through to `codex exec` verbatim" leak the token into orchestrator prior. Rephrase in prompt-facing files.
18. **Lint patterns must cover all syntactic shapes the orchestrator can emit** (iter-0010 R2 + iter-0011 lesson). Multi-line `codex exec \` had to be added; quoted/variable/literal shapes too. Bind the invocation *class*, not specific shapes.
19. **`set -u` traps are silent until they fire** (iter-0012 lesson). Pre-initialize every variable that downstream `export` references in the branch where it's introduced.
20. **References are docs; SKILL.md PHASE sections are scripts** (iter-0014 lesson). Contracts that live only in references get ignored at action time. Salience matters: contracts must surface where the orchestrator's attention is during execution.
21. **Prompt-body output contracts alone are not enough** (iter-0014 lesson). `build-gate.md` had explicit per-field contract and orchestrator still skipped the write empirically. Defense in depth: orchestrator validates after agent.
22. **Script paths must be relative to where they're invoked from** (iter-0014 lesson). SKILL.md ran `scripts/archive_run.py` but the orchestrator runs from work_dir; use `.claude/skills/<skill>/scripts/...` for portability.
23. **HANDOFF framings can decay** (iter-0013 lesson). Always re-read raw artifacts; never trust prior framings without verification.
24. **Change one variable per iter when measurement matters** (iter-0018.5 lesson). Codex R0 Q7 framing: bundling prompt edits + new arm + schema change makes attribution muddy. Split into prompt-only iter (text fix) + arm/schema iter (behavior fix) so any movement attributes cleanly. iter-0018.5 (prompt fold-ins) → iter-0019 (arm + schema) is the worked example.
25. **EVAL must execute, not just opine** (iter-0018.5 lesson). F9 in iter-0016 had spec=16 because EVAL inspected the diff but never ran the spec's `verification_commands`. Literal-match-by-execution is a different discipline; lives in EVAL `<quality_bar>` with four `rule_id`-anchored bullets (`correctness.{exit-code, spec-string, json-shape, format}-mismatch`).
26. **`quality_bar` is the right surface for cross-cutting BUILD/EVAL contracts** (iter-0018.5 lesson, builds on iter-0014 #20). Bullets there get re-read every phase invocation; rules buried in `references/findings-schema.md` reference docs may not be loaded at action time. When adding a new contract that the orchestrator must enforce, place it in `<quality_bar>` first; promote to a separate reference only if the contract grows beyond bullet-shape.
27. **Engine-routing is not the place for output-contract rules** (iter-0018.5 lesson, Codex R0 Q5). `_shared/engine-routing.md` controls *which engine* runs each phase; output contract (frontmatter ban, literal-match) is *what each engine does*. Different layers — do not conflate. Output contracts live in the phase prompt's `<quality_bar>`.
28. **Pair-policy claims need attribution between tool-lift and deliberation-lift** (iter-0018 / Codex R3 lesson). F4's +21 in iter-0016 is the largest L2 lift but plausibly tool-attached (browser_validate + native security-review fired on browser=true). Until iter-0020 instruments the two signals separately, "pair > solo" is unproven. iter-0019 / 0020 must keep this distinction live.

---

## Codex collaboration log (running)

- R1–R5 (iter 0005): inner-codex flag bundle work.
- R6: expand falsification gate F2 → F5 → F4 → F9 → full.
- R7: sync-gap fix = Option A.
- R8: routing-telemetry observability (later moot).
- R9: F4 score-94 borderline pass.
- R10: F9 #1 environmental, RERUN.
- R11: F9 #2 strict-fail by criteria.
- R12: harness-truth halt — RETRACTED in R13.
- R13: confirm retraction, run full-suite.
- R14: post-results — DEFER not REVERT, F6 isolation as iter-0007.
- R15: strategic check — fold iter-0008 wall-time into iter-0007, cut iter-0012 for now.
- R16: caught CSV column-order misread (F6 prior 0-files claim wrong; F4/F5 noise → "shared runtime/API failure").
- R17: post-isolation — REVERT confirmed; iter-0008 = narrow kill-shape ban.
- iter-0009 R1: hook → PATH shim swap. Wrapper streams full stdout (no `tail -200`).
- iter-0009 R2: `| tail -200` defeats wrapper streaming → wrapper must refuse pipe-stdout via `[ -p /dev/stdout ]`. Heartbeat to stderr (cleaner stdout = codex output). Mirror parity for `engine-routing.md`.
- iter-0010 R1: shim-shipping ship-blocker (hard-fails 127 without env wiring). Heartbeat doc bug. Drop shim-shipping; defer.
- iter-0010 R2: lint Check 10 multi-line blind spot caught before commit. Residual descriptive `codex exec` mentions to rephrase.
- iter-0011 R0: I proposed B → C → defer A (Karpathy #2). Codex flagged a real risk class (`codex exec "<prompt>"` evasion shape) and proposed Option D = cheap hardening (broaden Check 10 + scrub priming tokens). Adopted as iter-0011.
- iter-0012 R0: 5-line `timed_out` fix verdict. Caught (1) invariant misstatement (`elapsed=TIMEOUT-1` was already correct under `>=`); (2) `set -u` init-order trap requiring `WATCHDOG_FIRED=0` before `if DRY_RUN`; (3) don't couple to `INVOKE_EXIT==124`; (4) no new schema field; (5) leave SIGTERM grace alone; (6) `kill -0` race deferred.
- iter-0013 R0: F1 starvation reframe. Caught (1) my "0.6s away from natural exit" was over-asserted (SessionEnd hooks can be SIGTERM cleanup); (2) F1 didn't complete fast route; (3) one Bash dispatch took 268.5s. Recommendation: 900s discriminator first. Outcome A confirmed.
- iter-0014 R0: state-writes-per-phase + archive fix. Verdict: D4-lite (universal block + per-phase salience + prompt-body fixes). Pushback on knock-on bug claim — Codex read `archive_run.py` and showed moves are unconditional; verdict gates pruning only. Real cause: separate path bug. F1 verified post-fix.
- iter-0017 R0: auto-mirror config/skills → .claude/skills. Verdict: M2 inline shell (over M1 `bin/devlyn.js -y` too broad, M3 rsync too fragile). Per-skill staging + atomic mv for Ctrl-C safety. UNSHIPPED list inline + comment pointer.
- North Star R1 (84s, 41k tokens): release-gate numbers locked (suite avg ≥ +8 / ≥ +5, F9 ≥ +5, 7/9, zero DQ/CRITICAL/HIGH/timeouts). Per-phase decision-mode taxonomy (`solo` / `pair_critic` / `pair_consensus`). Iteration-loop pair vs auto-resolve pair = same vocabulary, different thresholds.
- North Star R2 (16k tokens): EVAL=gated solo not unconditional pair (would recreate F5/F6 waste). Profile-neutral abstraction = text-only, no runtime engine-swap dispatcher (overengineering since model-agnostic ≠ North Star).
- North Star R3 (97k tokens): re-ordered iter-0019 (L1-claude arm) ahead of iter-0020 (pair policy). L1-codex deferred (no non-Claude orchestrator path exists yet). F4 lift plausibly tool-attached (browser_validate) not pair-attached — pair > solo unproven. L2 release gate split from L1 (L1 must pass first; L2 vs L1 needs +5 on pair-eligible fixtures only).
- iter-0018 R0 (19k tokens, 27s): start iter-0018 on 5-fixture data; defer F1/F3/F7/F8 to iter-0019 paid run. F5 root cause = surgical-scope failure (BUILD added `completed=` to roadmap frontmatter beyond strict scope) not pair-deliberation waste. F9 = measurement-integrity adjacent (both arms failed same output contract — pipeline BUILD/EVAL prompt issue, not pair vs solo). L2-vs-L1 compression risk locked into NORTH-STAR.md test #13.
- iter-0019.A R-audit (2026-04-28, 7 rounds, ~640k tokens read total, xhigh): **SKILL audit + iter-0019.A patch**. Audit Round 1 (132k tokens, ~150s) scoped 3 gaps — Gap A (preflight Codex pair was single-shot, refined to preflight-only since ideate one-shot CHALLENGE is deliberate per cost discipline NORTH-STAR:122-123); Gap B (principle-evidence not surfaced — refined to rule_id overlay over canonical categories, NOT broad PRINCIPLE_VIOLATION bucket); Gap C (CLAUDE.md rules not propagating to SKILL prompts — confirmed via partial analogues in auto-resolve weaker than CLAUDE.md hard rules). Round 2 (81k tokens, ~200s) converged patch shape — RND2 5 triggers + Synthesis diagnostics shape; rule_id overlay 6-row table (subtractive-first-violation conditional on `base_ref_sha`; score-chasing/layer-cost-justified excluded as autoresearch-only); shared `runtime-principles.md` + lint Check 12 (separate from Check 6). Step 1-5 reviews (~430k tokens, 7 sub-rounds) caught: redundant intro lines, false consumption claims, hardcoded-values wording weakening, config-knob threshold drop, fix-loop+DOCS Codex hot path miss (HIGH×2), `DIVERGENT` auto-resolve-foreign category (HIGH), fake `tags` field schema mismatch (MEDIUM×2), section ordering contradiction in PHASE 3.5 placement, user presentation timing pre-R2, dedup key fallback for findings without rule_id, R2 engine = actual (not requested) Round 1 engine, BLOCKED + RETRACTED Phase 4 interaction, report-template forward-references, browser-auditor "or"→"and" evidence, Coverage always-present, Check 12 byte-compare via diff (command-substitution strips trailing newlines), marker topology + canonical order + contract-block containment, `runtime-principles.md` "verbatim"→"compact derived excerpt" wording. ALL findings adopted. **Pattern lessons**: (1) one-shot Codex critic is deliberate at planning-layer (ideate CHALLENGE) but wrong at verification-gate (preflight) — same vocabulary, different thresholds; (2) every cross-layer rule needs both shared-source-of-truth AND drift-detector lint; (3) schema discipline at design time prevents fake-field findings; (4) lint can subtractively net-positive when each added line closes a specific known failure mode (Check 12 hardening: 3 categories of drift caught only by markers + topology + diff-over-temp-files combined).
- iter-0019.6 R-verdict (2026-04-28, post-acceptance, 138k tokens, 256s, xhigh): **F9 acceptance verdict pair-review** — verdict **ship-as-PASS** with one wording correction adopted (namespace the "0 CRITICAL findings post-EVAL" claim to `correctness.spec-literal-mismatch` scope; the JUDGE still emits 2 critical findings on F9/variant — ranked format + exact stderr — non-DQ, out of iter-0019.6 scope, queued for iter-0020+ gate-vocabulary enrichment). Codex Q answers all confirm draft: (Q1) 1-fixture sufficient because HANDOFF explicitly scoped F9 acceptance, NOT sufficient for NORTH-STAR release readiness which is iter-0020's 9-fixture run; (Q2) judge findings don't invalidate but record explicitly; (Q3) solo_claude DQ is judge-side silent-catch behavior not codex leakage (settings.json shows no `CODEX_REAL_BIN`, iter-0019.5 fix held); (Q4) L1-L0=+3 is 1-fixture smoke read, not L1 release gate; (Q5) iter-0020 unblock confirmed, has its own hard acceptance; (Q6) main fragility is claim-boundary not mechanism — helper has no hard-coded command count, but **real-user runs without `.devlyn/spec-verify.json` staging are deliberate silent no-op** so do NOT claim real-user coverage yet (iter-0020 OR iter-0019.8 must address /devlyn:ideate generating the JSON from spec "## Verification" sections). **Pattern lesson**: post-acceptance pair-review pays for itself even on clean PASS — Codex caught the namespace blur that would have over-claimed coverage in DECISIONS.md. ship-as-PASS adopted, namespace correction applied.
- iter-0019.6 R-launch (2026-04-28, pre-launch acceptance, 137k tokens, 314s, xhigh): **F9 acceptance suite launch-time pair-review** — verdict **HOLD-and-fix-then-launch**. Caught a real fixture-contract bug that would have invalidated the paid run: F9 expected.json verification_commands[4] (`node --test tests/`) declared `stdout_not_contains: ["fail "]`, but Node's test runner always emits `# fail 0` in its passing summary. Pre iter-0019.6 the false negative was just a verify-score nuisance (3 arms iter-0019 verify.json data: variant/solo/bare all hit `pass:false reason:"unexpected_text"` with `# fail 0` in stdout tail). Post iter-0019.6 the same fixture line becomes a `correctness.spec-literal-mismatch` CRITICAL the orchestrator literally cannot fix — Node's output is fixed. Acceptance gate would have burned $5-10 testing fix-loop convergence on an unsatisfiable command, not the actual mechanism. Cheapest unblock: drop the `stdout_not_contains` entry; `exit_code: 0` already enforces zero failing tests via the runner's own exit semantics. Filed and shipped as iter-0019.6.1 (`da3eef5`) before launch. **Pattern lesson**: when promoting prompt-only contract enforcement to mechanical-bash-gate enforcement, audit fixture commands for **runner-output self-references** (`# pass`, `# fail 0`, `1..N`, `not ok`, `ok`) that overlap with `stdout_not_contains` literals — these become unsatisfiable post-promotion. Same anti-pattern as iter-0019.5's CODEX_REAL_BIN export ("diagnostic visibility justifies bypass weapon export"): "weak-signal verify-score noise" can become "fatal CRITICAL block" simply by tightening the enforcement layer beneath the contract.
- iter-0019 R5 (2026-04-28, post-verdict, ~76k tokens, 186s, xhigh): **iter-0019.6 design pair-review**. Adopted in full: (1) stage normalized `.devlyn/spec-verify.json` containing only verification_commands — keeps tier_a_waivers / scope oracles / deps caps out of BUILD_GATE by construction; (2) BENCH_WORKDIR is NOT currently inherited by orchestrator — must add `export BENCH_WORKDIR="$WORK_DIR"` in claude -p dispatch subshell or F9 cmd #3 is environment-flaky; (3) drafted custom finding fields (evidence_path, touched_files, rule_type) DROPPED — use canonical schema from references/findings-schema.md (id, rule_id, level, severity, confidence, message, file, line, phase, criterion_ref, fix_hint, blocking, status); (4) helper script NON-OPTIONAL — prose-only repeats iter-0018.5 failure mode; Python (not bash) for JSON parsing safety; (5) mirror post-run verifier exactly: combined stdout+stderr, 60s timeout per command; (6) F9 DQ-clean claim is OUT OF SCOPE for iter-0019.6 since forbidden_patterns silent-catch enforcement is a separate path; (7) skill mirror parity must include the new helper script. Q4 verdict: iter-0019.6 does NOT violate iter-0020 R3 acceptance — this is correctness/contract enforcement, iter-0020 is policy. Pattern lesson: every layered defense's "diagnostic visibility" justification needs to be inverted to "fail-closed" justification — comments at `run-fixture.sh:113-116` (CODEX_REAL_BIN justified as diagnostic but actually bypass weapon) and prose-only enforcement layers (iter-0018.5 quality_bar bullets) are the same anti-pattern at different scopes.
- iter-0019 R4 (2026-04-28, post-suite, 43s, xhigh): **iter-0019.4 mapfile fix design**. Confirmed while-read replacement is correct; recommend `|| [ -n "$line" ]` guard for exact `mapfile -t` parity (harmless, preserves behavior on final unterminated line). Q2 (Bash version sentinel) and Q3 (run-suite.sh shebang change) deferred — out of scope for the regression fix. Pattern lesson: macOS /bin/bash 3.2 compatibility is a hard constraint for any harness script invoked via `bash <script>` — Bash 4+ builtins (mapfile, ${var,,}, &>, etc.) silently fail.
- iter-0019 R3 (2026-04-28, mid-suite, ~16k tokens, 26s, xhigh): **queue pre-flight 0 audit**. Confirmed all four cuts: (1) iter-0021 dual-judge → reframe as conditional (fires only if iter-0020 lands within ±6pt of routing-decision threshold); permanent dual-judge would be measurement polish; (2) CLAUDE.md minimization → gate on measurable A/B degradation; pollution claim is plausible but unproven and pre-flight 0 forbids assertion-only starts; (3) iter-0020 acceptance language tightened — must produce per-fixture-class routing table + at least one routing decision differing from current behavior + deterministic short-circuit/abort enforced in code + coverage.json + recorded rollback condition; aggregate score movement alone is non-acceptance evidence; (4) iter-0019.5 stays separate iter/commit (distinct failure mode from L1 arm enforcement, future-bisect-friendly attribution). Cost/wall iters pass pre-flight 0 by definition (direct user harm). **Lesson**: "harness self-knowledge" iters (dual-judge, measurement-of-measurement) are legitimate ONLY when bad measurement can plausibly cause a wrong user-facing decision; otherwise they violate pre-flight 0.
- iter-0019 R2 (2026-04-28, mid-suite, ~17k tokens, 37s, xhigh): **NORTH-STAR alignment audit** — user asked the load-bearing question "is this score-chasing or principle-aligned?". Codex pushed back on three fronts: (1) iter-0019 is North-Star-aligned **only if it becomes the last attribution run before a cost/reliability decision** — if the next iter is "more measurement," the loop has gone 산으로 and L1 was just score instrumentation; (2) heuristic for future iters: **"Every iter must either remove a real user failure or make the next go/no-go decision impossible to fake"** — landed as PRINCIPLES.md pre-flight 0; (3) termination criterion incomplete without a **real-project trial gate** — landed as NORTH-STAR.md operational test #14. Immediate constraint: iter-0019 verdict can only lead to one of three follow-up actions — fix F9 contract mechanically, implement cost-aware pair policy, or disable/narrow L2 where it fails L1 cost-adjusted. **No new measurement-only iter** until correctness/cost guardrails move. Locked into HANDOFF queue item #0 as a precommit Codex R2 (2026-04-28) precommit clause.
- iter-0019 R1 (2026-04-28, mid-suite, ~112k tokens, 142s, xhigh): **pre-data falsification on solo_claude enforcement**. Caught a real bypass class I missed: `run-fixture.sh:126-131` writes `CODEX_REAL_BIN=<absolute-path>` into the settings.json env block unconditionally, **including for ARM=solo_claude**. Orchestrator can do `Bash("$CODEX_REAL_BIN exec ...")` and reach real codex — both shim (PATH lookup not used) and wrapper (codex-monitored.sh not invoked) are bypassed. The codex node binary itself does NOT honor CODEX_BLOCKED. Author comment at run-fixture.sh:113-116 acknowledges the leak but kept it for diagnostic visibility — Codex correctly inverts: stop exporting `CODEX_REAL_BIN` for solo_claude (shim BLOCKED check fires before needing it; if BLOCKED later unset, shim fails closed instead of silently delegating). **Verdict-pass detection**: post-hoc greps over `claude-debug.log` + `~/.codex/sessions/.../session_meta.cwd` matching solo_claude paths is a reliable independent signal. Filed as iter-0019.5 (post iter-0019 part 2 verdict, separate commit). Verdict-greps script staged at `/tmp/iter0019-verdict-greps.sh`. **Pattern lesson**: every variable the harness exports into a worker subshell is a potential bypass surface — diagnostic-visibility comments should not justify exporting the bypass weapon itself.
- iter-0019 R0 (terse, on iter-0018.5+0019 design): **B over A on solo_claude arm** — `CODEX_BLOCKED` env enforced in shim + monitored.sh, blocker shim staged on solo_claude arm; A (`--engine claude` flag alone) too trust-based, iter-0008 proved prompt-only engine constraints insufficient. **F1+F2+F4+F6+F9 fixture set** (added F6 for constraint-discipline coverage where L1 might beat L0, kept F1 as fast-route sentinel). **F2 timeout 1500s** not 1800 (if still TO, treat inter-phase gap as the bug). **Q4 wording fix**: my draft implied BUILD might do the status flip; Codex's wording correctly attributes the flip to DOCS only. **Q5 location**: BUILD `quality_bar` + EVAL `quality_bar`, not shared engine-routing.md (engine-routing is wrong layer; it controls which engine, not what engine does). **Q5 active enforcement**: my draft was passive ("must match the spec"); Codex pushed for "EVAL forced to execute the verification commands and produce findings" — adopted via four `rule_id`-anchored bullets. **Q6 schema risk**: `judge.sh` + `compile-report.py` are hard-coded variant/bare; iter-0019 must add real 3-arm schema (`scores_by_arm`, `margins.{solo_over_bare, variant_over_bare, variant_over_solo}`, wall ratios), and the same judge prompt must score all three arms (no separately-calibrated judge calls — would invalidate L2-vs-L1 derivation). **Q7 split**: iter-0018.5 (prompt-only) + iter-0019 (arm + schema) keep attribution clean. All Q1-Q7 verdicts adopted verbatim.

---

## Memory entries that matter (cumulative)

Stored in `~/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/memory/`:

- `feedback_codex_cross_check.md` — dual-model GAN pattern.
- `feedback_auto_resolve_autonomy.md` — hands-free contract.
- `feedback_user_directions_vs_debate.md` — user directions are decisions, surface codex pushback.
- `project_v3_*.md` — historical harness redesign series.
- `project_autoresearch_framework_2026_04_25.md` — framework genesis.
- `project_skill_sync_gap_2026_04_26.md` — sync-gap gotcha.
- `project_orchestration_modes_2026_04_26.md` — DEFERRED, user-direction.
- `project_benchmark_cross_mix_2026_04_26.md` — DEFERRED, user-direction.
- `project_dual_judge_2026_04_26.md` — DECIDED, A sidecar shipped, B queued as iter-0019.
- `project_skill_guardrails_2026_04_26.md` — G1-G5 design constraints from iter-0006/0007.
- `project_iter0009_shipped_2026_04_27.md` — wrapper + PATH shim ship details.
- `project_iter0010_shipped_2026_04_27.md` — production rollout + shim shipping deferred.
- `project_iter0011_shipped_2026_04_27.md` — Codex Option D: Check 10 evasion-shape close + priming-scrub.
- `project_iter0012_shipped_2026_04_27.md` — `timed_out` derivation switched to WATCHDOG_FIRED sentinel.
- `project_iter0013_shipped_2026_04_27.md` — F1 timeout discriminator: 480→900s; HANDOFF reframe corrected.
- `project_iter0014_shipped_2026_04_27.md` — state-writes-per-phase + archive script path.
