# HANDOFF — for the next session

**Read order on cold start (mandatory)**:
1. **This file** — operating context + collection hold + pair-collab protocol
2. [`NORTH-STAR.md`](NORTH-STAR.md) — goal + floor contract (L0/L1/L2, ops tests 1-16) + ceiling contract + ops test #17 + pair-mode policy
3. [`PRINCIPLES.md`](PRINCIPLES.md) — pre-flight 0 + #1-#7 (every iter cites)
4. [`MISSIONS.md`](MISSIONS.md) — Mission 1 active + ceiling addendum + roadmap to endgame + hard NO list
5. Accepted 0114 / held collection: [`iterations/0114-harness-direction.md`](iterations/0114-harness-direction.md) and [`0113/A15`](iterations/0113-layer-lift-meter-STUB.md). Parked: [`iterations/0112-venue-tolerant-horizon-STUB.md`](iterations/0112-venue-tolerant-horizon-STUB.md) § PARKED. Most recent closed: 0110 (`VENUE_REJECTED`), 0111 (SHIPPED). Everything older: iteration index + `DECISIONS.md`.
6. [`DECISIONS.md`](DECISIONS.md) — append-only ship/revert log (newest at bottom)

If any file contradicts another, **NORTH-STAR.md wins**, then this file, then PRINCIPLES.md. Open a doc-fix iter on the contradiction. Historical narratives live in `iterations/*` + DECISIONS.md — this file carries only what binds the next session (user cleanup directives 2026-07-07, 2026-09-02).

---

## Direction reassessment — 2026-09-05

Before continuing below, read [0115 direction and initialization ownership](../../devlyn-cli-0115-bootstrap-baseline/autoresearch/iterations/0115-bootstrap-baseline.md) and [0116 filename identity](../../devlyn-cli-0115-bootstrap-baseline/autoresearch/iterations/0116-baseline-path-identity.md). Verified isolated branch `codex/0115-bootstrap-baseline-20260905` contains `9394f5f` (bootstrap owns the mandatory baseline) and `bdfef51` (NUL framing closes a reproduced scope omission). Actual Fable 5.1/Grok 4.6 design and final Fable/Codex/Grok static reviews, required tests and full lint are recorded; durable evidence is in `~/.local/share/nx01/iter0115/` and `iter0116/`. These are candidate commits, not main adoption or whole-harness readiness.

**0114 is accepted; collection is held for a separately scoped quiet-detector correction and apparatus re-freeze.** Original product, frozen panels and historical run state are preserved. The new reader deliberately rejects nonempty legacy LF snapshots. Keep accepted A15 on its frozen product; adopt the candidate only with a fresh authorized baseline, never by recapturing a dirty active run. The linked direction record keeps original-intent closure, current role certification and real-project/matched-time comparisons as open evidence gates.

## 🚦 START-HERE — 0114/A15 ACCEPTED; COLLECTION HELD (2026-09-05)

