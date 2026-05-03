# HANDOFF — for the next session

**Read order on cold start (mandatory)**:
1. **This file** — operating context + active iter + Codex collab protocol
2. [`NORTH-STAR.md`](NORTH-STAR.md) — project goal + 3-layer composition contract + pair-mode policy (round-3 redesign 2026-05-03)
3. [`PRINCIPLES.md`](PRINCIPLES.md) — pre-flight 0 + #1-#7 (every iter cites)
4. [`MISSIONS.md`](MISSIONS.md) — Mission 1 active, hard NO list
5. The active-iter file (currently `iterations/0033f-pair-plan-impl.md` — STUB; design baseline at `iterations/0033d-pair-plan-measurement.md` § "CLOSURE")
6. [`DECISIONS.md`](DECISIONS.md) — append-only ship/revert log (most recent entries first to read)

If any file contradicts another, **NORTH-STAR.md wins**, then this file, then PRINCIPLES.md. Open a doc-fix iter on the contradiction.

Last refined 2026-05-03 (post iter-0033d CLOSED-DESIGN — Codex R0+R0.5+R0.6 + principles-decision pair convergence on option B (defer-as-design-iter); 18+ structural leak surfaces enumerated as design baseline; iter-0033f-pair-plan-impl PRE-REGISTERED-STUB as new Phase 4 cutover gate).

---

## 🚦 START-HERE — three things active right now

1. **Active iter: `iter-0033f` PLAN-pair implementation** ([iterations/0033f-pair-plan-impl.md](iterations/0033f-pair-plan-impl.md)) — PRE-REGISTERED-STUB only. Full pre-registration is the FIRST job of the next session that picks up implementation. The design baseline is locked at [iter-0033d closure §A-G](iterations/0033d-pair-plan-measurement.md) (18 structural leak surfaces enumerated across Codex R0+R0.5+R0.6, ~17 min Codex wall total). iter-0033f MUST close all 18 OR explicitly accept residuals with documented inference impact. Wall floor ~19h.

2. **iter-0033d CLOSED-DESIGN / NO IMPLEMENT (2026-05-03).** Original PLAN-pair measurement iter closed as design-iter after 3 Codex rounds (AGREE rate 12.5% → 37.5% → 12.5%, non-monotonic = NOT converging). Claude+Codex independent verdict on principles-decision pair = option B (defer-as-design-iter). PRINCIPLES #2 forbids in-place re-pre-registration; iter-0033b → iter-0033b' precedent followed (close original, open fresh impl iter).

3. **Pair-mode policy is round-3 measurement-gated** (NORTH-STAR.md "Pair-mode policy" section). No shipped pair surface at HEAD; solo is current default; pair ships ONLY after pre-registered L1-vs-L2 evidence per phase. Candidate phases: ideate spec audit, ideate PROJECT coherence audit, resolve PLAN audit, resolve VERIFY/JUDGE, CLEANUP residual audit (as VERIFY axis). Deterministic gates (`BUILD_GATE`, `VERIFY-MECHANICAL`, `archive_run.py`) are NOT pair candidates — they are command-output truth.

**Phase 4 cutover blocked on iter-0033f outcome** (was iter-0033d before closure). iter-0033a/iter-0033 C1/iter-0033c all closed (first two PASS, last FAIL); iter-0033d closed-design. iter-0033f ALL ship-blockers PASS → Phase 4 ships PLAN-pair as first product L2 surface; ANY ship-blocker FAIL → Phase 4 ships solo-only + NORTH-STAR records L2 as research-only.

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

# 3. Mirror parity for skills + shared kernel.
diff -q config/skills/devlyn:resolve/SKILL.md .claude/skills/devlyn:resolve/SKILL.md
diff -q config/skills/devlyn:ideate/SKILL.md .claude/skills/devlyn:ideate/SKILL.md
diff -q config/skills/_shared/archive_run.py .claude/skills/_shared/archive_run.py

# 4. Latest active iter file present.
ls autoresearch/iterations/0033d-pair-plan-measurement.md
ls autoresearch/iterations/0033e-project-coherence-stub.md
ls autoresearch/iterations/0033f-pair-plan-impl.md

