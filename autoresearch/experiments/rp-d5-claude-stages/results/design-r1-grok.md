Round 0 is applied on the question, the token composition table, the Codex exclusion, the frozen prediction, terminal-receipt accounting, the effort binding, failure retention, and Mixed. Three round-0 fixes did not become a function of the records.

A run is still required. The g01/g02 receipts have usage and ids, and no tool name, path, or timestamp. Effort is the right second factor: those slots are 23–28 turns and about 80% thinking, which is what `max` versus `high` changes. Four serial Claude slots are the smallest design that separates task from effort. Same-day Codex slots would not identify a stage.

0254 can supply the token rows as written. `audit.py` keeps one native terminal body per message id, requires `thinking_tokens` to be an integer no greater than `output_tokens`, folds foreground children into `totals`, and checks every request's `output_config.effort`. Row sums have to match `totals`, where `input_tokens` is the uncached count. The headline `input_tokens` on the report is uncached plus cache read plus cache write. Tool identity is not on the receipt. It is on the terminal response body, joined by `message_id` through `api-bodies/index.jsonl`. The retained `0254` fixture cannot prove the stage table: its only tools are `Agent` and Bash `true`, and all three index timestamps are identical.

## HIGH

**1. The stage table is not a total function of a terminal tool call.** `0247`'s max-effort owner was 36 Bash, two Read, three Write, and one Edit. This table's Bash write rule is an example list (`tee`, redirection, `sed -i`, `patch`, `git apply`). `0234/diagnostics.py` already shows why that scan is wrong: a `>` inside a heredoc is not a write, and observed writes also include `cp`, `mv`, and `write_text`. One Bash string can contain both `python3 -B -m pytest -q` (the actual public check in `tasks.json`) and `git commit`. Mixed is defined for two tool calls, so that row has no class. Read-only git (`status`, `diff`, `log`, `show`) is unnamed, so it becomes Other.

The first mutation is "the first row classified Edit." A Mixed row that contains the write does not start it, so later reads stay Explore and Verify never starts. Orient names `.claude/skills/**` and `.agents/skills/**` and drops `_shared/*.md`, which is the path `CLAUDE.md` and the Claude fixtures actually read (`_shared/task-completion.md`). "Task paths" and "engine preflight scripts" are undefined. Glob after the mutation is not Verify. Report is "the last terminal row," with no order once a child transcript exists.

`task-complete.py` returns `PENDING` or `PR` when the PR is not merged, and `COMPLETE` or `CLEANUP_PENDING` when it is. The design opens After delivery on the first of all four. The first poll then swallows the later merge, and any fixup edit, into After delivery.

Freeze this function and test it before the run. Do not retune it after.

- Order is `index.jsonl` order. One row per 0254 receipt. Tools come from that message's terminal response `content[]`, not from provisional JSONL lines.
- Normalize paths. Orient is `CLAUDE.md`, `AGENTS.md`, or any path whose suffix is under `skills/` or `skills/_shared/`. A task path is any other cell worktree path. Engine preflight is the named script, or it is Other.
- After heredoc stripping, a Bash string that matches two stage predicates is Mixed. The write matcher is one closed list covering redirection, `tee`, `sed -i`, `patch`, `git apply`, `cp`, `mv`, and an in-process file write. Read-only git is Explore before the first write and Verify after. The public check matches the `python3 -B -m pytest` prefix, including `-q`.
- The first mutation is the first row that contains a write, including a Mixed row. Later Glob of a task path is Verify.
- The After-delivery boundary is the first `complete` stdout object whose `status` is `COMPLETE` or `CLEANUP_PENDING`. `PR`, `PENDING`, `LOCAL_ONLY`, `FAILED`, and `BLOCKED` do not open it. Unparseable stdout leaves that boundary unknown.
- Report is the last index row with no tool call. An earlier no-tool row is Other. A parent `Agent` row does not take the child's class.

**2. The wall partition does not use the clock that produced `owner_seconds`.** `0251/cell.py` sets `started_at` before `docker create`, measures `owner_seconds` with `time.monotonic()` around `docker start -a` only, and sets `ended_at` after that wait. Treating `started_at` as launch puts create time into the leading residual, the 1 s check fails, and every wall split is UNKNOWN. `0254` does not read `timestamp`. The index row names both the request file and the response file, so the field is a property of the completed exchange. The design still says the span covers that row's inference plus the tool it triggered. Those two readings charge generation to opposite stages. Child rows sit in the same index (`0253` audit: owner, child, owner). "Next request" has to mean the next index row. The named pre-run fixture cannot catch this, because its timestamps are equal.

Seal the absolute start of the monotonic interval, use the existing `ended_at`, and keep `started_at` out of the residual. On the retained 0253 capture, record whether `timestamp` is request-logged or response-logged, and freeze that one reading. Strictly increasing global index order is required. An equal or backwards timestamp makes the wall split UNKNOWN.

**3. The removal key can be chosen after exposure.** "A concrete repeated operation" has no identity. Three re-reads at 6% of marginal tokens fail the 15% bar alone and clear it as a family. The bar is also an OR of marginal tokens and turn share, and the two tasks need not clear the same one. "Shows none applies" is still an essay over `task-completion.md`. Bash success is not a field on the assistant message. `0234/diagnostics.py` scrapes the exit code from the tool-result text. Read success is `is_error` false.

Freeze the key as tool name plus normalized path set, or the heredoc-stripped command. A family cannot be nominated. Both tasks must clear 15% of that slot's marginal tokens. Required commands are a list taken from the installed instructions before the run. Success is exit code 0 for Bash and `is_error` false otherwise. An intervening write uses the same matcher as Edit, including Mixed rows. The nomination stays a hypothesis, and this run still adopts nothing.

## MEDIUM

**4. Subtracting only c01's first request biases the effort delta.** g01's first receipt is cache write 18,443 and cache read 0. g02's first receipt is cache write 6,422 and cache read 12,030, so the later slot was already partly warm. The schedule runs BV `max`, BV `high`, Z0 `high`, Z0 `max`. Removing the cold write from BV `max` only, while Z0 `high` still pays whatever cold start it has, moves both marginal-token and wall deltas toward `max`. Turn and thinking deltas are unaffected, and those are the prediction.

Show the first request's cache write, cache read, and wall for every slot. Exclude every slot's first request from the marginal-token and wall deltas, or exclude none.

**5. Matched failures can still be read as an efficiency result.** A differing outcome reports the delta and draws no efficiency conclusion, and a failed slot nominates nothing. o08 already showed this prompt ending at `LOCAL_ONLY` with a completed usage record. If both efforts fail the same way, the text still leaves an efficiency conclusion available. The ladder rule has no per-success cost without a correctly completed task.

Draw an efficiency conclusion only when both slots of that task pass delivery grading. Report matched failures as outcomes and costs.

VERDICT: REVISE
