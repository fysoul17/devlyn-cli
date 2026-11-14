# 0266 amendment 3: a cleared model identity STOP of a registered slot is archived and run again once (2026-11-14)

This is a dated amendment to [DESIGN.md](DESIGN.md) "Operations", which ends the run on an unresolved identity failure
("Stop"). It changes one operation: what becomes of a registered slot whose STOP is a model identity mismatch once an
amendment has cleared its latch. DESIGN.md and [registration.md](registration.md) are unchanged.

## What happened

Times are KST on 2026-11-14. Every fact below was verified by the orchestrator in the runtime root: the lane's log,
c090's verdict and folder, and the attempt's `run/stdout` (what of it was read is listed under "What was known of the
outcomes").

- The Claude lane stopped at 11:50:32 on `c090-B5-claude-C-r5` with the harm latch `identity MISMATCH` (the driver's
  event). Its verdict is a STOP with `reason: "model identity mismatch"`, `teardown: "CLEAN"`, `owner_ran: true`,
  `owner_status: "EXITED_0"`, `scope_violations: []`, `changed: ["src/exports.js"]`, `owner_seconds: 33.2`,
  `input_tokens: 130935`, `output_tokens: 2283`, and `identity: {"owner": "MATCH", "status": "MISMATCH",
  "violations": ["claude owner ran claude-sonnet-5-5", "claude session 2eaabff0-… ran claude-sonnet-5-5"],
  "gaps": [], "owner_launched_sessions": [], "codex_seats": {}}`. The cell's `checks.json` holds the scope result
  `stop_evidence` wrote (`scope_violations: []`, `changed`) and no product check, oracle or assessment result: the STOP
  comes before grading (`run_cell.py`, the `stop =` chain).
- The cause, read from the attempt's `run/stdout` (event types, models, tool names and the `Agent` call's
  `subagent_type`, `model` and `description` only; the counts are stream events): the init event names
  `claude-opus-5-5`, the plan's model; all 9 assistant events of the owner itself (5 messages) ran `claude-opus-5-5`;
  the owner called its own `Agent` tool once, with `subagent_type: "general-purpose"`, `model: "sonnet"`,
  `description: "Independent review of deletion diff"`; the 2 assistant events (1 message) that ran
  `claude-sonnet-5-5` are that sub-session's (their `parent_tool_use_id` is that call's id; 2 tool uses, in 4172 ms by
  the `task_notification` event's `duration_ms`). The result event's `modelUsage` therefore lists both models. The
  registered identity check reads the result event's `modelUsage` and the session transcripts (`0233/evidence.py`,
  `transcripts`): the first violation is the owner's `modelUsage`; the second is the owner's session, whose transcript
  folder holds the sub-session's entries (`…/subagents/agent-….jsonl`, marked `isSidechain`). The registered rule
  (`0233/cell.py`, `identity`): the check holds the owner and its native sub-sessions (sidechain entries) to the plan's
  model, `claude-haiku-` helper calls aside (`INTERNAL`, `^claude-haiku-`); a separate Claude session the owner starts
  from the shell is listed (`owner_launched_sessions`) and held to no model (`owner_launched_claude`).
- The one `rate_limit_event` of the session reads `allowed_warning`, `seven_day` utilization 0.39: no limit was
  reached and nothing fell back. So no wrong model was routed to the cell: the planned model ran the owner, and the
  owner itself asked for a second Claude model for a review.
- This is the first such attempt: the model identity read MATCH on 0265's 161 verdicts; of this run, every final
  verdict reads MATCH and no other attempt read MISMATCH (the driver latches both cases; an attempt stopped by a launch
  fault, a memory kill or an account fault may carry no model record). 153 of 176 slots have a final verdict (Codex 64
  of 64; Claude c001-c089), c090 is the STOP, and 22 Claude slots have not started: c091-c112, replicate 5's D3 and D4
  rows and replicates 6 to 8 of B5, D3 and D4 (replicate 5's B5 rows are c089 and c090). 154 slots have a verdict
  record: those 153 and c090. R1's cells (Claude F10) all have a final verdict.
- As the driver stood, clearing the latch restarted nothing: `redispatch()` returned False for this STOP, so
  `terminal()` ended the lane at c090 every time and c091-c112 would never run.

## The change

### 1. A registered slot's cleared model identity mismatch is archived and run again once (`driver.py`)

A slot that is not a screen slot, whose verdict is a STOP with `reason` exactly `model identity mismatch`, whose
`identity.status` is `MISMATCH`, whose `identity.owner` is `MATCH`, whose `teardown` is `CLEAN`, whose latch an
amendment has cleared, and which has no archived attempt (`verdict-<name>.stop-*.json`) with that same reason, is
archived as `.stop-N` and dispatched again, as the slot's first launch fault is: no recovery step (its teardown was
clean).

