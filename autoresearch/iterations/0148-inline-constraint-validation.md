# 0148 — Reject silently discarded inline constraints

2026-09-11. Mission 1, intent fidelity. Root implements without resolve and
decides after independent Fable 5.1 and Grok 4.6 source review. Baseline
`337447b` includes the closed 0147 screen; this is a new deterministic repair,
not a rerun or explanation of its model misses.

## Reproduced contract failure

Generated and legacy inline verification accept only a `verification_commands`
carrier at execution time. However, their shape validator ignored other fields,
and staging silently discarded them. A generated author following the shared
sibling-template reference could supply `required_files` with a passing command
and receive successful verification even when the required file was missing.
An output expectation typo, `stdout_not_contians`, likewise passed validation
and disappeared from the executed obligation. Sibling contracts already reject
unknown command keys and enforce their file constraints.

Prediction was recorded before controls in `.devlyn/0148-carriers/prediction.json`.
The real CLI reproduces both failures in BUILD and VERIFY. Twenty-four before
and twenty-four final controls include missing/present files, generated/legacy
inline versus sibling contracts, correct executable guards, misspelled output
expectations, and generated prose with a sibling but no inline contract.

| Input | Before | After |
| --- | --- | --- |
| Inline `required_files`, file missing or present | accepted; field discarded | malformed before execution |
| Inline misspelled output expectation | accepted; assertion ignored | malformed before execution |
| Sibling required file missing / present | fail / pass | fail / pass |
| Correct generated executable file guard, missing / present | fail / pass | fail / pass |
| Generated prose plus sibling, without inline JSON | explicit error | explicit error |

This establishes a carrier-validation mismatch, not a general model-authoring
omission rate. Correctly authored executable guards reached execution and
produced the expected failure/success. No change to process-evidence transport
or `contract_refs` semantics is supported by this investigation.

## Smallest repair

Both authoring `--check` and runtime inline staging now use one inline validator.
It rejects unsupported top-level fields with guidance to encode checks as
commands or use a real spec's sibling contract, and reuses existing sibling
command-field validation. It retains the commands-only inline contract instead
of introducing a new carrier or silently enabling previously ignored fields.
Invalid inputs fail closed even when a stale staged carrier is present.

Generated authoring guidance now names the inline JSON location and supported
field, carries over the existing constraint/control guidance, and keeps residual
semantics as source-review obligations. Runtime staging validates generated
input; legacy-spec bootstrap also runs `--check`. An initially drafted extra
check instruction was removed. No generic semantic scanner or reviewer paragraph.

Regression cases exercise real `--check` and runtime paths for generated and
legacy spec sources, unsupported fields, command typos, a corrected executable
output guard, and stale staged files. Both tracked and installed owned mirrors
are synchronized. Generated pure-design handling and model guard-authoring
reliability are not established by these executable-carrier controls.

## Verification and owner decision

Source self-test passes; all 24 final owner controls match expected outcomes.
Full `bash scripts/lint-skills.sh` passes in 288.741s. Independent native source
reviews used the same hash-bound packet with no observed tool calls: Fable 5.1
**PASS_WITH_ISSUES** (98.857s), Grok 4.6, emitted `grok-4.6-build`, **PASS**
(207.937s). Neither found a CRITICAL/HIGH or an observed defect in this repair.
Their packet correctly reported lint as pending; the owner subsequently verified
its successful terminal result and byte-identical canonical/installed mirrors.

Fable requested a compatibility scan. Baseline/candidate `run_check_mode`
(the `--check` entry point) examined 144 tracked sentinel-containing Markdown
files without a sibling contract: 134/104 accepted, 30 newly rejected. The
changed population is 5 iteration documents, 8 historical specs and 17 archived
benchmark Markdown snapshots. Every change reports previously ignored
sibling-only fields or unsupported command keys, including `expect_exit`.
This is intentional fail-closed compatibility tightening; resubmitting those
contracts requires commands-only inline checks or a real sibling contract.
Historical files/results were not edited, rerun or regraded.

Both reviewers noted the separate pre-staged benchmark route. Source audit
confirms its runner copies the harness `expected.json` oracle and does not itself
invoke strict fixture lint (`run-fixture.sh:325`, `lint-fixtures.sh:164`,
`spec-verify-check.py:5087`). That route remains a separate validation follow-up;
this repair claims generated/legacy-inline coverage, not every benchmark path.
Fable's other LOW advice does not require expanding this repair: `contract_refs`
was already accepted and is oracle-link metadata (`expected.schema.json:107`),
stale files cannot execute after malformed-source rejection, and normal Python
self-tests plus the independent controls pass. Bare-assert diagnostic quality
and pre-existing generated pure-design guidance remain limitations.

**No workaround / Production ready:** reject assertions the carrier cannot
enforce instead of reporting false success. **No overengineering / Best
practice:** reuse the existing validator and delete the redundant authoring
instruction; removing either entry-point check reopens a reproduced failure.
**No guesswork / Worldclass:** predictions, raw controls, required lint and
independent reviews support this scoped Mission 1 repair. **Optimized:** no
model-speed, whole-run efficiency or semantic-recall improvement is claimed.

Raw evidence is at
`~/.local/share/nx01/iter0144/core-research/.devlyn/0148-carriers/`; final reviews
and finding dispositions are in `.devlyn/0148-final/`. Task receipt
`ce27a26535df3ab527d2da1f` owns delivery and evidence custody separately from
source verification. No npm release.
