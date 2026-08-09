---
complexity: high
---

# iter-0100 corpus build B — remaining 9 tasks (completes the 12-task corpus)

Trigger: `autoresearch/iterations/0100-main-ai-executor-quality.md`
(REGISTERED 2026-08-09). Corpus build A landed (run
`rs-20260809T044614Z-58fec95f19be` PASS, spec
`docs/specs/iter0100-executor-quality-corpus-a/spec.md`): scripts +
EQ-UA1/EQ-MI1/EQ-AF1 admitted. This spec authors the remaining 9
tasks, completing exactly three per taxonomy class.

## Authorized surface

`benchmark/executor-quality/tasks/EQ-{UA2,UA3,MI2,MI3,AF2,AF3,BD1,BD2,BD3}/**`
(new directories) plus ONE scoped doc edit: in
`benchmark/executor-quality/README.md`, update the now-stale
corpus-stage paragraph ("three exemplar tasks only") and the
per-task validate command list to cover the complete 12-task set —
no other README change. Everything else is FROZEN: both scripts, the
three corpus-A task directories, skills, other benchmark families.
**A frozen-file change is a spec violation** — if a task cannot be
admitted without changing `validate-task.py` or any other frozen
file, do NOT edit it; report the limitation as a finding naming the
task and stop that task. The frozen-scripts gate below enforces this
byte-exactly.

## Task set — 9 new tasks

| id | class |
|---|---|
| EQ-UA2, EQ-UA3 | unsupported_assumption |
| EQ-MI2, EQ-MI3 | missed_repo_invariant |
| EQ-AF2, EQ-AF3 | absent_failure_mode |
| EQ-BD1, EQ-BD2, EQ-BD3 | broken_dependency |

**broken_dependency materialization** (class has no corpus-A
exemplar): the goal directs a change in one component while another
component inside the fixture depends on the touched contract (call
surface, data format, ordering, error type). The primary invariant is
the DEPENDENT component's end-to-end behavioral contract, checked by
the oracle through ≥2 independent manifestations. The symptom patch
repairs the directly-visible break while leaving ≥1 dependent-path
manifestation failing — per the same-invariant symptom law.

## Per-task shape and laws — binding by reference

Every task directory is governed by
`docs/specs/iter0100-executor-quality-corpus-a/spec.md` § Layout, § R1,
and § R2. The registration remains the authority for corpus laws; the
referenced text supplies the admitted per-task template without
duplicating it here.

Before authoring or judging any task, the phase worker MUST read those
referenced sections. `validate-task.py` is the mechanical arbiter only
for the checks it encodes; validator PASS does not supersede any
referenced clause. VERIFY must inspect every new task against the
complete referenced contract, including clauses that require semantic
judgment.

## Corpus-level distinctness — human-judged at VERIFY

Validator PASS does not discharge this section. A VERIFY PASS requires
comparison of all 12 tasks under these rules:

- **Fresh authorship**: no new task may copy or merely entity-rename
  task-specific contract prose, implementation logic, or test/oracle
  scenario from the corpus-A tasks, `benchmark/probes/drift-bait/**`,
  or `benchmark/ceiling/corpus/**`. Standard language/test scaffolding
  and empty package markers are not task-specific reuse. Any violation
  must cite both source and target paths.
- **Behavioral distinctness**: derive each task's tuple
  `(component boundary, triggering condition, required state/order/error outcome)`
  from its invariant and visible evidence. All 12 tuples must remain
  distinct after entity renaming; different prose, entity names, or
  input values alone do not distinguish two tasks.
- **Family spread**: assign each task exactly one primary family from
  `ordering`, `rollback`, `idempotency`, `auth-order`, or
  `error-priority`; each class's three assignments must contain at
  least two distinct values. If an invariant touches multiple families,
  use the family whose violation makes the oracle manifestation fail.

## Out of scope

Corpus digest sealing, arm runner, dry arm, recert-seats.sh
`executor_quality` suite, seat-matrix.py collector, any script
change.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "printf '769a1826eacd8b503901a2229f15b493a6d9083b1f6b2c1361c35f1b0f74e47b  benchmark/executor-quality/scripts/validate-task.py\\n237476c0e51aa91080fef69e500d73e7c19770ce786afe7b824d51d307028114  benchmark/executor-quality/scripts/score-cohort.py\\n' | shasum -a 256 -c -",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "python3 -c 'import json,pathlib; root=pathlib.Path(\"benchmark/executor-quality/tasks\"); expected={\"EQ-UA1\":\"unsupported_assumption\",\"EQ-UA2\":\"unsupported_assumption\",\"EQ-UA3\":\"unsupported_assumption\",\"EQ-MI1\":\"missed_repo_invariant\",\"EQ-MI2\":\"missed_repo_invariant\",\"EQ-MI3\":\"missed_repo_invariant\",\"EQ-AF1\":\"absent_failure_mode\",\"EQ-AF2\":\"absent_failure_mode\",\"EQ-AF3\":\"absent_failure_mode\",\"EQ-BD1\":\"broken_dependency\",\"EQ-BD2\":\"broken_dependency\",\"EQ-BD3\":\"broken_dependency\"}; dirs={p.name:p for p in root.iterdir() if p.is_dir()}; assert set(dirs)==set(expected), f\"task directories: expected {sorted(expected)}, got {sorted(dirs)}\"; actual={name:json.loads((path/\"task.json\").read_text()) for name,path in dirs.items()}; assert all(data.get(\"id\")==name and data.get(\"class\")==expected[name] for name,data in actual.items()), {name:(data.get(\"id\"),data.get(\"class\"),expected[name]) for name,data in actual.items() if data.get(\"id\")!=name or data.get(\"class\")!=expected[name]}'",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-task.py --task benchmark/executor-quality/tasks/EQ-UA2",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-task.py --task benchmark/executor-quality/tasks/EQ-UA3",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-task.py --task benchmark/executor-quality/tasks/EQ-MI2",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-task.py --task benchmark/executor-quality/tasks/EQ-MI3",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-task.py --task benchmark/executor-quality/tasks/EQ-AF2",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-task.py --task benchmark/executor-quality/tasks/EQ-AF3",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-task.py --task benchmark/executor-quality/tasks/EQ-BD1",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-task.py --task benchmark/executor-quality/tasks/EQ-BD2",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-task.py --task benchmark/executor-quality/tasks/EQ-BD3",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-task.py --task benchmark/executor-quality/tasks/EQ-UA1",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-task.py --task benchmark/executor-quality/tasks/EQ-MI1",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-task.py --task benchmark/executor-quality/tasks/EQ-AF1",
      "exit_code": 0,
      "timeout_sec": 180
    }
  ]
}
```
