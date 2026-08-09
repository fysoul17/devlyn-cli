---
complexity: high
---

# iter-0101 batch-02 — tasks EQ2-UA2 / EQ2-MI2 / EQ2-AF2 / EQ2-BD2

Trigger: `autoresearch/iterations/0101-executor-quality-hard-corpus.md`
(DESIGN-FROZEN 2026-08-09), Freeze-protocol step 1 batch 2 of 8. Batch-01
landed (run `rs-20260809T125952Z-fbd722f7d0d0` PASS, spec
`docs/specs/iter0101-executor-quality-batch-01/spec.md`): all four scripts
final + EQ2-UA1/MI1/AF1/BD1 admitted. This batch authors the four index-2
tasks ONLY. Nothing in this spec runs a scored, calibration, or pilot arm.

## Authorized surface

- `benchmark/executor-quality/tasks-0101/EQ2-{UA2,MI2,AF2,BD2}/**` — NEW (R1)
- ONE scoped edit in `benchmark/executor-quality/README.md` (R2)

Everything else is FROZEN — all four scripts (byte pins in Verification),
the twelve iter-0100 `tasks/EQ-*` directories, and the four admitted
batch-01 `tasks-0101/EQ2-*1` directories. A frozen-file change is a spec
violation: if a task cannot be admitted without editing a frozen file, do
NOT edit it; report the limitation as a finding naming the file and stop
that task.

## Binding run constraint — difficulty-oracle prohibition

Registration § Difficulty calibration gate binds this run: no invocation of
`claude-sonnet-5`, `claude-opus-5`, or `claude-fable-5` may be used to
estimate manifestation-fail rates, band position, or "is this hard enough?"
on any EQ2 fixture or partial fixture. Executor and judges may implement and
run the mechanical validators/oracles only. (Pipeline judge review of the
diff is not a difficulty probe.)

## Sequencing — depth-first, one task per unit

An orchestrator phase call is wall-capped at 600 s. Five deliverables,
strictly sequenced; each must be COMPLETE — bytes landed + its own gate
green — before the next is started:

1. `EQ2-UA2` → `validate-hard-task.py --task` exit 0
2. `EQ2-MI2` → same
3. `EQ2-AF2` → same
4. `EQ2-BD2` → same
5. R2 README edit

## R1 — four tasks (frozen authoring-table rows; fixture internals IMPLEMENT-creative)

| id | pair | domain | component boundary | class |
|---|---|---|---|---|
| EQ2-UA2 | OI | print queue | spooler vs job dedup index | unsupported_assumption |
| EQ2-MI2 | OI | notification fanout | scheduler vs delivery dedup | missed_repo_invariant |
| EQ2-AF2 | OA | ticket escalation | severity router vs on-call ACL | absent_failure_mode |
| EQ2-BD2 | OA | firmware rollout | wave sequencer vs device attestation | broken_dependency |

**Language (frozen)**: apply the registration's per-index law to each R1
row: an odd numeric suffix means Python 3 stdlib; an even numeric suffix
means Node ≥20 with no third-party dependencies. Node fixtures use plain
node-runnable JavaScript and run their visible tests via `node`. In both
cases hidden `oracle.py` remains Python 3 stdlib because the frozen
validator invokes `python3 oracle.py <workdir>`; for an even-index fixture
it may invoke `node` subprocesses. It remains deterministic and offline
and must not mutate the workdir it is given.

**Axis role order (frozen)**: O=ordering, R=rollback, I=idempotency,
A=auth-order, E=error-priority. For pair code `XY`, axis1=X and axis2=Y.
Use the pair from each R1 row. Manifestation ids are exactly `axis1-a`,
`axis1-b`, `axis2-a`, `axis2-b`, `interaction`.

Every task directory follows
`docs/specs/iter0100-executor-quality-corpus-a/spec.md` § Layout, § R1,
§ R2 and the hard-corpus laws of
`docs/specs/iter0101-executor-quality-batch-01/spec.md` § R1 — both binding
by reference; the phase worker MUST read those sections before authoring or
judging any task.

For each R1 row, instantiate exactly the canonical trigger and required
composed outcome for that row's pair from registration § Axis-pair
templates, in the registered domain and component boundary. Do not
substitute another pair or reverse its axis order.

- **BD law (the R1 BD row)** — 0100 corpus-b § broken_dependency binds
  by reference: the goal directs change in one component of the
  registered boundary; the DEPENDENT component's composed contract is
  the invariant; symptom repairs the directly-visible break while the
  `interaction` manifestation on the dependent path fails.

