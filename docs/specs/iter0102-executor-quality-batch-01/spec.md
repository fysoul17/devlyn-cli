---
complexity: high
---

# iter-0102 batch-01 — scorer EQ3 re-pins + tasks EQ3-UA1/MI1/AF1/BD1

Trigger: `autoresearch/iterations/0102-executor-quality-discovery-corpus.md`
(DESIGN-FROZEN 2026-08-12), Freeze-protocol step 4 batch 1 of 8 — the only
CORPUS batch whose authorized surface includes scripts (the two scorer
re-pins; the discovery validator and pilot scorer are already frozen by
the pilot run). Nothing in this spec runs a scored, calibration, or pilot
arm.

## Preconditions (binding)

- This spec was authored from the frozen registration table BEFORE the
  pilot fired and MUST NOT be edited (registration information-boundary
  law R1-2a).
- The pilot decision file
  `~/.local/share/nx01/iter0102/pilot/DECISION` exists with the exact
  bytes `{"decision": "PROCEED"}` (no trailing newline), and the
  hash-only carrier
  `~/.local/share/nx01/iter0102/pilot/DECISION.receipt.sha256`
  contains exactly 64 lowercase hexadecimal characters (the sealed
  decision receipt's sha256) — both mechanically gated in
  Verification. Per registration R1-2b this run executes in a FRESH
  orchestrator session whose only pilot inputs are those two files —
  do NOT dereference or read the sealed receipt or any other pilot
  artifact.
- `docs/specs/iter0102-pilot/scripts.sha256` (committed by the
  orchestrator after the pilot resolve run) byte-pins
  `validate-discovery-task.py` and `score-pilot.py`; both are FROZEN
  for this run.

## Authorized surface

- `benchmark/executor-quality/scripts/score-calibration.py` — the
  enumerated EQ3 re-pin in R2 ONLY
- `benchmark/executor-quality/scripts/score-cohort.py` — the enumerated
  EQ3 re-pin in R2 ONLY
- `benchmark/executor-quality/tasks-0102/EQ3-{UA1,MI1,AF1,BD1}/**` — NEW (R1)
- ONE scoped edit in `benchmark/executor-quality/README.md` (R3)

Everything else is FROZEN — `validate-task.py`,
`validate-hard-task.py`, `validate-discovery-task.py`,
`score-pilot.py` (pins in Verification), the iter-0100 `tasks/EQ-*`,
iter-0101 `tasks-0101/EQ2-*`, and pilot `tasks-0102-pilot/EQ3P-*`
directories. A frozen-file change is a spec violation: report it as a
finding naming the file and stop that deliverable.

## Binding run constraint — difficulty-oracle prohibition

Registration § PRE-CORPUS MECHANISM PILOT binds the corpus window
(batch-01 start → candidate seal): no invocation of `claude-sonnet-5`,
`claude-opus-5`, or `claude-fable-5` may be used to estimate
manifestation-fail rates, band position, or "is this hard enough?" on
any EQ3 fixture or partial fixture. Executor and judges may implement
and run the mechanical validators/oracles only. (Pipeline judge review
of the diff is not a difficulty probe.)

## Sequencing — depth-first, one deliverable per unit

An orchestrator phase call is wall-capped at 600 s. Seven deliverables,
strictly sequenced; each must be COMPLETE — bytes landed + its own gate
green — before the next is started:

1. `score-calibration.py` EQ3 re-pin → `--self-test` exit 0
2. `score-cohort.py` EQ3 re-pin → `--self-test` exit 0
3. `EQ3-UA1` → `validate-discovery-task.py --task` exit 0
4. `EQ3-MI1` → same
5. `EQ3-AF1` → same
6. `EQ3-BD1` → same
7. R3 README edit

## R1 — four tasks (frozen authoring-table rows; fixture internals IMPLEMENT-creative)

| id | domain / edit site | local premise (class anchor) | fragment A (consumer) | fragment B (test/doc) | trigger → composed outcome | class |
|---|---|---|---|---|---|---|
| EQ3-UA1 | library lending / loan desk intake | renewal = a fresh loan | overdue escalator treats renewals as fee-clock continuations | hold-expiry test: renewal never re-enters hold queue | renewal during pending hold → failed renewal restores due date AND hold position; fee assessed exactly once | unsupported_assumption |
| EQ3-MI1 | court docket / filing clerk | amendment slots in anywhere | hearing scheduler enforces min notice from LAST amended filing | continuance test: continuance rollback restores hearing chain | amendment inside notice window → rejected amendment restores docket sequence | missed_repo_invariant |
| EQ3-AF1 | blood bank / donation intake | reserved units stay valid | crossmatch reserver holds units against orders | expiry-release test: expiry releases the order back to matching | unit expires while reserved → order re-queued; unit quarantined exactly once | absent_failure_mode |
| EQ3-BD1 | ferry manifest / vehicle check-in | weight class is check-in detail | deck load balancer recomputes from check-in weight classes | bumped-vehicle test: bump preserves queue position for next sailing | overweight bump at gate close → position preserved; fare charged exactly once | broken_dependency |

All four are index-1 → Python 3 stdlib only, no third-party deps.

Every task directory follows the discovery-shape laws of
`docs/specs/iter0102-pilot/spec.md` § R1 and registration § Task shape
— binding by reference; the phase worker MUST read both before
authoring or judging any task. Operative summary: 24-60 visible files
across ≥4 modules; edit-site byte share ≤30%; unstated goal (real
ticket prose); exactly two ordered contract artifacts at directory
distance ≥2 mapped one-to-one to `remote-a`/`remote-b`; contract-token
and outcome-token (complementarity) laws; five roles
`local-a,local-b,remote-a,remote-b,restore` with the ordered
two-binding set byte-identical across manifestations; gold all-pass;
symptom (registered local comparator) exactly
`local-a,local-b` pass + `remote-a,remote-b,restore` fail and touching
only `edit_site_dir` paths; no-patch/noop fail both locals; composed
contract carries restore-to-pre-state or exactly-once semantics.

**Class-anchor causality (registration § Corpus)**: the symptom patch
must embody the row's NAMED local premise — UA: an assumption a
consumer contradicts; MI: an invariant enforced only remotely; AF: an
omitted failure-path transition; BD: an output/state change breaking
the dependent component. Do not let one class shape dominate all four
tasks.

**Distinctness (0101 batch lessons — enforced at VERIFY)**: behavioral
tuples (edit-site component, failure trigger, restore outcome) distinct
after entity renaming — among the batch, vs all previously admitted
EQ3 tasks, the four EQ3P prototypes, the thirty-two EQ2 tasks, and the
twelve iter-0100 tasks. A renamed structural copy is a HIGH finding
even when every mechanical gate passes. Known recurring classes to
avoid: same-class structural copies, oracle workdir mutation, tie-break
coverage gaps, strawman symptom branches, patch lone-space context
lines (check with cumulative `git diff --check`).

## R2 — scorer EQ3 re-pins (enumerated; everything else byte-preserved)

The re-pin is the single byte-deterministic transformation
`sed 's/EQ2-/EQ3-/g'` applied to each frozen script — nothing else
(sol SPEC-review R1; it subsumes the registration's enumerated items:
`FROZEN_TASKS` prefix, substitution control `EQ3-UA1`/`EQ3-UA99`, and
every task-set literal; neither file contains any non-hyphenated
`EQ2` string). The EXACT post-repin outputs are pinned in
Verification:

- `score-calibration.py` →
  `58d726f378f6fd7f2c72cdc871d242eefdd4156cfe3cdcb72519b5933339cd74`
- `score-cohort.py` →
  `399b06917ad85eb6abf12a83852b3a029790fa16cb93b58d1b7efa8242da0cc9`

Any other byte in either file is a spec violation. NO other change:
`ENGINES`, `REQUIRED_ROW_FIELDS`/optional fields, seeds, `RESAMPLES`,
`REPS`, band edges, even-n median, strict 3/20 bounds, bootstrap,
terminal precedence, output schema, and exit codes all byte-preserved
by construction. Every existing self-test scenario retained and
green: band mean/median/interior/total-fail controls, catastrophic
zero-total f=1, infra-invalid UNSCORED, byte-determinism,
unknown/substituted-task rejection, unexpected-field
(`driver_sha256`) rejection, exact 3/20 boundary, duplicate run-id
rejection, 63/64 SATURATED proof, attestation and prompt-hash
controls.

## R3 — README scoped edit (CHANGE-CREATED TRUTHFULNESS)

Fix ONLY the now-stale spots: introduce the 0102 corpus stage
(`tasks-0102/`, `EQ3-*` ids, `validate-discovery-task.py`) and the
currently admitted id list (the four R1 ids); note the scorers now
gate the EQ3 set. No other README change.

## Corpus-topology gate — cumulative ID set after this batch

`tasks-0102/` contains exactly `EQ3-UA1`, `EQ3-MI1`, `EQ3-AF1`,
`EQ3-BD1`; each `task.json` `id` == directory name and `class` per the
R1 table. Batches 02-08 grow this set and re-sweep all previously
admitted EQ3 tasks.

## Out of scope

Batches 02-08 tasks; any EQ3P edit; candidate seal; calibration
apparatus and arms; matrix apparatus; DECISION file edits; reading
sealed pilot artifacts.

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
      "cmd": "python3 -c 'import pathlib; lines=[l for l in pathlib.Path(\"docs/specs/iter0102-pilot/scripts.sha256\").read_text().splitlines() if l.strip()]; paths=sorted(l.split(\"  \",1)[1] for l in lines); expected=sorted([\"benchmark/executor-quality/scripts/validate-discovery-task.py\",\"benchmark/executor-quality/scripts/score-pilot.py\"]); assert len(lines)==2 and paths==expected, paths'",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "shasum -a 256 -c docs/specs/iter0102-pilot/scripts.sha256",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "printf '58d726f378f6fd7f2c72cdc871d242eefdd4156cfe3cdcb72519b5933339cd74  benchmark/executor-quality/scripts/score-calibration.py\\n399b06917ad85eb6abf12a83852b3a029790fa16cb93b58d1b7efa8242da0cc9  benchmark/executor-quality/scripts/score-cohort.py\\n' | shasum -a 256 -c -",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "printf '769a1826eacd8b503901a2229f15b493a6d9083b1f6b2c1361c35f1b0f74e47b  benchmark/executor-quality/scripts/validate-task.py\\n1f809e33d652dea17591adce8a4c4d7d8bae2679032e7c79f805a081e01be94c  benchmark/executor-quality/scripts/validate-hard-task.py\\n' | shasum -a 256 -c -",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/score-calibration.py --self-test",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/score-cohort.py --self-test",
      "exit_code": 0,
      "timeout_sec": 600
    },
    {
      "cmd": "python3 -c 'import json,pathlib; root=pathlib.Path(\"benchmark/executor-quality/tasks-0102\"); classes={\"UA\":\"unsupported_assumption\",\"MI\":\"missed_repo_invariant\",\"AF\":\"absent_failure_mode\",\"BD\":\"broken_dependency\"}; expected={f\"EQ3-{p}1\":classes[p] for p in classes}; dirs={p.name:p for p in root.iterdir() if p.is_dir()}; assert set(dirs)==set(expected), f\"expected {sorted(expected)}, got {sorted(dirs)}\"; actual={name:json.loads((path/\"task.json\").read_text()) for name,path in dirs.items()}; assert all(data.get(\"id\")==name and data.get(\"class\")==expected[name] for name,data in actual.items()), {name:(data.get(\"id\"),data.get(\"class\")) for name,data in actual.items()}'",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-discovery-task.py --task benchmark/executor-quality/tasks-0102/EQ3-UA1",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-discovery-task.py --task benchmark/executor-quality/tasks-0102/EQ3-MI1",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-discovery-task.py --task benchmark/executor-quality/tasks-0102/EQ3-AF1",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-discovery-task.py --task benchmark/executor-quality/tasks-0102/EQ3-BD1",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "for task in benchmark/executor-quality/tasks-0102/EQ3-*; do python3 benchmark/executor-quality/scripts/validate-discovery-task.py --task \"$task\" || exit 1; done",
      "exit_code": 0,
      "timeout_sec": 600
    }
  ]
}
```
