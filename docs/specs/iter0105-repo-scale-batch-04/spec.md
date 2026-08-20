---
complexity: high
---

# iter-0105 batch-04 — tasks EQ4-UA4/MI4/AF4/BD4

Trigger: frozen `0105-repo-scale-discovery-corpus`; Sequencing step 4 batch
04. Lane: **terra direct-drive + trio verification**, not resolve. Hygiene
fuzz auditing and 0102 (a)–(l) are judge-gated authoring self-checks.

## Preconditions, surface, and sequencing

This sealed pre-pilot spec is immutable. In a fresh corpus session the ONLY
pilot inputs are `~/.local/share/nx01/iter0105/pilot/DECISION`, exact bytes
`{"decision": "PROCEED"}` (no newline), and
`~/.local/share/nx01/iter0105/pilot/DECISION.receipt.sha256`, exactly 64
lowercase hex. Do not dereference the receipt or read another pilot artifact. Pilot/batch-01 script
inventories are FROZEN. Authorized: NEW
`benchmark/executor-quality/tasks-0105/EQ4-{UA4,MI4,AF4,BD4}/**` and one
scoped README edit; all else frozen. No sonnet/opus-5/opus-4-8/fable
difficulty probe before candidate seal. Validate UA4, MI4, AF4, BD4
depth-first, then README.

## R1 — four tasks (frozen authoring-table rows; fixture internals IMPLEMENT-creative)

| id | domain / edit site | local premise (class anchor) | fragment A (consumer) | fragment B (test/doc) | trigger → composed restore outcome | class |
|---|---|---|---|---|---|---|
| EQ4-UA4 | semiconductor fabrication / recipe-revision issuer | UA assumption: a revised recipe is production-ready when staged | `genealogy/wafer/revision_consumer.py` — wafer genealogy exposes a recipe to production only after qualification accepts it | `qualification/system/test_rejected_recipe.py` — qualification test asserts rejection removes the staged wafer links | qualification rejection after staging → active recipe restored; staged wafer links removed once | unsupported_assumption |
| EQ4-MI4 | medicinal cold-chain / excursion-adjudication service | MI missed invariant: a batch-release lock survives a corrected temperature excursion | `batch_release/controls/hold_consumer.py` — hold consumer releases a batch only while its corrected excursion remains audit-free | `audit/system/test_external_flag.py` — audit test asserts an external flag keeps the downstream order blocked | external audit flag after correction → release hold reinstated; downstream order remains blocked once | missed_repo_invariant |
| EQ4-AF4 | public pension administration / survivor-benefit recalculator | AF absent failure transition: revoked beneficiary evidence has no staged-award withdrawal | `payments/instructions/award_consumer.py` — award consumer issues payment instructions only from final beneficiary evidence | `eligibility/system/test_document_revocation.py` — eligibility test asserts evidence revocation voids the payment instruction | evidence revoked after staging → prior award state restored; payment instruction voided once | absent_failure_mode |
| EQ4-BD4 | urban forestry permits / species-correction registrar | BD breaking change: correcting species changes the mitigation-credit ledger's category | `mitigation_credits/ledger/species_consumer.py` — credit ledger derives category from the approved species record | `survey/system/test_voided_species_record.py` — survey test asserts a voided record releases the reserved credits | survey void after partial approval → original species record restored; reserved credits released once | broken_dependency |

All four are Python 3 stdlib; deterministic offline oracles do not mutate
their workdir. `TASKS_ROOT = benchmark/executor-quality/tasks-0105`. The full
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
only `dependency_edges`, `contract_paths`, and `decoy_artifacts`. The pinned
generator (`213594c623ccc8abfa42044489f89a97352a89d2dde26249d7de35e0b51ed8d7`)
produces parameterized non-treatment mass and sealed payload-only inventories
that cannot name edit-site, artifact, decoy, or path-node content. Carry all
0102 bindings, vectors, unstated-goal, class causality, distinctness, and
judge-gated (a)–(l) self-check laws.