**User continuation resumed; scoped full PASS is archived as `rs-20260905T141220Z-694227ace2db` and implementation committed `4ccb6d7ad2c3a868f9e72c7e8a537c82e50cb02b`.** The [0114 final-evidence checkpoint](iterations/0114-harness-direction.md#checkpoint) owns exact base/spec pins, BUILD_GATE 7/7 + independent MECHANICAL 7/7, no-op CLEANUP, actual Codex/Fable/clean-isolated Grok final PASS with zero findings, durable 1186-file bundle/manifest and preserved incomplete rs104352 state. Historical failures, owner amendments and design-only GO receipts remain there; the final report owns interruption/provenance caveats.

**Next:** separately scope the quiet-detector correction and apparatus re-freeze before collection. Both drain `ACTIVE_CLI` and runner `real_writer_check` missed observed Grok `--prompt-file` execution. The runner's separate active-root-state predicate blocked at observation; usage/window were not evaluated, and no overall gate PASS is claimed. Frozen 0114 forbids drain changes. Follow [collection continuation](iterations/0114-harness-direction.md#collection-continuation-owned-by-root). Accepted A15 runner `8694c9fdb0149b3f985398d503a559d058d42010194872063a09b293baed12f5`, apparatus `644fef268345b0c9a435f7a28bb825d2c14122c07efacacfecb8b97fa39881c1`, params `38e0761882a9e2f4d3aab32e6d2d238ffe5dcca342f00b45d6e6dd8bb2cc425b` remain current; staged product stays `ee8f74d4d2a5061c36b1ad2b4459f6801f08af3b0d08d069a756532bdb8a89f1`.

Old `~/.local/share/nx01/iter0113/quick-1/` is stopped and preserved with historical smokes. **Collection is NOT LAUNCHED:** `~/.local/share/nx01/iter0113/quick-a15-1` / `lift-quick-a15-1` are reserved future names, revisable by new registration; no new collection exists. Retain quiet account, usage ≤10%, no other CLI seats, outside 23:00–01:00 KST, actual-pair smoke, one lane, 72 base cells (4/1/1), infra-only attempts 2/3, single evaluation and exact scorer `NEEDS_TOPUP`. Pre-A15 rows are noncomparable; no causal leakage effect is inferred.

The goal remains genuine `bare < solo < pair` in quality AND efficiency. Preserve invalid-exam corrections and valid negative results; do not force the ordering by changing the exam. NULL/INCONCLUSIVE do not automatically remove pair. [0114](iterations/0114-harness-direction.md) records the bounded SURFACE_CLOSE candidate for a separate future worktree. Broader superiority and whole-harness production readiness remain unproven.

Plain conversation may authorize implementation (DECISIONS 0069.1); once resolve is entered, its phase machinery is mandatory. Executor pins bind both routes. VERIFY pair stays default when available; explicit routes fail closed. The 0070 aggregate/off-resolve closure direction is not a shipped guarantee.

## Binding seat/lane rules (consolidated; details in the cited iters)

- fable = design / adjudication / verification / planning ONLY — token
  economy HARD (`feedback_fable_token_economy`); corpus authoring,
  apparatus builds, runbook scripting, repetitive runs → terra direct-drive
  lane or opus/sonnet; verification trio = fable + codex `gpt-6-astra` + grok 4.6 (402
  cleared 2026-09-05; if it returns → opportunistic skip, user ruling 2026-08-31); matrix arms only on a quiet
  account outside 23:00–01:00 KST; delegated edits = ONE writer at a time +
  digest pins in seat prompts (0105 race).
- Seat recipes (user direction 2026-09-05: codex `gpt-6-astra` + grok 4.6):
  terra = `codex-monitored.sh -s workspace-write -c model_reasoning_effort=xhigh`
  (omit `-m` → CLI default `gpt-6-astra`); sol = same wrapper read-only;
  grok = `grok -p "<prompt>" --allow read_file --allow grep --allow list_dir
  --no-memory --reasoning-effort high` (STDOUT-only, STATIC-ONLY in the
  prompt — `-p` can write files; it cannot run commands). Whole-tree pins:
  `cd <root> && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 shasum
  -a 256 | shasum -a 256`.
- Seat-lane gotchas (each observed ≥1×): seat prompts = literal strings
  (zsh `${var/pat/rep}` silently no-ops); watch completion by PID or by a
  line YOUR subshell appends after the wrapper exits (`echo rc=$?`) — seat
  logs ECHO other logs, including another seat's `codex exited` line
  (terra14, 2026-09-03); codex
  "model at capacity" is transient (retry loop, 3 min); terra STOPs on
  packet wording (re-pin BEFORE self-tests; whole-tree pin lines never pass
  `shasum -c`); terra once renamed full suites to `legacy_self_test` — grep
  before trusting "N/N"; background waiters cap at 10 min — use
  `run_in_background`/Monitor; the orchestrator overestimates the clock —
  read `date`; envelope `modelUsage` is invocation-cumulative (never a
  zero-usage predicate); parallel Bash calls inherit cwd; `ps | grep 'grok -p'` misses grok seats
  (multi-line argv — use `pgrep -fl`); a harness background task can be
  killed mid-seat (grok3, 2026-09-05) — detach long seats with `nohup` and
  Monitor the log's `rc=` line.
- Launch discipline (0102/0103/0110 rules): writer check (`ps` for live
  `claude -p`/`codex exec`/`grok -p` + `.devlyn` run_id) before any
  bootstrap; detached long runs via `python os.setsid()`; scorer frozen +
  pair-audited before inputs complete; ONE evaluation per registration,
  attempts only replace infra-invalid rows on identical digests; no
  retuning; corpus ids never in skill text; per-task outcomes sealed until
  the scorer runs. Driver seed = `benchmark/executor-quality/scripts/mx-driver.py`.
- Standing playbook: [`playbooks/model-checkup.md`](playbooks/model-checkup.md)
  (0104: new model ID → recert + discovery band → one-page verdict; user
  shorthand "모델 체크업"). 0113 becomes its harness-arm column.

## ⛔ Hard operating rules (binding)

1. **Pair-review IS the work** — every non-trivial claim pair-verified at write time; open cited file:line yourself; R-final before commit when results surprise.
2. **Cost framing is BANNED** (memory `feedback_no_cost_talk.md`, HARD). Axes: effectiveness × accuracy × reasonable wall-time.
3. **Verify before claim** — every cited file:line opened at citation time; stale references caused fabrication risk in past iters.
4. **Explain simply** (Korean, decision-maker view) — conclusion + options + recommendation; no internal label walls in user-facing summaries.
5. **Greenfield interface, NOT mechanisms** — any redesign edit must justify why a learned mechanism changes (not just relocates).
6. **Measurement-gated pair policy** — pair ships per-phase only on pre-registered L1-vs-L2 evidence; "no evidence pair needed" ≠ "evidence solo wins"; honest label is "unmeasured".
7. **Detached long runs + pre-frozen scorers** (0102 operator rules): long unattended matrices detach via `python os.setsid()` (macOS has no `setsid`; harness-tracked drivers were killed 3×); any adjudication/scoring apparatus is frozen and pair-audited BEFORE its inputs complete.
8. **Measurement tiering — do NOT gate every improvement on the ceiling full-run** (user directive 2026-07-11). Iterate on the fast behavioral instruments as the inner loop: self-tests + token gauge + lint (seconds), then `violation-matrix` / drift-bait bare probes / compliance cells (minutes), then a resolve-framed probe (~10-20 min). The ceiling 3-arm full run (`run-ceiling-tranche.sh`, hours) is a PERIODIC background exam only — run it detached, keep improving in parallel, never block design/impl work waiting on it. Need a quick directional ceiling read → `--tasks <1-2 rows>` (+ `--resume`), not the full corpus. Full-run stays the moat gate for 세계최고 claims (ops #17); it is not the iteration loop.

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

### Blocks 2-6 (2026-04-29 → 2026-05-03 — FOLDED; verbatim archive in git history of this file, pre-2026-07-20)

Operative content fully carried by binding surfaces — consult those, not
this summary: **B2** six directives → memory `feedback_no_cost_talk` /
`feedback_l2_pair_collaboration` / `feedback_codex_collaboration_not_consult` /
`feedback_pair_vs_solo_empirical` / `feedback_explain_simply` + Hard
rules above. **B3** PLAN=invariants, BUILD=constrained judgment,
EVAL=independent layer → NORTH-STAR product surface. **B4**
engineer-quality floor + cost-ban + score-variance skepticism +
Mission-1-solo-first → NORTH-STAR goal + MISSIONS. **B5** 2-skill
design (ideate optional / resolve standalone / multi-LLM via adapters)
→ NORTH-STAR § product surface (locked 2026-04-30). **B6** round-3
pair-redesign (measurement-gated pair; honest "unmeasured" labels;
HANDOFF cleanup mandate; Codex reads codebase directly) → NORTH-STAR
§ Pair-mode policy (round-3 locked).

### Block 7 (2026-07-06/07 — ceiling mandate + asymmetric harness + endgame + operating priority)

> 일단 얼추 맞는데 가장 중요한건, 엔지니어 품질이 아니라, 세계최고 수준의 대체불가능한 품질의 소프트웨어여야해. 그리고 효율, 성능, 정확도도 전세계 그 누구도 감히 따라할수 없는 천장을 뚫는 압도적인 수준이어야 하고. 그걸 염두에 두고, 지금 가는 방향이 맞는지, 형태 (skill)이 맞는지부터 해서 너의 모든 능력을 총 동원해서 분석하고 해당 목표까지 갈수 있는 방향으로 설계해봐.

> 이게 맞는지 모르겠지만, 결국 에이전트들이 각자 잘하는것을 힘을 합해서 각 에이전트의 잠재력과 성능 품질을 최고로 끌어올리는 하네스여야 한다는거야. 그래서 내가 생각했을때는 최소한의 하네스에 최대 자율이었는데, 그게 틀리면 개선해주고, 올바른 방향으로 align 되도록 해줘

> 그래서 하이브리드를 구상했던거고 에이전트 군단으로 만들어서 하네스 + 루프 엔지니어링으로 나는 최소한의 의도와 목표, 북극성만 주면 끝까지 에이전트들이 협력을 해서 완벽하게 완수하는것을 생각하고있어. 그게 궁극적인 엔드게임이야

> (2026-07-07) 1) codex 의 의견중에 너가 깊이 생각하고 너도 동의하는것만 채택하고 나머지는 너의 생각대로 설계 계획해줘. 2) … 모델의 버전이 바뀔때, 정확하게 어떤 모델이 어떤 포지션에서 가장 강한가를 측정할수 있는 것도 있어야 그 자리를 체크해서 가장 적합한 모델로 사용할수 있을 것 같아.

