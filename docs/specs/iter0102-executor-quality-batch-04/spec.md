---
complexity: high
---

# iter-0102 batch-04 — tasks EQ3-UA4 / EQ3-MI4 / EQ3-AF4 / EQ3-BD4

Trigger: `autoresearch/iterations/0102-executor-quality-discovery-corpus.md`
(DESIGN-FROZEN 2026-08-12), Freeze-protocol step 4 batch 4 of 8. This
batch authors the four index-4 tasks ONLY. Nothing in this spec runs a
scored, calibration, or pilot arm.

## Preconditions (binding)

- This spec was authored from the frozen registration table BEFORE the
  pilot fired and MUST NOT be edited (registration information-boundary
  law R1-2a). This run executes in a corpus session bound by R1-2b:
  the only pilot inputs are
  `~/.local/share/nx01/iter0102/pilot/DECISION` (exact bytes
  `{"decision": "PROCEED"}`, no trailing newline) and the hash-only
  carrier `~/.local/share/nx01/iter0102/pilot/DECISION.receipt.sha256`
  (exactly 64 lowercase hex) — do NOT dereference or read the sealed
  receipt or any other pilot artifact.
- `docs/specs/iter0102-executor-quality-batch-01/scripts.sha256`
  (committed by the orchestrator after batch-01) byte-pins all four
  0102 scripts (`validate-discovery-task.py`, `score-pilot.py`,
  `score-calibration.py`, `score-cohort.py`); ALL are FROZEN for this
  run.

## Authorized surface

- `benchmark/executor-quality/tasks-0102/EQ3-{UA2,MI2,AF2,BD2}/**` — NEW (R1)
- ONE scoped edit in `benchmark/executor-quality/README.md` (R2)

Everything else is FROZEN — every script (pins in Verification), the
iter-0100 `tasks/EQ-*`, iter-0101 `tasks-0101/EQ2-*`, pilot
`tasks-0102-pilot/EQ3P-*`, and all previously admitted `tasks-0102/EQ3-*`
directories. A frozen-file change is a spec violation: report it as a
finding naming the file and stop that task.

## Binding run constraint — difficulty-oracle prohibition

Registration § PRE-CORPUS MECHANISM PILOT binds the corpus window: no
invocation of `claude-sonnet-5`, `claude-opus-5`, or `claude-fable-5`
may be used to estimate manifestation-fail rates, band position, or "is
this hard enough?" on any EQ3 fixture or partial fixture. Executor and
judges may implement and run the mechanical validators/oracles only.
(Pipeline judge review of the diff is not a difficulty probe.)

## Sequencing — depth-first, one task per unit

An orchestrator phase call is wall-capped at 600 s. Five deliverables,
strictly sequenced; each must be COMPLETE — bytes landed + its own gate
green — before the next is started:

1. `EQ3-UA4` → `validate-discovery-task.py --task` exit 0
2. `EQ3-MI4` → same
3. `EQ3-AF4` → same
4. `EQ3-BD4` → same
5. R2 README edit

## R1 — four tasks (frozen authoring-table rows; fixture internals IMPLEMENT-creative)

| id | domain / edit site | local premise (class anchor) | fragment A (consumer) | fragment B (test/doc) | trigger → composed outcome | class |
|---|---|---|---|---|---|---|
| EQ3-UA4 | payroll ledger / timesheet importer | late entries may append | pay-run splitter closes periods immutably at cutoff | retro-adjustment test: late entry = reversal+repost pair | late timesheet after close → failed import leaves closed period byte-identical | unsupported_assumption |
| EQ3-MI4 | school bus routing / stop editor | stop edits apply immediately | route balancer requires per-segment capacity on the ACTIVE plan | snow-day test: swap-back replays the edit queue in submission order | stop edit during snow-day plan → edit queued; regular plan restored byte-identical with queued edits replayed exactly once | missed_repo_invariant |
| EQ3-AF4 | orchard harvest / picking recorder | picked = graded eventually | grader ledger reconciles lot weights to bin weights | rejected-lot test: rejection returns bins to field inventory | rejection after partial grading → bins restored; grade entries voided exactly once | absent_failure_mode |
| EQ3-BD4 | recycling pickup / route editor | stops are freely removable | depot intake forecaster consumes route stop material categories | missed-pickup test: missed stop auto-queues category-preserving makeup | removing a stop with pending makeup → makeup reassigned; forecast rebalanced once | broken_dependency |

**Language (frozen)**: registration per-index law — index 4 is even →
ALL FOUR tasks are Node ≥20 with no third-party dependencies; visible
tests run via `node`. Hidden `oracle.py` remains Python 3 stdlib (it may
invoke `node` subprocesses), deterministic, offline, and must not mutate
the workdir it is given.

Every task directory follows the discovery-shape laws of
`docs/specs/iter0102-pilot/spec.md` § R1 and registration § Task shape —
binding by reference; the phase worker MUST read both before authoring
or judging any task. Operative summary: 24-60 visible files across ≥4
modules; edit-site byte share ≤30%; unstated goal (real ticket prose);
exactly two ordered contract artifacts at directory distance ≥2 mapped
one-to-one to `remote-a`/`remote-b`; contract-token and outcome-token
(complementarity) laws; five roles
`local-a,local-b,remote-a,remote-b,restore` with the ordered two-binding
set byte-identical across manifestations; gold all-pass; symptom
(registered local comparator) exactly `local-a,local-b` pass +
`remote-a,remote-b,restore` fail and touching only `edit_site_dir`
paths; no-patch/noop fail both locals; composed contract carries
restore-to-pre-state or exactly-once semantics.

