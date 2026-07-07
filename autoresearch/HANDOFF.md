# HANDOFF — for the next session

**Read order on cold start (mandatory)**:
1. **This file** — operating context + active iter + pair-collab protocol
2. [`NORTH-STAR.md`](NORTH-STAR.md) — goal + floor contract (L0/L1/L2, ops tests 1-16) + **ceiling contract + ops test #17** (2026-07-06 amendment) + pair-mode policy
3. [`PRINCIPLES.md`](PRINCIPLES.md) — pre-flight 0 + #1-#7 (every iter cites)
4. [`MISSIONS.md`](MISSIONS.md) — Mission 1 active + ceiling addendum + roadmap to endgame + hard NO list
5. Latest closed iter: [`iterations/0064-ceiling-seat-instrument.md`](iterations/0064-ceiling-seat-instrument.md) (CLOSED 2026-07-07; iter-0065 levers A/B not yet opened)
6. [`DECISIONS.md`](DECISIONS.md) — append-only ship/revert log (newest at bottom)

If any file contradicts another, **NORTH-STAR.md wins**, then this file, then PRINCIPLES.md. Open a doc-fix iter on the contradiction. Historical narratives live in `iterations/*` + DECISIONS.md + NORTH-STAR § Pair-mode policy — this file carries only what binds the next session (user cleanup directive 2026-07-07).

Last rewritten 2026-07-07 (pollution cleanup per user directive; prior full history recoverable from git).

---

## 🚦 START-HERE — state after 2026-07-07 (late)

1. **iter-0064 — ceiling & seat-fitness instrument family v0 — CLOSED / SHIPPED 2026-07-07** (freeze commit `0bb4ef7` + closure commit; full record `iterations/0064-ceiling-seat-instrument.md`). Both products live and live-verified: 3-arm blind ceiling harness (`benchmark/ceiling/`) + seat matrix & fail-closed recert runner (`benchmark/seats/`) + codex judge route. **Tranche-1 ceiling verdict: FAIL-pilot** — pre-registered LC3 fired (mean wall_A/wall_B_first 4.32 > 3.0) even though quality went devlyn's way (LC1 lift A 2/3 vs bare-best 1/3; objective moat over copycat A 2 > C 1). 세계최고 axis honest label: instrument LIVE, pilot LOST on efficiency. Standing lenses reconfirmed: fake-binary self-tests cannot catch real-CLI contract gaps (8 live-caught defects: skip-git-repo-check, bash-3.2 mapfile, BSD find, diff-vs-frozen-base after the arm committed, uv-venv-no-pip, str/Path, participation≠certification, recert-attestation regress).
2. **Product findings the pilot licenses (repro archived under `benchmark/ceiling/results/iter0064-t1/`)**: (a) hands-free break — `/devlyn:resolve` free-form on a spec-shaped feature goal returned `BLOCKED:large-needs-ideation` as an interactive question → 0-byte delivery while bare AND copycat codex shipped 14/14 (FS1); (b) pair-VERIFY wall — SW2 arm burned to the 3600s cap inside VERIFY after implement/build_gate/cleanup all PASSed; (c) blind rank axes preferred failing-copycat diffs over objectively-resolving devlyn diffs 8/8 — objective-first adjudication is load-bearing, never let style axes decide.

