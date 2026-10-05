# 0232 — harness ladder: instruction-only first, then `intent` one measured rung at a time

2026-10-05. **Status: DRAFT (direction recorded; ladder design converging with Astra; registration not frozen).**

Authors: root (Opus 5.5) and Astra (gpt-6-astra, reasoning ultra, read-only). Independent Claude checks ran in parallel; they are summarized under "Direction check". Raw exchanges are in `.devlyn/bundle/`:
- `direction-a1-*` and `direction-root-position.md`;
- `harness-design-d1/d2/d3-*` and `harness-design-root-d1.md`;
- `product-d4-*` and `product-d5-*`.

## 1. Owner direction (2026-10-05, original words)

1. "지금 우리 하네스를 더 쪼으는것을 생각되는데 맞아? 우리 전체적으로 에이전트의 성능과 효율을 위해서 필요없는거는 해제하고 최대한 자율적으로 그러나 잠재력을 최대한으로 여는대신에 제대로 된 방향으로 가도록 설계하려고 하는건데 맞는거지?? 지금 방향성에 대해서 아스트라랑 잘 하고 있는건지 논의도 한번해줘봐"
2. "그리고 방향을, 너네 둘이 생각하게 최적의, 최선의 효율과 비용, 정확성 성능 등 잠재력을 최대한 활용할수 있는 방향의 하네스가 뭔지 스스로들 생각해서 제안하고 테스트 하고 알려줘봐."
3. "특히 resolve, ideate, design-ui 이런 스킬들 다 재구성해야하면 하고, 내가 의미하는게 뭔지 알지? resolve가 하려는거, 우리 의도 방향성 목표 북극성 등 다 고려해서"
4. On IndyDevDan's "Self-Compact Pi Agent": "적절한 시기에 self compactation 하는거 같은데 이거 가능하면 더 효율과 성능이 올라갈거 같은데"
5. On the threshold question:
   - "그 기준이 맞긴한데, 토큰도 늘지 않는게 맞는데, 오히려 줄일수 있으면 더 좋지. 예를 들어 pyx-memory는 필수는 아니지만, 그걸 사용하면 더 줄일수 있다던가 하는 부분? 불필요하게 뭔가 또 읽을필요는 없다는 얘기니까. 없는 경우는 가능한 최대로 하고."
   - The owner chose "핵심만 먼저" (core routes first) and "준비되면 바로 진행" (run when ready).
6. "design-ui는 폐기. ideate도 원래 의도 방향 목표에 따라 재설계. 그리고 이제 resolve가 없어지던지 intent로 재설계되든지 할거 같은데, 그거에 맞게 설계 되어야 하지 않겠어? 의도 파악을 잘 해봐. ideate 은 원래 loop engineering을 위해서 사용자가 의도만 주입하면 그걸 구현할수 있는 형태로 메타 프롬프트와 여러 task 로 잘 설계해서 쪼개서 정리한 후에 자동으로 에이전트가 가져가서 하나씩 처리하는걸 목표로 한거고. resolve(intent)는 기본 claude.md나 agents.md 하네스로만은 부족한, 복잡하거나 100% 자율로 했을때 틀리거나, 혹은 특히나 코드 정리라던가 클린업, verify 등을 놓치거나 필요할떄 정확한 소프트웨어 개발 방법론을 적용해서 깔끔하게 하기 위함인데, 이러한것들을 충분히 반영해서 불필요한건 걷어내고 필요한건 넣고 해서 최소한으로, 그리고 최대한 효율적으로 너네가 잠재력을 폭발시켜서 bare로 하는것보다 수십배 수백배 더 잘할수 있또록 하는게 의도야."
7. "그리고 사실 resolve가 없이도 claude.md나 agents.md 로 그게 가능하면 없어도 되긴 해. 예를 들면 개발하고 나면 항상 클린업한다거나, 여러 다른 모델로 verify 한다거나 등."
8. "하네스가 없다기보다는 사실 하네스가 agents.md 나 claude.md 에만 들어가도 잘 해내냐는거지. 그게 아니면 조금씩 intent를 조여서 하고, 조였을때 다른 수치들이 안좋아지면 안되고 더 좋아져야지 (실행 시간, 성능, 효율성, 토큰 등) 그런것들을 기준으로 해서 세계 최고 수준의 하네스를 만들어보자고. astra와 잘 논의해봐" (Astra at ultra.)
9. "우리가 지금까지 얘기한것들중에 의도 목표 북극성 등 관련 context가 부족하거나 아웃데이트 되었으면 업데이트도 하고 진행하자" This record and NORTH-STAR's 2026-10-05 block are that update.

