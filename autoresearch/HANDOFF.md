# HANDOFF — for the next session

**Read [`NORTH-STAR.md`](NORTH-STAR.md) first** (project goal + locked 2-skill product surface). **This file second** (operating context). **[`PRINCIPLES.md`](PRINCIPLES.md) before any iter file edit.** **[`MISSIONS.md`](MISSIONS.md)** confirms Mission 1 active.

Last refined 2026-04-30 (post 2-skill redesign Phases 1-3 SHIPPED — `/devlyn:ideate` + `/devlyn:resolve` + kernel + adapters all live on `main`. Phases 4-5 pending. shadow-suite v0 phase A only.)

---

## 🚦 START-HERE — five things active right now

1. **Branch is `main`.** The `benchmark/v3.6-ab-20260423-191315` branch was fast-forward merged into main (90 commits) and deleted both locally and on GitHub. Safety tag `pre-merge-2026-04-30` at commit `1129db6` if rollback ever needed. HEAD: `1024a7f` (iter-0032 SHA bake).

2. **2-skill redesign Phases 1-3 SHIPPED.**
   - **Phase 1** (iter-0029, commit `7ecc0e6`): kernel + adapter contract. `_shared/expected.schema.json`, `_shared/spec-verify-check.py` (moved from auto-resolve), `_shared/adapters/{README, opus-4-7, gpt-5-5}.md`.
   - **Phase 2** (iter-0031, commit `4d0e04a`): greenfield `/devlyn:resolve`. SKILL.md (175 lines) + 5 phase prompts + 2 references. PLAN → IMPLEMENT → BUILD_GATE → CLEANUP → VERIFY (fresh subagent, findings-only). 3 modes: free-form / `--spec` / `--verify-only`.
   - **Phase 3** (iter-0032, commit `6a8d798`): greenfield `/devlyn:ideate`. SKILL.md (137 lines) + 4 references. 4 modes: default / `--quick` / `--from-spec` / `--project`. `spec.kind` escape hatch.

3. **Phases 4-5 pending.** Phase 4 (cutover + deprecation of old `/devlyn:auto-resolve` + 14 other old skills) is gated by a Quality A/B that has not run yet. Phase 5 (move `/design-system`, `/team-design-ui`, `/devlyn:reap` to `optional-skills/`) follows Phase 4.

4. **shadow-suite v0 phase A only.** iter-0030 phase A (commit `a240558`) shipped infra + S1 task + `--suite shadow` flag + `lint-shadow-fixtures.sh`. Phase B (S2-S6, 5 more tasks × 6 files = 30 files) deferred.

5. **Active iter focus** (2026-05-02 — iter-0033 (C1) CLOSED, Codex R3+R4 pair-collab convergence; iter-0033c is next):
   - ✅ **iter-0033a SHIPPED 2026-04-30** — F9 fixture redesigned for 2-skill contract. F9 NEW L1 91 vs L0 76, **margin +15**. Commit chain `0b317a4` → `4e3d89a` → `75e08c3` (bake).
   - ✅ **iter-0033b SHIPPED 2026-05-02** — TAP carrier fix (`# fail 0` false positive on 6 fixtures: F1/F3/F5/F6/F7/F8). F3 NEW fabrication eliminated under fixed carrier. NEW resolve archive bug fixed (commit `3bc86dd`, port to `_shared/archive_run.py`). Carrier fix commits: `2638891` + `7669696` (bake).
   - ✅ **iter-0033b' SHIPPED 2026-05-02** — F6 N=3 paired variance per Codex R3 Path B pre-registered rule. n=2 + n=3 both clean → silent-catch in n=1 = single-shot tail variance. iter-0033 (C1) F6 marked **"PASS via variance adjudication"**. Commit `5378c89` + this commit's bake. See [`iterations/0033b-prime-f6-n3-paired-variance.md`](iterations/0033b-prime-f6-n3-paired-variance.md) verdict block.
   - ✅ **iter-0033 (C1) CLOSED — PASS via variance adjudication + headroom-adjusted L1 gate**. Codex R4 (2026-05-02, 139s) converged on D1: NORTH-STAR + RUBRIC + ship-gate.py headroom amendment formalizes saturation carve-out. Headroom-available count: **5/5 (F1, F2, F4, F5, F9)** ≥+5 PASS. F3/F6/F7 excluded (saturated/marginal — bare ceiling-near). Phase 4 still requires iter-0033c PASS.
   - **iter-0033c (next active focus) = NEW L2 vs NEW L1** — pre-registered with R0+R0.5+R0.6 collab. Sequenced: iter-0033b/'b' done → iter-0033c run → Phase 4 cutover. See [`iterations/0033c-l2-new-vs-new-l1.md`](iterations/0033c-l2-new-vs-new-l1.md).
   - **iter-0034 = Phase 4 cutover** — gated on iter-0033c PASS (iter-0033 (C1) + iter-0033a both closed).
   - **iter-0030 phase B** (S2-S6 shadow tasks) — independent, unblocked.
   - **Post-Phase-4 follow-up queue**: F3/F6/F7 fixture-rotation (RUBRIC two-shipped-version rule), VERIFY MECHANICAL test-diff silent-catch scan (deferred until N≥2 evidence).