**Distinctness (VJ-1 lesson from batch-01 — enforced at VERIFY)**:
0100 corpus-b § Fresh authorship and § Behavioral distinctness bind
verbatim. VERIFY compares the cumulative admitted EQ2 set and all twelve
iter-0100 tasks: no task may copy or merely entity-rename task-specific
contract prose, implementation logic, or test/oracle scenario; derive
each task's `(component boundary, triggering condition, required
state/order/error outcome)` tuple and require every tuple to remain
distinct after entity renaming. For every cumulative same-pair group,
different domain nouns alone are insufficient; a renamed structural copy
is a HIGH finding even when every mechanical gate passes. Do NOT assign
a single primary-family label.

## R2 — README scoped edit (CHANGE-CREATED TRUTHFULNESS)

Update ONLY the now-stale spots:
- the tasks-0101 admitted-id sentence ("currently admits …") → the full
  cumulative admitted set through the common index of the four R1 rows;
- the EQ2 validate for-loop id list → that same cumulative set;
- if the runtime-requirements sentence omits a runtime required by the
  newly admitted fixtures, update only that sentence to state that
  validation requires Python 3 and the POSIX `patch` utility, and that
  even-index EQ2 fixtures additionally require Node ≥20.
No other README change.

## Corpus-topology gate — cumulative ID set after this batch

`tasks-0101/` contains exactly every `EQ2-{UA,MI,AF,BD}<i>` directory
from index 1 through the common numeric suffix of the four R1 rows; each
`task.json` `id` equals its directory name and its `class` follows the
frozen prefix mapping.

## Out of scope

Authoring or editing any EQ2 task not named in R1; any script change;
candidate seal; calibration driver/runner; matrix apparatus; recert
fold-in.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "printf '769a1826eacd8b503901a2229f15b493a6d9083b1f6b2c1361c35f1b0f74e47b  benchmark/executor-quality/scripts/validate-task.py\\n1f809e33d652dea17591adce8a4c4d7d8bae2679032e7c79f805a081e01be94c  benchmark/executor-quality/scripts/validate-hard-task.py\\n418f3738caeb366bb54df0f435e3f4b0399fb7e89f407fead90ef542363c1d77  benchmark/executor-quality/scripts/score-calibration.py\\n5af3c1bd672a11b0092d7be9a70dfb48ad0c446f88197cb6276a6e33e77835e3  benchmark/executor-quality/scripts/score-cohort.py\\n' | shasum -a 256 -c -",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "python3 -c 'import json,pathlib; root=pathlib.Path(\"benchmark/executor-quality/tasks-0101\"); classes={\"UA\":\"unsupported_assumption\",\"MI\":\"missed_repo_invariant\",\"AF\":\"absent_failure_mode\",\"BD\":\"broken_dependency\"}; current_ids=(\"EQ2-UA2\",\"EQ2-MI2\",\"EQ2-AF2\",\"EQ2-BD2\"); current={name[4:6]:int(name[6:]) for name in current_ids}; assert set(current)==set(classes) and len(set(current.values()))==1, f\"current ids must contain one id per class at one index: {current_ids}\"; current_index=next(iter(current.values())); expected={f\"EQ2-{p}{i}\":classes[p] for p in classes for i in range(1,current_index+1)}; dirs={p.name:p for p in root.iterdir() if p.is_dir()}; assert set(dirs)==set(expected), f\"task directories: expected {sorted(expected)}, got {sorted(dirs)}\"; actual={name:json.loads((path/\"task.json\").read_text()) for name,path in dirs.items()}; assert all(data.get(\"id\")==name and data.get(\"class\")==expected[name] for name,data in actual.items()), {name:(data.get(\"id\"),data.get(\"class\"),expected[name]) for name,data in actual.items() if data.get(\"id\")!=name or data.get(\"class\")!=expected[name]}'",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-hard-task.py --task benchmark/executor-quality/tasks-0101/EQ2-UA2",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-hard-task.py --task benchmark/executor-quality/tasks-0101/EQ2-MI2",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-hard-task.py --task benchmark/executor-quality/tasks-0101/EQ2-AF2",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-hard-task.py --task benchmark/executor-quality/tasks-0101/EQ2-BD2",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "for task in benchmark/executor-quality/tasks-0101/EQ2-*; do python3 benchmark/executor-quality/scripts/validate-hard-task.py --task \"$task\" || exit 1; done",
      "exit_code": 0,
      "timeout_sec": 600
    }
  ]
}
```
