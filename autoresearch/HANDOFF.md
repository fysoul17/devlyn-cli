# HANDOFF — for the next session

**Read order on cold start (mandatory)**:
1. **This file** — operating context + active iter + Codex collab protocol
2. [`NORTH-STAR.md`](NORTH-STAR.md) — project goal + 3-layer composition contract + pair-mode policy (round-3 redesign 2026-05-03)
3. [`PRINCIPLES.md`](PRINCIPLES.md) — pre-flight 0 + #1-#7 (every iter cites)
4. [`MISSIONS.md`](MISSIONS.md) — Mission 1 active, hard NO list
5. The active-iter file (currently `iterations/0034-phase-4-cutover.md` — PRE-REGISTERED-STUB; design baselines at iter-0033 (C1) PASS evidence + `iterations/0033g-pair-plan-impl-pmo.md` § "CLOSURE" big-picture pivot)
6. [`DECISIONS.md`](DECISIONS.md) — append-only ship/revert log (most recent entries first to read)

If any file contradicts another, **NORTH-STAR.md wins**, then this file, then PRINCIPLES.md. Open a doc-fix iter on the contradiction.

Last refined 2026-05-03 (post iter-0033g CLOSED-DESIGN — anti-asymptotic hard stop fired exactly as pre-registered; Codex big-picture review found ZERO empirical evidence of subagent introspection in 6mo benchmark logs; Claude+Codex independent verdict converged on option VI: Phase 4 cutover solo + L2 PLAN-pair research-only; iter-0033g closed + iter-0034 Phase 4 cutover PRE-REGISTERED-STUB as next active iter). **Direction**: 솔로도 그대로 잘 동작하고 페어는 더욱 더 잘 동작하게 — L1 stays solid + L2 ships per-phase where empirically lifts.

---

## 🚦 START-HERE — three things active right now

1. **Active iter: `iter-0034` Phase 4 cutover** ([iterations/0034-phase-4-cutover.md](iterations/0034-phase-4-cutover.md)) — PRE-REGISTERED-STUB. Cleanup + product-surface ship: solo PLAN as default (already true at HEAD; mostly deletion work), delete 14+ legacy skills, label L2 PLAN-pair research-only with explicit unblock conditions. Suite re-run pre/post to prove L1 numbers unchanged. **NOT** Mission 1 terminal gate — that's iter-0035 real-project trial (NORTH-STAR test #15). Wall floor ~6-8h. Full pre-reg drafted by next session per PRINCIPLES #2.

2. **iter-0033g CLOSED-DESIGN / NO IMPLEMENT (2026-05-03).** PLAN-pair PMO implementation iter closed as design-iter via anti-asymptotic hard stop firing exactly as pre-registered. Codex R0 found items 25-28 (parent-process argv inspection, /dev/fd/1 derivation, /tmp glob enumeration, detached descendants outside checked PGID). Big-picture review (Codex independent, ~7min, 259k tokens) revealed killer finding: ZERO empirical evidence of subagent introspection in ~6 months of benchmark logs. Claude+Codex independent convergence on option VI: ship Phase 4 cutover with solo + label L2 PLAN-pair research-only. User adjudicated option VI 2026-05-03. Lessons captured in `feedback_explain_simply.md` + `project_iter0033g_asymptotic_firewall_lesson_2026_05_03.md`.

3. **Forward direction: L1 stays solid + L2 ships per-phase where empirically lifts.** User-confirmed 2026-05-03: "솔로도 그대로 잘 동작하고 페어는 더욱 더 잘 동작하게". L2 candidate priority (post Phase 4 cutover, by measurement difficulty + empirical grounding): (1) **VERIFY-pair frozen-diff** (verify-only mode — iter-0033c-fdfd already showed `deliberation_lift`, no leak surface), (2) **PROJECT-pair (ideate)** — iter-0033e queued, needs defect-class oracle, (3) **PLAN-pair** — research-only until container infra justified by other product needs OR empirical introspection observed, (4) **multi-LLM via pi-agent** (Block 5) — Mission 2/3 territory.

