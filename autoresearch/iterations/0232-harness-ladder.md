# 0232 — harness ladder: instruction-only first, then `intent` one measured rung at a time

2026-10-05. **Status: stage 1 FROZEN (§6); later rungs are registered separately.**

Authors: root (Opus 5.5) and Astra (gpt-6-astra, reasoning ultra, read-only). Independent Claude checks ran in parallel; they are summarized under "Direction check". Raw exchanges are in `/Users/aipalm/.local/share/nx01/core-continuation-20260912/.devlyn/bundle/`:
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

Also on 2026-10-05, before this redirection, the owner approved R5 ("보호함"). In 0230's v7 round, a PHASE 0 inventory protects pre-run ignored content from harness settlement deletion and permits adoption only by exact path. Separately authorized disposal of a released worktree remains governed by the completion contract.

## 2. Interpretation (what the record binds)

- **Product shape.**
  - The installed CLAUDE.md/AGENTS.md instructions carry the harness wherever they suffice.
  - `ideate` is the loop designer: intent → meta-prompt plus split, self-contained tasks → agents drain them one by one.
  - `intent` succeeds `resolve`. It is the methodology layer, used only where the instructions fall short: complex work, work that goes wrong under full autonomy, missed cleanup and verification. It need not exist if the instructions achieve that.
  - `design-ui` is retired.
- **Ladder rule.**
  - Rung 1 is the instruction-only harness.
  - Each later rung adds one `intent` mechanism, licensed by a failure observed on the rung below.
  - Retention follows O4 and §6: quality is preserved, and total resources, failures included, are compared per correctly completed task.
- **Tokens.** Input and output per success must not increase; lower is better. Optional memory may replace re-reading where present; it is never required.
- **Threat model and stopping rule for review and hardening** (the outcome of the direction check, §3):
  - Agents are capable, authorized and fallible.
  - Deliberate forgery is a documented trust boundary.
  - Only reproduced failures of a promised guarantee with a plausible trigger are fixed.
  - Each fix round gets one bounded review.

## 3. Direction check (owner message 1)

- **Root's position** (written before any reply): the goal matches the North Star.
  - The bundle cut agent-facing text: SKILL.md −31%, references −6%.
  - Gate-layer sizes (main → bundle → v7 wave 1): spec-verify-check 5,083 → 6,177 → 6,576 lines; finish-gate 521 → 708 → 1,080.
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
  - Full resolve (3.2.1) ran about 3× native wall, with recorded OUTPUT lower bounds roughly 3–9× native, and completed 0/4 against native's 1/4 (0224).
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
  - a handoff note at submission, and a fresh execution session only when review requires repair, leaving native compaction settings unchanged (an unmeasured design hypothesis);
  - a helper-written task record;
  - R5's inventory kept;
  - an already-unreadable, wholly untracked environment directory may become a protected opaque baseline entry. Tracked, staged or adopted source and required verification inputs are not exempt, and new unreadability still causes refusal.