**Next session entry points (recommended order)**:
1. **iter-0065 lever A — hands-free spec-shaped free-form goals** (FS1 repro): in hands-free contexts the complexity gate must assume-and-log / synthesize the spec, never ask. Needs own pre-registration; probe = FS1-class task through free-form resolve.
2. **iter-0065 lever B — bounded pair-VERIFY wall**: pair audit must not consume the delivery window after primary+mechanical verification passed (SW2/SW1 walls are the repro). Can pair with A or run separately.
3. **Ceiling tranche 2** (after A/B ship): more rows + the user-supplied real-project task (still user-gated), codex-judge schema-first prompt fix + judge packet-size/timeout fix first (0064 follow-ups #3).
4. **Codex drift-bait lane** (iter-0062 follow-up) — now also feeds the codex orchestrator seat, whose only current cell is a hung/aborted FAIL (single observation — needs the 2nd before conclusions).
5. E2 re-measurement; finish-gate skip-rate watch; `.git/info/exclude` for `.devlyn/` — unchanged from previous rotation.

Runner ("Mission 1.5") still NOT next — re-enters on skip-rate evidence. Doc nit pending: SKILL.md:110 "PLAN-pair unmeasured at HEAD" vs NORTH-STAR "research-only after 0033d/f/g" — reconcile in the next skill-touching iter (lever A/B likely IS that iter).

**Mission 2 (parallel-fleet substrate)**: BLOCKED until Mission 1 gates + real-project trial (#15). iter-0035 real-project trial stays user-gated (needs real project + task + developer). Hard NO list in MISSIONS.md binding.

---

## ⛔ Hard operating rules (binding)

1. **Pair-review IS the work** — every non-trivial claim pair-verified at write time; open cited file:line yourself; R-final before commit when results surprise.
2. **Cost framing is BANNED** (memory `feedback_no_cost_talk.md`, HARD). Axes: effectiveness × accuracy × reasonable wall-time.
3. **Verify before claim** — every cited file:line opened at citation time; stale references caused fabrication risk in past iters.
4. **Explain simply** (Korean, decision-maker view) — conclusion + options + recommendation; no internal label walls in user-facing summaries.
5. **Greenfield interface, NOT mechanisms** — any redesign edit must justify why a learned mechanism changes (not just relocates).
6. **Measurement-gated pair policy** — pair ships per-phase only on pre-registered L1-vs-L2 evidence; "no evidence pair needed" ≠ "evidence solo wins"; honest label is "unmeasured".

---

## 🤝 Pair-collab protocol (mandatory for non-trivial work; direction-symmetric)

Per `feedback_codex_collaboration_not_consult.md`; round-shape v2 (2026-07-04). The pair partner is the strongest available OTHER engine — when Codex orchestrates, the partner is Claude (iter-0060 proved reverse invocation works).

- **Round budget: R0 adversarial + R1 reconciliation.** R0 returns, per contested position: strongest counter, strongest form of MY position, synthesis with a NAMED decisive criterion (refute-only rejected). R1 reconciles on the actual diff/raw results. **Further rounds require NEW evidence** (fresh measurement, unopened file) — anti-asymptotic rule (iter-0033g).
- **Position-stating, not verdict-asking.** Convergence is the stop, not "partner agreed" — partner reads the codebase directly and forms independent verdicts.
- **Per-round prompt shape** (all four, every round): (1) source packet — exact file:lines; (2) supersession map; (3) decisive criterion stated BEFORE arguments; (4) the falsifier each side accepts. Codex invocation:
  ```bash
  bash config/skills/_shared/codex-monitored.sh \
    -C /Users/aipalm/Documents/GitHub/devlyn-cli \
    -s read-only \
    -c model_reasoning_effort=xhigh \
    "<prompt>"
  ```
  Output to file (`> /tmp/codex-<topic>/response.log 2>&1`); never pipe wrapper stdout (iter-0009 contract). `-s workspace-write` for delegated implementation; implementation is delegated to Codex CLI per `feedback_implementation_to_codex_2026_07_05`.
- **Adapter/prompt iters** must cite the official vendor prompt guides (Anthropic + OpenAI) as acceptance — "guide section X.Y says Z", not "I think this is better".

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

→ Confirmed: `/devlyn:resolve` standalone-capable via free-form mode + `--spec` mode. `/devlyn:ideate` is OPTIONAL.

### Block 6 (2026-05-03 — round-3 pair-redesign)

> 단순 사용자가 평소대로 resolve 만 하면 다 솔로가 아니라, **최대한의 성능과 효율을 내는 페어 모드여야해**. (풀 파이프라인이라고 하는 정의가 달라져야겠지? 거부된 풀 파이프라인이 아니라 --verify-only 가 풀 파이프라인이 된다던가, 우리의 결정에 따라서. **필요없는 옵션들은 클린업**)

> **계획과 설계가 모든 파이프라인중에 가장 중요해.** 그래서 이부분은 여러 LLM들이 (지금은 둘이지만, 나중에는 늘어날수있음) **페어로 논의하고 최종적으로 최상의 결론이 날때까지 라운드를 이어 나가는게 맞지 않아?** 첫 단추가 잘못 끼이면 뒤에 아무리 둘이서 논의하고 북치고 장구쳐도 안된단말이지. 우리 원칙들을 잘 지키면서 **context pollution, context 부족 등 이슈가 없이** 매우 명확하고 클린하게 spec을 작성하는것이 이후에 Resolve 할때 오류를 최소화 할 수 있는것이지.

> 잠시. **deterministic은 정확하게 무슨뜻이고**, cleanup, verify judge 를 비롯해서 **특히! ideate가 solo 가 더 낫다는 증거가 있나?** 특히 ideate은 **똑같이 plan 을 넘어 설계 단계일텐데, 이거야 말로 가장 중요한 스탭이고 이거야말로 여러 LLM이 유저와 면밀하게 검토해서 가장 정확한 방향의 북극성을 만드는 역할을 할텐데** (특히 프로덕트 전체 그림을 보고 일관되게 그림을 그리는 용도) 이걸 solo로 하는게 더 나은게 맞는거야?

> 새로운 context window 에서 진행할수 있도록 명확하게 모든 context를 pollution 없이 원칙들과 함께 HANDOFF를 클린업하고 재작성해줘. 처음부터 끝까지 멈추지 않고 진행될수 있도록. codex cli gpt 5.5 로 페어로 협의해서 최고의 결과를 얻을수 있도록. **codex에게 context만 제공하는게 아니라 직접 코드베이스를 읽어서 스스로 결정할수 있도록.**

### Block 7 (2026-07-06/07 — ceiling mandate + asymmetric harness + endgame + operating priority)

> 일단 얼추 맞는데 가장 중요한건, 엔지니어 품질이 아니라, 세계최고 수준의 대체불가능한 품질의 소프트웨어여야해. 그리고 효율, 성능, 정확도도 전세계 그 누구도 감히 따라할수 없는 천장을 뚫는 압도적인 수준이어야 하고. 그걸 염두에 두고, 지금 가는 방향이 맞는지, 형태 (skill)이 맞는지부터 해서 너의 모든 능력을 총 동원해서 분석하고 해당 목표까지 갈수 있는 방향으로 설계해봐.

> 이게 맞는지 모르겠지만, 결국 에이전트들이 각자 잘하는것을 힘을 합해서 각 에이전트의 잠재력과 성능 품질을 최고로 끌어올리는 하네스여야 한다는거야. 그래서 내가 생각했을때는 최소한의 하네스에 최대 자율이었는데, 그게 틀리면 개선해주고, 올바른 방향으로 align 되도록 해줘

> 그래서 하이브리드를 구상했던거고 에이전트 군단으로 만들어서 하네스 + 루프 엔지니어링으로 나는 최소한의 의도와 목표, 북극성만 주면 끝까지 에이전트들이 협력을 해서 완벽하게 완수하는것을 생각하고있어. 그게 궁극적인 엔드게임이야

> (2026-07-07) 1) codex 의 의견중에 너가 깊이 생각하고 너도 동의하는것만 채택하고 나머지는 너의 생각대로 설계 계획해줘. 2) … 모델의 버전이 바뀔때, 정확하게 어떤 모델이 어떤 포지션에서 가장 강한가를 측정할수 있는 것도 있어야 그 자리를 체크해서 가장 적합한 모델로 사용할수 있을 것 같아.