**Class-anchor causality**: the symptom patch must embody the row's
NAMED local premise — UA: an assumption a consumer contradicts; MI: an
invariant enforced only remotely; AF: an omitted failure-path
transition; BD: an output/state change breaking the dependent
component. Do not let one class shape dominate all four tasks.

**Distinctness (0101 batch lessons — enforced at VERIFY)**: behavioral
tuples (edit-site component, failure trigger, restore outcome) distinct
after entity renaming — among the batch, vs all previously admitted EQ3
tasks, the four EQ3P prototypes, the thirty-two EQ2 tasks, and the
twelve iter-0100 tasks. A renamed structural copy is a HIGH finding
even when every mechanical gate passes. Known recurring classes to
avoid: same-class structural copies, oracle workdir mutation, tie-break
coverage gaps, strawman symptom branches, patch lone-space context
lines (check with cumulative `git diff --check`).

## R2 — README scoped edit (CHANGE-CREATED TRUTHFULNESS)

Update ONLY the now-stale spots: the tasks-0102 admitted-id sentence →
the full cumulative admitted set through the common index of the four
R1 rows; the EQ3 validate for-loop id list → that same cumulative set;
if the runtime-requirements sentence omits a runtime the newly admitted
fixtures require, update only that sentence (Python 3 + POSIX `patch`;
even-index EQ3 fixtures additionally require Node ≥20). No other README
change.

## Corpus-topology gate — cumulative ID set after this batch

`tasks-0102/` contains exactly every `EQ3-{UA,MI,AF,BD}<i>` directory
from index 1 through the common numeric suffix of the four R1 rows;
each `task.json` `id` equals its directory name and its `class` follows
the frozen prefix mapping.

## Out of scope

Authoring or editing any EQ3 task not named in R1; any script change;
any EQ3P edit; candidate seal; calibration; matrix; DECISION file
edits; reading sealed pilot artifacts.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "python3 -c 'import pathlib; b=pathlib.Path.home().joinpath(\".local/share/nx01/iter0102/pilot/DECISION\").read_bytes(); assert b==b\"{\\\"decision\\\": \\\"PROCEED\\\"}\", b'",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "python3 -c 'import pathlib,re; t=pathlib.Path.home().joinpath(\".local/share/nx01/iter0102/pilot/DECISION.receipt.sha256\").read_text(); assert re.fullmatch(r\"[0-9a-f]{64}\\n?\", t), repr(t)'",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "python3 -c 'import pathlib; lines=[l for l in pathlib.Path(\"docs/specs/iter0102-executor-quality-batch-01/scripts.sha256\").read_text().splitlines() if l.strip()]; paths=sorted(l.split(\"  \",1)[1] for l in lines); expected=sorted(\"benchmark/executor-quality/scripts/\"+n for n in (\"validate-discovery-task.py\",\"score-pilot.py\",\"score-calibration.py\",\"score-cohort.py\")); assert len(lines)==4 and paths==expected, paths'",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "shasum -a 256 -c docs/specs/iter0102-executor-quality-batch-01/scripts.sha256",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "python3 -c 'import json,pathlib; root=pathlib.Path(\"benchmark/executor-quality/tasks-0102\"); classes={\"UA\":\"unsupported_assumption\",\"MI\":\"missed_repo_invariant\",\"AF\":\"absent_failure_mode\",\"BD\":\"broken_dependency\"}; current_ids=(\"EQ3-UA4\",\"EQ3-MI4\",\"EQ3-AF4\",\"EQ3-BD4\"); current={name[4:6]:int(name[6:]) for name in current_ids}; assert set(current)==set(classes) and len(set(current.values()))==1, f\"current ids must contain one id per class at one index: {current_ids}\"; current_index=next(iter(current.values())); expected={f\"EQ3-{p}{i}\":classes[p] for p in classes for i in range(1,current_index+1)}; dirs={p.name:p for p in root.iterdir() if p.is_dir()}; assert set(dirs)==set(expected), f\"task directories: expected {sorted(expected)}, got {sorted(dirs)}\"; actual={name:json.loads((path/\"task.json\").read_text()) for name,path in dirs.items()}; assert all(data.get(\"id\")==name and data.get(\"class\")==expected[name] for name,data in actual.items()), {name:(data.get(\"id\"),data.get(\"class\"),expected[name]) for name,data in actual.items() if data.get(\"id\")!=name or data.get(\"class\")!=expected[name]}'",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-discovery-task.py --task benchmark/executor-quality/tasks-0102/EQ3-UA4",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-discovery-task.py --task benchmark/executor-quality/tasks-0102/EQ3-MI4",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-discovery-task.py --task benchmark/executor-quality/tasks-0102/EQ3-AF4",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-discovery-task.py --task benchmark/executor-quality/tasks-0102/EQ3-BD4",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "for task in benchmark/executor-quality/tasks-0102/EQ3-*; do python3 benchmark/executor-quality/scripts/validate-discovery-task.py --task \"$task\" || exit 1; done",
      "exit_code": 0,
      "timeout_sec": 1200
    }
  ]
}
```
