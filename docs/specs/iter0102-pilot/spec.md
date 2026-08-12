---
complexity: high
---

# iter-0102 pilot — discovery-shape infra + 4 DISCARDED prototypes (EQ3P-UA1/MI1/AF1/BD1)

Trigger: `autoresearch/iterations/0102-executor-quality-discovery-corpus.md`
(DESIGN-FROZEN 2026-08-12; sol R0 ×8 + grok R1 ×5 adopted). This spec is
Freeze-protocol step 3 — the ONLY run whose authorized surface includes
`validate-discovery-task.py` and `score-pilot.py`. It lands those two NEW
frozen scripts and the four prototype tasks. The prototypes are DISCARDED
instruments: never corpus members; their domains and behavioral tuples are
banned from the corpus. Nothing in this spec runs a scored, calibration,
or pilot arm — the 8-run sonnet pilot arm is fired by the orchestrator
AFTER this run completes and its outputs are sealed.

## Authorized surface

- `benchmark/executor-quality/scripts/validate-discovery-task.py` — NEW (R2)
- `benchmark/executor-quality/scripts/score-pilot.py` — NEW (R3)
- `benchmark/executor-quality/tasks-0102-pilot/EQ3P-{UA1,MI1,AF1,BD1}/**` — NEW (R1)
- ONE scoped edit in `benchmark/executor-quality/README.md` (R4)

Everything else is FROZEN — in particular `scripts/validate-task.py`,
`scripts/validate-hard-task.py`, `scripts/score-calibration.py`,
`scripts/score-cohort.py` (byte pins in Verification), the twelve
iter-0100 `tasks/EQ-*` and thirty-two iter-0101 `tasks-0101/EQ2-*`
directories. A frozen-file change is a spec violation: if a deliverable
cannot land without editing a frozen file, do NOT edit it; report the
limitation as a finding naming the file and stop that deliverable.

## Binding run constraint — difficulty-oracle prohibition (pilot-scoped)

No invocation of `claude-sonnet-5`, `claude-opus-5`, or `claude-fable-5`
may be used to estimate manifestation-fail rates, difficulty, or "is this
hard enough?" on any EQ3P fixture or partial fixture. Prototypes are
authored BLIND, exactly like corpus tasks — a sonnet-tuned prototype
corrupts the mechanism screen the pilot exists to provide. Executor and
judges may implement and run the mechanical validators/oracles only.
(Pipeline judge review of the diff is not a difficulty probe.)

## Sequencing — depth-first, one deliverable per unit

An orchestrator phase call is wall-capped at 600 s. Seven deliverables,
strictly sequenced; each must be COMPLETE — bytes landed + its own gate
green — before the next is started:

1. `validate-discovery-task.py` → `--self-test` exit 0
2. `score-pilot.py` → `--self-test` exit 0
3. `EQ3P-UA1` → `validate-discovery-task.py --task` exit 0
4. `EQ3P-MI1` → same
5. `EQ3P-AF1` → same
6. `EQ3P-BD1` → same
7. R4 README edit

## R1 — four prototype tasks (frozen rows; fixture internals IMPLEMENT-creative)

| id | domain / edit site | local premise (class anchor) | fragment A (consumer) | fragment B (test/doc) | trigger → composed outcome | class |
|---|---|---|---|---|---|---|
| EQ3P-UA1 | campground bookings / site assigner | site swap is free | seasonal pricing engine bills site-class deltas | cancel test: cancellation restores availability + deposit once | swap across price class then cancel → deposit and availability restored exactly once | unsupported_assumption |
| EQ3P-MI1 | car rental / return intake | return closes immediately | damage biller requires photos-before-close ordering | early-return test: early return releases the reservation block | early return with pending damage review → block released once; final bill after review | missed_repo_invariant |
| EQ3P-AF1 | cinema concessions / combo editor | combos deplete independently | inventory decrementer maps combos to components | spoilage test: expiry voids combos, restores substitutable stock | component expiry mid-shift → combo availability recomputed; spoilage recorded once | absent_failure_mode |
| EQ3P-BD1 | community garden / plot assigner | abandonment frees a plot | water-share scheduler consumes plot assignments | abandonment test: return to lottery preserves waitlist order | abandonment mid-season → water shares rebalanced; waitlist order preserved | broken_dependency |

**Language (frozen)**: registration per-index law — index 1 is odd →
ALL FOUR prototypes are Python 3 stdlib, no third-party deps. Hidden
`oracle.py` is Python 3 stdlib, deterministic, offline, and must not
mutate the workdir it is given.

