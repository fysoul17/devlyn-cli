---
complexity: high
---

# iter-0105 pilot — repo-scale discovery infra + 4 DISCARDED prototypes (EQ4P-UA1/MI1/AF1/BD1)

Trigger: `autoresearch/iterations/0105-repo-scale-discovery-corpus.md`
(DESIGN-FROZEN 2026-08-20). This is Sequencing step 3. The lane is **terra
direct-drive (single writer) + trio verification**, NOT a resolve run. It
lands the derived validator, the pilot scorer, and four DISCARDED prototype
tasks before the 8-run sonnet pilot is fired. The prototypes are never corpus
members; their domains and behavioral tuples are banned from the corpus.

## Authorized surface

- `benchmark/executor-quality/scripts/validate-repo-task.py` — NEW (R2)
- `benchmark/executor-quality/scripts/score-pilot-0105.py` — NEW (R3)
- `benchmark/executor-quality/tasks-0105-pilot/EQ4P-{UA1,MI1,AF1,BD1}/**` — NEW (R1)
- ONE scoped edit in `benchmark/executor-quality/README.md` (R4)

Everything else is FROZEN. In particular, `validate-task.py`,
`validate-hard-task.py`, `validate-discovery-task.py`, `score-pilot.py`,
`score-calibration.py`, and `score-cohort.py`, the 0100/0101/0102 task
directories, the generator, and this registration are not authorized. A
frozen-file change is a finding that names the file and stops that
deliverable.

## Binding constraints

**Difficulty-oracle prohibition (pilot-scoped).** Do not invoke
`claude-sonnet-5`, `claude-opus-5`, `claude-opus-4-8`, or `claude-fable-5`
to estimate difficulty, manifestation-fail rates, or “hard enough?” for an
EQ4P fixture or partial fixture. Mechanical validators/oracles and trio diff
review are permitted; a model difficulty probe is not.

Work depth-first: R2 validator self-test; R3 scorer self-test; EQ4P-UA1,
EQ4P-MI1, EQ4P-AF1, EQ4P-BD1 (each validator-green); then R4 README. Each
unit must land and pass its own gate before the next. No scored, calibration,
or pilot arm runs in this lane.

## R1 — four prototype tasks (frozen rows; fixture internals IMPLEMENT-creative)

| id | domain / edit site | local premise (class anchor) | fragment A (consumer) | fragment B (test/doc) | trigger → composed restore outcome | class |
|---|---|---|---|---|---|---|
| EQ4P-UA1 | space-launch range / payload-window allocator | UA assumption: a payload swap frees the prior trajectory slot | `range_safety/trajectory/reservation_consumer.py` — reservation consumer retains the trajectory slot until range safety accepts the swap | `launch/operations/test_weather_hold.py` — operations test asserts a weather hold retains the hazard notice | weather hold after payload swap → original launch allocation restored; hazard notice retained once | unsupported_assumption |
| EQ4P-MI1 | currency circulation / note-fitness policy editor | MI missed invariant: destruction eligibility follows the signed fitness-policy version | `destruction_ledger/authorizations/policy_consumer.py` — authorization consumer permits destruction only for the signed fitness-policy version | `vault/system/test_unsigned_policy.py` — vault test asserts an unsigned replacement leaves authorization unused | unsigned policy replacement → prior fitness policy restored; destruction authorization remains unused | missed_repo_invariant |
| EQ4P-AF1 | heritage preservation / facade-permit change processor | AF absent failure transition: a withdrawn structural report has no permit-hold transition | `inspection_holds/permits/report_consumer.py` — permit consumer keeps a provisional facade approval contingent on the structural report | `conservation/system/test_withdrawn_report.py` — conservation test asserts withdrawal releases the inspection appointment | report withdrawn after provisional approval → permit state restored; inspection appointment released once | absent_failure_mode |
| EQ4P-BD1 | remote examination services / accommodation allocator | BD breaking change: changing an accommodation alters the proctor-scheduling consumer's seat plan | `proctor_scheduling/seats/accommodation_consumer.py` — seat consumer assigns proctors from the currently approved accommodation | `accessibility/system/test_expired_accommodation.py` — accessibility test asserts expiry reopens the proctor seat | accommodation expiry after seat assignment → prior accommodation restored; proctor seat reopens once | broken_dependency |

All four are Python 3 stdlib only, deterministic and offline. Hidden
`oracle.py` must not mutate its given workdir. Class anchors are binding:
UA is a named local assumption contradicted by a consumer; MI an invariant
absent locally and enforced only remotely; AF an omitted failure-path
transition; BD an output/state change that violates a dependent contract.

Every task uses `TASKS_ROOT_PILOT = benchmark/executor-quality/tasks-0105-pilot`
and the full 0105 law set. L-R1 requires at least 120 visible regular files
and 2,000,000 visible source bytes. L-R2 requires stdlib-`ast` import-graph
distance at least 4 edges from the edit-site module set to **each** contract
artifact, registered `dependency_edges` equal derived edges, each registered
`contract_paths` path, and directory distance at least 4. If and only if the
freeze-round graph-deriver self-test bar fails, use the pre-committed,
reported distance-only fallback and narrow the claim to distance plus
distractor-mass discovery; never silently fall back. L-R3 requires at least
10 decoy modules, none an artifact or L-R2-path node, each directory-distance
at most 2 and strictly closer than every artifact; distinct case-folded
whole-word `(file, token)` hits over both contract-token sets exceed artifact
hits, with a hit in each decoy. In a temporary copy, neutralizing every
registered decoy-token occurrence must leave no-patch/noop/symptom/gold oracle
vectors identical. L-R4 carries the mechanical two-fragment
complementarity law.