> (2026-07-07) 일단은 최대한 너가 해줘야해. 천장을 뚫고 세계최고 수준의 Loop Egnineering/Harness Engineering 이 되려면. 최대한 너에게 맡길거야. 너가 없어도 돌아가는건 차선이야.

> (2026-07-07) 압도적이고 독보적이어야해

> (2026-07-07) 핸드오프든 뭐든 앞으로 참조하는 문서들에 방해가 되는 context들은 다 클린업해줘

→ Shipped: NORTH-STAR ceiling contract + ops test #17 + moat=survives-copycat (`eda7e7f`); MISSIONS ceiling addendum + endgame roadmap; iter-0064 STUB; CLAUDE.md/AGENTS.md § Evolution loop; this HANDOFF rewrite (`e58e65c`+). **Operating priority**: strongest available orchestrator (Fable while available) drives the loop directly at maximum depth; orchestrator-neutral continuation is insurance (차선). Harness philosophy ASYMMETRIC: max determinism in the skeleton (code), max autonomy in the intelligence. Codex R0 archive: `/tmp/codex-northstar2/r0-response.log`.

### Memory directives (auto-loaded; cite, do not duplicate)

At `~/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/memory/`: `feedback_no_cost_talk.md` (HARD), `feedback_l2_pair_collaboration.md`, `feedback_pair_vs_solo_empirical.md`, `feedback_codex_collaboration_not_consult.md`, `feedback_explain_simply.md`, `feedback_implementation_to_codex_2026_07_05.md`, `feedback_test_engine_tiering_2026_07_04.md` (probe/test arms codex/sonnet/opus, never fable), `feedback_executor_codex_always_pair_verify.md`, `feedback_worldclass_ceiling_mandate_2026_07_06.md`.