**Discovery-shape laws** (registration § Task shape — binding verbatim;
restated operatively):

- **Fixture**: 24-60 regular files under `visible/`, spread across ≥4
  top-level modules (non-symlink immediate child directories of
  `visible/` each containing ≥1 registered regular file). Raw bytes of
  registered files under `edit_site_dir` ≤30% of all registered visible
  bytes.
- **`task.json` exact schema**: `id`, `class`, `goal`, `invariant`
  (the composed contract sentence — hidden-side binding only),
  `visible_files`, `edit_site_dir`, `contract_artifacts` (ordered
  array, length exactly 2: index 0 = fragment A path, index 1 =
  fragment B path), `contract_tokens_a`, `contract_tokens_b` (each ≥3
  unique non-generic tokens), `outcome_tokens_a`, `outcome_tokens_b`
  (nonempty, disjoint, union ≥3 unique tokens). NO `contract_excerpt`
  field.
- **Unstated**: the goal reads like a real ticket — observed behavior,
  desired behavior, how to run the fixture's own tests, nothing else.
  Neither the goal nor any file under `edit_site_dir` states the
  contract.
- **Distance law**: each contract artifact sits at directory distance
  ≥2 from `edit_site_dir` (edge count through the lowest common
  ancestor after normalized safe resolution under `visible/`).
- **Token laws** (UTF-8, Unicode-casefolded, whole lexical tokens):
  `contract_tokens_a` appear in artifact A, `contract_tokens_b` in
  artifact B; BOTH sets appear in ZERO of: goal, any file under
  `edit_site_dir`, any relative path or filename under
  `edit_site_dir`. Goal contains no `contract_artifacts` path.
- **Complementarity law**: every `outcome_tokens_a` token appears in
  artifact A, every `outcome_tokens_b` token in artifact B; ≥1 token
  of `outcome_tokens_a` ABSENT from artifact B and ≥1 of
  `outcome_tokens_b` ABSENT from artifact A; NEITHER artifact contains
  ALL union tokens; every union token appears in the `invariant`
  sentence. Neither artifact alone may state or imply the composed
  restore/exactly-once outcome.
- **Manifestations**: exactly five, ids exactly `local-a`, `local-b`,
  `remote-a`, `remote-b`, `restore`; ONE composed contract sentence
  byte-identical in `task.json.invariant` and every `manifests.json`
  entry; every manifestation carries the SAME ordered two-binding set
  (for each artifact: path + lowercase SHA-256 + exact nonempty quote
  present in that artifact). `remote-a` checks fragment A's consumer,
  `remote-b` fragment B's, `restore` their composition. Every task's
  composed contract involves restore-to-pre-state or exactly-once
  semantics across a failure path.
- **Patch vectors**: `gold.patch` → all five pass. `symptom.patch` =
  the registered local comparator patch → exactly `local-a` PASS,
  `local-b` PASS, `remote-a` FAIL, `remote-b` FAIL, `restore` FAIL,
  and it modifies ONLY paths under `edit_site_dir`. It must be the
  best plausible LOCAL fix for the ticket, not a strawman. Pristine
  (no patch) and `noop.patch` must each fail BOTH `local-*` roles.
- **Fresh authorship + distinctness**: no reuse from
  `benchmark/executor-quality/tasks/**`, `tasks-0101/**`,
  `benchmark/probes/drift-bait/**`, or `benchmark/ceiling/corpus/**`;
  the four behavioral tuples (edit-site component, failure trigger,
  restore outcome) must remain distinct after entity renaming — among
  themselves and vs the twelve iter-0100 and thirty-two iter-0101
  tasks. A renamed structural copy is a HIGH finding even when every
  mechanical gate passes.

## R2 — `scripts/validate-discovery-task.py` (NEW; frozen after this run)

`python3 validate-discovery-task.py --task <task_dir>` (exit 0 =
admitted; stdlib-only, deterministic, never mutates the task dir).
STANDALONE — it does NOT invoke `validate-task.py`. Registration
§ Validator is the contract; its 16 laws verbatim:

1. Exact required files: `task.json`, `hidden/oracle.py`,
   `hidden/manifests.json`, `patches/{gold,noop,symptom}.patch`.
2. Exact `task.json` schema (R1 above); nonempty strings; class enum
   {unsupported_assumption, missed_repo_invariant, absent_failure_mode,
   broken_dependency}; id == directory name; id registered in the
   embedded frozen ID table (this run: the four `EQ3P-*1` ids with
   their R1 classes; the thirty-two `EQ3-*` corpus ids with their
   registration-table classes — embed BOTH so the same script gates
   the corpus batches unchanged).