> (2026-07-07) 일단은 최대한 너가 해줘야해. 천장을 뚫고 세계최고 수준의 Loop Egnineering/Harness Engineering 이 되려면. 최대한 너에게 맡길거야. 너가 없어도 돌아가는건 차선이야.

> (2026-07-07) 압도적이고 독보적이어야해

> (2026-07-07) 핸드오프든 뭐든 앞으로 참조하는 문서들에 방해가 되는 context들은 다 클린업해줘

→ Shipped: NORTH-STAR ceiling contract + ops test #17 + moat=survives-copycat (`eda7e7f`); MISSIONS ceiling addendum + endgame roadmap; iter-0064 STUB; CLAUDE.md/AGENTS.md § Evolution loop; this HANDOFF rewrite (`e58e65c`+). **Operating priority**: strongest available orchestrator (Fable while available) drives the loop directly at maximum depth; orchestrator-neutral continuation is insurance (차선). Harness philosophy ASYMMETRIC: max determinism in the skeleton (code), max autonomy in the intelligence. Codex R0 archive: `/tmp/codex-northstar2/r0-response.log`.

### Block 8 (2026-07-10 — value axes for frontier engines + three-way pair)

> 그러면 우리가 지금 계속 이렇게 진화시키려는 의도와 목표 북극성등을 바탕으로 codex cli gpt 5.6-sol 과 grok 4.5 와 셋이서 함께 의논해가면서 진짜 우리 하네스를 쓰면 모든 모델들의 성능과 효율과 모든 잠재력을 다 사용할수 있게 하도록 계속 진행해줘.

