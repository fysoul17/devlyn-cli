---
complexity: high
---

# iter-0105 batch-06 — tasks EQ4-UA6/MI6/AF6/BD6

Trigger: frozen `0105-repo-scale-discovery-corpus`; Sequencing step 4 batch
06. Lane: **terra direct-drive + trio verification**, not resolve. Hygiene
fuzz auditing and all 0102 (a)–(l) bars are judge-gated authoring self-checks.

## Preconditions, surface, and sequencing

This sealed pre-pilot spec is immutable. In a fresh corpus session the ONLY
pilot inputs are `~/.local/share/nx01/iter0105/pilot/DECISION`, exact bytes
`{"decision": "PROCEED"}` (no newline), and
`~/.local/share/nx01/iter0105/pilot/DECISION.receipt.sha256`, exactly 64
lowercase hex. Do not dereference the receipt or read another pilot artifact. The
pilot/batch-01 script inventories are FROZEN. Authorized: NEW
`benchmark/executor-quality/tasks-0105/EQ4-{UA6,MI6,AF6,BD6}/**` and one
scoped README edit; everything else is frozen. No sonnet/opus-5/opus-4-8/fable
difficulty probe through candidate seal. Validate UA6, MI6, AF6, BD6, then
README, depth-first.

## R1 — four tasks (frozen authoring-table rows; fixture internals IMPLEMENT-creative)

| id | domain / edit site | local premise (class anchor) | fragment A (consumer) | fragment B (test/doc) | trigger → composed restore outcome | class |
|---|---|---|---|---|---|---|
| EQ4-UA6 | polar field logistics / cargo-manifest reprioritizer | UA assumption: an itinerary substitution overwrites the existing manifest | `survival_cache/allocation/load_consumer.py` — load consumer assigns survival-cache reservations from the accepted itinerary | `airlift/safety/test_weight_rejection.py` — safety test asserts a weight rejection rolls the cache reservation back | aircraft weight rejection → original manifest restored; cache reservation rolled back once | unsupported_assumption |
| EQ4-MI6 | geotechnical monitoring / threshold-rule publisher | MI missed invariant: alert thresholds advance as a monotonic versioned sequence | `alerts/acknowledgement/version_consumer.py` — acknowledgement consumer accepts alerts only for the current threshold version | `calibration/system/test_failed_threshold.py` — calibration test asserts failure preserves the acknowledgement state | failed calibration → prior threshold rule remains active; acknowledgement state preserved once | missed_repo_invariant |
| EQ4-AF6 | emergency shelter operations / family-reunification intake | AF absent failure transition: a failed guardian match has no provisional-placement unwind | `bed_management/assignments/family_consumer.py` — assignment consumer commits a bed only after the guardian match succeeds | `safeguarding/system/test_guardian_mismatch.py` — safeguarding test asserts a mismatch consumes one case token | guardian mismatch after placement → previous bed assignment restored; case token consumed once | absent_failure_mode |
| EQ4-BD6 | road-toll concession / exemption-rule importer | BD breaking change: an imported exemption changes the dependent invoice processor's toll class | `invoicing/charges/exemption_consumer.py` — invoice consumer maps toll class only from a valid exemption rule | `ordinance/system/test_malformed_exemption.py` — ordinance test asserts a malformed rule emits one correction notice | malformed ordinance → prior toll class restored; correction notice emitted once | broken_dependency |

All four are Python 3 stdlib, with deterministic offline workdir-immutable
oracles, at `TASKS_ROOT = benchmark/executor-quality/tasks-0105`. The full law
set **BINDS BY REFERENCE**: before authoring or judging any task, the authoring
worker MUST read `autoresearch/iterations/0105-repo-scale-discovery-corpus.md`
§ Registered treatment (L-R1..L-R4 + schema) and
`docs/specs/iter0105-pilot/spec.md` § R1. This in-spec summary is an operative
gloss, not the law.

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
only `dependency_edges`, `contract_paths`, and `decoy_artifacts`. Pinned generator
`213594c623ccc8abfa42044489f89a97352a89d2dde26249d7de35e0b51ed8d7`
produces parameterized non-treatment mass and a sealed payload-only inventory
that names no edit-site, artifact, decoy, or contract-path node. Carry 0102
bindings, vectors, goal, class/distinctness, and judge-gated (a)–(l) laws.