3. Safe POSIX-relative paths under `visible/`; no absolute paths,
   `..`, escapes, symlinks, or non-regular files anywhere in the task
   tree.
4. Unique, exhaustive `visible_files` matching every regular visible
   file.
5. Exact ordered two-binding schema — each manifestation entry carries
   `contract_bindings`: an ordered array of exactly two objects
   `{"file": "<visible-relative path>", "sha256": "<64 lowercase
   hex>", "quote": "<exact fragment>"}` (index 0 = artifact A, index
   1 = artifact B, matching `task.json.contract_artifacts` order);
   hash match against file bytes; UTF-8; nonempty quote present in
   the artifact.
6. Exact manifest root/entry schema (sol SPEC-review REC-5 skeleton):
   `{"manifestations": [{"id": "<role>", "class": "<task class>",
   "invariant": "<composed sentence>", "contract_bindings": [<the two
   binding objects>]}, ...]}` — exactly five entries, ids exactly the
   five registered roles, no other fields.
7. Every manifestation matches the task invariant, class, and the SAME
   ordered two-binding set.
8. Leakage scanning of manifestation ids, hidden filename stems, and
   assertion/comparison literals ≥12 characters against relative
   visible paths, visible UTF-8 contents, and goal text.
9. Oracle exit 0 within a fixed timeout; stdout is exactly one JSON
   object `{"manifestations": [{"id": "<role>", "passed":
   true|false}, ...]}` — exactly five entries whose ids match the
   manifests, boolean `passed`, no duplicates, no other fields.
10. Patch utility availability; fail-closed application on a pristine
    copy via `patch -p1 --forward --batch`.
11. Independent pristine cases: no-patch, noop, gold, symptom.
12. Registered pass-vectors: gold all-pass; symptom exactly
    `local-a`/`local-b` pass + `remote-a`/`remote-b`/`restore` fail;
    no-patch and noop each fail both `local-*`.
13. Discovery topology: file count 24-60, ≥4 modules, language parity
    per index (odd Python / even Node), distance ≥2 per artifact,
    token presence/absence laws incl. path/filename scan, goal-path
    law, edit-site byte share ≤30%, artifact↔remote-role one-to-one
    order, symptom-patch locality (only paths under `edit_site_dir`).
14. Filesystem snapshot before/after EVERY oracle invocation; any
    created, deleted, or modified path (incl. `__pycache__`) fails
    validation. Oracle invocations in self-tests set
    `PYTHONDONTWRITEBYTECODE=1` so valid Python tasks do not
    false-fail on `__pycache__`.
15. Complementarity law (R1 above) — outcome-token partition
    presence/absence checks across the two artifacts and the
    invariant sentence.
16. `--self-test` (exit 0): ≥1 named fail-closed scenario per law
    family — missing required file; bad schema; path escape/symlink;
    incomplete `visible_files`; binding hash mismatch; wrong role
    set; divergent two-binding set; goal/token leakage; oracle
    non-zero-exit/non-JSON; patch apply failure; wrong pass-vector
    for each of gold/symptom/no-patch/noop; each topology clause
    (file count, modules, distance, byte-share, language parity,
    token path scan, symptom locality, artifact-role order); oracle
    mutation residue; complementarity violation — PLUS one valid
    end-to-end Python task and one valid Node task green path (both
    built synthetically in a temp dir with ids from the embedded
    table).

On success print id, class, edit_site_dir, and both artifact paths so
VERIFY can cross-check the semantic assignment.

## R3 — `scripts/score-pilot.py` (NEW; frozen after this run)

Pilot-decision scorer. Registration § PRE-CORPUS MECHANISM PILOT is
the contract:

- Input `--ledger <jsonl>`: frozen row schema identical to
  `score-calibration.py` (REQUIRED fields `run_id, task, rep,
  engine_requested, engine_attested, manifestations_total,
  manifestations_failed, catastrophic, incomplete, infra_invalid,
  wall_ms`; only optional extra `prompt_sha256`). Validity gate:
  exactly 8 rows = 1 engine × 4 tasks × 2 reps; every row
  `engine_requested == "claude-sonnet-5"`; non-empty
  `engine_attested` must equal it; empty/null attested legal only
  when `catastrophic == true`; task set == the four `EQ3P-*1` ids;
  unique `run_id`s; complete task×rep matrix; zero-total rows require
  catastrophic|incomplete; any `infra_invalid` row → UNSCORED exit 3.