> 그냥 코딩하는것도 좋은데, 이제는 왠만하면 코딩은 다 잘 푸니까 (프론티어 모델이 아닌경우는 효과가 있겠지만), 이제 내가 주로 프론티어 모델을 사용할때는, 코딩 실력도 코딩실력인데, 내 의도나 목표를 얼마나 잘 파악하고 얼마나 잘 쪼개서 얼마나 같이 페어로 협업을 잘하고 얼마나 설계를 그냥 혼자 할때보다 꼼꼼하고 오류없이 확실한 근거를 바탕으로 잘 하는지 등 (그래서 내가 원칙 몇개를 세운거고) 그런게 더 중요할거 같아. Loop 엔지니어링도 결국에 나나 다른 유저가 의도나 목표를 주입하면, 그걸 제대로 의도파악하고 추측하지않고 제대로 된 근거를 바탕으로 제대로 된 판단을 하고 그를 바탕으로 task를 잘 쪼개서 하나씩 차근차근 다른 에이전트들과 페어로 협업하고 검증하고 테스트하고 클린업까지 제대로 완벽하게 말하지 않아도 딱 잘하는 그러한 하네스와 루프 엔지니어링을 만들고 싶은거거든. 그럼에 있어서, 확실하게 전세계 그 어떤 하네스보다 우리것을 쓰면 해당 모델이나 에이전트 (LLM등)를 최대한의 잠재력을 다 꺼내서 쓰고, 협업을 제대로 시켜서 각자 가진 장점을 최대한 발휘해서 시너지를 내도록 하는것, 그것이 우리 목표였잖아? 이거 로드맵이나 의도 목표 등에 context 잘 녹아있는지 확인하고 너와 codex cli gpt 5.6-sol, 그리고 grok 4.5 까지 다 이해해서 다음계속 진행할수 있도록 해줘.

> 방향을 제대로.

> 그렇다고 해서 코딩을 놓자는 얘기가 아니야. 말그대로 각자 에이전트의 코딩능력 분석능력등 기본적인 잠재력은 최대한 가져가고, 추가적으로 이해력, 의도파악 능력, 분해, 설계, 협업 능력, 시너지 등을 더 극대화해보자는 얘기지.

> 이미 알고 있겠지만, 중요한건 하네스로 인해서 원래 모델/에이전트가 가지고 있던 자율성을 기반으로 한 성능이 저하되면 안되고, 오히려 잠재력을 더 증폭시켜야해. 하네스를 너무 꽉 조이면 오히려 안좋지 않을까 하는거니까, 이것도 철저하게 테스트를 해서 규명하고 밸런스를 잘 맞출수 있도록 해줘.