**Conflict rule**: if HANDOFF and a memory file disagree, stop before editing and ask the user.

---

## 🧠 Empirical TL;DR (what is measured, one screen)

| Surface | Verdict | Evidence anchor |
|---|---|---|
| Codex BUILD/IMPLEMENT routing | **FALSIFIED** | iter-0020: L2−L1 = −3.6 on 9-fixture suite |
| Pair VERIFY on frozen diffs | **PASS** | frozen-verify-gate internal F12/F10 + SWE-bench Lite n11 (avg wall 1.87x, cap 3x) |
| Full-pipeline pair via risk probes | **PASS (small suite)** | F16/F23/F25 bare<solo<pair aggregate (avg wall 1.73x) — NOT broad product superiority |
| PLAN-pair | research-only | iter-0033d/f/g (no empirical subagent introspection; unblock conditions in SKILL.md PHASE 1) |
| Golden fixture suite as evolution signal | RETIRED | solo-saturates 88-99 (`benchmark/probes/README.md`) |
| Contract violations under temptation | live instrument | violation-rate matrix N=4: opus 12/24, sonnet 9/24 at baseline; E1 sentence flipped sonnet B4 4/4→1/4 (iter-0062); prose ceiling → mechanical gates (iter-0046 BUILD_GATE scope, iter-0063 finish-gate) |
| Codex ordinary-invocation pipeline | AGENTS.md IS the binding entry | iter-0061 A/B 4/4-vs-4/4 |
| Engine-symmetric pair invocation | REAL both directions | iter-0060 (codex→claude judge fired via adapter) |
| gemma3:4b as judge | MODEL CEILING — do not re-prompt | iter-0055/0056 |
| Ceiling quality (세계최고 axis) | **MEASURED-pilot: FAIL-pilot on efficiency** (LC3 4.32 > 3.0); quality lift + objective moat present (A 2/3 vs B 1/3 vs C 1/3, n=3) | iter-0064 `benchmark/ceiling/results/iter0064-t1/ceiling-verdict.json` |
| Seat fitness (모델 × 포지션) | matrix live; 5 current cells; executor/pair-judge pins fail-closed "recert required" | `benchmark/seats/seat-matrix-2026-07-07.json` |

Working instruments: violation matrix (`run-violation-matrix.sh`), compliance cells (`run-compliance-cell.sh` + `check-compliance-cell.py`, now incl. `finish_gate_ran`), drift-bait probes (bare + resolve-framed), judge-quality bench (+codex route), frozen-VERIFY pair gates, token gauge (`scripts/skill-token-gauge.py`), **ceiling 3-arm harness** (`benchmark/ceiling/scripts/run-ceiling-tranche.sh`), **seat matrix + recert runner** (`benchmark/seats/recert-seats.sh`, fail-closed pins).

