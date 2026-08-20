---
complexity: high
---

# iter-0105 batch-02 — tasks EQ4-UA2/MI2/AF2/BD2

Trigger: frozen `0105-repo-scale-discovery-corpus`; Sequencing step 4 batch
02. Lane: **terra direct-drive + trio verification**, not a resolve run.
Hygiene fuzz auditing and the 0102 (a)–(l) bars are judge-gated authoring
self-checks. No scored, calibration, or pilot arm runs here.

## Preconditions and authorized surface

This sealed pre-pilot spec must not be edited. In a fresh corpus session the
ONLY pilot inputs are `~/.local/share/nx01/iter0105/pilot/DECISION`, exact
bytes `{"decision": "PROCEED"}` (no newline), and
`~/.local/share/nx01/iter0105/pilot/DECISION.receipt.sha256`, exactly 64
lowercase hex. Do not dereference the receipt or read another pilot artifact. The pilot and
batch-01 script inventories pin `validate-repo-task.py`, `score-pilot-0105.py`,
`score-cohort-0105.py`, and `score-calibration-0105.py`; all are FROZEN.

- `benchmark/executor-quality/tasks-0105/EQ4-{UA2,MI2,AF2,BD2}/**` — NEW (R1)
- ONE scoped `benchmark/executor-quality/README.md` edit (R2)

Everything else is FROZEN. Report and stop on a frozen-file change.

## Constraints and sequencing

From batch-01 start through candidate seal, do not invoke sonnet, opus-5,
opus-4-8, or fable to estimate any EQ4 fixture’s difficulty or fail rate.
Mechanical validators/oracles and trio review only. Work depth-first:
EQ4-UA2, EQ4-MI2, EQ4-AF2, EQ4-BD2, then README; each task is
`validate-repo-task.py --task` green before the next.

## R1 — four tasks (frozen authoring-table rows; fixture internals IMPLEMENT-creative)

| id | domain / edit site | local premise (class anchor) | fragment A (consumer) | fragment B (test/doc) | trigger → composed restore outcome | class |
|---|---|---|---|---|---|---|
| EQ4-UA2 | satellite operations / maneuver-window editor | UA assumption: a late maneuver simply supersedes the booked burn window | `propellant/reservations/window_ledger.py` — reservation ledger retains the booked burn window until its replacement is accepted | `mission/acceptance/test_protected_pass.py` — acceptance test asserts a protected-pass collision releases the provisional propellant allocation | collision with protected pass → prior maneuver plan restored; provisional propellant allocation released once | unsupported_assumption |
| EQ4-MI2 | university endowment / valuation-roll-forward service | MI missed invariant: a valuation after lock date cannot change official unit history | `custody/units/official_ledger.py` — official ledger accepts valuation changes only before the lock date | `governance/close/test_rejected_valuation.py` — close test asserts rejection removes the provisional allocation | rejected valuation at close → official units restored; provisional allocation erased once | missed_repo_invariant |
| EQ4-AF2 | fisheries quota exchange / transfer confirmer | AF absent failure transition: a disputed catch report has no transfer-reversal transition | `quota_ledger/settlement/balance_consumer.py` — balance consumer treats a quota transfer as provisional until its report is undisputed | `disputes/system/test_report_challenge.py` — disputes test asserts a challenged report closes the transfer record | catch report challenged after transfer → both quota balances restored; transfer record closed once | absent_failure_mode |
| EQ4-BD2 | social-housing allocation / household-priority normalizer | BD breaking change: normalizing priority changes the subsidy calculator's quoted state | `rent_support/quotes/priority_consumer.py` — quote consumer derives subsidy only from the official waitlist priority | `appeals/system/test_withdrawn_household_appeal.py` — appeals test asserts withdrawal removes the subsidy quote | appeal withdrawn after quote → waitlist priority restored; subsidy quote withdrawn once | broken_dependency |