→ Folded: NORTH-STAR § Value axes for frontier engines (2026-07-10, nuance-corrected same day: baseline capability extraction is kept at MAXIMUM — the five axes are ADDITIVE maximization on top, not a substitute); three-way pair protocol live (memory `feedback_threeway_pair_grok_2026_07_10.md`); iter-0068's categorical-trap corpus measures the DISCIPLINE axis (scope/atomicity/cleanup/spec-fidelity). **Corpus roadmap directive (user, same day)**: the reinforcement round exists because the exam corpus previously considered ONLY coding-shaped problems — future corpus expansion must also cover the non-coding axes (intent fidelity / decomposition / design rigor / collaboration), which need different problem shapes than hidden code oracles (candidate instruments named in iter-0068 R-preFreeze record); to be discussed three-way before the next corpus iter. **No-suppression directive (user, same day)**: the harness must never degrade the engine's native autonomy-based performance — it must AMPLIFY potential; over-tightening is a live risk to be rigorously measured and balanced. Existing evidence FOR the risk: iter-0067 neutral judge preferred copycat diffs 16:3 over the devlyn A-arm on saturated rows, and wall 8.33× — both are over-tightening signals. Measurement lever already in hand: saturated rows (bare-solves) become the NO-DEGRADATION control corpus — on them the harness must match bare's objective outcome, not lose the blind quality ranking, and stay within the wall cap; the discriminating rows measure amplification. Balance = win on discriminating rows WITHOUT losing on saturated controls. Asymmetric-harness philosophy (Block 7: max determinism in skeleton, max autonomy in intelligence) is the design principle this tests.

### Block 9 (2026-07-10 — loop architecture: intake skill → queue loop + universal final intent-verification)

> 우리 계속 진행할 로드맵에, 유저가 입력하면 의도파악, 팀으로 설계, 로드맵 설정, task 분리 등등을 하잖아? 그거 skill 로 하나 만들어야 할것 같고, 그 스킬을 통해서 유저 입력과 함께 결과 context가 나오고, 그걸 받아서 두번째 에이전트가 해당 context를 가지고 큐에 넣고, 그 큐를 계속 돌리게 하는 그러한 스탭으로 진행되는걸 loop 로 생각하긴 했어. 그래서 이 부분과, 그리고 하나 빠진건지 아직 있는건지는 모르겠지만, 마지막에 원래 의도나 설계, 목표에 맞게 잘 되었는지도 팀으로 검증하고 아니면 다시 하고 하는게 있어야하는데 resolve에 있다고는 알고 있거든, 없으면 넣어주고. 그리고 resolve를 돌지 않고 해결을 하는 건이라도 그게 되어야해.

> 이건 혼자 생각하지말고 codex 5.6-sol 과 grok 4.5 와도 팀으로 논의해서 결정하고 context에 올려서 로드맵에 넣고 해결/개선하자.

> (same day, full-loop refinement) loop 엔지니어링시에 워크플로우가, 유저인풋>ideate로 팀이 함께 의도파악, 설계, task 분리 등 이 맞는지 > 맞다면 그뒤에 queue에 저절로 넣는건지 아니면 devlyn:qeueu로 직접 넣어야하는건지, 그러면 어떤 ideate가 어떻게 queue에 들어갈지 어떻게 아는지 > 그 후에 drain-queue 로 진행하면 > 팀이 함께 하는데, 오케스트레이터가 직접 할수도있고 resolve로 진행할수도 있겠지 > 그 이후에 다 되면 역시 팀이 함께 검증하고 테스트 하고 클린업하고, 원래 처음 의도대로 잘 되었는지도 팀으로서 체크하고, playwright도 필요하면 사용하고 가능하면 스크린샷으로 UI도 찍고 > 그 뒤에 커밋/푸시 하는 그러한 full loop 를 상상하는건데, 그 의도대로 지금 context가 잘 되어있는지 확인해주고 셋다 팀으로 논의해서 방향이 맞는건지, 수정/개선해야할 포인트가 있는지 등도 얘기해서 업데이트 해놔줘. 그리고 outdated 된 방해되는 context들은 클린업해주고.

→ Current-state facts (verified at record time): `/devlyn:ideate --project` already does intent-elicitation + 3-7-spec decomposition + plan.md (SKILL.md:59; team-design inside ideate is UNMEASURED, not wired); `/devlyn:queue` drain does spec→resolve→outer-loop (SKILL.md:19-22); NO wired handoff plan.md→queue; resolve VERIFY verifies against SPEC (fresh subagent + conditional pair) — intent fidelity = spec fidelity; **plain-conversation (non-resolve) work has NO final intent-verification** — iter-0069.4 deferred exactly this with revisit precondition "user funds a measured mechanism"; THIS directive is that unfreeze (licenses a pre-registered ITER, not permanent prose — 0069.3 rule stands). **→ RESOLVED 2026-07-10: three-way round CONVERGED (Codex + Grok, zero-dissent essentials); design + 5-rung ladder frozen in `iterations/0070-loop-architecture-STUB.md`** — no new skill (evolve ideate --project), plan.md = locked root intent contract, `queue add-plan` wiring, post-drain project intent-closure (≤2 re-queue), shared INTENT_CLOSURE kernel for off-resolve work (semantic, never Stop-hook/regex; "measured" bar defined), pair surfaces last and evidence-gated. Entry condition: iter-0068 closes first.