Everything below this fold supports those five.

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

### Old skills that will deprecate in Phase 4

Currently present on `main` but slated for removal once Quality A/B confirms new pair wins:

`/devlyn:auto-resolve` `/devlyn:resolve` (the old focused-debug; replaced this iter — but old SKILL.md content gone, file replaced) `/devlyn:implement-ui` `/devlyn:design-ui` `/devlyn:team-design-ui` `/devlyn:design-system` `/devlyn:clean` `/devlyn:update-docs` `/devlyn:preflight` `/devlyn:evaluate` `/devlyn:review` `/devlyn:team-review` `/devlyn:team-resolve` `/devlyn:browser-validate` (→ kernel runner) `/devlyn:product-spec` `/devlyn:feature-spec` `/devlyn:recommend-features` `/devlyn:discover-product`.

`/devlyn:reap` and `/design-system` + `/team-design-ui` move to `optional-skills/` in Phase 5 (creative or maintenance, non-hot-path).

---

## ⛔ Hard operating rules

### Rule 1 — Pair-review IS the work

Every non-trivial claim must be Codex-verified at the time of writing. Don't trust paraphrases; open the cited file:line. R-final BEFORE commit when results surprise you. Recent rounds caught (a) stale-HANDOFF fabrication risk, (b) wrong unit-of-minimization in 3-skill model, (c) F2 oracle-artifact-vs-real-defect.

### Rule 2 — Cost framing is BANNED

Memory `feedback_no_cost_talk.md` (HARD). Never use "paid run", "model invocation cost", "spendy", "$X-Y", or any cost-coded equivalent. Effectiveness × accuracy × reasonable wall-time are the axes.

### Rule 3 — Verify before claim

Every cited file:line opened at citation time. iter-0028 R-final-2 generalization: stale HANDOFF references caused fabrication risk in iter-0028 R0 — verify, don't paraphrase from prior context.

### Rule 4 — Explain simply (Korean, decision-maker view)

Plain Korean. Lead with conclusion + options + recommendation. Drop internal labels (iter numbers OK in artifacts; P1-P7 / α-ε / etc. NOT in user-facing summaries). Define technical terms inline.

### Rule 5 — Greenfield interface, NOT mechanisms

Codex R1 (session `019dde5c`) closing line. The 2-skill redesign deletes skill surface area while preserving `build-gate.py` mechanisms, `spec-verify-check.py`, state discipline, one-spec-at-a-time pattern. Any redesign edit must justify why a learned mechanism is being changed (not just relocated).

---

## 🧠 What we now know empirically (TL;DR)

### Mission 1 single-task signal (post iter-0028 N=3 valid run)

| arm | F2 score (N=3 mean) | F2 DQ rate | wall ratio over bare |
|---|---|---|---|
| bare (raw Claude) | 81.3 | 0/3 | 1.0× |
| L1 (solo harness) | 92.3 | 0/3 | ~6× |
| L2 (Claude + Codex pair) | 96.0 | 0/3 | ~10× |