- Per-run `f = Fraction(manifestations_failed, manifestations_total)`
  with `manifestations_total` required equal to 5 on valid non-flag
  rows; `catastrophic` or `incomplete` on a VALID attempt → `f = 1`.
  `q_pilot[t]` = exact two-rep mean. All comparisons exact
  `fractions.Fraction`, never float.
- **Decision rule**: PROCEED iff `mean(q_pilot) ≥ 1/10` AND
  `mean(q_pilot) ≤ 3/5` AND ≥3 of 4 prototypes have
  `0 < q_pilot < 1` AND no prototype has `q_pilot = 1`. Else REJECT
  (→ MECHANISM_REJECTED terminal).
- Output: ONE deterministic JSON verdict — `decision`
  (`PROCEED`/`REJECT`), `mean` and per-task `q_pilot` as exact
  `"n/d"` strings, `engine`, `ledger_sha256`. Exit 0 = PROCEED,
  exit 2 = valid REJECT, exit 3 = UNSCORED. Same ledger →
  byte-identical verdict bytes.
- `--self-test` (exit 0) covering at least: (a) PROCEED control;
  (b) mean below 1/10; (c) mean above 3/5; (d) interior count 2 of 4;
  (e) one prototype q_pilot = 1; (f) UNSCORED on infra-invalid;
  (g) UNSCORED on wrong row count / wrong task set / duplicate
  run_id; (h) catastrophic zero-total null-attested row scored f=1;
  (i) unexpected extra field (`driver_sha256`) → UNSCORED;
  (j) byte-determinism of the verdict; (k) exact-boundary admission:
  mean exactly 1/10 → PROCEED and mean exactly 3/5 → PROCEED (both
  inclusive edges, exact Fraction); (l) a valid non-flag row with
  `manifestations_total != 5` → UNSCORED (sol SPEC-review R4).

## R4 — README scoped edit (CHANGE-CREATED TRUTHFULNESS)

This run makes `benchmark/executor-quality/README.md` stale; fix ONLY:
introduce the 0102 pilot stage (`tasks-0102-pilot/`, `EQ3P-*` ids,
`validate-discovery-task.py` standalone, `score-pilot.py`) alongside
the retained 0100/0101 text, with a one-sentence note that the
prototypes are discarded instruments and the corpus lives in
`tasks-0102/` (authored by later batches). No other README change.

## Corpus-topology gate

`tasks-0102-pilot/` contains exactly `EQ3P-UA1`, `EQ3P-MI1`,
`EQ3P-AF1`, `EQ3P-BD1`; each `task.json` `id` == directory name and
`class` per the R1 table. `tasks-0102/` does not exist yet.

## Out of scope

Corpus batches 01-08 and any `EQ3-*` task; the 8-run pilot arm and its
apparatus; pilot manifest seal; DECISION file; candidate seal;
calibration; matrix; any edit to the four frozen 0100/0101 scripts.

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
      "cmd": "python3 benchmark/executor-quality/scripts/validate-discovery-task.py --self-test",
      "exit_code": 0,
      "timeout_sec": 600
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/score-pilot.py --self-test",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 -c 'import json,pathlib; root=pathlib.Path(\"benchmark/executor-quality/tasks-0102-pilot\"); classes={\"UA\":\"unsupported_assumption\",\"MI\":\"missed_repo_invariant\",\"AF\":\"absent_failure_mode\",\"BD\":\"broken_dependency\"}; expected={f\"EQ3P-{p}1\":classes[p] for p in classes}; dirs={p.name:p for p in root.iterdir() if p.is_dir()}; assert set(dirs)==set(expected), f\"expected {sorted(expected)}, got {sorted(dirs)}\"; assert not pathlib.Path(\"benchmark/executor-quality/tasks-0102\").exists(), \"tasks-0102 must not exist yet\"; actual={name:json.loads((path/\"task.json\").read_text()) for name,path in dirs.items()}; assert all(data.get(\"id\")==name and data.get(\"class\")==expected[name] for name,data in actual.items()), {name:(data.get(\"id\"),data.get(\"class\")) for name,data in actual.items()}'",
      "exit_code": 0,
      "timeout_sec": 60
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-discovery-task.py --task benchmark/executor-quality/tasks-0102-pilot/EQ3P-UA1",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-discovery-task.py --task benchmark/executor-quality/tasks-0102-pilot/EQ3P-MI1",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-discovery-task.py --task benchmark/executor-quality/tasks-0102-pilot/EQ3P-AF1",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 benchmark/executor-quality/scripts/validate-discovery-task.py --task benchmark/executor-quality/tasks-0102-pilot/EQ3P-BD1",
      "exit_code": 0,
      "timeout_sec": 300
    }
  ]
}
```