### Block 10 (2026-07-10 evening — non-coding exam corpus: axes over saturating coding skill)

> 그리고 사실상 코딩 능력은 갈수록 bare 가 좋아질테니까 (모델의 성능이 올라가기 때문에), 그보다는 얼마나 의도를 잘 파악하고 얼마나 잘 설계하고 얼마나 우리가 설정한 원칙들 (추측하지말고, 필요하면 5 why로 생각해서 근본적인 문제를 풀고 등등) 을 잘 활용하는지, 얼마나 다음 에이전트가 작업하기 쉽게 task를 적절하게 잘 쪼개고 분배하고 메타 프롬프팅을 잘하고 context engineering을 잘하는지 등 우리 의도/목표/북극성 등을 잘 참조해서 그에 맞는 시험지를 만들고 테스트 해야하는거 아닌가 생각이 되긴해.

→ Executes Block 8's corpus-roadmap directive; the three-way design round was pulled forward (user license, same message) while the 0068 gate ran — ladder order + live gate untouched. RESOLVED same day: third three-way round CONVERGED (Codex + Grok both GO-WITH-EDITS; every load-bearing citation orchestrator-verified at the cited files). Four instrument cells + shared Non-Coding Admission Kernel folded into `iterations/0070-loop-architecture-STUB.md` § "Non-coding exam corpus fold": **Packet Utility Differential** (the one genuinely uncovered surface — meta-prompting/context-engineering measured as next-agent outcome; supersedes 0033e), **Counterfactual Intent Holdout** (supersedes weak B1 always-halt fixture), **Blind Design-Defect Differential**, **Root-Cause Recurrence rows** (drift-bait extension, no new family). Anti-saturation = kernel manifest fields (cohort identity + re-gate on engine drift), NOT new NORTH-STAR prose.

At `~/.claude/projects/-Users-aipalm-Documents-GitHub-devlyn-cli/memory/`: `feedback_no_cost_talk.md` (HARD), `feedback_l2_pair_collaboration.md`, `feedback_pair_vs_solo_empirical.md`, `feedback_codex_collaboration_not_consult.md`, `feedback_explain_simply.md`, `feedback_implementation_to_codex_2026_07_05.md`, `feedback_test_engine_tiering_2026_07_04.md` (probe/test arms codex/sonnet/opus, never fable), `feedback_executor_codex_always_pair_verify.md`, `feedback_worldclass_ceiling_mandate_2026_07_06.md`.

**Conflict rule**: if HANDOFF and a memory file disagree, stop before editing and ask the user.

### Block 11 (2026-09-02 — design review → fixed layer-lift meter, verbatim)

> Opus 4.8 보다 확실하게 Opus 5 가 많이 놓치는 느낌은 분명히 있었는데, 이걸 증명하는 방법이 지금 설계대로 하는게 맞는지 아니면 의미가 없는건지, 의도 목표 비전 북극성 등을 검토해서 다시 알려줘. 우리가 이걸 하는 이유는, 지난번 Opus 4.7 때도 굉장히 이상한 모델 튜닝이 되어서 그런가 모든 사람들이 이상하다 라고 했었고. 이후에도 이런 일이 있을지 없을지 보장을 못하기도 하고, claude 뿐 아니라 codex 등 새로운 버전이 나왔을때 이전꺼를 써야하는지, 새로운걸 써야하는지 아니면 Grok 이나 Gemini 처럼 또 다른것보다 성능이 어떻게 다른지 등을 체크하는 어떤 최소한의 체킹 머신이 필요했떤거거든.

> 그러면 해당 테스트가 devlyn-cli 하네스가 없는 환경에서 돌린건지, 만약에 하네스가 있는 환경에서 측정이 달라지면 우리 하네스의 문제니까 하네스를 업그레이드 혹은 개선/수정 해야한다는 신호로도 읽힐수 있는데, 이것도 비교하게할 수 있나?

> 어쨌든 우리 비전이나 의도 목표 북극성 등을 살펴보면, 우리가 하려는게, bare 보다 더 나은 하네스 그리고 pair 로 했을때 더더욱 나은 하네스를 구축하는게 목표인데, 그걸 제대로 측정하는 고정된 방법이 필요한거야. 측정기.