L1 - bare = +11.0; L2 - bare = +14.7. After F2 regex narrow-fix (iter-0028 R-final): both L1 and L2 = 0 DQ on F2 (categorical reliability passes).

### What the iter-0027/0028 cycle taught

- F2 silent-catch DQ "60%" was an oracle artifact (broad regex over-matched legitimate `return { level, message }` structured errors). 38/38 narrow-regex sweep = 0 real silent catches.
- The mechanism (B-minus, 281 LOC + carrier resilience 76 LOC) was solving a non-problem. Reverted; only the regex fix kept.
- Lesson hard-coded into NORTH-STAR test #10: **measurement validity ≥ mechanism cleverness**.

### Multi-LLM evolution direction (binding for `/devlyn:resolve`)

Per NORTH-STAR.md and memory `project_2_skill_harness_redesign_2026_04_30.md`:
- Today: Claude (Opus 4.x) + Codex (GPT-5.5).
- Tomorrow: pi-agent abstraction enables Qwen / Gemini / Gemma / future frontier swap-in.
- Pair-mode location: VERIFY/JUDGE only per current iter-0020 evidence (empirically gated, not architecturally frozen).
- Schema (`_shared/expected.schema.json`) + adapters (`_shared/adapters/<model>.md`) are load-bearing decouplers.
- All multi-LLM additions bind no-overengineering / no-guesswork / no-workaround / worldclass / best-practice principles.

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

→ Multi-LLM evolution direction binding. Pair-mode in VERIFY/JUDGE today (empirically gated); pi-agent future swap-in via adapter system. no-xxx / worldclass principles bind multi-LLM coordination layer.

> 근데 ideate가 없어도 단독으로도 동작해야하잖아?

→ Confirmed: `/devlyn:resolve` standalone-capable via free-form mode + `--spec` mode (handwritten specs from any source). `/devlyn:ideate` is OPTIONAL.

### Memory directives (auto-loaded; cite, do not duplicate)

Critical for next session at `~/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/memory/`:

- `project_2_skill_harness_redesign_2026_04_30.md` — full redesign decision record + multi-LLM evolution clause.
- `feedback_no_cost_talk.md` — HARD rule: no cost framing.
- `feedback_l2_pair_collaboration.md` — L2 = pair 협업 (not 분업).
- `feedback_pair_vs_solo_empirical.md` — pair fires per-phase ONLY where measurement shows lift.
- `feedback_codex_collaboration_not_consult.md` — Codex is partner; multi-round dialogue.
- `feedback_explain_simply.md` — plain Korean + concise + decision-maker-framed.
- `feedback_codex_cross_check.md` — reason independently first; send Codex evidence + falsification ask.

**Conflict rule**: if HANDOFF and a memory file disagree, stop before editing and ask the user.

---

## 📍 Branch + project state (verify before editing)