Each task seals `generator-inventory.json` (payload files only: relative path plus sha256); the inventory validator rejects any edit-site, contract-artifact, `decoy_artifacts`, or `contract_paths` node entry.

## R2 — README, topology, and scope

Only newly stale 0105 admitted ids and validator-loop text may change.
Cumulative topology is exactly EQ4-{UA,MI,AF,BD}1 through 6, matching
ids/classes. All other work is out of scope.

<!-- devlyn:verification -->
## Verification

```json
{"verification_commands":[
{"cmd":"python3 -c 'import pathlib; assert pathlib.Path(\"~/.local/share/nx01/iter0105/pilot/DECISION\").expanduser().read_bytes()==b\"{\\\"decision\\\": \\\"PROCEED\\\"}\"'","exit_code":0,"timeout_sec":60},
{"cmd":"python3 -c 'import pathlib,re; assert re.fullmatch(r\"[0-9a-f]{64}\\n?\", pathlib.Path(\"~/.local/share/nx01/iter0105/pilot/DECISION.receipt.sha256\").expanduser().read_text())'","exit_code":0,"timeout_sec":60},
{"cmd":"shasum -a 256 -c docs/specs/iter0105-pilot/scripts.sha256","exit_code":0,"timeout_sec":60},
{"cmd":"shasum -a 256 benchmark/executor-quality/scripts/gen-repo-skeleton.py | grep '^213594c623ccc8abfa42044489f89a97352a89d2dde26249d7de35e0b51ed8d7  '","exit_code":0,"timeout_sec":60},
{"cmd":"python3 -c 'import json,pathlib; root=pathlib.Path(\"benchmark/executor-quality/tasks-0105\"); classes={\"UA\":\"unsupported_assumption\",\"MI\":\"missed_repo_invariant\",\"AF\":\"absent_failure_mode\",\"BD\":\"broken_dependency\"}; current_ids=(\"EQ4-UA6\",\"EQ4-MI6\",\"EQ4-AF6\",\"EQ4-BD6\"); current={name[4:6]:int(name[6:]) for name in current_ids}; assert set(current)==set(classes) and len(set(current.values()))==1, f\"current ids must contain one id per class at one index: {current_ids}\"; current_index=next(iter(current.values())); expected={f\"EQ4-{p}{i}\":classes[p] for p in classes for i in range(1,current_index+1)}; dirs={p.name:p for p in root.iterdir() if p.is_dir()}; assert set(dirs)==set(expected), f\"task directories: expected {sorted(expected)}, got {sorted(dirs)}\"; actual={name:json.loads((path/\"task.json\").read_text()) for name,path in dirs.items()}; assert all(data.get(\"id\")==name and data.get(\"class\")==expected[name] for name,data in actual.items()), {name:(data.get(\"id\"),data.get(\"class\"),expected[name]) for name,data in actual.items() if data.get(\"id\")!=name or data.get(\"class\")!=expected[name]}'","exit_code":0,"timeout_sec":60},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/EQ4-UA6","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/EQ4-MI6","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/EQ4-AF6","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/EQ4-BD6","exit_code":0,"timeout_sec":600},
{"cmd":"for id in EQ4-UA1 EQ4-MI1 EQ4-AF1 EQ4-BD1; do python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/$id || exit 1; done","exit_code":0,"timeout_sec":600},
{"cmd":"for id in EQ4-UA2 EQ4-MI2 EQ4-AF2 EQ4-BD2; do python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/$id || exit 1; done","exit_code":0,"timeout_sec":600},
{"cmd":"for id in EQ4-UA3 EQ4-MI3 EQ4-AF3 EQ4-BD3; do python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/$id || exit 1; done","exit_code":0,"timeout_sec":600},
{"cmd":"for id in EQ4-UA4 EQ4-MI4 EQ4-AF4 EQ4-BD4; do python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/$id || exit 1; done","exit_code":0,"timeout_sec":600},
{"cmd":"for id in EQ4-UA5 EQ4-MI5 EQ4-AF5 EQ4-BD5; do python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/$id || exit 1; done","exit_code":0,"timeout_sec":600},
{"cmd":"for id in EQ4-UA6 EQ4-MI6 EQ4-AF6 EQ4-BD6; do python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/$id || exit 1; done","exit_code":0,"timeout_sec":600}
]}
```
