The cited totals match the sealed results. The question family is right, and four Claude slots are enough, but this draft would not produce a stage split you can act on. Revise the question, the attribution function, and the removal rule before a run.

The rp-d4 figures match `results/measured/summary.json`: g01 is 423.2 s, 1,458,953 input, 36,686 output; g02 is 447.5 s, 1,616,305 input, 39,814 output; the eight Codex slots are 91.7–184.2 s, 330,245–764,671 input, 4,439–6,082 output. rp-d1 Claude per success is 778.5 s, 2,554,664 input, 74,601 output. `tasks.json` pins Claude at `max` and Codex at `high`. The ladder rule in `NORTH-STAR.md` is tokens and wall per success, failures included, and a mechanism that fails it is removed.

Those same verdicts already decompose the Claude tokens. Tool names and timestamps are gone with the cleaned-up transcripts, so a run is still required for stages and for effort. It is not required to learn where the tokens went.

| Slot | Terminal turns | Thinking / output | Uncached input | Cache read | Cache write |
|---|---:|---:|---:|---:|---:|
| g01 BV | 23 | 29,289 / 36,686 (80%) | 46 | 1,366,684 | 92,223 |
| g02 Z0 | 28 | 31,382 / 39,814 (79%) | 56 | 1,544,695 | 71,554 |

Headline input is uncached + cache read + cache write (`0232/record_usage.py`). Cache read is 94% and 96% of it. Non-thinking output is 7,397 and 8,432, next to Codex’s 4–6k. Both slots have `agent_id: null` and no launched child session. The output multiple is thinking. The input multiple is the same growing context (about 12k to about 90k) re-read on every turn.

## HIGH

**1. The Codex-gap fraction is not identifiable, and the token composition does not need a new run.** "How much of the gap disappears at `high`" uses rp-d4 Codex totals from another day as the denominator. Those eight slots already span 92–184 s, they mix the X and Y arms, and the Claude numbers being explained are the Y guards. The new run is the shipped X tarball. A same-day Claude drop can be provider latency, the cold first slot, or effort. Keep Codex out of the schedule. State the question as: on BV and Z0, how do Claude’s turns, marginal tokens, and wall split across stages at `max` and at `high`? Report the within-Claude delta. Leave the rp-d4 Codex range as history. Put the table above in the design so the run is aimed at tool identity and effort, which the verdicts do not contain.

**2. Assigning a turn’s cache read and thinking to that turn’s tool does not measure the stage.** Each terminal message’s `input_tokens` is 2. The large number is `cache_read_input_tokens` of the whole prefix so far. Later stages will look expensive because the transcript is longer. Thinking is already inside `output_tokens` (`usage.output_tokens_details.thinking_tokens` in the 0254 receipt; g01’s last turn is 1,058 output of which 11 is thinking, while an earlier turn is 6,120 of which 5,906 is thinking). Labeling the whole gap by the tool call charges model thinking to Orient, Explore, or Deliver. Freeze the stage row as turns, cache write, uncached input, output, and thinking. Keep cache read as a per-turn series, not a stage cause. The predicted saving of dropping a turn is that turn’s output plus the cache reads later turns would not re-send. Require the marginal sums to equal the slot’s 0254 totals, or mark the slot UNKNOWN.

**3. The taxonomy is not yet a function of the sealed Claude records.** `0254/test_audit.py` shows the carriers this runner seals: the project JSONL holds `message.content[]` tool blocks and terminal usage; `api-bodies/index.jsonl` holds the request timestamp; the request body holds `output_config.effort`. The project row in that fixture has no timestamp. `0238` shows a provisional assistant line for the same message id with `stop_reason` absent and a smaller usage; only the terminal line is counted. Subagent transcripts live at `projects/.../subagents/agent-*.jsonl` with `parentSessionId`. A max-effort exploration that uses `Agent` would put the tokens there. The parent g01/g02 slots happened not to. Bash is unclassified, and a prior max-effort audit in `0247` was mostly Bash. "The later stage wins" has no closed order once Bash can test and commit in one call. Turns with no tool call, other than the final one, have no stage. The last turn has no next timestamp.