---

## 📍 Project state (verify before editing)

- **Branch**: `main`. HEAD ≈ iter-0064 closure commit ← `0bb4ef7` (iter-0064 pre-arms freeze) ← `b63dde9` (HANDOFF rewrite). Run `git log --oneline -5`.
- **Engine pins**: `.devlyn/engines.json` = `{"executor": "codex"}` (machine-local; orchestrator passes `--pair-verify` on resolve runs per `feedback_executor_codex_always_pair_verify.md`).
- Housekeeping (deferred per user 2026-04-30, unchanged): 4 dirty `.claude/worktrees/agent-*` — save patches before any removal; NOT in iter scope.

### Cold-start sanity check (~30s)

```bash
git status                                  # main, clean
bash scripts/lint-skills.sh                 # "All checks passed." (npm-pack check is occasionally slow — rerun once before diagnosing)
diff -q config/skills/devlyn:resolve/SKILL.md .claude/skills/devlyn:resolve/SKILL.md
diff -q config/skills/_shared/finish-gate.py .claude/skills/_shared/finish-gate.py
grep -q "CLOSED-PASS" autoresearch/iterations/0063-finish-gate-mechanical.md && echo "0063 ✓"
grep -q "^status: CLOSED" autoresearch/iterations/0064-ceiling-seat-instrument.md && echo "0064 CLOSED ✓"
grep -q "FAIL-pilot" benchmark/ceiling/results/iter0064-t1/ceiling-verdict.json && echo "ceiling verdict artifact ✓"
grep -q "Ceiling instrument gate" autoresearch/NORTH-STAR.md && echo "ceiling contract ✓"
command -v codex && codex --version 2>&1 | head -1
```

If any unexpected output, do NOT proceed. Surface to user.

---

## 🚫 Forbidden (binding; full rationale in the cited iters)

- No iter-0033h-style PLAN-pair firewall attempts (unblock conditions: SKILL.md PHASE 1 + iter-0033g §H). No deleting closed-iter replay assets.
- No degrading L1 solo behavior (revert-smallest-unit + re-smoke; 2× fail → surface).
- No skipping pair-collab rounds; no trivial questions to user mid-pipeline (pair first; surface only strategic ambiguity with options + recommendation).
- No bypassing CLAUDE.md Core principles (7 + 3); no cost framing; no fable test arms.
- No pre-registering iter-0035 real-project trial without user-supplied project + task + developer.
- Skill/CLAUDE.md/AGENTS.md edits require: user mandate, observed failure, or probe-guarded evidence. "Could be cleaner" is drift.
- No broad full-pipeline L2 claims beyond the measured F16/F23/F25 + SWE-bench n11 surface; no 세계최고/대체불가능/압도적 claims before the iter-0064 instrument exists (ops test #17).
- Thermometer discipline: probes are thermometers, not targets; shipped contract text never names fixture literals.

---

## ⏭️ End of HANDOFF

Evolution loop trajectory since re-open (2026-07-03): 0037-0039 conversational handoff + queue → 0040 cross-CLI portability → 0042-0047 instrument panel → 0048-0050 language-neutral + doctor → 0051-0057 local-backend shipped→measured→deleted → 0058-0060 violation-rate axis + engine-symmetric pair → 0061 F6 closed (AGENTS.md binding) → 0062 contract decidability (E1 shipped) → 0063 mechanical finish-gate → 0064 ceiling & seat instrument SHIPPED, pilot verdict FAIL-pilot on efficiency → **0065 levers: hands-free spec-shaped goals + bounded pair-VERIFY wall (next)**. Detail: DECISIONS.md + iteration files. Mission 1 not formally closed (test #15 user-gated). 압도적·독보적 is the bar; the ceiling instrument made it losable — and round 1 was honestly lost on wall-time, which is what keeps it honest.