All four are Python 3 stdlib only; oracles are deterministic, offline, and
workdir-immutable. `TASKS_ROOT = benchmark/executor-quality/tasks-0105`. The
full law set **BINDS BY REFERENCE**: before authoring or judging any task, the
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
only `dependency_edges`, `contract_paths`, and `decoy_artifacts`.
Pinned generator `213594c623ccc8abfa42044489f89a97352a89d2dde26249d7de35e0b51ed8d7`
emits parameterized non-treatment mass only and each sealed payload-only
inventory must not include edit-site, artifact, decoy, or contract-path data.
Carry binding/order, gold/symptom/noop, unstated-goal, class-anchor, semantic
distinctness, and judge-gated 0102 (a)–(l) self-check laws.

Each task seals `generator-inventory.json` (payload files only: relative path plus sha256); the inventory validator rejects any edit-site, contract-artifact, `decoy_artifacts`, or `contract_paths` node entry.

## R2 — README, topology, and scope

Change only newly stale 0105 admitted-id/validator loop text. The cumulative
topology is exactly every EQ4-{UA,MI,AF,BD} suffix 1–2, with matching ids and
prefix classes. Out of scope: every other batch, scripts, pilot, seals,
calibration/matrix, DECISION edits, and sealed pilot artifacts.

<!-- devlyn:verification -->
## Verification

```json
{"verification_commands":[
{"cmd":"python3 -c 'import pathlib; assert pathlib.Path(\"~/.local/share/nx01/iter0105/pilot/DECISION\").expanduser().read_bytes()==b\"{\\\"decision\\\": \\\"PROCEED\\\"}\"'","exit_code":0,"timeout_sec":60},
{"cmd":"python3 -c 'import pathlib,re; assert re.fullmatch(r\"[0-9a-f]{64}\\n?\", pathlib.Path(\"~/.local/share/nx01/iter0105/pilot/DECISION.receipt.sha256\").expanduser().read_text())'","exit_code":0,"timeout_sec":60},
{"cmd":"shasum -a 256 -c docs/specs/iter0105-pilot/scripts.sha256","exit_code":0,"timeout_sec":60},
{"cmd":"shasum -a 256 benchmark/executor-quality/scripts/gen-repo-skeleton.py | grep '^213594c623ccc8abfa42044489f89a97352a89d2dde26249d7de35e0b51ed8d7  '","exit_code":0,"timeout_sec":60},
{"cmd":"python3 -c 'import json,pathlib; root=pathlib.Path(\"benchmark/executor-quality/tasks-0105\"); classes={\"UA\":\"unsupported_assumption\",\"MI\":\"missed_repo_invariant\",\"AF\":\"absent_failure_mode\",\"BD\":\"broken_dependency\"}; current_ids=(\"EQ4-UA2\",\"EQ4-MI2\",\"EQ4-AF2\",\"EQ4-BD2\"); current={name[4:6]:int(name[6:]) for name in current_ids}; assert set(current)==set(classes) and len(set(current.values()))==1, f\"current ids must contain one id per class at one index: {current_ids}\"; current_index=next(iter(current.values())); expected={f\"EQ4-{p}{i}\":classes[p] for p in classes for i in range(1,current_index+1)}; dirs={p.name:p for p in root.iterdir() if p.is_dir()}; assert set(dirs)==set(expected), f\"task directories: expected {sorted(expected)}, got {sorted(dirs)}\"; actual={name:json.loads((path/\"task.json\").read_text()) for name,path in dirs.items()}; assert all(data.get(\"id\")==name and data.get(\"class\")==expected[name] for name,data in actual.items()), {name:(data.get(\"id\"),data.get(\"class\"),expected[name]) for name,data in actual.items() if data.get(\"id\")!=name or data.get(\"class\")!=expected[name]}'","exit_code":0,"timeout_sec":60},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/EQ4-UA2","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/EQ4-MI2","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/EQ4-AF2","exit_code":0,"timeout_sec":600},
{"cmd":"python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/EQ4-BD2","exit_code":0,"timeout_sec":600},
{"cmd":"for id in EQ4-UA1 EQ4-MI1 EQ4-AF1 EQ4-BD1; do python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/$id || exit 1; done","exit_code":0,"timeout_sec":600},
{"cmd":"for id in EQ4-UA2 EQ4-MI2 EQ4-AF2 EQ4-BD2; do python3 benchmark/executor-quality/scripts/validate-repo-task.py --task benchmark/executor-quality/tasks-0105/$id || exit 1; done","exit_code":0,"timeout_sec":600}
]}
```
