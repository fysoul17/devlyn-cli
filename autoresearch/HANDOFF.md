# HANDOFF — for the next session

**Read [`NORTH-STAR.md`](NORTH-STAR.md) first** (project goal). **This file second** (operating context). **[`PRINCIPLES.md`](PRINCIPLES.md) before any iter file edit** (pre-flight 0 + #1-#7). **[`MISSIONS.md`](MISSIONS.md)** confirms which mission is active.

Last refined 2026-04-30 (post iter-0022 → iter-0027 batch ship; user pivot from "+5 floor reliability" → "categorical-reliability silent-catch in BUILD" surfaced empirically).

---

## 🚦 START-HERE — three things only

1. **iter-0028 has not started.** Code state ends at iter-0027 (commit `4feae35`, baked at `f4a7e29`). The next session opens iter-0028 from scratch after the cold-start sanity check below.

2. **iter-0028 = silent-catch detection in BUILD before EVAL.** F2 N=5 paired variance (iter-0027) showed L1 silent-catch DQ rate **2/5 (40%)** structurally — same engine, same prompt, same git baseline produced silent-catch (`catch-return fallback` / `catch returning an object`) in 2 out of 5 fresh runs. Mean L1-L0 = +13.25 when clean (well above +5 floor) — the failure mode is NOT margin, it's the recurring silent-catch DQ. Fix the prompt/CRITIC to detect silent-catch in BUILD output BEFORE EVAL gates it. Three candidate approaches in "iter-0028 execution plan" below — Codex R0 picks one.

3. **Cross-fixture variance (F3 N=3, F9 N=3) BLOCKED until iter-0028 ships.** Codex iter-0027 R-final pivot rule: ≥2/5 DQ on F2 → stop broad fixture expansion → run iter-0028 categorical reliability first. After iter-0028 ships AND F2 N=3 re-run shows 0/3 DQ, then F3 N=3 + F9 N=3 follow as iter-0029.

Everything below this fold supports those three.

---

## 🧠 What we now know empirically (TL;DR for the next session)

### The real signal: L1 already beats bare on categorical reliability

User correction 2026-04-30 reframed the entire game. **Score margin is a proxy; the real question is "does the harness produce better code than bare?"** Re-read iter-0026/0027 raw DQ data with that lens:

| arm | F2 silent-catch DQ rate (6 runs) | Same, n5 invalid excluded (5 runs) |
|---|---|---|
| **bare (raw Claude, no harness)** | 5 / 6 (83%) | 5 / 5 (**100%**) |
| **L1 (our solo harness)** | 3 / 6 (50%) | 3 / 5 (**60%**) |
| L2 (Claude + Codex pair) | 2 / 6 (33%) | 2 / 5 (40%) |

**Bare produces silent-catch nearly every time** on F2 (a fixture whose spec explicitly forbids silent catches). The harness already cuts that failure rate by ~40 percentage points. **Our system is empirically better than bare on the only signal that actually matters** (real categorical correctness on a real spec constraint), even though the cumulative judge score margin (+4.4 suite-avg) hides it.

### What the score-margin journey was actually tracking
- Single-shot suite-avg L1-L0 = +4.4 (iter-0020, iter-0025 cross-judge confirmed +4.44 vs +4.67).
- F2 N=4 effective (clean + DQ blend): L1 mean **94.5** / stdev **2.89**, L1-L0 mean **+13.25** / stdev **3.50**.
- Per-fixture variance ±3-15 (DQ-dependent) dominates the +5 floor signal — the floor logic was reading proxy noise.
- `completed:` removal mechanism confirmed N=5 wide (F2 scope stdev 0.00) — minor lift, not the load-bearing fix.

### The honest framing the next session must adopt
**"+5 floor" is a proxy of a proxy.** The real Mission 1 gate is: *does the harness reliably produce better code than bare on real tasks?* iter-0027 already shows yes on F2 categorical reliability (L1 60% DQ vs bare 100%). What's missing isn't more decimal places on suite-avg — it's:
1. **Cross-fixture confirmation**: does L1-vs-bare DQ rate gap hold on F3/F6/F7/F9? (iter-0029)
2. **Real-project trial**: NORTH-STAR ops test #14 — pick a real codebase, real task, run `/devlyn:auto-resolve` end-to-end, have a human compare to bare. (iter-0030 or later, but this is the binding terminal gate.)
3. **Drive L1 silent-catch rate down further** (60% → ~0%) so the bare-vs-L1 gap isn't just "less broken" but "actually clean". (iter-0028)

iter-0028's design stays useful (silent-catch detection in BUILD) but its acceptance gate must reframe: **"L1 DQ rate < bare DQ rate by ≥30 percentage points, AND L1 absolute DQ rate ≤ 1/3"** — categorical-vs-bare, not absolute floor.

---

## ⛔ Hard operating rules

### Rule 1 — Pair-review IS the work (iter-0021 lesson, repeatedly validated through iter-0027)

Every non-trivial claim must be Codex-verified at the time of writing. Don't trust paraphrases; open the cited file:line. iter-0026 R-final caught me framing the variance result too softly ("attributed to BUILD variance") when the honest framing was "consistent with BUILD variance but not yet attributed." iter-0027 R-final caught the over-read of N=3 mean +12.7 as a clean lift. Pattern: **R-final BEFORE commit when results surprise you.**

### Rule 2 — Cost framing is BANNED

User memory `feedback_no_cost_talk.md` (HARD rule, reinforced 2026-04-29 late evening). Never use "paid run", "model invocation cost", "GO before paid step", "spendy", "$X-Y", or any cost-coded equivalent. User is on subscription. Effectiveness × accuracy × reasonable wall-time are the axes; cost is not. CLAUDE.md "Executing actions with care" must NOT be translated into "warn before more expensive operations" for this user.

### Rule 3 — Verify before claim

Every cited file:line opened at citation time. iter-0021 R-final fabrication-rescue lesson generalizes to every iter since.

### Rule 4 — Explain simply (Korean, decision-maker view)

User repeatedly pushed back on jargon-loaded explanations. Per `feedback_explain_simply.md`: lead with conclusion + options + recommendation; drop internal labels (iter numbers OK, but P1-P7 / α-ε / Q1-Q5 / B-1 etc. NOT in user-facing summaries). Plain Korean. If using a technical term (e.g. silent-catch, DQ, L1), define it in one sentence inline before using.

---

## 🧭 STANDING USER DIRECTIVES

Block 1 is **strictly user-verbatim** (the 2026-04-28 directive logged on every HANDOFF.md commit). Blocks 2-4 contain **binding operational excerpts** from each rapid-fire 2026-04-29 / 2026-04-30 directive. Originals had connecting words and minor typos that have been edited out for compactness; the live conversation transcript is authoritative if anything is disputed.

Never re-summarize Block 1. If context auto-compacts, FIRST action on resume is re-load this whole section.

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

### Block 3 (2026-04-29 architecture compromise, user-adjudicated)

User picked option 1 of "BUILD pure execution vs BUILD constrained judgment" trade-off. Codex framing is canonical (NOT user-verbatim):

> PLAN은 non-negotiable invariants + acceptance contract을 만든다. BUILD는 그 안에서 *constrained design judgment*를 수행한다. EVAL/CRITIC은 BUILD의 judgment를 대체하지 않는 독립 품질 레이어다.

PLAN remains the heaviest phase per Block 2, but BUILD is not pure execution — it has constrained judgment latitude that EVAL/CRITIC must independently audit.

### Block 4 (2026-04-29 late evening through 2026-04-30 — engineer-quality + bare-case correction + cost-framing HARD rule + variance pushback + plain explanation)

> 기존 bare case가 틀린거라면 그걸 수정해야해. 북극성을 보자고. 유저가 하나부터 끝까지 다 하는게 목적이 아니야. 유저는 계획하고 실행하면 나머지는 처음부터 끝까지 완벽하게 클린업과 문서화, 기술부채 제거 등을 완벽하게 다 해야해. 소프트웨어 엔지니어링을 생각해보자고.

→ Adopted in iter-0024 (CLAUDE.md `Bare-Case Guardrail` rewritten: engineer-quality is North-Star promise; broad cleanup stays in standalones; cost discipline = bare-best-of-N, NOT zero-regression-on-bare). EVAL hygiene severity made task-aware (MEDIUM blocking when introduced by this diff; LOW pre-existing).

> 비용이고 뭐고 그냥 신경쓰지말라고 몇번얘기해.

→ Memory rule `feedback_no_cost_talk.md` upgraded to HARD rule. Includes disguised cost framing: "model invocation step", "GO before paid step", "this step makes calls" all banned. Subscription means no spendy/non-spendy distinction at the decision layer.

> 점수가 신뢰가 있나? +5 라는게 의미가 정말 있나? 4.5나 5.2나 크게 차이가 없을수도 있을것 같은데?

→ User was correct. iter-0023 fixed measurement bugs; iter-0025 cross-judged with Opus 4.7; iter-0027 N=5 paired variance confirmed per-fixture variance ±3-15 dominates the +5 floor signal; **DQ rate (not margin) is the real Mission 1 quality gate**.

> 미션1이 팀으로 가는거고 이건 미래에 하는거고, 일단은 혼자서 단일로 하는 케이스도 충분히 만들어져야 한다고 했잖아. 그건 왜 뛰어넘지?

→ Single-task L1 must clear Mission 1 gate before ANY team / multi-agent work. iter-0026 → iter-0027 → iter-0028 chain is squarely on this path. Team / multi-agent stays as Mission 2/3 destination per Codex δ/ε/β verdict (NOT immediate work).

> 좀 쉽게 설명해줄래?? / 무슨얘기인지 쉽게 설명하고 / 아니 좀 쉽게 설명하라니까

→ Plain-Korean explanation rule = HARD. Define every technical term inline. Lead with one-line conclusion. No jargon walls. iter-0028's user-facing summaries must follow.

### Memory directives (auto-loaded; cite, do not duplicate)

Memory files at `~/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/memory/`. Critical for next session:

- `feedback_no_cost_talk.md` — HARD rule: never use cost framing, including disguised forms.
- `feedback_l2_pair_collaboration.md` — L2 = pair 협업 (not 분업).
- `feedback_pair_vs_solo_empirical.md` — pair fires per-phase ONLY where measurement shows lift over solo.
- `feedback_codex_collaboration_not_consult.md` — Codex is partner not advisor; multi-round dialogue.
- `feedback_explain_simply.md` — every user-facing surface = plain Korean + concise + decision-maker-framed.
- `feedback_codex_cross_check.md` — reason independently first; send Codex evidence + falsification ask.

**Conflict rule**: if HANDOFF and a memory file disagree, stop before editing and ask the user.

---

## 📍 Branch + project state (verify before editing)

- **Branch**: `benchmark/v3.6-ab-20260423-191315`
- **Recent ship trail**: `f4a7e29` (iter-0027 SHA bake) → `4feae35` (iter-0027 ship) → `b06fffd` (iter-0026 SHA bake) → `60c8a38` (iter-0026 ship) → `b5a2a60` (iter-0025 SHA bake) → `6f0e693` (iter-0025 ship) → `fd58abf` (iter-0024 SHA bake) → `349818f` (iter-0024 ship) → `109ca7d` (iter-0023 SHA bake) → `356f056` (iter-0023 ship) → `5f9020e` (iter-0022 SHA bake) → `8fcc509` (iter-0022 ship).
- **Mission 1 active** ([`MISSIONS.md`](MISSIONS.md)). Hard NOs binding.
- **iter-0020** = FAILED-EXPERIMENT-REVERTED-POLICY (commit `948e4bd`). e2e BUILD=Claude routing deleted. Auto-resolve runtime default = `--engine claude`.
- **iter-0021** = SHIPPED (calibration overlay). Per-axis L1-L0 readout: spec +7 / cons +18 / scope -4 / qual +19 (single-shot, suite avg +4.4).
- **iter-0022** = SHIPPED. PLAN-pair infrastructure (5 deliverables: schema doc + idgen + lint + preflight + auto-resolve `--plan-path`). Real provider/model invocations: 0.
- **iter-0023** = SHIPPED. Measurement trust: judge.sh axis [0,25] clamp + ship-gate.py L1 (`solo_over_bare`) enforcement.
- **iter-0024** = SHIPPED. Bare-Case Guardrail correction. EVAL hygiene severity task-aware.
- **iter-0025** = SHIPPED. Opus 4.7 sidecar cross-judge: GPT vs Opus suite avg L1-L0 +4.44 vs +4.67. Quality magnitude single-judge artifact (`-4` disagreement).
- **iter-0026** = SHIPPED-MECHANISM. F2 single-shot after `completed:` removal: scope 23→25 ✓; L1 total 94→81 (tail event).
- **iter-0027** = DATA. F2 N=5 paired variance: L1 mean 94.5 / stdev 2.89 (n=4 effective); L1 DQ rate 2/5 (40%). Codex pivot threshold reached → iter-0028 categorical-reliability work.

### Cold-start sanity check (run before any edit; ~30s)

```bash
# 1. Branch tip in expected range (top entry on this branch should be the
#    iter-0027 SHA bake `f4a7e29` or an iter-0028 commit added by the next session).
git log --oneline -10

# 2. Working tree clean (`.claude/scheduled_tasks.lock` is gitignored runtime).
git status --short

# 3. Lint full pass (Check 13 = idgen determinism, added in iter-0022).
bash scripts/lint-skills.sh
# Expected: "All checks passed."

# 4. Mirror parity (critical-path docs unchanged between source and installed).
diff -q config/skills/_shared/runtime-principles.md .claude/skills/_shared/runtime-principles.md
diff -q config/skills/_shared/pair-plan-schema.md   .claude/skills/_shared/pair-plan-schema.md
# Expected: silent.

# 5. iter-0027 file exists (most recent shipped iter file).
ls autoresearch/iterations/0027-f2-paired-variance-n5.md
# Expected: file present.

# 6. iter-0028 deliverables NOT on disk yet (start-from-scratch confirmation).
test ! -e config/skills/devlyn:auto-resolve/scripts/forbidden-pattern-check.py && \
echo "iter-0028 not started — proceed"
# Expected: prints "iter-0028 not started — proceed". (Filename is candidate
# B; if Codex R0 picks A or C the file may have a different name.)

# 7. Auto-resolve runtime default still `--engine claude`.
grep -E '^[[:space:]]+- `--engine MODE`' config/skills/devlyn:auto-resolve/SKILL.md
# Expected: line includes `(claude)` not `(auto)`.
```

If any unexpected output, do NOT proceed. Surface to user.

---

## 🛠️ iter-0028 execution plan — silent-catch detection in BUILD before EVAL

### Why this iter exists (PRINCIPLES.md pre-flight 0 + Codex iter-0027 R-final pivot)

iter-0027 N=5 measured L1 silent-catch DQ rate **2/5 (40%)** on F2 alone — at the same git baseline `b06fffd`, same engine (Claude solo), same prompt. Different runs hit different silent-catch sites:
- n2: `Forbidden disqualifier-severity catch-return fallback` (the `catch (e) { return null }` pattern)
- n4: `Forbidden-pattern hit for catch returning an object` (the `catch (e) { return {} }` variant)

This is NOT noise. It's a structural BUILD failure mode that the current pipeline catches only at EVAL after BUILD has already shipped DQ-grade code. iter-0024 introduced task-aware MEDIUM hygiene severity. iter-0028 extends the principle: **silent-catch / forbidden-pattern detection moves into BUILD-phase verification, not just post-hoc EVAL gating**.

**Decision this iter unlocks**: whether structural silent-catch DQ rate drops to 0/3 (or close) when BUILD is required to self-check for forbidden-pattern matches before declaring its phase complete. If yes → expand cross-fixture (F3 N=3 + F9 N=3) and Mission 1 gate decision becomes unambiguous. If no → silent-catch is a model-level failure mode that needs different surface.

### Mission 1 service

Serves Mission 1 gate 1 (L1 vs L0 quality) directly. The user's "단일 먼저, 그 다음 팀" sequencing is honored: this is single-task work. Mission 1 hard NOs untouched.

### Three deliverable candidates (Codex R0 picks one)

The next session's first iter-0028 R0 task is to pick between these. Listing them so the next session has the candidate set without re-deriving:

**Candidate A — BUILD prompt self-check**
Add a final sanity-check step to `references/phases/phase-1-build.md`: before declaring BUILD complete, BUILD agent must `grep -nE '<forbidden_pattern_regex>' <changed_files>` and either fix any hits or surface them in the build summary. Cheapest implementation; relies on prompt compliance (LLM following instructions). Risk: same model that produces silent-catch may also miss its own self-check.

**Candidate B — Mechanical BUILD-GATE forbidden-pattern check (recommended)**
Extend `spec-verify-check.py` (or add `forbidden-pattern-check.py`) to scan changed files for `expected.json:forbidden_patterns` regex matches and emit CRITICAL `correctness.silent-catch-introduced` finding when any match. Integrate into BUILD_GATE phase (which already wires the fix-loop). Mechanical, deterministic, model-agnostic. Highest reliability. ~50-100 LOC script. Pattern matches iter-0019.6 (`spec-verify-check.py`) which mechanized verification commands successfully.

**Candidate C — Pre-EVAL CRITIC pass**
Re-route CRITIC's design sub-pass to fire BEFORE EVAL (currently after, in PHASE 3). Requires re-thinking post-EVAL invariant (CRITIC currently is findings-only post-EVAL). Most architectural; highest risk of disturbing other invariants.

**Recommendation (will be Codex R0 input, NOT committed yet)**: Candidate B — mechanical check is principle-#3 root-cause (forbidden patterns are mechanically detectable; relying on LLM self-check for them is a workaround). Same architectural pattern as iter-0019.6.

### iter-0028 acceptance gate (pre-registered before R0; reframed per user 2026-04-30 "categorical-vs-bare > absolute floor")

After whichever candidate ships:
- **F2 N=3 paired re-run** at iter-0028 commit. Acceptance:
  - **L1 silent-catch DQ rate ≤ 1/3** (absolute; targets bringing 60% down to ≤33%).
  - **L1 DQ rate < bare DQ rate by ≥ 30 percentage points** (categorical-vs-bare; the real signal per user direction).
- L1-L0 mean lift on F2 stays ≥ +10 (clean-run regime preserved). Suite-avg "+5 floor" is reporting only, not decisive.
- Lint Check 13 still PASSES post-mirror.
- No regression on iter-0020 baseline F1/F4/F6/F7 single-fixture spot-check.

If acceptance passes → iter-0029 = F3 N=3 + F9 N=3 cross-fixture variance (test bare-vs-L1 gap on more spec types).
If acceptance fails → iter-0028 close-out with revert; pivot to Candidate C (pre-EVAL CRITIC) in iter-0029.

### iter-0028 hard NO list

- ❌ NO change to `judge-prompt.txt` or judge rubric (RUBRIC.md:3 freeze still binding).
- ❌ NO new fixture.
- ❌ NO multi-agent coordination beyond pipeline.state.json.
- ❌ NO ideate/preflight/team-* default change.
- ❌ NO Mission 2 surface touch (worktree, parallel, lease, queue).
- ❌ NO "while I'm here" cleanup of unrelated code paths.

---

## 🚧 iter-0029+ deferred queue (reordered per user 2026-04-30 reframing)

- **iter-0029**: F3 N=3 + F9 N=3 paired variance — measure **bare-vs-L1 DQ rate gap on more spec types**, not just absolute floor. BLOCKED until iter-0028 acceptance passes.
- **iter-0030 (priority shift up — was 0031)**: **NORTH-STAR ops test #14 — real-project trial**. Pick a real (non-fixture) codebase, real feature/bug, run `/devlyn:auto-resolve` end-to-end, have a human read both bare and L1 outputs and rate which is ship-worthier. THIS is the binding Mission 1 terminal gate per user 2026-04-30 directive ("실제로 bare보다 더 나은 코드"). Fixture suite is calibrated proxy; real-project trial is ground truth.
- **iter-0031 (candidate)**: ship-gate.py language change (Codex iter-0027 R-final Q3) — reframe gate from "+5 absolute floor" to "L1 DQ rate < bare DQ rate by ≥30pp AND L1-L0 mean lift ≥ +5 on clean runs". Small doc + script change. Can land in parallel with iter-0029 since it's pure documentation/gate-text.
- **iter-0032+ (candidate)**: drive L1 silent-catch rate to <10% (post iter-0028 measurement-driven prompt/CRITIC iteration).

---

## 📋 Mission 1 hard NO list (binding for iter-0028+)

- ❌ No worktree-per-task substrate (Mission 2).
- ❌ No parallel-fleet smoke / N≥2 simultaneous runs.
- ❌ No resource-lease helper / SQLite leases / port pools / queue metrics.
- ❌ No run-scoped state migration (`.devlyn/pipeline.state.json` stays at worktree root).
- ❌ No multi-agent coordination beyond what `pipeline.state.json` already provides.
- ❌ No cross-vendor / qwen / gemma infrastructure.
- ❌ No restart of iter-0020 e2e routing.
- ❌ No edit to ideate / preflight / team-* `--engine auto` defaults without skill-specific benchmark evidence.
- ❌ No aggregate-margin chasing.
- ❌ No "while I'm here" cross-mission additions.

---

## 📚 Read-order on cold start

1. [`NORTH-STAR.md`](NORTH-STAR.md) — project goal (L0/L1/L2 contract, 14 ops tests, real-project trial gate).
2. **This file** — operating context. `START-HERE` block + `STANDING USER DIRECTIVES` + `iter-0028 execution plan` are load-bearing for the next session.
3. [`PRINCIPLES.md`](PRINCIPLES.md) — pre-flight 0 + #1-#7. Cite each in iter-0028's iter file.
4. [`MISSIONS.md`](MISSIONS.md) — confirms Mission 1 active, hard NOs binding.
5. [`CLAUDE.md`](../CLAUDE.md) — runtime contract. `Bare-Case Guardrail` was rewritten in iter-0024 (engineer-quality is North-Star promise; cost discipline = bare-best-of-N).
6. `autoresearch/DECISIONS.md` — append-only ship/revert log. Latest entries: 0022 → 0027.
7. [`autoresearch/iterations/0027-f2-paired-variance-n5.md`](iterations/0027-f2-paired-variance-n5.md) — most recent iter file. The DQ rate 2/5 finding is the load-bearing input for iter-0028.
8. [`autoresearch/iterations/0026-completed-removal-scope-axis-probe.md`](iterations/0026-completed-removal-scope-axis-probe.md) — single-shot tail event that surfaced the variance question.
9. [`autoresearch/iterations/0025-opus-sidecar-cross-judge.md`](iterations/0025-opus-sidecar-cross-judge.md) — cross-judge data (Quality axis magnitude single-judge artifact; suite avg robust).
10. `config/skills/_shared/runtime-principles.md` — runtime contract sub-agents consume.
11. Memory directives (auto-loaded; cited above).

---

## 🤝 Codex pair-review pattern for iter-0028 (mandatory)

Per `feedback_codex_collaboration_not_consult.md`:

- **Multi-round, not one-shot.** Plan for R0 (design / candidate selection) + R1 (diff review) + R-final (post-test interpretation, especially when results surprise you).
- **Position-stating, not verdict-asking.** State position with evidence; Codex pushes back; iterate.
- **Convergence is the stop.** Not "Codex agreed."
- **Per-round prompt shape**: rich evidence + falsification ask + my response to prior round. Use:
  ```bash
  bash config/skills/_shared/codex-monitored.sh \
    -C /Users/aipalm/Documents/GitHub/devlyn-cli \
    -s read-only \
    -c model_reasoning_effort=xhigh \
    "<prompt>"
  ```
  Never pipe wrapper output (`| tail`, `| grep` etc); wrapper refuses pipe-stdout.
- **Verify before claim.** Every cited file:line opened at citation time.

---

## ⏭️ End of HANDOFF

Current iter focus: **iter-0028 (silent-catch detection in BUILD before EVAL)**. iter-0029 (F3 + F9 cross-fixture variance) BLOCKED until iter-0028 acceptance clears. Mission 1 active. Single-task L1 quality is the binding gate; team / multi-agent work stays deferred until single-task gates clear.
