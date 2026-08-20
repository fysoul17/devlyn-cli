---
complexity: high
---

# iter-0105 batch-01 — EQ4 scorers + tasks EQ4-UA1/MI1/AF1/BD1

Trigger: `autoresearch/iterations/0105-repo-scale-discovery-corpus.md`
(DESIGN-FROZEN 2026-08-20), Sequencing step 4 batch 01. Lane: **terra
direct-drive + trio verification**, not a resolve run. Hygiene fuzz auditing
and the 0102 (a)–(l) authoring bars are judge-gated self-checks. No scored,
calibration, or pilot arm runs here.

## Preconditions (binding)

This sealed pre-pilot spec must not be changed. In a fresh corpus session the
ONLY pilot inputs are `~/.local/share/nx01/iter0105/pilot/DECISION`, exact
bytes `{"decision": "PROCEED"}` (no newline), and
`~/.local/share/nx01/iter0105/pilot/DECISION.receipt.sha256`, exactly 64
lowercase hex. Do not dereference the receipt or read another pilot artifact.
`docs/specs/iter0105-pilot/scripts.sha256` uses repo-relative paths and pins
`validate-repo-task.py` and `score-pilot-0105.py`; they are FROZEN.

## Authorized surface

- `benchmark/executor-quality/scripts/score-cohort-0105.py` — NEW (R2)
- `benchmark/executor-quality/scripts/score-calibration-0105.py` — NEW (R2)
- `benchmark/executor-quality/tasks-0105/EQ4-{UA1,MI1,AF1,BD1}/**` — NEW (R1)
- ONE scoped edit in `benchmark/executor-quality/README.md` (R3)

Everything else is FROZEN, including the generator, pilot tasks, prior task
trees, parent scripts, validator, and pilot scorer. A frozen-file change is a
named finding and stops that deliverable.

## Binding run constraint and sequencing

From batch-01 start through candidate seal, do not invoke `claude-sonnet-5`,
`claude-opus-5`, `claude-opus-4-8`, or `claude-fable-5` to estimate rates,
band position, or difficulty on EQ4 fixtures. Validators/oracles and trio
review are permitted. Work depth-first: both R2 scorer self-tests; then
EQ4-UA1, EQ4-MI1, EQ4-AF1, EQ4-BD1 validator-green; then R3.

## R1 — four tasks (frozen authoring-table rows; fixture internals IMPLEMENT-creative)

| id | domain / edit site | local premise (class anchor) | fragment A (consumer) | fragment B (test/doc) | trigger → composed restore outcome | class |
|---|---|---|---|---|---|---|
| EQ4-UA1 | biobank logistics / aliquot-relocation confirmer | UA assumption: a relabelled aliquot replaces its source custody leg | `chain_of_custody/reconcile/ledger_consumer.py` — reconciler consumes relocation legs as append-only custody segments | `quality/system/test_duplicate_barcode.py` — system test asserts duplicate-barcode rejection restores the source rack without another custody event | duplicate barcode during relocation → source rack AND custody sequence restored; one custody event remains | unsupported_assumption |
| EQ4-MI1 | meteorological reanalysis / observation-backfill merger | MI missed invariant: post-publication backfill must retain the external revision identity | `forecast/baselines/revision_consumer.py` — baseline consumer keys reanalysis by the external revision identity | `publication/system/test_station_correction.py` — publication test asserts a duplicate correction leaves one superseding issue | duplicate station correction → revision lineage restored; one superseding issue remains | missed_repo_invariant |
| EQ4-AF1 | additive manufacturing / powder-blend release | AF absent failure transition: contamination after staging has no quarantine transition | `material_control/quarantine/lot_consumer.py` — lot consumer blocks material release until the contamination state is cleared | `release/system/test_contaminant_flag.py` — release test asserts a contaminant flag restores the material reservation | contaminant flag mid-release → powder lots quarantined; material reservation restored once | absent_failure_mode |
| EQ4-BD1 | nuclear-waste logistics / container-label updater | BD breaking change: reclassifying a label changes the transport-eligibility consumer's state | `transport_eligibility/certificates/label_consumer.py` — eligibility consumer reads transport state from the currently classified label | `safeguards/system/test_manifest_reclassification.py` — safeguards test asserts reclassification retains the route certificate | reclassification after manifest draft → prior label restored; route certificate retained once | broken_dependency |

All tasks are Python 3 stdlib only; hidden oracles are deterministic,
offline, and workdir-immutable. UA/MI/AF/BD class-anchor causality is binding.
Each task uses `TASKS_ROOT = benchmark/executor-quality/tasks-0105`. The full
law set **BINDS BY REFERENCE**: before authoring or judging any task, the
authoring worker MUST read
`autoresearch/iterations/0105-repo-scale-discovery-corpus.md` § Registered
treatment (L-R1..L-R4 + schema) and `docs/specs/iter0105-pilot/spec.md` § R1.
This in-spec summary is an operative gloss, not the law.