Also on 2026-10-05, before this redirection, the owner approved R5 ("보호함"). In 0230's v7 round: a PHASE 0 inventory of ignored entries protects pre-run user files, which are never deleted and are adopted only by an exact path.

## 2. Interpretation (what the record binds)

- **Product shape.**
  - The installed CLAUDE.md/AGENTS.md instructions carry the harness wherever they suffice.
  - `ideate` is the loop designer: intent → meta-prompt plus split, self-contained tasks → agents drain them one by one.
  - `intent` succeeds `resolve`. It is the methodology layer, used only where the instructions fall short: complex work, work that goes wrong under full autonomy, missed cleanup and verification. It need not exist if the instructions achieve that.
  - `design-ui` is retired.
- **Ladder rule.**
  - Rung 1 is the instruction-only harness.
  - Each later rung adds one `intent` mechanism, licensed by a failure observed on the rung below.
  - A mechanism stays only if it improves at least one of wall time, quality, efficiency and tokens, and regresses none.
- **Tokens.** They must not increase, and lower is better. Optional memory may replace re-reading where present; it is never required.
- **Threat model and stopping rule for review and hardening** (the outcome of the direction check, §3):
  - Agents are capable, authorized and fallible.
  - Deliberate forgery is a documented trust boundary.
  - Only reproduced failures of a promised guarantee with a plausible trigger are fixed.
  - Each fix round gets one bounded review.

## 3. Direction check (owner message 1)

- **Root's position** (written before any reply): the goal matches the North Star.
  - The bundle cut agent-facing text: SKILL.md −31%, references −6%.
  - The review-fix rounds grew the gate layer: spec-verify-check 5,083 → 6,576 lines, finish-gate 521 → 1,080.
  - Confirmed findings per seven-lens round did not fall: 38 → 44 → 49.
- **Astra A1:** the bundle's architecture fits, but open-ended hardening does not. Finish bounded v7, stop, measure.
- **Claude classification of the 49 v7 rows:**

  | Trigger | Rows |
  |---|---|
  | Common | 0 |
  | Plausible | 12 |
  | Rare | 33 |
  | Adversarial-only | 4 |

  Further observations:
  - 19 rows come from code that earlier fix rounds wrote.
  - 0 rows concern efficiency.
  - About 24% of wave 1's new test lines pin the 4 adversarial rows.
- **Claude evidence review, 0213–0231:**
  - Full resolve ran about 3× native wall and 3–9× OUTPUT, and completed 0/4 against native's 1/4 (0224).
  - The repeatedly measured lifts are review→reproduce→repair on hard tasks (0184 2/4 → 4/4) and the cross-engine pair's unique hits (0227, 0229).
  - 0224's final-report audit recorded 0 false completions. Native reports of success on I0185 failed only hidden oracle rows. That shows inadequate coverage, not knowingly false reporting (Astra D4 correction).
  - Most other phases and gates are unmeasured.
- **Claude independent critic:** the tightening is real and sits in the gate layer. It proposed the threat model and stopping rule adopted above.

## 4. Design convergence so far

- **D1** (independent): root and Astra both proposed one continuous owner, deterministic final acceptance, independent review that binds only on evidence, bounded repair, and no phase choreography.
- **D2/D3** (converged N kernel):
  - one logical owner, continuous implementation;
  - a declared scope with one recorded amendment inside the user's authorization;
  - mechanical acceptance on the final source, with no corrective mutation;
  - two fresh reviewers, where a binding claim names the requirement, trigger, causal path and evidence;
  - a handoff note plus a fresh session only at review→repair;
  - a helper-written task record;
  - R5's inventory kept;
  - an unreadable environment directory that existed before the run becomes an opaque baseline entry.
