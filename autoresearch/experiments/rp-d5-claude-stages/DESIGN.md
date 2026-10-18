# rp-d5 design — where Claude's delivery time goes

Design closed after round 4; the remaining classifier detail is fixed in
the code and its frozen oracle (below), reviewed with the apparatus. Research only: no
product change, no release. Rounds 0–2: Astra ultra REVISE, Grok 4.7 REVISE
([r0 Astra](results/design-r0-astra.md), [r0 Grok](results/design-r0-grok.md),
[r1 Astra](results/design-r1-astra.md), [r1 Grok](results/design-r1-grok.md),
[r2 Astra](results/design-r2-astra.md), [r2 Grok](results/design-r2-grok.md),
[r3 Astra](results/design-r3-astra.md), [r3 Grok](results/design-r3-grok.md),
[r4 Astra](results/design-r4-astra.md), [r4 Grok](results/design-r4-grok.md));
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

On BV and Z0 under the shipped 4.2.22 (rp-d4 X), at effort `max` and at
`high`: how do Claude's turns and marginal tokens split across delivery
stages, how do slot wall time, turns and tokens differ between the two
efforts, and which exact operations repeat?

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

**Smoke.** One Claude cell on SM at `high` before c01, ungraded. It
qualifies delivery, the effort binding, receipt reconciliation and a stage
table without UNKNOWN. A failed smoke is kept; one spare smoke; a failed
spare stops the run. Smoke never changes the function, the schedule or the
prediction.

**Failure handling.** Every dispatched slot is kept with its costs; none is
replaced. Delivery is graded as in rp-d1 (scope and regression checks,
exactly one correctly merged PR, preserved user files); the report is not
graded. rp-d1 o08 showed the unchanged prompt can lead Claude to stop at
`LOCAL_ONLY`; such a slot is a failed delivery. An efficiency conclusion for
a task is drawn only when both of its slots pass delivery; otherwise the
task's outcomes and costs are reported as they are. A STOP, UNKNOWN
usage or an unreconciled slot (below) is
reported as UNKNOWN for the affected numbers.

## Accounting (reuse 0254; no new token accounting)

- **Rows.** One row per audited 0254 receipt (one native terminal response
  body per message id, parent and foreground children), in
  `api-bodies/index.jsonl` order. The auditor's own checks (identity,
  conflict, effort, thinking ≤ output) apply unchanged; a slot the auditor
  refuses is UNKNOWN. Tool calls come from that response body's `content[]`.
  Tool results (Bash exit code scraped from the result text as in
  `0234/diagnostics.py`, `is_error` otherwise) come from the project JSONL,
  joined by tool-use id. A child's rows are classified by their own tools;
  the parent `Agent` row does not take the child's class.
- **Tokens.** Per row: uncached input, cache read, cache write, output and
  thinking (already inside output). Row sums must equal the auditor's slot
  totals, or the slot's token figures are UNKNOWN.
- **Marginal tokens.** A row's marginal tokens are its output plus cache
  write. It is a descriptive proxy, not a saving.
  Cache read is shown per row as a series and is never charged to a stage.
- **Wall.** Reported per slot only, as the owner's `owner_seconds`
  (monotonic, around `docker start -a`). There is no per-stage wall split:
  the semantics of the index timestamps are not validated, and a
  telescoping partition would reconcile even when misattributed.
- **First request.** Every slot's first row (cache write, cache read) is
  shown on its own line. Effort deltas are reported raw; a sensitivity line
  repeats them with every slot's first row excluded. Neither is called
  cold-cache overhead.

## Stage attribution (closed function, frozen before the run)

Paths are normalized to the cell worktree. **Instruction paths** are
`CLAUDE.md`, `AGENTS.md` and any path under a `skills/` directory (including
`skills/_shared/`). **Task paths** are every other path in the cell
worktree or its task worktree. A Read/Grep/Glob with no path, or with the
worktree root, is a task-tree look.

**Bash.** Two views of each command. The **pipeline view** is the
heredoc-stripped text, split into commands on `|`, `;`, `&&`, `||` and
newlines **outside quotes**, each command split with `shlex`; a `shlex`
failure makes that call Other. A command word is the first token of a
command after the prefixes `sudo`, `command`, `nohup`, `time`, `env` and
leading `VAR=value`; a quoted word is never a command word. The **full view** is the whole text, heredoc payloads
included. Command-word predicates use the pipeline view only;
in-process-write patterns use the full view only. A file named as an
argument is a read or a mention, never an execution (`cat
.../task-complete.py` reads it; `python3 .../task-complete.py complete`
runs it).

**Shell-read paths.** Only path-position tokens are judged. Flags in a
pinned consume-list take the next token (`head`/`tail -n`; the `sed -n`
script; `rg -g/-t/-A/-B/-C/-e/-f/-m` and long forms; `grep -e/-f/-m/-A/-B/-C`).
For `rg` and `grep` the first remaining token is the pattern unless `-e`
or `-f` gave one; the rest are paths. For `cat`, `ls`, `head`, `tail` and
`sed -n` every remaining token is a path. For `find` only the start paths
before the first predicate are paths. For `git diff`, `git log` and
`git show` a token that does not normalize into the worktree is a revision
and is ignored.
Zero paths, or all paths in the task tree or at its root, is a task look;
all paths under instruction paths is orient; a mix, or a token that is not a
worktree path, makes the call Other.

Call predicates:

| Predicate | Calls |
|---|---|
| write | Edit, Write, NotebookEdit; pipeline command `tee`, `patch`, `git apply`; `sed` with an argument `-i`, `--in-place` or starting `-i`; `cp`, `mv`, `rm` when a path argument normalizes into the task tree outside the exclude prefixes (all-excluded is not a write; any other path is unknown); a redirection target matched by the `0234/diagnostics.py` regex outside its exclude prefixes (`/dev/null`, `/tmp/`, `/private/tmp/`, `$TMPDIR/`, `tmp/`, `.devlyn/`); full-view `\bwrite_text\s*\(`, `\bwrite_bytes\s*\(`, or `open(` with a literal mode beginning `w`, `a` or `x` |
| check | pipeline command `pytest` or `python`/`python3` with `-m pytest` (any flags, e.g. `python3 -B -m pytest -q`), or a task check script named in `tasks.json` |
| deliver | pipeline command running `task-complete.py`, or command words `git add/commit/push/fetch/merge/worktree/branch`, `gh` |
| orient | Read/Grep/Glob of instruction paths; shell reads whose paths are all instruction paths |
| look | Read/Grep/Glob of task paths, no path or the root; shell reads that are task looks; `git status` |
| unknown | a pipeline command running a script or interpreter (`python3 x.py`, `node x.js`, `python -c`, `python - <<`) that matches none of the above, or `open(` with a non-literal mode |

A row's stage, applied in this order:

1. **Report:** the last row (index order) with no tool call. Any earlier
   row with no tool call is **Other**.
2. **After delivery:** every row after the first `complete` result whose
   stdout object has `status` `COMPLETE` or `CLEANUP_PENDING` (with
   `delivery_status` `COMPLETE`). The object is found by `raw_decode` from
   each `{` in the tool-result text (string content as is, other content
   JSON-encoded, as in `0234/diagnostics.py`), so a trailer such as
   `Local commit: …` does not hide it. The invoking row stays Deliver. `PR`, `PENDING`, `LOCAL_ONLY`, `FAILED`
   and `BLOCKED` do not open it. If a `complete` stdout cannot be parsed,
   the boundary and every later row are **Other**.
3. If the row's calls (or one Bash string) match two or more of write,
   check, deliver, orient and look, it is **Mixed** (its predicates
   listed).
4. Otherwise: orient → **Orient**; write → **Edit**; check → **Verify**;
   deliver → **Deliver**; look → **Explore** if the row precedes the first
   write, **Verify** if it follows it; unknown or anything else → **Other**.

The **first write** is the first row (index order) containing a write call,
whether its stage is Edit or Mixed. A row with an unknown call is
mutation-unknown. If a mutation-unknown row precedes the first write, the
slot's look counts are still shown but its Explore/Verify split is marked
unsupported (this does not fail the smoke; accounting UNKNOWN does).

**Definition by code.** `attribute.py` at the registered commit is the
classifier; this section states its rules. Its fixture oracle gives the
expected label of every case named in design rounds 3 and 4, including: a
heredoc payload with `write_text` and one containing the word `cp`;
`open(p, "w")`, `open(p, "rb")`, `open(p, mode)`; `2>&1`, `>/dev/null`,
`>/tmp/x`, `rm /tmp/x`, `sudo cp a b`, `sed -i.bak f`; `dispatch`; `cat` of
the helper versus running it; `rg is_expired src/expiry/__init__.py`,
`rg "is_expired|stale" src/expiry/__init__.py`, `rg -g '*.py' is_expired
src/expiry/__init__.py`, `rg -n "def complete|merge_refused"
.agents/skills/_shared/task-complete.py`, `grep -n deadline
src/limitcli/__init__.py`, `head -n 40 src/expiry/__init__.py`,
`sed -n '1,40p' CLAUDE.md`, `ls -la`, `cat CLAUDE.md
src/expiry/__init__.py`, `git diff HEAD`, `git log -n 5`,
`find . -name '*.py'`; pathless Grep/Glob; Read+Edit in one row;
`cat x && sed -i ... x`; `python3 fix.py`; a look after
`python3 -c 'print(1)'`; `python3 -c 'print(1); cp a b'`; PR/PENDING before
COMPLETE; a `complete` stdout with the `Local commit:` trailer; children;
unparseable stdout. The oracle is reviewed with the apparatus, frozen with
the registration, and must pass before c01. Nothing in this section or the
code changes after the run. Each slot's table shows Other's share of
turns; a slot with Other above 20% of its turns is marked low-coverage.

## Repeats (descriptive)

An **operation** is a tool call identified by its tool name and its
canonical JSON input (every argument, including Read offset/limit, Grep
pattern and options, and the full Bash text with heredoc payload). The
analysis lists every operation that occurs more than once in a slot, with
its stage, the row ids of its occurrences, and whether a write call or a
mutation-unknown row came between occurrences. Tokens shown beside an
occurrence are its **enclosing row's** tokens: shared with the row's other
calls and not additive. The table makes no claim that a repeat was
unnecessary or devlyn-caused.

No candidate is nominated in this run. The write-up gives the stage and
repeat tables and the observed effort deltas; any reduction candidate is a
separate design, with its own review, judged later by the ladder rule
(total wall, input and output per success, failures included). Effort is a
user setting: a large effort delta is reported, and whether future
benchmarks pin Claude at `high` is a separate owner decision.

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
rate. Slot wall includes model latency, which the harness does not
control. A repeat is an observation, not a proven saving.