Every other case stays as it is today. Not cleared, it latches both lanes. With `identity.owner` not `MATCH`, or
`identity.status` `UNVERIFIED` or `UNKNOWN` (their reasons read `model identity unverified` / `unknown`), or a
teardown that is not `CLEAN`, or a second such STOP on the same slot, it stays a STOP, and a cleared one ends its lane
without a new latch. A screen slot is never run again for it and, once cleared, is passed as today.

In code, `redispatch()` decides every verdict with that reason and returns there, so no later line can make it a
redispatch; it reads the slot's archive as the once-per-slot check of a launch fault does. `dispatch()` is unchanged:
such a STOP is no Docker loss (`docker_fault` needs `teardown: FAILED`) and its reason does not start with
`teardown failed: `, so nothing is recovered; the existing rename archives the verdict and the folder, and the slot is
run. As in amendment 2, the rule reads a SMOKE row as a registered slot; SMOKE ended before the screen and is not run
again. The rule names no engine; the Codex lane is complete, and the proof below reads a Claude owner's stream.

### 2. The operator's proof before the latch is cleared

Before the operator clears such a latch, the operator proves from the attempt's records (its verdict, `plan.json`,
`run/stdout` and session transcripts) that the other model ran only in sub-sessions the owner itself started with its
`Agent` tool naming that model. The proof passes only when (a) every violation the verdict lists is a Claude owner's or
session's model (`claude owner ran …`, `claude session … ran …`); (b) the init model is the plan's and the owner's own
assistant events (no `parent_tool_use_id`) ran the plan's model only; (c) every sub-session event that ran another
model (Haiku helpers aside) has, as its `parent_tool_use_id`, an owner `Agent` call whose `model` input names that
model; (d) every other model in the result event's `modelUsage` and every model the verdict names is accounted for by
(c); (e) in the attempt's transcripts every assistant entry on another model is a sidechain entry on a model accounted
for by (c). It prints `PROOF: PASS` or `PROOF: FAIL:` with the reasons.

A verdict alone cannot tell this from a model routed to the owner's own messages; an attempt that does not pass this
proof is not cleared under this amendment. A proof that fails for a reason that is not a wrongly routed model (a
sub-session started by a skill or an agent definition that sets its own model, a `<synthetic>` owner event) still
fails: such a latch is not cleared under this amendment. The driver does not read the proof: it is the condition for
clearing the latch. The orchestrator ran the command on six altered copies of c090's records in a scratch folder (an
owner message on the other model; the `Agent` call naming no model; a violation of another kind; the transcript's
entries not marked sidechain; a third model in `modelUsage` only; the sub-session under an unknown call): each read
`PROOF: FAIL`.

The command the orchestrator ran for c090, and its output:

```
python3 - c090-B5-claude-C-r5 <<'EOF'
import json, os, re, sys
from pathlib import Path
out, name = Path(os.path.expanduser('~/.local/share/nx01/0266-live/output')), sys.argv[1]
plan = json.loads((out / name / 'plan.json').read_text())['model']
other = lambda model: model != plan and not re.match(r'claude-haiku-', model)  # 0233/evidence.py INTERNAL
def events(path):
    for line in path.read_text(errors='replace').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            yield event
fails, named, calls, own, accounted, usage, init = [], set(), {}, set(), set(), set(), None
for violation in json.loads((out / f'verdict-{name}.json').read_text())['identity']['violations']:
    match = re.fullmatch(r'claude (?:owner|session \S+) ran (\S+)', violation)
    named.add(match.group(1)) if match else fails.append(f'a violation of another kind: {violation}')
for event in events(out / name / 'run/stdout'):
    if event.get('type') == 'system' and event.get('subtype') == 'init':
        init = event.get('model')
    if event.get('type') == 'result':
        usage = {model.split('[')[0] for model in event.get('modelUsage') or {}}
    if event.get('type') != 'assistant':
        continue
    message, parent = event.get('message') or {}, event.get('parent_tool_use_id')
    model = str(message.get('model'))
    if not parent:
        own.add(model)
        calls.update({part.get('id'): (part.get('input') or {}).get('model') for part in message.get('content') or []
                      if part.get('type') == 'tool_use' and part.get('name') == 'Agent'})
    elif other(model):
        asked = calls.get(parent)
        if isinstance(asked, str) and (asked == model or asked in model.split('-')):
            accounted.add(model)
        else:
            fails.append(f'a sub-session message ran {model} under no owner Agent call that names it')
for path in sorted((out / name / 'home/.claude/projects').rglob('*.jsonl')):
    for event in events(path):
        model = str((event.get('message') or {}).get('model'))
        if (event.get('type') == 'assistant' and not event.get('isApiErrorMessage') and model != '<synthetic>'
                and other(model) and not (event.get('isSidechain') and model in accounted)):
            fails.append(f'{path.name}: a transcript entry ran {model} outside an accounted sub-session')
if init != plan or own != {plan}:
    fails.append(f"the owner's own messages ran {sorted(own)} after init {init}, the plan is {plan}")
if not named or not named <= accounted or not {m for m in usage if other(m)} <= accounted:
    fails.append(f'named {sorted(named)}, in modelUsage {sorted(usage)}, accounted {sorted(accounted)}')
print(f"plan {plan} | init {init} | the owner's own messages ran {sorted(own)} | owner Agent calls name "
      f'{sorted(str(v) for v in calls.values())}')
print(f'the verdict names {sorted(named)} | modelUsage {sorted(usage)} | accounted to owner Agent calls '
      f'{sorted(accounted)}')
print('PROOF: ' + ('FAIL: ' + '; '.join(sorted(set(fails))) if fails else 'PASS'))
EOF
plan claude-opus-5-5 | init claude-opus-5-5 | the owner's own messages ran ['claude-opus-5-5'] | owner Agent calls name ['sonnet']
the verdict names ['claude-sonnet-5-5'] | modelUsage ['claude-opus-5-5', 'claude-sonnet-5-5'] | accounted to owner Agent calls ['claude-sonnet-5-5']
PROOF: PASS
```

c090 passes: the plan's model and the init model are the same, the owner's own messages ran that model only, its one
`Agent` call names `sonnet`, and the one other model, which the verdict names and `modelUsage` lists, is accounted to
that call. For another slot, the command's argument (`c090-B5-claude-C-r5`, on its first line) names that slot.

## Why the slot is run again, and neither graded nor left stopped

- Not graded: the registered check holds the owner and its native sub-sessions (sidechain entries) to the plan's model,
  `claude-haiku-` helper calls aside, and stops a cell in which one of them ran another model. Reading this attempt as
  the slot's result would change, after part of its outcome was known, what the run counts as the measured model.
- Not left stopped: DESIGN "Operations" ends the run on an *unresolved* identity failure. This one is resolved: its
  cause is established, and it is not a routing fault of the apparatus or the account. Left stopped, 22 registered
  cells would never run and the verdict would be NOT_FINISHED by this one slot.
- Run again: the registered identity rule defines which attempts can stand for a slot. This attempt cannot, so the
  slot needs another, as after a launch fault, a memory kill or an account fault (each run again once). The exclusion
  is by the registered rule and not by the attempt's outcome. The attempt is archived, not dropped: DESIGN "attempts"
  charges every attempt that ran an owner and makes it part of the slot's harm (scope, findings, false completions),
  and `decide.py` reads archived attempts so (`load()`: `attempt_cost`, `evidence`).
- Once per slot: a second such STOP on the slot stays a STOP. The driver reads it from the slot's archive, so it is a
  STOP at a restart too.

## What does not change

- Every decision rule and every verdict reading.
- The registered identity check (`0233/cell.py`, its `INTERNAL` pattern) and the STOP it writes: a model identity
  mismatch is still a STOP, is never graded, and latches both lanes until an amendment clears it.
- The grading path: `stop_evidence`, the checks, the assessors, the witnesses, the probe, the judges, `decide.py`.
- The caps.
- The screen's rule: a screen slot's cleared STOP, a model identity mismatch among them, is passed and reads as an
  unknown; no screen cell is run again.
- Amendment 2's rule for a failed teardown, and the STOPs the lane runs again by itself: a slot's first launch fault,
  memory kill or shared account fault, and a Docker loss.
- `0233/cell.py`, `0265/cell.py` and `run_cell.py`.

## What can still fail