L-R1 requires at least 120 visible regular files and 2,000,000 visible source
bytes. L-R2 applies to the Python-only corpus: a stdlib-`ast` import graph over
visible files (imports, re-exports, literal file loads) must put the edit-site
module set at graph distance at least 4 edges from each contract artifact;
registered `dependency_edges` must exactly match the derived edges;
`contract_paths` must hold the L-R2 path-node set for each artifact; and
`directory_distance(edit_site, artifact.parent) ≥ 4`. Only if the graph deriver
fails its freeze-round self-test bar may the pre-committed, reported
distance-only fallback apply, narrowing the claim to distance plus
distractor-mass discovery; it is never silent. L-R3 requires at least 10 decoy
modules, none a contract artifact nor on any registered L-R2 path; each
`directory_distance(edit_site, decoy) ≤ 2` and strictly less than every contract
artifact's distance; distinct case-folded whole-word `(file, token)` decoy hits
over `contract_tokens_a ∪ contract_tokens_b` exceed contract-artifact hits with
at least one hit in each of the at least 10 decoys; temporary-copy
neutralization of every registered decoy-token occurrence leaves
no-patch/noop/symptom/gold oracle vectors identical. L-R4 carries the
registered mechanical two-fragment complementarity law. The exact schema adds
only `dependency_edges`, `contract_paths`, and `decoy_artifacts`. Per-task
parameterized generation through pinned
`gen-repo-skeleton.py` is non-treatment mass only; each sealed
payload-only `generator-inventory.json` is rejected if it names an edit-site,
artifact, decoy, or contract-path node. Carry all 0102 binding/manifestation,
gold/symptom/noop, unstated-goal, semantic-distinctness, and judge-gated
(a)–(l) hygiene self-check laws.

## R2 — derived scorers (enumerated deltas only)

`score-cohort-0105.py` derives from `score-cohort.py`: `ENGINES` becomes
`("claude-opus-5", "claude-opus-4-8")`, `FROZEN_TASKS` becomes the EQ4
32-set, and the substitution self-test IDs become EQ4 analogs. `REPS`, all
thresholds, bootstrap, and `SATURATED` are byte-preserved.
`score-calibration-0105.py` derives from `score-calibration.py` with the
task-set delta only; every gate constant is byte-preserved. Both full
self-tests must pass before task authoring.

## R3 — README, topology, and scope

Make only CHANGE-CREATED TRUTHFULNESS edits for the admitted 0105 root, EQ4
ids, and the two scorers. After this batch, `tasks-0105/` contains exactly
EQ4-UA1, EQ4-MI1, EQ4-AF1, EQ4-BD1 with matching ids/classes. Out of scope:
batches 02–08, pilot changes, candidate seal, calibration/matrix apparatus,
DECISION edits, and sealed pilot artifacts.

<!-- devlyn:verification -->
## Verification

```json
{"verification_commands":[
{"cmd":"python3 -c 'import pathlib; assert pathlib.Path(\"~/.local/share/nx01/iter0105/pilot/DECISION\").expanduser().read_bytes()==b\"{\\\"decision\\\": \\\"PROCEED\\\"}\"'","exit_code":0,"timeout_sec":60},
{"cmd":"python3 -c 'import pathlib,re; assert re.fullmatch(r\"[0-9a-f]{64}\\n?\", pathlib.Path(\"~/.local/share/nx01/iter0105/pilot/DECISION.receipt.sha256\").expanduser().read_text())'","exit_code":0,"timeout_sec":60},
{"cmd":"shasum -a 256 -c docs/specs/iter0105-pilot/scripts.sha256","exit_code":0,"timeout_sec":60},
{"cmd":"shasum -a 256 benchmark/executor-quality/scripts/gen-repo-skeleton.py | grep '^213594c623ccc8abfa42044489f89a97352a89d2dde26249d7de35e0b51ed8d7  '","exit_code":0,"timeout_sec":60},
{"cmd":"python3 benchmark/executor-quality/scripts/score-cohort-0105.py --self-test","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/score-calibration-0105.py --self-test","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/EQ4-UA1","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/EQ4-MI1","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/EQ4-AF1","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/EQ4-BD1","exit_code":0,"timeout_sec":600},
{"cmd":"python3 -c 'import json,pathlib; r=pathlib.Path(\"benchmark/executor-quality/tasks-0105\"); e={\"EQ4-UA1\":\"unsupported_assumption\",\"EQ4-MI1\":\"missed_repo_invariant\",\"EQ4-AF1\":\"absent_failure_mode\",\"EQ4-BD1\":\"broken_dependency\"}; d={p.name:json.loads((p/\"task.json\").read_text()) for p in r.iterdir() if p.is_dir()}; assert set(d)==set(e) and all(d[k].get(\"id\")==k and d[k].get(\"class\")==v for k,v in e.items())'","exit_code":0,"timeout_sec":60}
]}
```
