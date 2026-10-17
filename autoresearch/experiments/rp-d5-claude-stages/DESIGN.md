# rp-d5 design — where Claude's delivery time goes

DRAFT for design review (round 1). Research only: no product change, no
release. Round 0: Astra ultra REVISE, Grok 4.7 REVISE
([Astra](results/design-r0-astra.md), [Grok](results/design-r0-grok.md));
every finding is applied below.

## Why

On the same small tasks Claude spends far more than Codex. The rp-d4 Claude
guard slots (arm Y, the stopped helper-sentence candidate on 4.2.22) took
423 s and 448 s, 1.46M and 1.62M input, 37k and 40k output; the eight rp-d4
Codex slots took 92–184 s, 0.33–0.76M input, 4–6k output. rp-d1 measured
Claude at 778 s, 2.55M input and 74.6k output per report-graded success.
These are motivation, not a control.

The retained rp-d4 receipts already split the guard tokens (0254 accounting):

| Slot | Terminal turns | Thinking / output | Uncached input | Cache read | Cache write |
|---|---:|---:|---:|---:|---:|
| g01 BV | 23 | 29,289 / 36,686 (80%) | 46 | 1,366,684 | 92,223 |
| g02 Z0 | 28 | 31,382 / 39,814 (79%) | 56 | 1,544,695 | 71,554 |