# 5. iter-0033c CLOSED status + iter-0033d CLOSED-DESIGN status.
grep -q "^status: CLOSED" autoresearch/iterations/0033c-l2-new-vs-new-l1.md && echo "0033c CLOSED ✓"
grep -q "^status: CLOSED-DESIGN" autoresearch/iterations/0033d-pair-plan-measurement.md && echo "0033d CLOSED-DESIGN ✓"
grep -q "^status: PRE-REGISTERED-STUB" autoresearch/iterations/0033f-pair-plan-impl.md && echo "0033f PRE-REGISTERED-STUB ✓"

# 6. NORTH-STAR pair-mode policy is round-3.
grep -q "round-3 redesign" autoresearch/NORTH-STAR.md && echo "NORTH-STAR round-3 ✓"

# 7. SKILL.md PLAN-pair framing fixed (no overreach).
grep -q "PLAN-pair is \*\*unmeasured at HEAD\*\*" config/skills/devlyn:resolve/SKILL.md && echo "SKILL.md round-3 ✓"

# 8. Codex CLI available.
command -v codex && codex --version 2>&1 | head -1
```

If any unexpected output, do NOT proceed. Surface to user.

---

## 🚧 iter queue (post iter-0033d closure 2026-05-03)

Sequence: iter-0033a ✅ → iter-0033b ✅ → iter-0033b' ✅ → iter-0033 (C1) ✅ → iter-0033c ✅ CLOSED FAIL → iter-0033d ✅ CLOSED-DESIGN (Codex 3-round + principles-decision pair → option B) → **iter-0033f ⬅ NEXT** (PRE-REGISTERED-STUB) → iter-0034 Phase 4 cutover (gated on iter-0033f) → iter-0033e (QUEUED-STUB, gated on iter-0033f outcome + defect-class oracle).

### iter-0033f (NEXT — PLAN-pair implementation; STUB)

- **Spec**: [iterations/0033f-pair-plan-impl.md](iterations/0033f-pair-plan-impl.md) — STUB only. Full pre-registration (hypothesis, gates, predictions, wall budget) is the FIRST job of the next session. Cannot reuse iter-0033d hypothesis verbatim — threat model is materially different post-leak-enumeration (PRINCIPLES.md #2).
- **Design baseline (load-bearing)**: [iterations/0033d-pair-plan-measurement.md § "CLOSURE — design-iter, no implementation, hand-off to iter-0033f"](iterations/0033d-pair-plan-measurement.md). All 18 leak surfaces in §A are ship-blockers for iter-0033f.
- **Suite (carry-forward, frozen)**: 6 high-value fixtures {F2, F3, F4, F6, F7, F9}. Arms: `solo_plan` + `pair_plan`. Same HEAD, same env (anon WORK_DIR + RESULT_DIR), same IMPLEMENT engine.
- **Gates**: 8-gate structure carries forward (1a-d smokes + 2/3/4 + 5/6/7 + 8); thresholds restate; Gate 8 expands per closure §A items 12-14 (artifact persistence, archive lifecycle, IMPLEMENT prompt scan).
- **Wall floor**: ~19h (~10-12h impl + 0.5h smokes + 0.25h mirror+lint + 6h suite + 1h R-final/closure + 0.25h commit).
- **Sequencing** (per closure §D step 5):
  1. Pre-registration (hypothesis + gates + predictions + wall — drafted at start of next session, BEFORE any code).
  2. Codex R0 on the implementation plan (against iter-0033d closure as design baseline).
  3. SKILL.md cleanse (PHASE bodies free of pair-mode mention).
  4. Standalone `scripts/validate-plan.py` (deterministic schema + reserved-token script).
  5. Expanded Check 15 in `scripts/lint-skills.sh` (full scan list per closure §A item 11).
  6. `archive_run.py` updates (explicit moves per closure §A items 13-14) + IMPLEMENT-prompt-persistence (§A item 12).
  7. `run-fixture.sh` anon-WORK_DIR refactor (§A items 3-7).
  8. `judge.sh` + `iter-0033f-compare.py` anon-aware (resolve via out-of-tree anon-map.json written post-child-exit).
  9. `run-iter-0033f.sh` orchestrator + smokes 1a-d (mktemp per closure §A item 17). R-smoke if any smoke fails.
  10. Suite (~6h serial). R-final on raw numbers.
  11. Update HANDOFF.md + DECISIONS.md + iter-0033f closure verdict.
  12. iter-0034 Phase 4 cutover (gated on iter-0033f ALL ship-blockers PASS).

### iter-0034 Phase 4 cutover (gated on iter-0033f)

Deletes `/devlyn:auto-resolve` + 14 other old skills. Result depends on iter-0033f:
- iter-0033f ALL ship-blockers PASS → ships PLAN-pair as first product L2 surface.
- iter-0033f any ship-blocker FAIL → ships solo-PLAN only; NORTH-STAR records L2 as research-only.

### iter-0033e (QUEUED-STUB, not pre-registered)

- **Spec**: [iterations/0033e-project-coherence-stub.md](iterations/0033e-project-coherence-stub.md).
- **Candidate**: ideate PROJECT coherence audit (cross-spec defect detection in `plan.md + N child specs`).
- **Blocked on**: (1) defect-class oracle definition with scriptable detectors; (2) iter-0033f outcome (validates pair mechanism — was iter-0033d before closure); (3) ≥3 real PROJECT corpus runs for oracle calibration.

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

### Old skills that will deprecate in Phase 4 (gated on iter-0033d)

`/devlyn:auto-resolve`, `/devlyn:resolve` (old focused-debug; replaced), `/devlyn:implement-ui`, `/devlyn:design-ui`, `/devlyn:team-design-ui`, `/devlyn:design-system`, `/devlyn:clean`, `/devlyn:update-docs`, `/devlyn:preflight`, `/devlyn:evaluate`, `/devlyn:review`, `/devlyn:team-review`, `/devlyn:team-resolve`, `/devlyn:browser-validate` (→ kernel runner), `/devlyn:product-spec`, `/devlyn:feature-spec`, `/devlyn:recommend-features`, `/devlyn:discover-product`.

`/devlyn:reap` and `/design-system` + `/team-design-ui` move to `optional-skills/` in Phase 5.

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

Current status: iter-0033 family fully closed (iter-0033a/C1/b/b' PASS; iter-0033c CLOSED FAIL; iter-0033d CLOSED-DESIGN). iter-0033f-pair-plan-impl PRE-REGISTERED-STUB and is the **sole remaining Phase 4 cutover gate**. Pair-mode policy stays measurement-gated per phase; no shipped pair surface at HEAD; iter-0033d closure §A enumerates 18 structural leak surfaces as the locked design baseline iter-0033f must close.

**Next session can pick up by**:
1. Reading this file → NORTH-STAR.md → PRINCIPLES.md → MISSIONS.md → **`iterations/0033d-pair-plan-measurement.md` § "CLOSURE — design-iter, no implementation, hand-off to iter-0033f"** (load-bearing — 18 leak surfaces enumerated) → `iterations/0033f-pair-plan-impl.md` → recent DECISIONS.md entries.
2. Running cold-start sanity check (~30s).
3. **First job**: draft full pre-registration for iter-0033f (hypothesis + gates + predictions + wall budget) BEFORE any code. Cannot reuse iter-0033d hypothesis verbatim. Cite closure §A items 1-18 in the new gates as ship-blockers.
4. Then Codex R0 on the implementation plan (against iter-0033d closure as design baseline).
5. Then sequence per HANDOFF "iter-0033f Sequencing" steps 3-12.

**Wall floor**: ~19h (~10-12h impl + 6h suite + smokes/lint/closure/commit). The session needs to plan for context-window bridging via state files — the 6h suite is best run via `run_in_background` Bash with HANDOFF state continuity.

Multi-LLM evolution direction (Block 5) binds `/devlyn:resolve` (Claude + Codex today, pi-agent tomorrow) under no-xxx / worldclass / measurement-gated principles.