- **Self-compaction (owner message 4):**
  - Neither CLI lets the model trigger compaction headless.
  - Claude Code: `autoCompactWindow`, plus a SessionStart hook with source `compact` for re-injection.
  - Codex: `model_auto_compact_token_limit` and `compact_prompt`.
  - N therefore implements it as a session boundary with an agent-written handoff.
- **D4 (product restructure):**
  - N becomes `devlyn-intent`.
  - `devlyn-ideate` is the public loop owner, with the queue protocol kept as its internal durable utility.
  - B is dropped, and v7 and the bundle are parked. R5 carries into intent.
  - The ideate loop gets its own later experiment: the whole intent run through frozen intent, against ideate decomposition drained through the same rung.
- **D5 (measured ladder, after owner messages 7–8):** stage 1 runs A/I/F before any N build.
  - **I** replaces the devlyn-managed instruction payload with a short methodology block (target 350 tokens, cap 500). It covers:
    - the contract and scope;
    - a baseline failure first when feasible;
    - cleaning up what the change created;
    - required checks on the submitted source;
    - one fresh review by another engine, plus repair;
    - a truthful report.
  - I also gets one stateless cross-engine review launcher. It has no skill, no phase files, no task record and no memory discovery.
  - **Later rungs** are licensed only by failures observed in I, in this priority order:
    1. enforced scope and ownership;
    2. a deterministic acceptance runner;
    3. a second reviewer;
    4. mechanical binding of findings;
    5. a review→repair handoff;
    6. a task receipt.
  - **Panels.** An easy-task panel (8 cells, A/I) is scored separately before any default is selected. Each later rung runs 24 cells against the last admitted rung.

## 5. Owner decisions (2026-10-05)

| # | Question | Decision |
|---|---|---|
| O1 | Promotion threshold against the incumbent | Keep ≥30% less wall than F with quality preserved; tokens must not increase, and lower is better |
| O2 | Scope of the first package | Core routes first; unsupported routes are rejected explicitly |
| O3 | Running the cells | Run when ready; no further run approval |
| O4 | A mechanism improves quality but costs some time or tokens | **Judge per success** (Claude recommended; Astra recommended strict sums). A failed run counts as not done, and a mechanism stays if time and tokens per correctly completed task do not increase, quality does not regress, and at least one of them strictly improves |
| — | Baseline failure first | Settled without the owner: required when feasible, with the reason recorded otherwise (Astra D4/D5). This matches CLAUDE.md's existing rule ("Bugs: write the failing test first"). Root's broader "failing test first for every behavior change" has no supporting record and adds cost |
| open | Dependent tasks in ideate's local loop start from the accepted predecessor commit in a new owned worktree | Deferred to the ideate stage (Astra recommends yes) |

## 6. Registration

Not frozen. Stage 1 is planned as follows:

- **Cells:** A/I/F × D3/D4/I0185 × claude/codex × 2 replicates = 36 measured cells, plus 6 SMOKE, on the 0231 apparatus.
- **Fixed conditions:**
  - pinned CLIs, tasks, roles and the four-round allowance;
  - F at `4056ebe2`;
  - A as the task repository with no devlyn installation.
- **Decision rule (O4):** applied per configuration to arm X's six cells.
  - **Definitions:**
    - S_X = completed cells;
    - W_X, I_X, O_X = sums over all six cells, failures included;
    - per-success cost = sum ÷ S_X.
  - **Admitting a candidate** against the last admitted rung, which is A at the start:
    - per-task completion counts and oracle-row passes are no lower;
    - there is no false completion, scope violation, user-data harm or severe regression;
    - per-success W, I and O do not increase;
    - at least one of completion, W, I and O strictly improves.
  - A candidate with S = 0 earns no claim.
  - If I fails against A, A stays the admitted rung.
  - **Incumbent replacement against F** applies O1 on per-success terms.
  - Raw sums are published alongside.
- **To freeze:** exact definitions, predictions, identities and the build list are frozen with Astra before any cell runs.