- **Branch**: `main` (origin/main).
- **HEAD**: see `git log -1` — most recent ship is iter-0033 (C1) close-out + headroom amendment commit (2026-05-02). Previous: `5378c89` (iter-0033b' pre-registration), `7669696` (iter-0033b bake), `2638891` (iter-0033b carrier fix), `3bc86dd` (NEW resolve archive port to `_shared/`), `75e08c3` (iter-0033a bake), `4e3d89a` (F9 NEW prompt --quick fix), `0b317a4` (iter-0033a fixture redesign).
- **Iter-0033 family closure**: iter-0033a + iter-0033b + iter-0033b' + iter-0033 (C1) all CLOSED. iter-0033c is next.
- **Headroom amendment ACTIVE** (NORTH-STAR.md, RUBRIC.md, ship-gate.py). Saturation carve-out: F3, F6, F7 excluded from L1 ≥+5 count this cycle; rotation candidates if next shipped version also saturates.
- **Mission 1 active** ([`MISSIONS.md`](MISSIONS.md)). Hard NOs binding.
- **Safety tag**: `pre-merge-2026-04-30` at `1129db6`.

### Cold-start sanity check (run before any edit; ~30s)

```bash
# 1. On main, no detached HEAD.
git status

# 2. Lint passes (Check 14 added in iter-0033a).
bash scripts/lint-skills.sh   # expect "All checks passed."

# 3. Mirror parity for new skills + shared kernel.
diff -q config/skills/devlyn:resolve/SKILL.md .claude/skills/devlyn:resolve/SKILL.md
diff -q config/skills/devlyn:ideate/SKILL.md .claude/skills/devlyn:ideate/SKILL.md
diff -q config/skills/_shared/archive_run.py .claude/skills/_shared/archive_run.py

# 4. Latest iter files present.
ls autoresearch/iterations/0033b-prime-f6-n3-paired-variance.md
ls autoresearch/iterations/0033c-l2-new-vs-new-l1.md

# 5. Headroom amendment in place (added 2026-05-02 per iter-0033 R4).
grep -q "Headroom amendment" autoresearch/NORTH-STAR.md && echo "NORTH-STAR amendment ✓"
grep -q "headroom-aware" benchmark/auto-resolve/RUBRIC.md && echo "RUBRIC amendment ✓"
grep -q "headroom-available" benchmark/auto-resolve/scripts/ship-gate.py && echo "ship-gate.py amendment ✓"

# 6. F9 renamed fixture in place (iter-0033a).
test -d benchmark/auto-resolve/fixtures/F9-e2e-ideate-to-resolve && echo "F9 NEW dir ✓"
test -d benchmark/auto-resolve/fixtures/retired/F9-e2e-ideate-to-preflight && echo "F9 OLD retired ✓"

# 7. Old auto-resolve still in place (Phase 4 will deprecate; not yet).
test -f config/skills/devlyn:auto-resolve/SKILL.md && echo "old auto-resolve present (expected pre-Phase-4)"

# 8. Shadow suite present.
test -d benchmark/auto-resolve/shadow-fixtures/S1-cli-lang-flag && echo "shadow S1 present"
```

If any unexpected output, do NOT proceed. Surface to user.

---

## 🚧 iter queue (post iter-0033 (C1) close-out, 2026-05-02)

Sequence: iter-0033a ✅ → iter-0033b ✅ → iter-0033b' ✅ → iter-0033 (C1) ✅ → **iter-0033c ⬅ NEXT** → iter-0034 Phase 4 cutover.

- **iter-0033c (NEXT) = NEW L2 vs NEW L1**. Pre-registered design at [`iterations/0033c-l2-new-vs-new-l1.md`](iterations/0033c-l2-new-vs-new-l1.md). Codex R0+R0.5+R0.6 sign-off. 8 gates: L2 mode wiring smoke (1a), Codex availability harness check (1b), impl-confound smoke (1c), no-regression vs L1 (Gate 2), pair-eligible lift (Gate 3 ship-blocker, single threshold ≥+5 on ≥50% of frozen pair-eligible set), hard-floor zero (Gate 4), efficiency (Gate 5), trigger-policy fixture-level (Gate 6), 4-class attribution (Gate 7), artifact contract (Gate 8). Frozen pair-eligible high-value list: F2/F3/F4/F6/F7 + F9 (F1/F5 conditional on L1≤L0; F8 reporting-only). Manifest checksum sequencing: pair-eligible selection rule already pre-committed in iter-0033c file; manifest produced post-iter-0033 (C1) `summary.json` is consumed by iter-0033c. Harness change required: explicit `l2_gated` + `l2_forced` arms in `run-fixture.sh` with `CODEX_BLOCKED=0`, `--engine claude --pair-verify` for forced; engine config: NEW L2 IMPLEMENT=Claude (same as L1) + pair-JUDGE=Codex via "OTHER engine" rule.
- **iter-0034 = Phase 4 cutover** (gated by iter-0033c PASS). New `/devlyn:resolve` becomes the default; old `/devlyn:auto-resolve` deprecated → one cycle redirect → delete. Same for the 14 other old skills slated for removal.
- **iter-0035 = Phase 5 optional plugin separation**. Move `/design-system`, `/team-design-ui`, `/devlyn:reap` to `optional-skills/`. README update.
- **iter-0030 phase B (deferred but unblocked)**. S2-S6 shadow tasks (5 fixtures × 6 files). Independent of Phase 4 sequencing.
- **iter-0036+ post-Phase-4 follow-up queue**:
  - F3/F6/F7 fixture-rotation (RUBRIC two-shipped-version saturation rule; iter-0033 (C1) was first cycle).
  - VERIFY MECHANICAL test-diff silent-catch scan (Codex R3 §3 architectural gap; deferred until N≥2 evidence outside F3 fabrication N=1).
  - ship-gate.py reframe (+5 floor → categorical reliability gate).
  - NORTH-STAR ops test #15 real-project trial (Mission 1 terminal gate).
  - L2 design-space update if iter-0033c attribution shows tool-lift dominance.

---

## 📖 Open question — extracting each model's max capability per official guides

**Binding references** (re-read at the start of any iter that touches prompt content or adapters):

- Anthropic Opus 4.7 prompt-engineering best practices: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices>
- OpenAI GPT-5.5 prompt guidance: <https://developers.openai.com/api/docs/guides/prompt-guidance?model=gpt-5.5>

iter-0029 shipped initial adapter files at `_shared/adapters/{opus-4-7, gpt-5-5}.md` — small per-engine deltas reflecting each guide's distinct guidance (Opus 4.7: literal interpretation, self-check pattern, less imperatives; GPT-5.5: outcome-first, decision rules over absolutes, validation tools over self-belief). These adapters are prepended to canonical phase prompts at runtime.

Ongoing question (deferred to iter-0036 or later): does measured A/B show the adapter system materially changes per-engine performance vs canonical-only? If yes, expand adapter content. If no, simplify.

**Standing rule**: any iter that touches an adapter file or canonical phase prompt MUST cite both official guides as part of acceptance. "I think this is better" is not a justification; "guide section X.Y says Z" is.

---

## 📋 Mission 1 hard NO list

- ❌ No worktree-per-task substrate (Mission 2).
- ❌ No parallel-fleet smoke / N≥2 simultaneous runs.
- ❌ No resource-lease helper / SQLite leases / port pools / queue metrics.
- ❌ No cross-vendor / qwen / gemma infrastructure (until adapter shipped + measured).
- ❌ No restart of iter-0020 e2e routing.
- ❌ No "while I'm here" cross-mission additions.

---

## 📚 Read-order on cold start

1. [`NORTH-STAR.md`](NORTH-STAR.md) — project goal + locked product surface (2-skill redesign).
2. **This file** — operating context. `START-HERE` + standing user directives + iter-0033 queue are load-bearing.
3. [`PRINCIPLES.md`](PRINCIPLES.md) — pre-flight 0 + #1-#7.
4. [`MISSIONS.md`](MISSIONS.md) — confirms Mission 1 active.
5. Memory: `project_2_skill_harness_redesign_2026_04_30.md` — full redesign + multi-LLM clause.
6. [`CLAUDE.md`](../CLAUDE.md) — runtime contract.
7. `autoresearch/DECISIONS.md` — append-only ship/revert log.
8. Most recent iter files: `0032-ideate-greenfield-phase3.md`, `0031-resolve-greenfield-phase2.md`, `0029-kernel-and-adapter-contract.md`.

---

## 🤝 Codex pair-review pattern (mandatory for non-trivial work)

Per `feedback_codex_collaboration_not_consult.md`:

- **Multi-round, not one-shot.** R0 (design) + R1 (diff review) + R-final (post-test interpretation when surprised).
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

Current status: 2-skill redesign Phases 1-3 SHIPPED **skill bodies** + **iter-0033a / iter-0033b / iter-0033b' / iter-0033 (C1) all CLOSED** as of 2026-05-02. Phase 4 cutover gated on **single remaining iter**: **iter-0033c (NEW L2 vs NEW L1)**. Pre-registered design + R0+R0.5+R0.6 collab complete; harness change for L2 arms + Codex availability smoke + impl-confound smoke + frozen pair-eligible manifest are the next unit of work. Mission 1 active. Single-task L1 quality already gate-passing under headroom amendment; L2 first-class measurement is the last validation before deprecating `/devlyn:auto-resolve`. Multi-LLM evolution direction binds `/devlyn:resolve` (Claude+Codex today, pi-agent tomorrow) — under no-xxx / worldclass principles.
