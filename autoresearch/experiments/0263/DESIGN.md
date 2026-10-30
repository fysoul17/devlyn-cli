# 0263 design — independent acceptance look for user-facing changes (candidate D)

Status: revised after design-check round 2. Astra ultra and Grok 4.7 both asked for controller custody of the verdict, a defined repair transition, an equal delivery boundary and re-rated denominators. Nothing is implemented or measured.

## Why

0262 rejected C, the self-observation loop ([RESULT](../0262/RESULT.md)).
- C looked at the screens and claimed done on 16/16 runs; the owner rejected 30/32 outputs, mostly for polish.
- The executors claimed done on 25/32 in all.
- Fresh AI raters holding only the request, the captures and an explicit bar agreed with the owner far more often: Astra ultra 28/32 with 3 missed rejects, Opus 5.5 24/32 with 7.
- In the direct Claude→Codex route, the Claude orchestrator was a different engine from the implementer, saw C's captures, and still claimed done on all four C runs. The owner rejected all four.

The working hypothesis (0262 did not isolate it): the gap is who decides "done" and against what bar, not access to the screen or engine diversity.

## Candidate D, one rung

The done decision for a user-facing change moves from the session that builds and delivers it to a fresh, read-only reviewer that sees only the request, the captures and a written ship bar. The capture transport D needs comes from C and is declared part of this candidate: a pass adopts both, a fail adopts neither. There is no third arm.

**Invariants**
1. **Who decides.** A user-facing change is done only on a `ship` verdict from a reviewer session that:
   - did not build or deliver it;
   - is read-only;
   - is fresh, never resumed and with no shared context.
2. **What the reviewer sees.** Only these three inputs:
   - the original request, verbatim from the task packet or the user's message;
   - the captures, each labelled with its state, width or platform;
   - the ship bar.

   The reviewer never sees the diff, the executor's report or reasoning, a proposed verdict, or engine identity.
3. **Reviewer engine.** Codex (GPT) when it is installed: it was measured closest to the owner, and Claude-family rating missed more on Claude-made output. Otherwise a fresh session of the engine that is available. The verdict records the engine, model and effort. There is no symmetric "the other engine checks" rule: the Claude→Codex route already shows a different engine is not sufficient.
4. **Bound.** A drain keeps one executor process.
   1. The first review request returns `ship`, or `send back` with defects verbatim in the spool reply.
   2. On `send back`, the same executor repairs and recaptures the complete packet, not only the affected states, then asks once more.
   3. A new fresh reviewer session judges the repaired source.
   4. The controller refuses a third request. Round two requires a different source SHA, at least one changed image digest and all labels from the original packet; another request after a bound ship is refused without changing that ship. Validation or discovery failures before launch spend no attempt and remain correctable; an unknown outcome after launch is terminal.

   In direct work, `complete` reviews once. On `send back`, the delivering session gets the defects, makes one repair, recaptures, and calls `complete` once more. A second `send back` ends as `NOT SHIPPABLE` with the defects. No reviewer shopping, no dialogue.
5. **Custody.** The controller launches the reviewer and keeps its result. No worker-supplied file or argv confers a verdict. The controller is `queue.py` in a drain and `task-complete.py` in direct delivery.
   - **Flag.** A `user_facing` flag, with the verbatim request, is fixed before the working session starts:
     - drain: from the committed task contract, copied into the packet;
     - direct: by the environment that starts the session. `DEVLYN_USER_FACING=1` (or repository-local `git config devlyn.userFacing true`) makes `allocate` record the flag and refuse to allocate without a request file.

     The executor cannot clear the flag: `source_problems` already rejects package edits, and `complete` has no API to unset it. The 0263 pilot driver sets it for every D run before the session starts.
   - **Drain review.** The executor asks for a review through the existing spool with a fixed request kind that carries no argv and no prompt. `observer.py` refuses to exec it, and `queue.py` handles it beside its spool pump.
     - `queue.py` spawns a fresh read-only reviewer using the shared unattended-tool guard and native process monitor, completing discovery before recording an attempt. The reviewer sees the committed request bytes, the capture inventory with digests and `_shared/ship-bar.md`.
     - The reviewer's verdict is bound to the task, the round, the source SHA it judged, the request digest and the capture digests.
     - `queue.py` keeps the verdict list itself and hands it to `acceptance.py`.
   - **Drain acceptance.** For a user-facing task, `[x]` requires the last controller verdict to be `ship` and bound to the owned branch head. Any other ending is `needs-review`, even with no blocker in the submission: a missing review, a second send-back or an empty capture inventory.
   - **Drain restart.** The attempt count, every verdict and any terminal rejection persist in controller-owned drain state, in the controller’s OS-home `~/.devlyn/acceptance-looks/<sha256 of absolute common Gitdir>/<receipt id>/` (0700), outside repository and executor writable roots. The flag, request digest and absolute reviewer/interpreter commands are fixed there at allocation; receipt/packet copies must agree. A sandboxed executor cannot write this custody; deliberate outside-file forgery by unsandboxed execution, including observation commands, is outside the trust model. A restart reads that state: it never re-opens a candidate rejected twice, and it never adds a review beyond the bound. If recovery cannot establish the state, the task fails closed as `needs-review`.
   - **Direct delivery.** `complete` spawns the same reviewer when the receipt is user-facing. It reviews the accepted source with the request recorded at allocation and the captures under the evidence directory. A caller-supplied verdict is ignored, and a non-`ship` result reports `NOT SHIPPABLE` and does not publish as done.
   - **Residual.** Direct work with no delivery stays prompt-controlled, as does direct work where nothing set the flag before the session and the session never declares it.
   - **Launch isolation.** The reviewer runs read-only in its external capture snapshot, with no repository instructions and none of the executor's context. Codex uses a private auth-only HOME/CODEX_HOME and supported `--ignore-user-config`/`--ignore-rules`; only its reviewer environment drops `CODEX_BLOCKED`. The recorded Claude fallback uses verified safe/restricted mode, empty setting sources and strict empty MCP configuration. Help and dry argv are checked before launch. Reconciliation requires the same source/request/capture-bound ship before cleanup or COMPLETE.