Each task seals `generator-inventory.json` (payload files only: relative path plus sha256); the inventory validator rejects any edit-site, contract-artifact, `decoy_artifacts`, or `contract_paths` node entry.

## R2 — README, topology, and scope

Only update newly stale 0105 admitted ids and validator-loop text. Cumulative
topology is exactly EQ4-{UA,MI,AF,BD}1 through 4, with matching ids/classes.
All other batches, scripts, pilot/seals/arms, DECISION edits, and sealed pilot
artifacts are out of scope.

<!-- devlyn:verification -->
## Verification

```json
{"verification_commands":[
{"cmd":"python3 -c 'import pathlib; assert pathlib.Path(\"~/.local/share/nx01/iter0105/pilot/DECISION\").expanduser().read_bytes()==b\"{\\\"decision\\\": \\\"PROCEED\\\"}\"'","exit_code":0,"timeout_sec":60},
{"cmd":"python3 -c 'import pathlib,re; assert re.fullmatch(r\"[0-9a-f]{64}\\n?\", pathlib.Path(\"~/.local/share/nx01/iter0105/pilot/DECISION.receipt.sha256\").expanduser().read_text())'","exit_code":0,"timeout_sec":60},
{"cmd":"shasum -a 256 -c docs/specs/iter0105-pilot/scripts.sha256","exit_code":0,"timeout_sec":60},
{"cmd":"shasum -a 256 benchmark/executor-quality/scripts/gen-repo-skeleton.py | grep '^213594c623ccc8abfa42044489f89a97352a89d2dde26249d7de35e0b51ed8d7  '","exit_code":0,"timeout_sec":60},
{"cmd":"python3 -c 'import json,pathlib; root=pathlib.Path(\"benchmark/executor-quality/tasks-0105\"); classes={\"UA\":\"unsupported_assumption\",\"MI\":\"missed_repo_invariant\",\"AF\":\"absent_failure_mode\",\"BD\":\"broken_dependency\"}; current_ids=(\"EQ4-UA4\",\"EQ4-MI4\",\"EQ4-AF4\",\"EQ4-BD4\"); current={name[4:6]:int(name[6:]) for name in current_ids}; assert set(current)==set(classes) and len(set(current.values()))==1, f\"current ids must contain one id per class at one index: {current_ids}\"; current_index=next(iter(current.values())); expected={f\"EQ4-{p}{i}\":classes[p] for p in classes for i in range(1,current_index+1)}; dirs={p.name:p for p in root.iterdir() if p.is_dir()}; assert set(dirs)==set(expected), f\"task directories: expected {sorted(expected)}, got {sorted(dirs)}\"; actual={name:json.loads((path/\"task.json\").read_text()) for name,path in dirs.items()}; assert all(data.get(\"id\")==name and data.get(\"class\")==expected[name] for name,data in actual.items()), {name:(data.get(\"id\"),data.get(\"class\"),expected[name]) for name,data in actual.items() if data.get(\"id\")!=name or data.get(\"class\")!=expected[name]}'","exit_code":0,"timeout_sec":60},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/EQ4-UA4","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/EQ4-MI4","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/EQ4-AF4","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/EQ4-BD4","exit_code":0,"timeout_sec":600},
{"cmd":"for id in EQ4-UA1 EQ4-MI1 EQ4-AF1 EQ4-BD1; do python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/$id || exit 1; done","exit_code":0,"timeout_sec":600},
{"cmd":"for id in EQ4-UA2 EQ4-MI2 EQ4-AF2 EQ4-BD2; do python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/$id || exit 1; done","exit_code":0,"timeout_sec":600},
{"cmd":"for id in EQ4-UA3 EQ4-MI3 EQ4-AF3 EQ4-BD3; do python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/$id || exit 1; done","exit_code":0,"timeout_sec":600},
{"cmd":"for id in EQ4-UA4 EQ4-MI4 EQ4-AF4 EQ4-BD4; do python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/$id || exit 1; done","exit_code":0,"timeout_sec":600}
]}
```
