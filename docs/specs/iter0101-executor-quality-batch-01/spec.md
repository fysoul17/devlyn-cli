---
complexity: high
---

# iter-0101 batch-01 — hard-corpus infra + first axis-pair tasks (EQ2-UA1/MI1/AF1/BD1)

Trigger: `autoresearch/iterations/0101-executor-quality-hard-corpus.md`
(DESIGN-FROZEN 2026-08-09; sol R0 ×8 + grok R1 ×5 adopted). This spec
is Freeze-protocol step 1, batch 1 of 8 — the ONLY batch whose
authorized surface includes scripts. It lands two NEW frozen scripts,
the enumerated `score-cohort.py` amendment, and the four index-1
tasks. Batches 02-08 author tasks only. Nothing in this spec runs a
scored, calibration, or pilot arm.

## Authorized surface

- `benchmark/executor-quality/scripts/validate-hard-task.py` — NEW (R2)
- `benchmark/executor-quality/scripts/score-calibration.py` — NEW (R3)
- `benchmark/executor-quality/scripts/score-cohort.py` — the
  enumerated amendment in R4 ONLY
- `benchmark/executor-quality/tasks-0101/EQ2-{UA1,MI1,AF1,BD1}/**` — NEW (R1)
- ONE scoped edit in `benchmark/executor-quality/README.md` (R5)

Everything else is FROZEN — in particular `scripts/validate-task.py`
(byte pin in Verification) and the twelve iter-0100 `tasks/EQ-*`
directories. A frozen-file change is a spec violation: if a
deliverable cannot land without editing a frozen file, do NOT edit
it; report the limitation as a finding naming the file and stop that
deliverable.

## Binding run constraint — difficulty-oracle prohibition

Registration § Difficulty calibration gate binds this run: no
invocation of `claude-sonnet-5`, `claude-opus-5`, or `claude-fable-5`
may be used to estimate manifestation-fail rates, band position, or
"is this hard enough?" on any EQ2 fixture or partial fixture.
Executor and judges may implement and run the mechanical
validators/oracles only. (Pipeline judge review of the diff is not a
difficulty probe.)

## Sequencing — depth-first, one deliverable per unit

An orchestrator phase call is wall-capped at 600 s (0100 build-B
lesson), so the eight deliverables are strictly sequenced. Each must
be COMPLETE — bytes landed + its own gate green — before the next is
started; never begin deliverable N+1 with deliverable N's gate red.

1. `validate-hard-task.py` → `--self-test` exit 0
2. `score-calibration.py` → `--self-test` exit 0
3. `score-cohort.py` amendment → `--self-test` exit 0
4. `EQ2-UA1` → `validate-hard-task.py --task` exit 0
5. `EQ2-MI1` → same
6. `EQ2-AF1` → same
7. `EQ2-BD1` → same
8. R5 README edit

## R1 — four tasks (frozen authoring-table rows; fixture internals IMPLEMENT-creative)

| id | pair | domain | component boundary | class |
|---|---|---|---|---|
| EQ2-UA1 | OR | seat reservation | hold queue vs seat map | unsupported_assumption |
| EQ2-MI1 | OR | auction bids | bid book vs settlement | missed_repo_invariant |
| EQ2-AF1 | OR | parking assignment | slot allocator vs release pool | absent_failure_mode |
| EQ2-BD1 | OI | media transcode queue | encoder feed vs manifest dedup | broken_dependency |

All four are index-1 → Python 3 stdlib only, no third-party deps.
Axis codes: O=ordering, R=rollback, I=idempotency, A=auth-order,
E=error-priority. **Axis role order is frozen**: pair code `XY` →
`axis1 = X`, `axis2 = Y`. UA1/MI1/AF1 (OR): axis1=ordering,
axis2=rollback. BD1 (OI): axis1=ordering, axis2=idempotency.

Every task directory follows
`docs/specs/iter0100-executor-quality-corpus-a/spec.md` § Layout,
§ R1, and § R2 — binding by reference; the phase worker MUST read
those sections before authoring or judging any task — PLUS these
hard-corpus laws (registration § Task shape):