6. **The ship bar** is `_shared/ship-bar.md`. It is the 0262 rating guide, registered before any 0262 rating and untouched by the owner's 0262 notes:
   - "A developer brought this as done; would you ship it as is?"
   - Reject if any of these holds: something requested is missing on screen; it is hidden or hard to find on a narrow window or phone; anything is broken, overlapping, cut off, oddly line-broken or awkwardly laid out; it departs from the request's intent.
   - Otherwise ship; minor taste differences ship.
   - Every defect names the capture it is visible in.
   - A target state the request names (a width, platform, error state or journey step) with no labelled capture is a send-back.

**Delete from C:** the executor's own compare-and-repair as the path to done. That covers the Observation bullet's "compares the captures with the original request; repairs and rechecks", identical in CLAUDE.md, AGENTS.md and runtime-principles.md, and "the implementer judges" in `adapters/codex.md`. The executor still captures every requested journey and may fix what it sees before asking for review.

**Keep from C:**
- `observer.py` as capture transport only where a sandbox blocks the executor. It never runs a review;
- evidence retention;
- the `NOT OBSERVED` gap rule.

**Files:**
- `queue.py`: review request handling, reviewer spawn and the verdict list;
- `acceptance.py`: the user-facing `[x]` rule;
- `task-complete.py`: the flag from the environment or Git config at `allocate`, a persisted attempt count, and the review on `complete`;
- `observer.py`: refuse the review kind;
- `_shared/ship-bar.md` (new);
- `loop.md`, `task-completion.md`, `package-format.md`: the `user_facing` field;
- `adapters/codex.md`;
- the Observation bullet in `CLAUDE.md`, `AGENTS.md` and `runtime-principles.md`;
- tests in `scripts/test-ideate-loop.py` and the helpers' self-tests.

**Not in D:** planner-declared journeys, a per-surface cookbook, a symmetric engine-pairing rule, an AI rater replacing the owner.

## Pilot (owner replays, owner blind rating)

- **Runs.** 16 D runs on 0262's apparatus: T1/T2 × 4 routes × 2 replicates, the same clone starts and the same driver policy as 0262's B runs.
- **Comparator.** 0262's 16 B outputs and their costs. They are reused only where the clone start SHA and driver policy match D's run; a mismatched B output is unscored. Product changes merged since 0262 (the unattended-tool guard) are listed.
- **Delivery boundary, equal across routes.** D counts as delivered only with a final source-bound `ship` and route completion. Drain acceptance and direct `complete` are both required; a bare local commit is not enough. B keeps 0262's boundary.
- **Blocked candidates.** D's blocked final candidates are captured and rated in the same blind packet. They count as a false-rejection diagnostic, never as CC.
- **Rating.**
  - The owner re-rates B and D, 32 outputs, blind and mixed on the improved 0262 page. C is excluded.
  - B's earlier ratings are reported only as drift.
  - The AI raters rerun on the packet as a secondary measure.
- **Definitions (as in 0262).**
  - CC = delivered ∧ witness PASS ∧ checks pass ∧ owner accept.
  - claimed_done: blind majority classification of the report. `NOT SHIPPABLE` and `needs-review` are not claimed done.
  - FC = claimed_done ∧ (witness FAIL ∨ checks fail ∨ owner reject).
  - Tokens and wall include the reviewer sessions and failed attempts.
- **REJECT D if any of these holds,** with both arms' CC recomputed from the new blind ratings:
  - (a) D CC < B CC on either task;
  - (b) D FC > B FC on either task;
  - (c) a D safety violation;
  - (d) D has zero CC;
  - (e) with B CC > 0: D's tokens per CC exceed B's, or D's wall per CC exceeds 1.5× B's.

  If B CC is 0 and D CC is positive, the per-success ratios are undefined and are not scored as passed. The raw token and wall ratios are reported beside the decision, and the owner weighs them. Missing usage is INCONCLUSIVE.
- **Not rejected:** the owner decides. A pass on these exposed tasks licenses a held-out confirmation (two new replays, fresh B and D), not general adoption.
- **Predictions, frozen before any D run:**
  1. D FC ≤ 3 of 16.
  2. 2 ≤ D CC ≤ 5.
  3. D raw tokens ≥ 1.5× B's.
  4. At least one D task ends `NOT SHIPPABLE`.
  5. Owner drift on B ≤ 2 of 16 changed verdicts.

## Risks

- **0236:** findings-driven repair confirmed 1 of 8 repairs on code tasks. The single repair round may add cost without lifting completions. Prediction 2 and rule (d) test it.
- **The owner's bar.** The owner accepted 2/32 in 0262. If D's repairs cannot reach the bar, D lowers false completions without raising correct ones, and rule (d) rejects it.
- **Overfitting.** The ship bar is the pre-registered guide, not the owner's notes on these outputs.