Freeze this before any synthetic test, and do not retune it after the run:

- One row per terminal assistant message (`stop_reason` set), last copy of each message id. Summing every JSONL line is UNKNOWN.
- Wall comes from consecutive `api-bodies/index.jsonl` timestamps. The slot’s leading and trailing residuals are explicit. Stage walls plus residuals equal `owner_seconds`, or the slot is UNKNOWN.
- Include subagent JSONL in the same totals, tied to the parent `Agent` tool call.
- Closed tool table, in this order: Orient (Read/Grep/Glob of `CLAUDE.md`, `AGENTS.md`, skill and `_shared/*.md`, and engine preflight), Explore (Read/Grep/Glob of task paths before the first mutation), Edit (Edit/Write/NotebookEdit, and a Bash command whose argv writes), Verify (test commands, and reads after the first mutation), Deliver (`task-complete.py`, git commit/push, `gh`), After delivery (those same calls after the `complete` result), Report (the last terminal message with no tool call). Any other tool, any no-tool message that is not last, and any Bash command outside that argv list go to Other. Other is ineligible for a candidate. A message with tools in two stages takes the later stage in the order above. The first mutation is the first terminal message in Edit.
- Thinking is the receipt field above, must be an integer ≤ output, and is not added to output.

**4. The removal rule can nominate a stage the harness cannot honestly drop.** "Caused by devlyn" is a reading of the turn, with no second reviewer and no conflict rule. "Tokens" is undefined, so cache read, thinking, or output can each clear 15%. "Largest" is undefined when wall and tokens disagree. "Both max slots or both high slots" treats BV and Z0 as replicates and still qualifies a stage that exists only at `max`. "Not by effort alone" has no numeric comparison. "Changes no delivered outcome" treats a second passing check, or a second read, as removable even when `task-completion.md` required the check. The later-stage rule hides a repeated read that shares a message with an edit inside Edit, which then fails the outcome test.

A stage is eligible only when all of these hold on both tasks at the same effort: it is not Other; its marginal output plus cache write is at least 15% of that slot’s output plus cache write, or its turn count is at least 15% of the slot’s turns; the high slot on that task has that stage below half the max slot’s turn count and marginal tokens when the claim is "not effort"; every counted turn is a repeated tool use whose paths and exit status the trace shows were already successful earlier in that slot; the repeated command is not named by the installed delivery instructions. If wall and marginal tokens disagree, marginal tokens win. If more than one stage is eligible, the larger marginal-token share is the hypothesis. The write-up calls it a hypothesis for a later registered experiment. This run adopts nothing. A slot whose delivery fails produces no candidate.

## MEDIUM

**5. c01 is the cold cache.** The schedule is BV `max`, BV `high`, Z0 `high`, Z0 `max`. g01’s first message is cache write 18,443 and cache read 0; later messages only read. BV’s `max` slot pays the cold start, and BV’s `high` slot does not. Exclude the first request’s cache write and its wall from the effort delta, and show it as its own line. The Z0 order already reverses effort, so keep the crossover.

**6. Pin the effort receipt.** The binding check is every sealed request body’s `output_config.effort` equal to the slot pin (`0254/test_audit.py` records that field). An argv flag alone does not show what was sent. A mismatch stops the run before the next slot.

## LOW

**7. Label the historical rows.** The 423 s and 448 s rows are rp-d4 Y guards on 4.2.22; this run is the X tarball, which is the shipped product after the helper sentence was stopped. Say that in the Why section. Point at `slowness-investigation.json` for the 8× claim; that file is not in this worktree, and `HANDOFF.md` uses it for the delivery-scope decision. Deliver wall includes `gh` and GitHub, so record it as its own residual inside Deliver.

Effort is the right second factor: the retained slots are thinking-heavy and many-turned, which is what that setting changes. Four serial slots, full sealed evidence, delivery graded as in rp-d1, and no product change are the right size. Codex does not belong in the schedule once the result is a within-Claude delta.

VERDICT: REVISE