> 그러면 가장 최소한의 토큰과 시간으로 가장 효율적으로 제대로 모델별로 측정할수 있는 측정기를 어떻게 만들어야할지 먼저 설계하고 그걸 만들어보자. 설명은 쉽고 간결하게 해줘 내가 이해하기 쉽게. … 그리고 그 계획을 5.6-sol 에게 검증시켜보고, 답변을 보고 너가 결정해봐 … 그리고 나서 새 세션에서 하나씩 완성시켜나갈수 있게 컨텍스트 이제 더이상 쓸모 없는건 지우고 업데이트된 핸드오프 문서로 준비해줘.

→ Folded: iter-0113 STUB (three-arm meter on the sealed 0102 corpus; predictions stated before any run); 0112 PARKED as a module; this HANDOFF compressed (closed-iter narratives removed — recover via `git log -p -- autoresearch/HANDOFF.md`, iteration files, DECISIONS.md).

---

## 🧠 Empirical TL;DR (what is measured, one screen)

| Surface | Verdict | Evidence anchor |
|---|---|---|
| Iter-0020 Codex BUILD/IMPLEMENT architecture | **FALSIFIED for that architecture** | iter-0020: L2−L1 = −3.6 on 9-fixture suite |
| Pair VERIFY on frozen diffs | **PASS** | frozen-verify-gate internal F12/F10 + SWE-bench Lite n11 (avg wall 1.87x, cap 3x) |
| Full-pipeline pair via risk probes | **PASS (small suite)** | F16/F23/F25 bare<solo<pair aggregate (avg wall 1.73x) — NOT broad product superiority |
| PLAN-pair | research-only | iter-0033d/f/g (no empirical subagent introspection; unblock conditions in SKILL.md PHASE 1) |
| Golden fixture suite as evolution signal | RETIRED | solo-saturates 88-99 (`benchmark/probes/README.md`) |
| Contract violations under temptation | live instrument | violation-rate matrix N=4: opus 12/24, sonnet 9/24 at baseline; E1 sentence flipped sonnet B4 4/4→1/4 (iter-0062); prose ceiling → mechanical gates (iter-0046 BUILD_GATE scope, iter-0063 finish-gate) |
| Codex ordinary-invocation pipeline | AGENTS.md IS the binding entry | iter-0061 A/B 4/4-vs-4/4 |
| Engine-symmetric pair invocation | REAL both directions | iter-0060 (codex→claude judge fired via adapter) |
| gemma3:4b as judge | MODEL CEILING — do not re-prompt | iter-0055/0056 |
| Ceiling quality (세계최고 axis) | FAIL-pilot twice (0064 LC3 4.32×; 0067 copycat 16:3, wall 8.33×) — no moat claim | iter-0064/0067 `ceiling-verdict.json` |
| No-degradation (Block 8 suppression axes) | Latest cohort `nodeg-20260722a` (0077.5): complete **6/7 best-ever** · zero K1 · objective 6/7 · blind **A_win 9→19**, B_win 36 ≤45 · wall median **10.659×** (best-ever, below no-lever noise band, still ≥3× cap) · quality bar still unpassed. Interphase lever shipped (12% of baseline); startup unmoved (110.8%) — mechanical-absorption hypothesis falsified; phase_union frozen-five +31.7% | `nodeg-20260722a` verdict + corrected-baseline.json; DECISIONS 0077.5 (history: 0073.2/.3) |
| C1 Stop-hook (terminal-claim pressure) | claude route VETO-CAPABLE — 5/5 BLOCK_HONORED strict bar; HONEST BOUND: CLI caps stop-hook loop (~9) — C1 = pressure, C2 = authority; codex ROUTE-DISABLED-BY-HARNESS, omp unmeasured | `benchmark/ceiling/probes/c1-stop-parity/results/`; DECISIONS 0074.3 |
| T1 packet calibration (seat×defect) | complementary override: catalog admits ONLY sonnet, credential ONLY terra (risk-diff 1.0 both) → routed-seat v2, validation fixtures landed | 0070a Amendment 2 + addendum 9; `benchmark/noncoding/validation/` |
| Seat fitness (모델 × 포지션) | matrix live; 5 current cells; executor/pair-judge pins fail-closed "recert required" | `benchmark/seats/seat-matrix-2026-07-07.json` |
| Opus line, bare, discriminating corpus | opus-5 fails LESS than opus-4-8 (Δ=−0.181, CI[−0.256,−0.109]); opus-5 ≈ fable-5; felt regression NOT reproduced by 0100/0102/0103; repo-scale band 0105–0109 REJECTED ×4; session-horizon 0110 VENUE_REJECTED, 0112 PARKED | DECISIONS 0102.1/0103.1/0105.1–0110.1; `~/.local/share/nx01/iter0102/` |
| **Layer contract L1>L0, L2>L1 on a discriminating corpus** | **UNMEASURED** — scoped 0114/A15 accepted and committed; collection NOT LAUNCHED, held for separate quiet-detector correction and apparatus re-freeze | [0114 checkpoint](iterations/0114-harness-direction.md#checkpoint), [0113/A15](iterations/0113-layer-lift-meter-STUB.md) |

Working instruments: violation matrix (`run-violation-matrix.sh`), compliance cells (`run-compliance-cell.sh` + `check-compliance-cell.py`, now incl. `finish_gate_ran`), drift-bait probes (bare + resolve-framed), judge-quality bench (+codex route), frozen-VERIFY pair gates, token gauge (`scripts/skill-token-gauge.py`), **ceiling 3-arm harness** (`benchmark/ceiling/scripts/run-ceiling-tranche.sh`), **seat matrix + recert runner** (`benchmark/seats/recert-seats.sh`, fail-closed pins).

---

## 📍 Project state (verify before editing)

- **Working state**: see START-HERE and actual `git status` / `git log -1` before editing. Push and release/installer publishing remain USER territory, hands off.
- **Engine pins**: `.devlyn/engines.json` = `{"executor": "codex"}` (verified 2026-09-02; machine-local; orchestrator passes `--pair-verify` on resolve runs per `feedback_executor_codex_always_pair_verify.md`). NOTE for 0113: the meter's L1/L2 arms stage their OWN `engines.json` with executor `claude` inside the arm worktree — the repo pin is untouched.
- Housekeeping (deferred per user 2026-04-30, unchanged): 4 dirty `.claude/worktrees/agent-*` — save patches before any removal; NOT in iter scope.

### Cold-start sanity check (~30s)

```bash
git status                                  # inspect current branch and WIP; see START-HERE
bash scripts/lint-skills.sh                 # "All checks passed." (npm-pack check is occasionally slow — rerun once before diagnosing)
diff -q config/skills/devlyn:resolve/SKILL.md .claude/skills/devlyn:resolve/SKILL.md
diff -q config/skills/_shared/finish-gate.py .claude/skills/_shared/finish-gate.py
python3 -c "import json; v=json.load(open('benchmark/ceiling/results/nodeg-20260713/nodeg-verdict.json')); b=v['bars']; assert b['objective']['passed'] and not b['quality']['passed'] and not b['wall']['passed']" && echo "nodeg 3-bar verdict ✓"
bash benchmark/ceiling/scripts/test-nodeg-cell.sh >/dev/null 2>&1 && echo "nodeg selftests ✓"
python3 benchmark/noncoding/scripts/classify-defect-family.py --self-test >/dev/null 2>&1 && echo "classifier ✓"
python3 benchmark/noncoding/scripts/conformance-gate.py benchmark/noncoding/validation/* >/dev/null 2>&1 && echo "validation fixtures gate ✓"
python3 config/skills/_shared/run-bounded.py 1 -- sleep 3 >/dev/null 2>&1; [ $? -eq 124 ] && echo "run-bounded ✓"
python3 config/skills/_shared/spec-verify-check.py --self-test && echo "spec-verify self-test ✓"
python3 config/skills/_shared/state-phase-write.py --self-test && echo "phase-write (L-D) ✓"
python3 config/skills/_shared/terminal-claim-check.py --self-test && echo "terminal-claim ✓"   # moved to _shared in 0078 Stage A (5339e41)
python3 config/skills/_shared/collect-codex-findings.py --self-test && echo "collector (0080 envelope gate) ✓"
python3 benchmark/ceiling/probes/r-weld-0082/test-collector-contract.py   # 114 checks incl. 12 real captures + 61 tracked non-regression (iter-0082; batch B + verdict ruling 2026-08-18)
python3 benchmark/ceiling/scripts/attribution.py --self-test >/dev/null && echo "attribution ✓"
python3 benchmark/ceiling/scripts/isolation-payload.py --self-test >/dev/null 2>&1 && echo "isolation-payload ✓"
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

---

## ⏭️ End of HANDOFF

Evolution-loop trajectory 0037→0111 is recorded in `DECISIONS.md` and the iteration files (0064/0067 ceiling FAIL-pilots; 0073 bottleneck = residual+VERIFY; 0102/0103 opus line; 0105–0109 band rejections; 0110 venue rejected). What is measured today: the harness ties bare on objective outcome, loses blind quality on saturated rows, and runs 8–12× wall — and the layer contract (L1>L0, L2>L1) has never been measured on a discriminating corpus. iter-0113 is the instrument that makes that claim losable. 압도적·독보적 is the bar; honesty about where it loses is the moat-in-progress.