The exact task schema adds exactly three frozen fields and no others:
`dependency_edges`, `contract_paths`, and `decoy_artifacts`. The generator
may emit only non-treatment mass through the pinned
`gen-repo-skeleton.py` (`213594c623ccc8abfa42044489f89a97352a89d2dde26249d7de35e0b51ed8d7`),
with per-task parameters. It emits a sealed `generator-inventory.json` of
payload-file relative paths and sha256 values; the inventory excludes itself.
The validator rejects an inventory path under `edit_site_dir`, a contract
artifact, a `decoy_artifacts` entry, or any `contract_paths` node.

Carry the 0102 discovery laws as mechanically reparameterized: an unstated
real-ticket goal; exactly two ordered artifacts and byte-identical ordered
bindings across `local-a`, `local-b`, `remote-a`, `remote-b`, `restore`; gold
passes all; the best plausible local symptom patch changes only the edit site
and passes precisely both locals; no-patch/noop fail both locals; all tasks
carry the composed restore/exactly-once contract. Judge-gated authoring
self-checks carry all 0102 (a)-(l) bars, including semantic distinctness,
oracle workdir immutability, coverage, non-strawman symptom patches, and
`git diff --check` hygiene. They do not replace trio judgement.

## R2 — `scripts/validate-repo-task.py` (derived, then frozen + digested)

Derive solely from `validate-discovery-task.py`, applying the complete
registration transformation list: topology window → L-R1; distance 2 → 4;
add the import-graph deriver with its pre-committed distance-only fallback;
add decoy laws and neutralization; add and tamper-cover the three schema
fields and generator-inventory law; delete the language-parity law **and its
self-test corollary**, including odd/even fixture generation, parity tamper
scenarios, and parity diagnostics; retain the stdlib import-walk as L-R2’s
primitive; re-target EQ3/EQ3P IDs to EQ4/EQ4P; re-target self-test fixtures
to EQ4 and extend them with one tamper fixture per NEW law. The validator
enforces the same payload-only inventory self-exclusion. It is stdlib-only,
deterministic, standalone, and never mutates a task directory. No other
parent byte or semantic changes are authorized.

## R3 — `scripts/score-pilot-0105.py` (REGISTRATION-GAP AMENDMENT)

Derive from `score-pilot.py` with exactly two enumerated deltas:
`PILOT_TASKS` → the EQ4P set (base `:17`) and the self-test wrong-task
literal → an EQ4P analog (base `:276`). Every threshold, exact-Fraction rule,
PROCEED/REJECT decision bijection, maximum-three-launch rule, row schema,
and exit behavior is byte-preserved. This is a **REGISTRATION-GAP AMENDMENT**:
the pilot scorer was unenumerated in Apparatus deltas, but is mechanically
forced by Sequencing step 3’s in-kind mirror; the orchestrator records the
adjudication and trio reviews it in the pilot apparatus round.

## R4 — README scoped edit (CHANGE-CREATED TRUTHFULNESS)

Change only newly stale 0105 text: the repo-scale pilot root, `EQ4P-*` ids,
derived validator and pilot scorer, and that prototypes are discarded while
the corpus will live at `tasks-0105/`. No unrelated README cleanup.

## Corpus-topology gate and information boundary

`tasks-0105-pilot/` contains exactly EQ4P-UA1, EQ4P-MI1, EQ4P-AF1, and
EQ4P-BD1, with matching `task.json` ids/classes; `tasks-0105/` does not yet
exist. At the later pilot, only one DECISION line and a receipt digest may
reach corpus authoring; all per-task outcomes remain sealed.

## Out of scope

Corpus batches 01–08; any EQ4 corpus task; pilot scoring execution or its
receipt/DECISION; candidate seal; calibration; matrix; apparatus other than
R2/R3; frozen scripts and prior fixture trees.

<!-- devlyn:verification -->
## Verification

```json
{"verification_commands":[
{"cmd":"shasum -a 256 benchmark/executor-quality/scripts/gen-repo-skeleton.py | grep '^213594c623ccc8abfa42044489f89a97352a89d2dde26249d7de35e0b51ed8d7  '","exit_code":0,"timeout_sec":60},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --self-test","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/score-pilot-0105.py --self-test","exit_code":0,"timeout_sec":300},
{"cmd":"python3 -c 'import json,pathlib; r=pathlib.Path(\"benchmark/executor-quality/tasks-0105-pilot\"); e={\"EQ4P-UA1\":\"unsupported_assumption\",\"EQ4P-MI1\":\"missed_repo_invariant\",\"EQ4P-AF1\":\"absent_failure_mode\",\"EQ4P-BD1\":\"broken_dependency\"}; d={p.name:json.loads((p/\"task.json\").read_text()) for p in r.iterdir() if p.is_dir()}; assert set(d)==set(e) and all(d[k].get(\"id\")==k and d[k].get(\"class\")==v for k,v in e.items()); assert not pathlib.Path(\"benchmark/executor-quality/tasks-0105\").exists()'","exit_code":0,"timeout_sec":60},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105-pilot/EQ4P-UA1","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105-pilot/EQ4P-MI1","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105-pilot/EQ4P-AF1","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105-pilot/EQ4P-BD1","exit_code":0,"timeout_sec":600}
]}
```