- **Files**: 10-15 regular files under `visible/` (narrowed from the
  frozen validator's 5-15).
- **Manifestations**: exactly five, ids exactly `axis1-a`, `axis1-b`,
  `axis2-a`, `axis2-b`, `interaction`. axis1-a/b = two independent
  manifestations of the first axis alone; axis2-a/b = the second axis
  alone; interaction = the composed outcome.
- **Compound invariant**: ONE sentence stating both axes AND their
  composition, byte-identical in `task.json.invariant` and every
  `manifests.json` entry (the frozen validator's same-binding law
  enforces equality; compound content is VERIFY-judged). The bound
  `contract_excerpt` quote must state both axes and their composition
  in the visible contract.
- **Template instantiation** (registration § Axis-pair templates,
  instantiated in the task's own domain):
  - OR (UA1, MI1, AF1) — trigger: lower-priority entity arrives
    first; a middle entity partially applies then fails. Outcome:
    higher-priority wins AND the failed entity's tentative state is
    fully released for a later entity.
  - OI (BD1) — trigger: duplicate submission of a queued entity
    around a priority reorder. Outcome: priority order holds AND the
    duplicate is absorbed exactly-once regardless of arrival slot.
- **Patch semantics (hard-corpus law)**: `symptom.patch` passes ALL
  FOUR single-axis manifestations and fails `interaction` — a
  plausible fix that satisfies both axes independently but misses
  their composition, not a strawman. `gold.patch` passes all five.
  `noop.patch` fails.
- **BD law (EQ2-BD1)** — 0100 corpus-b § broken_dependency binds by
  reference: the goal directs change in the encoder-feed component;
  the DEPENDENT manifest-dedup component's composed contract is the
  invariant; symptom repairs the directly-visible break while the
  `interaction` manifestation on the dependent path fails.
- **Leakage**: 0100 leakage law + the same hidden-token set must be
  absent from `task.json.goal` (mechanically enforced by R2).
- **Fresh authorship + distinctness**: no reuse from
  `benchmark/executor-quality/tasks/**`,
  `benchmark/probes/drift-bait/**`, or
  `benchmark/ceiling/corpus/**`; the four behavioral tuples
  (component boundary, template trigger, template outcome) must
  remain distinct after entity renaming — among themselves and vs the
  twelve iter-0100 tasks (0100 corpus-b § Behavioral distinctness
  binds by reference). Do NOT assign a single primary-family label —
  that 0100 rule is superseded for two-axis tasks.
- Goal text: user-intent + how to run the fixture's own tests,
  nothing else.

## R2 — `scripts/validate-hard-task.py` (NEW; frozen after this run)

`python3 validate-hard-task.py --task <task_dir>` (exit 0 = admitted;
stdlib-only, deterministic, never mutates the task dir):

1. First invokes the byte-frozen `validate-task.py --task <task_dir>`
   as a subprocess (script path resolved relative to this script's
   own location); nonzero exit → fail, propagating its output.
2. **Embedded frozen ID→pair map** — all 32 registered ids, verbatim
   from the registration authoring table:
   `UA1:OR UA2:OI UA3:OA UA4:OE UA5:RI UA6:RA UA7:RE UA8:IE ·
   MI1:OR MI2:OI MI3:OA MI4:RI MI5:RE MI6:IA MI7:IE MI8:AE ·
   AF1:OR AF2:OA AF3:OE AF4:RI AF5:RA AF6:IA AF7:IE AF8:AE ·
   BD1:OI BD2:OA BD3:OE BD4:RI BD5:RA BD6:RE BD7:IA BD8:AE`
   (each key prefixed `EQ2-`). The task id (task.json `id`, which the
   frozen validator already requires; additionally require id ==
   directory name) must be a key of this map; manifestation ids must
   be exactly the five frozen roles. On success print id, pair, and
   both axis names so VERIFY can cross-check the semantic assignment.
3. `visible_files` count 10-15.
4. **Goal-leakage**: rebuild the SAME token set `validate-task.py`
   derives (manifestation ids, hidden file stems ≥4 chars, oracle
   assertion literals) and fail if any token appears
   case-insensitively in `task.json.goal`.
5. **Symptom exact pass-vector**, in a fresh temp copy of `visible/`:
   apply `patches/symptom.patch`, run the hidden oracle — `axis1-a`,
   `axis1-b`, `axis2-a`, `axis2-b` all `passed=true` AND
   `interaction` `passed=false`. Any other vector → named failure.

`--self-test` (exit 0) proves fail-closed on at least: unregistered
id; wrong role-id set; symptom passing `interaction`; symptom failing
a single-axis manifestation; a 9-file visible tree; a hidden token in
`goal` — plus one valid synthetic task (id taken from the frozen map,
built in a temp dir) passing end-to-end.

## R3 — `scripts/score-calibration.py` (NEW; frozen after this run)

Single-engine calibration-band scorer. Registration § Difficulty
calibration gate is the contract:

- Input `--ledger <jsonl>`: frozen row schema identical to
  `score-cohort.py` (only optional extra field `prompt_sha256`).
  Validity gate: exactly 64 rows = 1 engine × 32 tasks × 2 reps;
  every row `engine_requested == "claude-sonnet-5"` (exact ID); a
  non-empty `engine_attested` must equal `engine_requested`, while
  empty/null `engine_attested` is legal only when
  `catastrophic == true` (the frozen scored-estimator rule); task
  set == the frozen EQ2 32-set; unique `run_id`s;
  complete task×rep matrix; zero-total rows require
  catastrophic|incomplete; any `infra_invalid` row → UNSCORED. Any
  validity failure → terminal `UNSCORED`, exit 3.
- Per-run `f = manifestations_failed / manifestations_total` as exact
  `fractions.Fraction`; catastrophic or incomplete → `f = 1`.
  `q_cal[t]` = mean of the two reps.
- **Band verdict** (every comparison exact Fraction, never float):
  PASS iff `1/5 ≤ mean_t(q_cal) ≤ 3/5` AND `1/5 ≤ median ≤ 3/5` AND
  ≥22 of 32 tasks interior (`0 < q_cal[t] < 1`) AND ≤2 tasks with
  `q_cal[t] = 1`. **Even-n median, mandatory**: sort ascending;
  `median = (q_sorted[15] + q_sorted[16]) / 2` (0-based).
- Output: ONE deterministic JSON verdict — band, mean and median as
  exact `"n/d"` strings, interior_count, total_fail_count, per-task
  `q_cal`, engine, ledger_sha256. Exit 0 = band PASS; exit 2 = valid
  evaluation, band MISS; exit 3 = UNSCORED. Same ledger → byte-
  identical verdict bytes.
- `--self-test` (exit 0) covering at least: (a) band-PASS control;
  (b) mean below 1/5; (c) mean above 3/5; (d) median below 1/5 with
  mean in-band; (e) median above 3/5 with mean in-band; (f) interior
  count <22; (g) total-fail count >2; (h) UNSCORED on an
  infra-invalid row; (i) byte-determinism of the band verdict;
  (j) a catastrophic zero-total row with null `engine_attested` is
  scored as `f = 1`, not UNSCORED.
  In (d)/(e) the mean must sit in-band so the median conjunct is
  load-bearing.

## R4 — `scripts/score-cohort.py` enumerated amendment

Wholesale-frozen except EXACTLY these (registration § Metrics):

1. `FROZEN_TASKS = {f"EQ2-{prefix}{index}" for prefix in
   ("UA", "MI", "AF", "BD") for index in range(1, 9)}` (32 ids; the
   existing class parser already handles the `EQ2-` prefix —
   seat-verified, no `task_class` change).
2. `--expected-tasks` default 12 → 32.
3. Self-test controls re-derived for N=32:
   - INCONCLUSIVE_AT_PILOT_N control → 16 zeros + 16 × 2/5.
   - CI-touch (upper-boundary) control → 7 × 2/5 + 25 zeros; assert
     `ci == [0.0375, 0.15]` (exact interval `[3/80, 3/20]`; upper
     bound exactly 3/20 under the frozen bootstrap — verified by
     execution twice, sol + orchestrator).
   - Substitution control → `EQ2-UA1` → `EQ2-UA99`.
   - SATURATED boundary proof at 63/64: the all-zeros control PLUS a
     control where exactly one run of one engine is non-clean —
     still SATURATED.
   - The four 0100 repro controls, re-derived against the EQ2 set:
     exact-δ `[3/20, 3/20]` → INCONCLUSIVE_AT_PILOT_N; two rows
     sharing one `run_id` → UNSCORED; a timeout-shaped catastrophic
     zero-total null-attested row → scored `f = 1`; one row carrying
     unexpected field `driver_sha256` → UNSCORED.
   - Retained non-repro controls: attestation mismatch → UNSCORED;
     infra-invalid → UNSCORED; `prompt_sha256` tolerance;
     byte-determinism; bad-control non-reachability.
4. The one user-facing string whose "12" becomes wrong:
   `"task is not in the frozen 12-task set"` → `"task is not in the
   frozen task set"`.

NO other change: `ENGINES`, `REQUIRED_ROW_FIELDS`/optional fields,
`SEED 20260809`, `RESAMPLES 100000`, `REPS`, percentile method,
bootstrap, `select_terminal` thresholds and precedence, output
schema, exit codes all byte-preserved.

## R5 — README scoped edit (CHANGE-CREATED TRUTHFULNESS)

This run makes `benchmark/executor-quality/README.md` stale in two
places; fix ONLY those:

- Corpus-stage paragraph + validate commands: introduce the 0101
  hard corpus (`tasks-0101/`, EQ2 ids, `validate-hard-task.py`
  wrapping the frozen validator, `score-calibration.py`) alongside
  the retained 0100 corpus text; per-task validate commands for the
  EQ2 set may enumerate only the currently admitted batch-01 ids.
- § Score a cohort: 48-row/12-task → 128-row/32-task EQ2 matrix.
- Binding-rules pointer gains iteration 0101 alongside 0100.

No other README change.

## Corpus-topology gate — cumulative ID set after this batch

`tasks-0101/` contains exactly `EQ2-UA1`, `EQ2-MI1`, `EQ2-AF1`,
`EQ2-BD1`; each `task.json` `id` == directory name and `class` per
the R1 table. Mechanical command below; batches 02-08 grow this set
and re-sweep all previously admitted EQ2 tasks.

## Out of scope

Batches 02-08 tasks; candidate seal / tree hash / flat manifest;
calibration driver/runner and the 64-run sonnet arm; matrix
apparatus changes (`TASKS_ROOT`, `BOUND_SEC`, `driver_sha256`
deletion are calibration/matrix freeze steps, NOT this run); recert
`executor_quality` fold-in; any edit to `validate-task.py` or the
twelve iter-0100 task directories.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "printf '769a1826eacd8b503901a2229f15b493a6d9083b1f6b2c1361c35f1b0f74e47b  benchmark/executor-quality/scripts/validate-task.py\\n' | shasum -a 256 -c -",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-task.py --self-test",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-hard-task.py --self-test",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/score-calibration.py --self-test",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/score-cohort.py --self-test",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 -c 'import json,pathlib; root=pathlib.Path(\"benchmark/executor-quality/tasks-0101\"); expected={\"EQ2-UA1\":\"unsupported_assumption\",\"EQ2-MI1\":\"missed_repo_invariant\",\"EQ2-AF1\":\"absent_failure_mode\",\"EQ2-BD1\":\"broken_dependency\"}; dirs={p.name:p for p in root.iterdir() if p.is_dir()}; assert set(dirs)==set(expected), f\"task directories: expected {sorted(expected)}, got {sorted(dirs)}\"; actual={name:json.loads((path/\"task.json\").read_text()) for name,path in dirs.items()}; assert all(data.get(\"id\")==name and data.get(\"class\")==expected[name] for name,data in actual.items()), {name:(data.get(\"id\"),data.get(\"class\"),expected[name]) for name,data in actual.items() if data.get(\"id\")!=name or data.get(\"class\")!=expected[name]}'",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-hard-task.py --task benchmark/executor-quality/tasks-0101/EQ2-UA1",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-hard-task.py --task benchmark/executor-quality/tasks-0101/EQ2-MI1",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-hard-task.py --task benchmark/executor-quality/tasks-0101/EQ2-AF1",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-hard-task.py --task benchmark/executor-quality/tasks-0101/EQ2-BD1",
      "exit_code": 0,
      "timeout_sec": 300
    }
  ]
}
```