- **Self-compaction (owner message 4).** Root's vendor-documentation research identified these native compaction controls:
  - Claude Code: `autoCompactWindow` sets the threshold; a SessionStart hook with source `compact` can re-inject context (https://code.claude.com/docs/en/settings-reference.md, https://code.claude.com/docs/en/hooks.md).
  - Codex: `model_auto_compact_token_limit` and `compact_prompt` (https://developers.openai.com/codex/config-reference).
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
| O4 | A mechanism improves quality but costs some time or tokens | **Judge per success** (root recommended; Astra recommended strict sums). Count all run costs, failures included, per correctly completed task, and preserve quality. §6 proposes the operational admission rule |
| — | Baseline failure first | A design choice, not an owner decision: demonstrate a relevant baseline failure before repair when feasible; otherwise record why it is unavailable and provide meaningful behavioral coverage (Astra D4/D5) |
| — | Dependent tasks in ideate's local loop start from the accepted predecessor commit in a new owned worktree | Yes: root decided under the owner's delegation of architecture, with Astra concurring (D4, D6) |

## 6. Registration (stage 1)

**FROZEN 2026-10-05.** Astra's stage-1 readiness review (`stage1-app-v1-astra.out.md`) required four apparatus fixes, made in `a1d48e53`; its freeze verification is `stage1-freeze-v1-astra.out.md` (REVISE: the SMOKE criterion for I) and `stage1-freeze-v2-astra.out.md`. Any later change is a dated addendum at the end of this section.

- **Cells:** A/I/F × D3/D4/I0185 × claude/codex × 2 replicates = 36 measured cells, run one at a time in `experiments/0232/cells.tsv` order. Six SMOKE cells (`smoke.tsv`) run first and stay outside every sum and decision.
- **Arms**, the same way in both configurations:
  - **A:** the task repository as supplied, with no devlyn installation, and the native prompt (`common.txt` plus the caller contract).
  - **I:** the rung-1 package, installed offline by its own installer: the methodology block in CLAUDE.md/AGENTS.md and the review launcher `$HOME/.devlyn/review.js`. Same prompt as A.
  - **F:** 4.1.0 as in 0231. Its package (Claude settings included), resolve command, committed goal file and worker/judge machinery are all F's treatment. The four-round allowance (`--max-rounds 4`) belongs to F alone; A and I run natively.
  - **Common to all arms:** owner pins, image, environment, resources and the 5,400 s owner watchdog. Every arm's anchor starts with `origin/main` and `origin/HEAD` at the allocation commit. 0231's F construction lacked them, so these F results are not pooled with any earlier run.
- **Identities:**
  - I: `candidate/0232-rung1` at `5bf3dc740773851bee787a4f69c05b02ae0d62b6`; pack sha256 `3ee56995952ec6b4bf0335f37ba7161dee1f061ab7281b6a01c0752772225427`.
  - F: `4056ebe24cba16c03bc447a8fbd4bb92cbf21edb`; pack sha256 `48d21558e717a8b833b619d7ea696d07512cb78b6f29d13b0ccfb063ac263806`, file for file the published 4.1.0 tarball.
  - Image `devlyn-0231` `sha256:1a1c68897b18960e56f176ce03e8209f5b6c9950efc0d2631b7290d9de25a283`: Claude Code 2.1.281, Codex 0.156.1, Node 22.23.2.
  - Every cell gets the same frozen Codex models cache, sha256 `0968c49e13f086fb4211c5a1a2d20255f0bfd96ac8588054894f7956c885c794`.
  - Apparatus `experiments/0232/` at `5dbdd4b3`. Control-tree manifest digest `fcc5b8acb3bfcdc49e17c8da47ef07b55912fcd31b2c87d202ffd33948c9d633`; its public and oracle trees are identical to 0231's.
  - Routes (`experiments/0222/tasks.json`):
    - claude config: owner claude-opus-5-5 high; reviewer codex gpt-6-astra high;
    - codex config: owner gpt-6-astra high with native children gpt-6-sol high; reviewer claude-opus-5-5 high.
- **Evaluation.** Each cell yields one snapshot: F by its accepted-commit or task-worktree rule, A and I by the native rule in `DESIGN.md`. 0222's checks, oracle rows and blinded assessors grade it; completion is as in [0231](0231-bundle-live-comparison.md) "Metrics".
- **Usage.** Processed input (cache counted once) and output cover the owner, native children, F's workers and judges, and I's review launches. Gaps are named. A sum that is not COMPLETE is published as unknown, with its lower bound.
- **Methodology** is reported and never part of the rule:
  - I's compliance: a successful review by the registered other engine of exactly the final tree, against the allocation commit;
  - F's obligations: 0231's meter.
- **Decision rule (implements O4).** Each configuration is evaluated separately.
  - **Totals.** For arm X, S_X is the number of correctly completed cells under the frozen completion definition. W_X is total owner wall; I_X and O_X are total input and output over all six measured cells, failures included. They include all workers, reviewers, repairs, retries and resumed sessions, and count cache input without double counting. SMOKE and external evaluation are reported separately.
  - **Per-success costs.** w_X = W_X/S_X, i_X = I_X/S_X and o_X = O_X/S_X when S_X > 0; when S_X = 0 these costs are +∞ for selection only.
  - **Missing usage.** Unknown usage remains UNKNOWN. Accounting too incomplete to establish an inequality makes that comparison inconclusive. Input and output cannot offset each other.
  - **Admission.** Candidate C is admitted against the last admitted rung P (initially A) only if all of these hold:
    - S_C > 0;
    - each task's completion count and each check/oracle-row pass count is no lower than P's;
    - there is no false completion, scope violation, user-data harm or severe regression;
    - w_C ≤ w_P, i_C ≤ i_P and o_C ≤ o_P;
    - S_C > S_P, or at least one per-success cost strictly improves.
  - **Ties and zero success.** Increased completion with tied costs qualifies; equal completion with all three costs tied does not. A zero-success candidate never qualifies, even against a zero-success comparator. If I fails, P remains A.
  - **Incumbent replacement** additionally requires the same quality and safety conditions against F:
    - When S_F > 0: w_C ≤ 0.70 w_F, i_C ≤ i_F and o_C ≤ o_F.
    - When S_F = 0 < S_C: the per-success cost gate passes by dominance over the zero-success incumbent. That outcome is reported as such, not as a numerical percentage wall reduction, and no raw-sum comparison is substituted.
  - **Publication.** Raw sums, success counts and per-success costs are published together. They are observed selection results, not guarantees about future tasks.
  - The +∞ convention and the tie treatment are root and Astra's freeze wording, not owner decisions. The 30% threshold applies to incumbent replacement, not to every adjacent rung.
- **SMOKE must show:**
  - the registered routes and identities;
  - allocation from the mirror;
  - snapshot selection;
  - usage reconciled, or its gaps named;
  - in each I SMOKE configuration, at least one review by the registered other engine completes successfully: exit zero, native terminal success, a nonempty final answer, and its retained launch record;
  - clean teardown.

  A failed SMOKE blocks measurement. Final-tree compliance stays reported methodology there, and SMOKE requires neither product success nor full instruction compliance. The only pre-authorized treatment adjustment comes from Astra's readiness review: if the Bash tool's default two-minute timeout cuts off a Claude owner's review, I's block gains the instruction to run the review in the foreground with a 600000 ms timeout. That change is recorded as an addendum with its new commit and pack digest, and both I SMOKE cells repeat. Any other treatment change needs a separate registration.
- **Accounts:** cells run on the host's Claude and Codex logins. Each cell is behind 0231's preflight (fresh login, identity, limits and free space), except that the free-space floor is 8 GiB instead of 20 GiB. Root's monitoring and reviews share those accounts; no other model-heavy work runs during measured cells.
- **Faults:** as in [0231](0231-bundle-live-comparison.md) "Faults". One exception: I's review launcher has no deadline of its own. The owner's tool timeouts and the common owner watchdog govern it.
- **After stage 1:** later rungs, the easy-task panel and ideate's loop experiment are each registered separately, under this rule against the last admitted rung.

### Predictions (before any run)

**Root**, verbatim from `.devlyn/bundle/0232-root-predictions.md`. It was written on 2026-10-05, before anything was built or run.

Per configuration, over each arm's six measured cells (3 tasks × 2 replicates):

1. **Completions.**
   - A completes 1–2 cells on claude and 2 on codex.
   - I completes at least as many as A in both configurations.
   - F completes at most 1 in each configuration.
2. **I0185.** No arm completes it in either configuration.
3. **Wall.**
   - I's raw wall sum is 1.1–1.6× A's in each configuration, because of the review session and repair.
   - I's per-success wall is ≤ A's in at least one configuration.
4. **F's wall.** F's raw wall sum is ≥ 2× A's in each configuration. F has the worst per-success cost, or no successes at all.
5. **The review and input.**
   - I runs the cross-engine review in at least 10 of its 12 cells.
   - I's input per cell, review sessions included, is ≤ 1.5× A's.
6. **Decisions.**
   - I is admitted over A in at least one configuration: p ≈ 0.5.
   - The incumbent-replacement gate against F passes in both configurations: p ≈ 0.8.

**Astra**, verbatim from its stage-1 readiness review. Astra had not seen root's predictions.

1. In both configurations, raw owner wall will order **A < I < F**.
2. I will consume more raw input and output than A in both configurations.
3. I will complete at least as many cells as A in each configuration; I0185 will remain the largest completion risk.
4. I will fail admission or remain inconclusive in at least one configuration, principally because the per-success token inequalities are not established.
5. At least one I cell will pass product evaluation while failing the final-source review-compliance rule.
6. Passing the resource comparison against F will be easier than earning admission against A.

### Honest limits

- The tasks are exposed and n is small. Replicates are not a significance test.
- Results hold only for the pinned CLIs, image, tasks and routes.
- Compaction requests carry no native usage (0231 "Honest limits"). A compaction in a cell makes that cell's usage PARTIAL.
- The compliance meter's host-tree limits are listed in `DESIGN.md` "Tests and limits".

### Addendum 2026-10-05 — SMOKE round 1

SMOKE round 1 ran `smoke-claude-A`, `smoke-claude-I` and `smoke-claude-F`, then stopped.
- **A and I met their SMOKE criteria.** I's Codex review completed with exit zero, `turn.completed`, a nonempty answer and its record.
- **F stopped in the locator.** The operator loop had been launched from a directory under macOS privacy protection, so Git could not read its working directory.

Root then found three apparatus defects. None changes a treatment; each fix applies to every arm alike.

1. **Codex's Linux sandbox refused every command in the cells.**
   - Cause: `/tmp` was a host bind mount ("cannot establish app-server socket mount isolation").
   - Effect: I's Codex reviewer ran without tools. F's Codex judges and workers would have done the same.
   - Fix: `/tmp` is now a per-cell Docker volume, copied into the cell output after teardown (`cell.py`).
2. **The frozen models cache came from the host's Codex 0.160.0.**
   - Effect: 4.1.0's role check refused it against the pinned 0.156.1. F's pair judge was therefore BLOCKED before dispatch.
   - Fix: the pinned Codex 0.156.1 regenerated the cache, sha256 `c24e50cef6c1df5e78a964aede20823d7bd72827936b8dbb75ddb725b26c3c0e`. It replaces `0968c49e…`.
3. **The usage meter misread 4.1.0's files.**
   - Effect: it took 4.1.0's extracted judge text (`*.stdout`) for unreadable result envelopes, and it missed SURFACE_CLOSE's envelope. F's usage read PARTIAL when it was complete.
   - Fix: envelopes are the `*.output.json` files (`evidence.py`).

The operator loop now starts from its runtime directory.

**Identities after this addendum:**
- apparatus `92c6571e`;
- models cache `c24e50ce…`;
- everything else unchanged.

SMOKE repeats in full. Round 1's evidence stays in `0232-live/out/smoke-round1/`.

### Addendum 2026-10-05 — SMOKE round 2 passed

SMOKE round 2 used apparatus `92c6571e` and models cache `c24e50ce…`. All six cells exited 0 with a recorded verdict.

**Every criterion holds:**
- **Identity:** MATCH in 6 of 6 cells.
- **Allocation:** each F run's `base_ref` equals the allocation commit, in both configurations.
- **Snapshots:** one per cell.
- **Usage:** 5 cells COMPLETE. `smoke-codex-I` is PARTIAL with one named gap: a Codex parent's in-flight request was cancelled when its child messaged it ("response stream dropped before provider terminal event"), so it has no native usage.
- **I's review** completed in both configurations, each with its record:
  - claude config, Codex reviewer: exit 0, `turn.completed`, a nonempty answer, and its own unittest rerun;
  - codex config, Claude reviewer: exit 0, `subtype: success`, `is_error: false`, a 1,561-character answer.
- **Teardown:** clean in all cells, with no surviving volume.

The pre-authorized timeout adjustment was not needed: no review command timed out or moved to the background.

Astra reviewed the round-1 fixes (`smoke-r1-fix-astra.out.md`, SHIP) and recommended two follow-ups. Both are made in `a8b18137`, with no change to a normal run:
- the teardown record decodes a timeout's byte stderr;
- the `/tmp` volume test now covers a linked worktree, a symlink, an executable mode and a skipped socket.

Measured cells use apparatus `a8b18137`.

**Added honest limit:** like compaction requests, cancelled Codex inferences carry no native usage. Each one makes its cell's usage PARTIAL. In the codex configuration that can leave token tests inconclusive.

### Addendum 2026-10-05 — measured run: an assessor fault and its regrade

**The fault.** The drive stopped at `m07-D3-claude-F-r1`: assessment failed with `[Errno 17] File exists`.
- Cause: the assessors' review tree copied the snapshot over a checkout of the allocation commit. That checkout already held commander's tracked fixture symlinks, and a symlink cannot be copied over an existing one. Every D3 cell would have stopped the same way.
- Fix (`cce71305`): every tracked file is removed before the copy.
- D4 and I0185 track no colliding symlink, so their review trees are unchanged and the assessments of `m01`–`m06` stand.

**The regrade.** Per 0231 "Faults", an assessor-only fault is regraded from preserved evidence, never re-dispatched.
- `run_cell.py --regrade` now runs the same `grade` path that a cell runs, and keeps the STOP verdict as `.stop-1`.
- `m07` regraded to COMPLETE. Its execution record, snapshot and checks are unchanged.

From `m08` on, cells use apparatus `cce71305`. That change affects only the assessment tree and the regrade.

**A measured observation, not a fault.** In `m02-D4-claude-I-r1` the Claude owner started the required review with `run_in_background: true` and a 600000 ms timeout. It said it would pick up the findings when the review finished, then ended its session. Headless Claude Code terminates background tasks at the final response, so the review was killed before it answered.
- Compliance records "failed review", and the killed reviewer's usage is a named gap, so the cell's usage is PARTIAL. Its product verdict is COMPLETE.
- This is not the pre-authorized contingency, which covers a cut-off by the default two-minute timeout. The treatment stays frozen.
- Such cells are evidence about rung I, a failure that can license a later rung.

### Addendum 2026-10-05 — venue change at m11

**What happened.** After `m10`, the host's Claude login changed. The preflight refused `m11` with "account/organization mismatch", as 0231's rule requires: the account never switches automatically.
- Before: account `cc43a4e02ede`, organization `2905f4abf05b`.
- After: account `45eff57aaa45`, organization `b6b7768fd228`, `claude_max`, rate tier `default_claude_max_20x`.

**What root did.**
- Recorded the switch as a venue change.
- Set the runtime's account to the new fingerprint.
- Resumed from `m11`.

`m01`–`m10` ran on the first account, and `m11`–`m36` run on the second. Models, CLIs, image, apparatus and treatments are unchanged. The balanced cell order puts every arm on both accounts. The account change can affect only wall time, through provider-side throughput, and RESULT reports it per cell.
