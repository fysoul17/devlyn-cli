---
complexity: high
---

# iter-0100 corpus build A — executor-quality instrument: infra + 3 exemplar tasks

Trigger: `autoresearch/iterations/0100-main-ai-executor-quality.md`
(REGISTERED 2026-08-09, R1 REVISE ×2 adopted). This spec builds the
instrument skeleton and the first 3 of 12 tasks; the remaining 9 tasks
are a separate follow-up spec (corpus build B) reusing the validated
template. Nothing in this spec runs a scored arm.

Authorized surface: `benchmark/executor-quality/**` ONLY (new
directory). No edits to skills, recert-seats.sh, seat-matrix.py, or
any existing benchmark family in this run.

## Layout (create)

```
benchmark/executor-quality/
  README.md                 — operator guide: what the cell measures, commands, binding rules pointer to iterations/0100
  scripts/
    validate-task.py        — per-task smoke + conformance gate (spec R2)
    score-cohort.py         — frozen cohort scorer + --self-test (spec R3)
  tasks/
    EQ-UA1/  EQ-MI1/  EQ-AF1/   — exemplar tasks (spec R1)
```

Per task directory:

```
  task.json      — {id, class, invariant (one sentence), goal (prompt text), visible_files:[...], contract_excerpt:{file, sha256, quote}}
  visible/       — the fixture the measured arm will see (5-15 files, self-contained)
  hidden/
    oracle.py    — deterministic manifestation checks, run offline: `python3 oracle.py <workdir>` → JSON {manifestations:[{id, invariant, passed}]}
    manifests.json — manifestation → invariant/class map + visible-contract binding {file, sha256, quote}
  patches/
    gold.patch   — invariant-level fix (applies to visible/ copy)
    symptom.patch— plausible happy-path-only fix
    noop.patch   — empty/no-behavior-change patch
```

## R1 — three exemplar tasks (one each: unsupported_assumption, missed_repo_invariant, absent_failure_mode)

Each task is a small self-contained mini-project (Python 3 stdlib OR
Node ≥20 no-deps; 5-15 files under `visible/`) whose goal REQUIRES a
design decision materialized as ONE primary behavioral invariant
(ordering / rollback / idempotency / auth-order / error-priority
family). Binding quality bars:

- The hidden oracle checks the invariant via **≥2 independent
  manifestations** (different input shapes or paths — never the same
  assertion twice). `oracle.py` is deterministic, stdlib-only, makes
  no network/LLM calls, and never mutates `visible/`.
- **Fairness/conformance**: the goal text must NOT name the invariant
  outright, but the invariant MUST be derivable from visible repo
  evidence (a doc, test, or contract file inside `visible/`).
  `task.json.contract_excerpt` binds that evidence: the `quote` string
  must appear literally in the named visible file, and `sha256` must
  match that file's bytes. `hidden/manifests.json` carries the same
  binding per manifestation (0070a hidden-conformance lineage).
- **Patch semantics** (0100 freeze law): `gold.patch` → ALL
  manifestations pass. `noop.patch` → oracle FAILS. `symptom.patch` →
  passes ≥1 manifestation AND fails ≥1 manifestation of the SAME
  invariant (a completely broken symptom patch is a spec violation —
  it must be a plausible happy-path fix, not a strawman).
- No ground-truth leakage: no `hidden/` filename, manifestation id, or
  oracle assertion string may appear anywhere under `visible/`.
- Goal text (task.json `goal`) is frozen prompt material: it states
  the user-intent (what to build/fix) + how to run the fixture's own
  tests, nothing else.

## R2 — `scripts/validate-task.py`

`python3 validate-task.py --task <task_dir>` (exit 0 = task admitted):

1. Structural: task.json schema, all `visible_files` exist, hashes match.
2. Conformance: contract_excerpt quote found in cited visible file;
   manifests.json bindings valid; leakage scan (hidden filenames,
   manifestation ids, oracle assertion literals absent from visible/).
3. Smoke, each in a fresh temp copy of `visible/` (never in-place):
   no patch → oracle fails; `noop.patch` → oracle fails;
   `gold.patch` → all manifestations pass; `symptom.patch` → ≥1 pass
   AND ≥1 fail on the same invariant.
4. Any failure → exit 1 with a one-line named reason per failure.

`--self-test` (exit 0): builds synthetic tasks in a temp dir proving
the gate FAILS closed on: leaked oracle string, hash mismatch, missing
excerpt, strawman symptom patch (fails all), gold patch that misses a
manifestation — plus one fully valid synthetic task passing end-to-end.

## R3 — `scripts/score-cohort.py` (frozen statistics; registration § Metrics/Decision rule is the contract)

Input: ledger JSONL, one row per run:
`{run_id, task, rep, engine_requested, engine_attested, manifestations_total, manifestations_failed, catastrophic, incomplete, infra_invalid, wall_ms}`.

- Validity gate (before any statistic): exactly 2 engines × 12 tasks ×
  2 reps (48 rows) unless `--expected-tasks N` overrides for pilot;
  every row's `engine_attested` == `engine_requested` (exact model
  ID); any `infra_invalid` row → cohort terminal `UNSCORED` (exit 3).
- Per run `f = manifestations_failed / manifestations_total`;
  catastrophic or incomplete → `f = 1.0`. `q[e,t]` = mean of reps;
  `R[e]` = mean over tasks; `d[t] = q[opus,t] − q[fable,t]`;
  `Δ = mean(d[t])`. 95% CI via paired-task bootstrap: resample the 12
  task-pairs with replacement, **seed 20260809, 100000 resamples**,
  percentile interval. Reps/manifestations never increase N.
- Terminal precedence (exactly one, after validity):
  1. `SATURATED` — both engines ≥ 23/24 runs with `f == 0`.
  2. `H1_CONFIRMED` — CI lower bound of Δ > 0.15.
  3. `H1_MATERIAL_GAP_REFUTED` — CI upper bound of Δ < 0.15.
  4. `INCONCLUSIVE_AT_PILOT_N` — otherwise (CI contains 0.15).
- Output: JSON verdict {terminal, delta, ci:[lo,hi], R per engine,
  completion_rate per engine, per-task d[t], per-class failed-task
  counts, seed, resamples, ledger sha256}. Deterministic: same ledger
  + seed → byte-identical verdict JSON.
- `--self-test` (exit 0): synthetic ledgers driving EACH terminal
  (1-4) + UNSCORED + attestation-mismatch rejection + determinism
  check (two runs byte-equal) + known-good/bad separation (an
  obviously-bad synthetic engine must not reach SATURATED/REFUTED).

## Out of scope (build B / later)

Remaining 9 tasks; corpus digest sealing; arm runner; recert-seats.sh
`executor_quality` suite; seat-matrix.py collector. Do not touch.

## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-task.py --self-test",
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
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/score-cohort.py --self-test",
      "exit_code": 0,
      "timeout_sec": 180
    }
  ]
}
```