**Phase 4 cutover unblocked.** iter-0033 (C1) PASS evidence (5/5 headroom fixtures, suite-avg L1−L0 +6.43) is sufficient for cutover. iter-0033d/iter-0033f/iter-0033g closed-design (PLAN-pair measurement deferred). iter-0033c closed FAIL (VERIFY-pair full-pipeline). Mission 1 terminal gate is iter-0035 real-project trial (NORTH-STAR test #15), NOT Phase 4 cutover.

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

# 4. Latest active iter file present + closed-iters preserved as design archive.
ls autoresearch/iterations/0033d-pair-plan-measurement.md
ls autoresearch/iterations/0033e-project-coherence-stub.md
ls autoresearch/iterations/0033f-pair-plan-impl.md
ls autoresearch/iterations/0033g-pair-plan-impl-pmo.md
ls autoresearch/iterations/0034-phase-4-cutover.md

# 5. iter-0033c CLOSED + iter-0033d/iter-0033f/iter-0033g CLOSED-DESIGN + iter-0034 STUB.
grep -q "^status: CLOSED" autoresearch/iterations/0033c-l2-new-vs-new-l1.md && echo "0033c CLOSED ✓"
grep -q "^status: CLOSED-DESIGN" autoresearch/iterations/0033d-pair-plan-measurement.md && echo "0033d CLOSED-DESIGN ✓"
grep -q "^status: CLOSED-DESIGN" autoresearch/iterations/0033f-pair-plan-impl.md && echo "0033f CLOSED-DESIGN ✓"
grep -q "^status: CLOSED-DESIGN" autoresearch/iterations/0033g-pair-plan-impl-pmo.md && echo "0033g CLOSED-DESIGN ✓"
grep -q "^status: PRE-REGISTERED-STUB" autoresearch/iterations/0034-phase-4-cutover.md && echo "0034 STUB ✓"

# 6. NORTH-STAR pair-mode policy is round-3.
grep -q "round-3 redesign" autoresearch/NORTH-STAR.md && echo "NORTH-STAR round-3 ✓"

# 7. SKILL.md PLAN-pair framing fixed (no overreach).
grep -q "PLAN-pair is \*\*unmeasured at HEAD\*\*" config/skills/devlyn:resolve/SKILL.md && echo "SKILL.md round-3 ✓"

# 8. Codex CLI available.
command -v codex && codex --version 2>&1 | head -1
```

If any unexpected output, do NOT proceed. Surface to user.

---

## 🚧 iter queue (post iter-0033g closure 2026-05-03 + big-picture pivot to option VI)

Sequence: iter-0033a ✅ → iter-0033b ✅ → iter-0033b' ✅ → iter-0033 (C1) ✅ PASS (5/5 headroom fixtures, suite-avg L1−L0 +6.43) → iter-0033c ✅ CLOSED FAIL (VERIFY-pair full-pipeline) → iter-0033d ✅ CLOSED-DESIGN (3-layer firewall insufficient) → iter-0033f ✅ CLOSED-DESIGN (anon paths + sidecar relocation insufficient) → iter-0033g ✅ CLOSED-DESIGN (PMO insufficient — anti-asymptotic hard stop fired exactly as pre-registered; Codex grep found 0 empirical introspection) → **iter-0034 ⬅ NEXT** (PRE-REGISTERED-STUB Phase 4 cutover) → iter-0035 real-project trial (Mission 1 terminal gate per NORTH-STAR test #15) → iter-0036+ L2 candidates by measurement priority.

### iter-0034 (NEXT — Phase 4 cutover STUB)

- **Spec**: [iterations/0034-phase-4-cutover.md](iterations/0034-phase-4-cutover.md) — PRE-REGISTERED-STUB. Full pre-reg drafted by next session per PRINCIPLES #2.
- **Design baseline 1**: iter-0033 (C1) PASS evidence (solo PLAN empirically world-class — 5/5 headroom-available fixtures, suite-avg L1−L0 +6.43).
- **Design baseline 2**: [iterations/0033g-pair-plan-impl-pmo.md § "CLOSURE"](iterations/0033g-pair-plan-impl-pmo.md) — big-picture pivot rationale; full 28-item leak surface enumeration preserved as archive (re-applicable when container infra ships).
- **Scope**: cleanup + product-surface ship. Solo PLAN is already shipped default at HEAD; iter-0034 is mostly DELETION work + doc updates + L2 PLAN-pair research-only label.
- **Suggested gates** (next session refines):
  - Gate 1: solo PLAN behavior unchanged pre/post Phase 4 (smoke F1+F2+F9, scores byte-equal or within ±2)
  - Gate 2: legacy skill deletion complete (lint/grep verifies no references)
  - Gate 3: doc surface updated (SKILL.md PHASE 1 line 80 replaced; NORTH-STAR Phase 4 done; HANDOFF Mission 1 progress)
  - Gate 4: optional-skills/ migration (`/devlyn:reap`, `/devlyn:design-system`, `/devlyn:team-design-ui`)
  - Gate 5: post-cutover bench suite re-run shows L1 numbers within variance band of pre-cutover

#### ▶ Execution sequence (run end-to-end without blocking)

The next session executes this sequence start-to-finish — measurement-included. No mid-sequence pauses for user input unless an anti-asymptotic / forbidden / new-class condition triggers (see "Question handling" below).

**0. Cold-start sanity check (mandatory before any edit)**
   - Read in order: `HANDOFF.md` (this file) → `NORTH-STAR.md` → `PRINCIPLES.md` → `MISSIONS.md` → `CLAUDE.md` → memory file `project_iter0033g_asymptotic_firewall_lesson_2026_05_03.md` (load-bearing — meta-lesson + 6 reusable principles) → `iterations/0033g-pair-plan-impl-pmo.md § "CLOSURE"` (big-picture pivot + L2 candidate priority) → `iterations/0034-phase-4-cutover.md` (active STUB) → recent `DECISIONS.md` entries.
   - Run cold-start sanity check 8 commands (above) — all must PASS. Surface any unexpected output to user before proceeding.

**1. iter-0034 full pre-registration draft**
   - Following `iterations/0034-phase-4-cutover.md` STUB §"Hand-off contract". Cannot recycle iter-0033 (C1) hypothesis verbatim — this is cleanup + ship iter, different threat model from measurement iters.
   - Pre-register: NEW hypothesis (cleanup + ship form), 5 gates finalized (Gate 1-5 per STUB), filled predictions BEFORE run, wall budget breakdown, risk register, principles check (#0-#7).
   - Status frontmatter: `PRE-REGISTERED-STUB` → `PRE-REGISTERED`.

**2. Codex R0 on pre-reg (mandatory pair-collab — see "Codex pair contract" below)**
   - Position: pre-reg + iter-0033 (C1) PASS evidence + iter-0033g closure as combined design baseline.
   - Falsification ask: any deletion that breaks 2-skill design dependency? any doc update that mislabels L2 status? gate threshold under-specified? sequencing risk?
   - Expected verdict: **CONVERGED** (no adversarial threat model — cleanup iter).
   - **NOT CONVERGED — revisions only**: pair-collab another round (R0.5 acceptable here — NOT an adversarial threat-model iter, so in-place revision is principles-aligned per PRINCIPLES #2 case-by-case).
   - **NEW STRUCTURAL CLASS** (very unlikely for cleanup iter): immediately surface to user. Cleanup iter finding new class would mean pre-reg scope itself is wrong.

**3. Documentation updates first (lowest risk, easy revert)**
   - `config/skills/devlyn:resolve/SKILL.md` PHASE 1 line 80: replace "PLAN-pair is **unmeasured at HEAD** — iter-0033d is the first L1-vs-L2 measurement; iter-0020 falsified Codex-BUILD/IMPLEMENT, NOT PLAN-pair" with the L2 PLAN-pair research-only label per `iterations/0034-phase-4-cutover.md` §"L2 PLAN-pair research-only label". Cite explicit unblock conditions A (container infra justified by other product needs) and B (empirical introspection probe).
   - `autoresearch/NORTH-STAR.md`: Phase 4 marked done; pair-mode policy section reflects "L2 PLAN-pair research-only" + L2 candidate priority list.
   - `autoresearch/HANDOFF.md`: Mission 1 progress reflects Phase 4 SHIPPED; iter-0035 real-project trial moves to active position.
   - `autoresearch/MISSIONS.md`: Mission 1 status reflects cutover.
   - `README.md`: 2-skill design (`/devlyn:resolve` + `/devlyn:ideate`); legacy skill mentions removed.
   - `CLAUDE.md`: 2-skill quick-start; legacy skill table removed.
   - Mirror sync (`bin/devlyn.js -y`) + lint (`bash scripts/lint-skills.sh`) — both must PASS.

**4. Skill deletion**
   - Delete from `config/skills/` AND `.claude/skills/` mirror per deletion list in `iterations/0034-phase-4-cutover.md` §"Deletion list". Use `git rm -r` for atomicity.
   - Update `bin/devlyn.js` to remove references to deleted skills.
   - Move `/devlyn:reap`, `/devlyn:design-system`, `/devlyn:team-design-ui` to `optional-skills/` (Phase 5 planned migration; do NOT delete).
   - Mirror sync + lint again — both must PASS.

**5. Gate 1 smoke (solo behavior unchanged)**
   - F1, F2, F9 single-fixture runs at post-cleanup HEAD.
   - Compare scores vs iter-0033 (C1) baseline (run-id `3bc86dd`+iter-0033b carrier fix, see DECISIONS 0033 (C1) entry).
   - PASS criterion: per-axis ±2 (variance band per iter-0027 N=5 evidence).
   - **FAIL** → identify regression source (which doc edit / which deletion?), revert smallest unit, re-smoke. Pair with Codex on root cause if not obvious.

**6. Gate 5 suite re-run (background, full bench)**
   - Use `run_in_background: true` Bash. Suite is long; do NOT block on it.
   - 9-fixture bench (F1-F9) serial at post-cleanup HEAD.
   - While suite runs in background: draft iter-0034 closure section structure, draft iter-0035 STUB skeleton, prep R-final prompt for Codex.
   - Use HANDOFF state continuity for context-window bridging — write progress notes to disk every major milestone.

**7. Compare + R-final (Codex pair-collab on raw numbers)**
   - `iter-0033c-compare.py` (or new `iter-0034-compare.py` if needed) on pre/post baselines.
   - Per-fixture variance band check (±2 axes).
   - Codex R-final: position with raw numbers + falsification ask "any regression hidden by aggregation? any L2 label inaccurate post-cutover?".
   - **ALL Gate 1-5 PASS** → proceed to closure.
   - **ANY Gate FAIL** → identify regression source, revert smallest unit, re-smoke. Surface to user only if revert+re-smoke loop fails 2x (anti-asymptotic at smaller scale).

**8. iter-0034 closure**
   - frontmatter status → `CLOSED-PASS / SHIPPED`.
   - CLOSURE section: 5 gate results with raw numbers, principles check (#0-#7), what shipped, what's preserved as archive, hand-off to iter-0035.
   - Update `HANDOFF.md`: iter-0034 SHIPPED, iter-0035 NEXT, Mission 1 progress, START-HERE refresh.
   - Update `DECISIONS.md`: append iter-0034 SHIPPED entry.

**9. iter-0035 STUB draft + commit**
   - NEW `iterations/0035-real-project-trial.md` STUB per NORTH-STAR test #15. Hand-off contract: what user input is needed (project choice, feature/bug spec, success criteria), what next session does, what's blocked.
   - Lint pass.
   - Commit per repo conventions. iter-0035 real-project trial unblocked.

#### 🤝 Codex pair contract (mandatory for steps 2, 7 — recommended for any non-trivial edit)

Per `feedback_codex_collaboration_not_consult.md` + `feedback_codex_cross_check.md` (memory):

- **Codex CLI GPT-5.5 is your collaboration partner, not consultant.** Multi-round dialogue until convergence; not single-shot Q&A.
- **Reason independently first.** Form your own verdict with concrete evidence (file paths, line numbers, expected vs observed) BEFORE asking Codex.
- **Send rich evidence + falsification ask.** Not "what should I do?" — instead "I conclude X because file:line evidence; falsify if you disagree".
- **Wrapper invocation** (per CLAUDE.md):
  ```bash
  bash config/skills/_shared/codex-monitored.sh \
    -C /Users/aipalm/Documents/GitHub/devlyn-cli \
    -s read-only \
    -c model_reasoning_effort=xhigh \
    "<position + evidence + falsification ask>"
  ```
  Output to file: `... > /tmp/codex-iter0034-<round>/response.log 2>&1`. NEVER pipe wrapper output (`| tail`, `| grep`); wrapper refuses (iter-0009 contract).
- **Codex reads codebase directly.** Use `-s read-only` so Codex can `Read`/`Grep`/`Glob` independently — don't pre-package context.
- **Verify before claim.** Every cited file:line opened at citation time on YOUR side too — Codex's citations may be stale.
- **Convergence is the stop, not "Codex agreed".** If Codex pushes back, surface both views to user; user is final arbiter.
- **Required Codex rounds for iter-0034**: R0 (step 2), R-final (step 7). Add R-smoke if Gate 1 fails or Gate 5 produces unexpected pattern.

#### ⛔ Hard constraints (binding throughout iter-0034)

**Principles (PRINCIPLES.md #0-#7) — verify EVERY step against these. NO EXCEPTIONS.**

The 7 principles are not optional. The user-verbatim directive (Block 1, Block 4, repeated multiple times):
> "지금 하고있는 것들이 북극성의 목표를 향해서 no xxxx, worldclass xxx 5대 원칙들을 바탕으로 계속 개선을 해나가고 있는게 맞지? 그냥 오로지 점수를 위해서 하는게 아니고 말이야?"

Every step asks:
1. **#1 No overengineering / Subtractive-first** — am I deleting more than adding? Pure-addition needs cited prior failure mode OR explicit user spec. Defaults to deletion.
2. **#2 No guesswork** — falsifiable hypothesis pre-registered BEFORE run; predicted directions filled BEFORE run; raw data filled AFTER (no retroactive prediction edits).
3. **#3 No workaround** — root-cause fixes; no `any`, no `@ts-ignore`, no silent catch, no hardcoded fallbacks. Codex CLI downgrade is the ONLY documented exception.
4. **#4 Worldclass production-ready** — zero CRITICAL, zero HIGH `design.*`/`security.*` findings on shipped surfaces.
5. **#5 Best practice** — idiomatic for language/framework; no hand-rolled helpers replacing standard primitives.
6. **#6 Layer-cost-justified** — every change beats previous-layer-best-of-N on quality AND wall-time. iter-0034 is L1 surface ship; layer-cost evaluated on cleanup-vs-leave (cleanup wins by deletion).
7. **#7 Mission-bound** — Mission 1 single-task scope; Mission 1 hard NO list (no parallel-fleet, no resource-lease helper, no cross-vendor infra).

**Pre-flight #0**: every iter must close a real user-visible failure OR ship a real product surface. iter-0034 closes both (cleanup + 2-skill ship surface).

**User direction Block 5 (multi-LLM evolution)**: preserved as future direction; pi-agent adapter is Mission 2/3 territory; do NOT bake single-LLM assumptions in iter-0034 doc updates. NORTH-STAR's `expected.schema.json` + `_shared/adapters/<model>.md` already hold the contract.

**User direction Block 6 (페어가 PLAN에서 가장 중요)**: preserved as L2 candidate priority. Block 6 says PLAN is the most important PHASE for pair-mode IF pair-mode ships. iter-0034 ships solo + L2 PLAN-pair research-only; this honors Block 6 by NOT pretending to ship unproven L2 (which would be opposite of "최고의 결과").

**User direction (2026-05-03)**: "솔로도 그대로 잘 동작하고 페어는 더욱 더 잘 동작하게" — L1 stays solid + L2 ships per-phase where empirically lifts. Gate 1 + Gate 5 mechanically enforce "솔로 그대로". L2 candidate priority list in iter-0033g closure §H + iter-0034 STUB §"L2 PLAN-pair research-only label" enforces "페어 더 좋게 (per-phase, measurement-gated)".

**Anti-asymptotic guard (iter-0033d/f/g lesson)**: cleanup iter is NOT expected to find adversarial new structural classes. If R0 / R-smoke / R-final returns NEW STRUCTURAL CLASS (very unlikely on cleanup), that signals pre-reg scope itself is wrong — surface to user immediately, do NOT in-place revise.

#### 💬 Question handling (no-blocking discipline)

If you encounter a non-trivial question mid-execution:

1. **Try to answer with code + memory + Codex pair first.** Most questions have file:line evidence answers. Read the code, search memory, ask Codex with rich evidence.
2. **If genuinely ambiguous**: pair with Codex multi-round to converge on best-practice answer. Per `feedback_codex_collaboration_not_consult.md` — multi-round dialogue is the contract.
3. **If still ambiguous after pair-collab**: surface to user with (a) the question, (b) the options Codex+Claude considered, (c) the recommended option with rationale, (d) what's blocked. Don't surface the question alone — surface a position the user can confirm/redirect.
4. **Never surface trivial questions.** "Should I use git rm or rm -r?" — answer yourself (use git rm for tracked files). User adjudication is for genuinely ambiguous strategic decisions, not implementation details.
5. **Hands-free pipeline rule applies** (CLAUDE.md): inside automated execution, log assumptions explicitly in iter file / commit message rather than blocking for confirmation. User reviews after iter completes.

#### 📋 Definition of "done" for this session

iter-0034 is done when:
- All 5 gates PASS with raw evidence cited.
- iter-0034 closure committed.
- iter-0035 STUB committed with hand-off contract for real-project trial.
- HANDOFF refreshed: iter-0035 is new active iter; iter-0034 SHIPPED.
- DECISIONS appended.
- Memory updated only if NEW lesson surfaced (not for routine cleanup completion).
- L1 solo behavior verified unchanged (Gate 1 + Gate 5 raw numbers).
- 2-skill design surface clean (Gate 2 + 3 + 4 verified).
- All actions trace back to a principle (#0-#7) + cite file:line evidence.

If session is interrupted before "done": leave HANDOFF reflecting actual state with explicit "in progress at step N" marker. Do NOT leave half-finished implementations without a state file the next session can resume from.

### iter-0035 (TBD post-cutover — real-project trial, Mission 1 terminal gate)

- **NORTH-STAR test #15**: developer who has not tuned the harness picks a real (not fixture) feature/bug from a real (not test) codebase, runs `/devlyn:resolve "<spec or goal>"` end-to-end, and the output ships without human prompt-engineering rescue.
- **Pass criteria**: (a) no human edits to skill prompts mid-run, (b) no manual phase re-runs, (c) the produced code passes the project's existing test suite + the developer's spec acceptance check, (d) wall-time within budget for the layer the user paid for.
- **Blocked on**: iter-0034 Phase 4 cutover SHIP.
- **NOT pre-registered yet** — will be when iter-0034 ships.

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

Current status: iter-0033 family fully closed (iter-0033a/C1/b/b' PASS; iter-0033c CLOSED FAIL; iter-0033d/iter-0033f/iter-0033g CLOSED-DESIGN). **Big-picture pivot 2026-05-03**: 3 design-iters chasing PLAN-pair leak firewall hit asymptotic pattern; Codex grep across 6mo benchmark logs found ZERO empirical evidence of subagent introspection; Claude+Codex independent verdict converged on option VI: ship Phase 4 cutover with solo + label L2 PLAN-pair research-only. iter-0034 Phase 4 cutover PRE-REGISTERED-STUB and is **next active iter** — Phase 4 cutover unblocked because iter-0033 (C1) PASS evidence is sufficient. Mission 1 terminal gate is iter-0035 real-project trial (NORTH-STAR test #15), NOT Phase 4 cutover.

**Direction (user-confirmed 2026-05-03)**: 솔로도 그대로 잘 동작하고 페어는 더욱 더 잘 동작하게 — L1 stays solid + L2 ships per-phase where empirically lifts. L2 candidate priority: VERIFY-pair frozen-diff > PROJECT-pair > PLAN-pair (research-only) > multi-LLM via pi-agent (Mission 2/3).

**Next session entry point**: see "▶ Execution sequence (run end-to-end without blocking)" subsection inside iter-0034 entry above. Self-contained; covers cold-start → pre-reg → Codex R0 → impl → smokes → suite (background) → R-final → closure → iter-0035 STUB → commit. No mid-sequence pauses unless an anti-asymptotic / forbidden / new-class condition triggers. Codex CLI GPT-5.5 pair-collab is mandatory for steps 2 (R0) and 7 (R-final).

**Forbidden under this branch** (per iter-0033g closure §G + memory lesson `project_iter0033g_asymptotic_firewall_lesson_2026_05_03.md`):
- Do NOT open iter-0033h with another firewall architecture attempt. If user later wants to revisit PLAN-pair, the unblock conditions are documented in iter-0034 STUB §"L2 PLAN-pair research-only label" + iter-0033g closure §H.
- Do NOT delete iter-0033c-compare.py / build-pair-eligible-manifest.py / iter-0033f-* / iter-0033g-* assets — they preserve closed-iter replay + design archive; CLAUDE.md goal-lock forbids tangential cleanup.
- Do NOT degrade L1 solo behavior in Phase 4 cutover — Gate 1 + Gate 5 catch this; user direction is "솔로 그대로 + 페어 더 좋게".
- Do NOT skip Codex pair-collab steps. Reasoning independently first + Codex multi-round dialogue is the contract per memory `feedback_codex_collaboration_not_consult.md`.
- Do NOT surface trivial questions to user mid-pipeline. Pair with Codex first; surface only genuinely strategic ambiguity with options + recommendation. Hands-free pipeline rule (CLAUDE.md).
- Do NOT bypass any of PRINCIPLES.md #0-#7. Every action traces back to a principle. The user reminder (Block 1, repeated): "no xxxx 원칙들 잊지말고".

Multi-LLM evolution direction (Block 5) binds `/devlyn:resolve` (Claude + Codex today, pi-agent tomorrow) under no-xxx / worldclass / measurement-gated principles.