- A second mismatch on the slot. The rerun's verdict is a new one (its sha256 differs), so it latches both lanes as
  `identity MISMATCH`; once cleared, it stays a STOP, because the slot's archive holds the first. The lane ends there,
  the slots after it do not run, and the run reads NOT_FINISHED (`decide.py`: a slot without a final verdict is a
  missing input of G1, G2 and G3).
- What this can bias. What is selected is the slot's final attempt: G1, the completion counts, the tree, the probe and
  the witnesses of the slot are the rerun's. What is kept is the archived attempt's cost and harm: it is charged to its
  arm in G3 (130,935 input tokens here, 25,226 of them the sub-session's on the other model, by the attempt's
  `usage.json`), and its scope result and tree are part of the slot's harm in G2. So an arm whose sessions hand work to
  another Claude model more often gets a narrower G1 (its sessions that did not) and a higher cost. The readings
  therefore do not describe sessions that hand work to another Claude model through the `Agent` tool; they never did
  (the registered check). R1 is not touched: its cells were all final before this amendment. RESULT.md reports every
  such attempt by slot and arm. It is 1 of the run's Claude attempts so far (arm C, B5). A later design should say what
  a Claude sub-session on another model is.
- The lane's death between the two renames of the archive (the verdict's, then the folder's) leaves a verdict without
  its folder. It is the edge amendment 2's operator step 7 names, unchanged; that state is resolved by a further
  amendment.

## What was known of the outcomes

When this amendment was written no registered verdict had been opened except two STOP records: c069's first attempt
(amendment 2) and c090's, of which the fields listed under What happened were read. Of c090's `run/stdout` the
orchestrator read event types, models, tool names, the `Agent` call's `subagent_type`, `model` and `description`, the
init event's model, agent, skill and plugin names, the `task_*` system events, the result event's `subtype`,
`is_error`, `num_turns`, `duration_ms` and `modelUsage` token counts, and the one `rate_limit_event`; no assistant
text, no tool input or output otherwise, no product check, oracle or assessment result (the attempt has none). Of
c090's folder it also read the first line of `run/stderr` (the status line), `checks.json` (the scope result),
`snapshot.json`, `plan.json`'s model, the names of the transcript files and, by the proof command, the models and
`isSidechain` marks of the transcript entries. The lane logs' `rc` values and the count of verdicts (153 of 176 slots
with a final verdict, 154 with a verdict record, c090's STOP among them) were known. No probe, witness, judge or
decision had run on a registered cell (the screen's decision and its event counts were known, as amendment 2 records,
and the controls and the calibration, as registration.md records). The verifiers of this amendment read the same
folder under the same limit.

## Which cells ran under which rule

c001-c089 and the Codex lane's 64 cells ran before this amendment. c090's rerun and c091-c112 run after it, and carry
the new `driver.py` in their `seal.json` (`apparatus` and `source_commit`); c090's first attempt, archived, keeps its
own. The rule changes no cell's run or grading, only whether a stopped slot is run again.

## Operator steps

1. The proof (no model): the command under "The change", part 2, on c090's attempt; its output must read as shown
   there, `PROOF: PASS` on its last line.
2. Merge this amendment by PR.
3. Move the run worktree (`~/.local/share/nx01/0266-run`) to the merge commit of this amendment.
4. While c090's verdict is unchanged, release its latch:
   `python3 $X/driver.py --clear-latch $X/amendment-3.md $R/runtime-claude.json`
5. Start the Claude lane as README step 14 says, its terminal log under a new name.
6. A later latch of this kind on another slot (`identity MISMATCH`, the verdict's reason `model identity mismatch`,
   `identity.owner` MATCH, a clean teardown, no such attempt in the slot's archive): the proof command first, with
   that slot's name as its argument; if it prints `PROOF: PASS`, step 4 again with this file and step 5, and the
   proof's output goes into RESULT.md. If it prints `PROOF: FAIL`, the latch is not cleared under this amendment.

## Reported in RESULT.md

- Every archived model-mismatch attempt by slot and arm (`verdict-<name>.stop-N.json` with reason
  `model identity mismatch`), with its proof output: c090's first attempt (arm C, B5) and its rerun. `decide.py`'s
  fault table (`reported.faults`) does not list a model-mismatch archive, so the list comes from `decision.json`
  (`slots[<name>].archived`, `reported.attempts`).
- The Claude lane's lost time: from the latch at 11:50:32 to the restart's first dispatch.
- The interpretation limit: the bias paragraph under "What can still fail".

## Reviews

(written by the orchestrator after the review)

## Applied

(written by the orchestrator)