So the output gap is mostly thinking (non-thinking output 7.4k and 8.4k,
near Codex's 4–6k), and the input gap is the same growing context re-read on
each of 23–28 turns. What the receipts do not hold is which tool step each
turn served, or how the turn count and thinking change with effort. The
benchmark pins Claude at effort `max` and Codex at `high` (rp-d1
`tasks.json`); the 2026-10-07 host investigation reported max effort as a
default costing about 8× on a small task through extra exploration turns
(record outside this repository; not re-verified here). Raw transcripts of
earlier runs were deleted, so a new run is needed.

## Question

On BV and Z0 under the shipped 4.2.22 (rp-d4 X), how do Claude's turns,
marginal tokens and wall time split across delivery stages at effort `max`
and at `high`, and which stages, if any, contain repeated devlyn-caused
operations that change no outcome?

The Codex gap is not attributed: only within-Claude, within-task max/high
deltas are reported.

## Prediction (frozen before the run)

> On each task, the `max` slot has more terminal turns and more thinking
> tokens than the `high` slot, with the same delivery outcome.

## Runs

Registry `devlyn-cli@4.2.22` (rp-d4 X: same tarball, image definition,
tasks BV and Z0, `common.txt` prompt unchanged). Claude Code 2.1.296,
`claude-opus-5-5`.

| Slot | Task | Effort |
|---|---|---|
| c01 | BV | max |
| c02 | BV | high |
| c03 | Z0 | high |
| c04 | Z0 | max |

Four serial slots in this order; the Z0 crossover offsets order effects. No
Codex slots. **Effort binding:** every sealed request body's
`output_config.effort` must equal the slot's effort; a mismatch STOPs the
run before the next slot.

**Failure handling.** Every dispatched slot is kept with its costs; none is
replaced. Delivery is graded as in rp-d1 (scope and regression checks,
exactly one correctly merged PR, preserved user files); the report is not
graded. rp-d1 o08 showed the unchanged prompt can lead Claude to stop at
`LOCAL_ONLY`; such a slot is a failed delivery. If the two slots of a task
differ in delivery outcome, that task's effort delta is reported but no
efficiency conclusion is drawn from it, and a failed slot yields no removal
candidate. A STOP, UNKNOWN usage or an unreconciled slot (below) is
reported as UNKNOWN for the affected numbers.

## Accounting (reuse 0254; no new token accounting)

- **Turns.** One row per terminal assistant message (`stop_reason` set),
  the last copy of each message id, from the parent project JSONL and any
  `subagents/agent-*.jsonl`, each subagent row tied to its parent `Agent`
  call. Provisional lines are never summed.
- **Tokens.** Per row: uncached input, cache read, cache write, output and
  thinking (`usage.output_tokens_details.thinking_tokens`, an integer ≤
  output, already inside output). Row sums must equal the slot's audited
  0254 totals, or the slot's token figures are UNKNOWN.
- **Marginal cost.** A stage's marginal tokens are its rows' output plus
  cache write. Cache read is reported per turn as a series, never charged
  as a stage's cause; dropping a turn would save its output plus the cache
  reads of later turns, which the write-up states only as an estimate.
- **Wall.** Each request's span runs from its `api-bodies/index.jsonl`
  timestamp to the next request's timestamp; it covers that inference plus
  the tool execution it triggered, and is charged to that row's stage. The
  leading residual (launch to first request) and trailing residual (last
  request to owner exit) are explicit rows. Stage walls plus residuals must
  equal `owner_seconds` within 1 s, or the slot's wall split is UNKNOWN.
  Deliver wall includes GitHub round-trips and is reported as is.
- **Cold cache.** c01 is the first slot. The first request's cache write and
  wall are shown as their own line and excluded from every effort delta.

## Stage attribution (closed table, frozen before the run)

Each terminal row is classified by its tool calls with these predicates:

| Stage | Tool calls |
|---|---|
| Orient | Read/Grep/Glob of `CLAUDE.md`, `AGENTS.md`, `.claude/skills/**`, `.agents/skills/**`; engine preflight scripts |
| Explore | Read/Grep/Glob of task paths before the first mutation |
| Edit | Edit/Write/NotebookEdit; Bash whose argv writes task files (`tee`, redirection, `sed -i`, `patch`, `git apply`) |
| Verify | Bash test commands (`pytest`, `python -m pytest`, `python3 -B -m pytest`, task check scripts); Read/Grep of task paths after the first mutation |
| Deliver | Bash `task-complete.py` (allocate, accept, complete), `git add/commit/push/worktree`, `gh` before the successful `complete` result |
| After delivery | any call after the first `complete` result whose status is `COMPLETE`, `CLEANUP_PENDING`, `PR` or `PENDING` |
| Report | the last terminal row with no tool call |
| Other | any other tool or command, and any non-final row with no tool call |

The first mutation is the first row classified Edit. A row whose calls fall
in two stages is **Mixed**, listed with its stages and costs and never
eligible for a candidate. Rules are tested on synthetic JSONL and on the
retained 0254 test fixtures before the run and are not changed after it.

## Removal hypothesis rule (frozen)

A concrete repeated operation (not a whole stage) is nominated only if all
hold, in both tasks at the same effort:

1. its rows are not Other or Mixed;
2. each counted row repeats a tool call whose paths and exit status the
   trace shows already succeeded earlier in that slot, with no edit, rebase
   or copy to those paths in between;
3. the repeated call is not required by the installed delivery
   instructions at that point (the write-up quotes the instruction it
   follows, or shows none applies);
4. its marginal tokens are at least 15% of the slot's marginal tokens, or
   its rows are at least 15% of the slot's terminal turns;
5. if it is claimed to be independent of effort, the `high` slot of each
   task has it too, at no less than half the `max` slot's rows.

If wall and marginal tokens disagree, marginal tokens decide. If several
qualify, the largest marginal-token share is nominated. Ties go to the
earlier stage in the table. The nomination is a hypothesis for a later
registered experiment; this run adopts nothing. If none qualifies, the
result says so and reports the observed effort deltas. Effort is a user
setting: a large effort delta is reported, and whether future benchmarks
pin Claude at `high` is a separate owner decision.

## Apparatus

Reuse rp-d4's runner and rp-d2's Claude path by path (auth snapshot,
6300 s floor, identical-account renew, Claude token scan before sealing,
`merge_refused` byte scan). New code only: the four-slot schedule with the
effort binding, `attribute.py` (built on the 0254 audit receipts) and offline
tests. Fresh run ID, four private repositories, a fresh fine-grained PAT,
benchmark hard rule 5 (fixed network, VPN client apps quit, route watcher),
image prune guard. Evidence stays until the analysis is reviewed.

## Interpretation limits

One slot per task per effort. The split is what these four runs did, not a
rate. Wall per stage includes model latency, which the harness does not
control. A nominated operation is a hypothesis, not a proven saving.
