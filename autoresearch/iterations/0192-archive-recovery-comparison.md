# 0192 — archive transfer recovery comparison

2026-09-20. Six fresh runs completed within scope; each passed34/34 external
checks. Minimal met its registered time screen, but all arms completed2/2:
no demonstrated incremental quality value and no operational adoption.

| Arm | Run1 seconds | Run2 seconds | Total seconds | Completion |
| --- | ---: | ---: | ---: | --- |
| Native |138.029|177.262|315.290|2/2|
| Unchanged0179 minimal |155.830|153.792|309.622|2/2|
| Actual canonical solo resolve |907.108|951.900|1859.008|2/2|

Per-run values are rounded independently; totals sum unrounded elapsed times.
Minimal took16.66% of the actual solo resolve total and98.20% of native.
The small native/minimal difference does not establish a general speed ranking.
Both actual C archives passed canonical task-completion acceptance. Root reviewed
all242 structured parent/worker records and10 independent-primary commands,
all final product diffs/tests and completion claims. Scope, protected inputs,
residue and semantic review passed. Participants corrected their own internal
errors within measured runs; there were no rerolls or root repairs.

## Frozen task and measurement

Baseline `bcbe4e767b12d783a5130c51904d245ca5ab92f3`; preregistration `7c68ace`.
The real archive module and four unchanged helpers/caller were copied under
`package/`, distinct from C's installed workflow code. Root reproduced an
existing defect: `shutil.move` can leave its current target after fallback copy
fails; the completed-only rollback omits it, and retry rejects the collision.
This is controlled IO-failure injection on real files, not a reported disk-full
outage or actual separate-volume test.

The [protocol](../experiments/0192/PROTOCOL.md) froze68 source, request, oracle,
transport, model-metadata and canonical-skill files before serial A/B/C/C/B/A
calls. Requested Astra/high, Codex0.155.1,1800s/workflow. A is native; B is unchanged
0179 minimal; C is actual canonical trivial-spec `--no-pair --no-risk-probes`,
including fresh primary verification. This measures workflow packages under
explicit constraints, not default paired cost or a prompt-only causal effect.
The request preserves the standard `shutil.move` transport and unwrapped errors.

Final calibration: original10/34, reference34/34; rename-only9/34,
swallowed-error10/34, omitted-prior-rollback16/34, overwritten-collision31/34.
Exact failure sets and reasons were asserted. The matrix exercises partial copy,
metadata and source-unlink failures at first/later/nested/bound judge-role paths,
including simulated cross-device rollback. It checks original bytes/modes,
unrelated entries, error identity and exact successful retry layout. Real CLI,
strict validation, collision refusal and existing self-tests are controls.

Fable's pre-dispatch NO-GO identified an oracle/implementation ambiguity, a C
archive restriction ambiguity and under-specified interpretation. Root clarified
these, registered the actual assessor/transport, resolved fixture paths, added
CLI/self-test/retry checks, removed a duplicate mutant and calibrated failure
reasons. A symlinked fixture-parent replay also passed34/34. Versions and raw
review are preserved; no participant had been dispatched. Opus's source review
found a Windows path-key defect in the proposed package regression; root fixed
it before applying the production change. Adjudications: `.devlyn/0192/REVIEW-ADJUDICATION.json`
and `SOURCE-REVIEW-ADJUDICATION.json`.

All-arms completion is preregistered as non-discriminating quality evidence.
This is one maintainer-selected task with its mechanism supplied and two repeats,
not a field trial, a reliability estimate, or Mission1 gate15 closure. Time is
supervisor wrapper-return time, including internal failed commands and repairs;
research preparation, external assessment and source review are separate.
Whole C usage/cost cannot be inferred from structured counters when text-only
primary judge usage is absent. Host runtime warnings and non-identical child
context isolation remain limitations; native headers/receipts do not attest
provider-internal model weights.

## Production change and verification

The root worked directly; resolve ran only in the two experimental controls.
Under **No workaround**, the violated invariant is removal of output from a
failed transfer before rethrowing and rolling back earlier completed moves.
The production change catches synchronous `OSError` around the existing
`shutil.move`, removes that attempt's target with `unlink(missing_ok=True)`, then
re-raises. The existing reverse rollback, preflight validation and public API
remain intact; canonical source and the tracked local mirror agree.

Under **No overengineering**, the change adds four net lines per source copy.
Preflight guarantees absent destinations and validated file sources. This relies on standard `shutil.move` raising before successful source removal.
Recovery IO must succeed; this is not a crash, concurrent-mutation, asynchronous-exception,
post-success-unlink injection or recovery-failure guarantee. No new transport,
flags or abstraction. Empty directories may remain after failed transfer.

The portable package regression exercises first/later copy, metadata and unlink
failure, pre-copy failure and successful fallback on real files. It uses the
standard copy-function seam so Windows CopyFile2 cannot bypass fault injection.
The original fails6 subcases; removing `missing_ok=True` fails2. The fixed packed
artifact passes17/17 PackageTests and existing archive self-tests. This supplies
the final subtraction check: deleting either cleanup or missing-target tolerance
breaks observed recovery behavior. See `.devlyn/0192/FINAL.md` for required lint, hosted CI and delivery status; no npm release is part of this task.

Raw registration, calibration versions, reviews/adjudications, launches, native
logs, product seals, external assessment, root audits, telemetry and production
checks live in `.devlyn/0192/`. `METRICS.json` derives elapsed sums;
`ASSESSMENT.json` preserves each external result. All68 frozen inputs matched
immediately after collection, before the intentional production source edit.
All6 participant seals matched assessment. Before handoff edits,81708 retained
file hashes matched, including original-checkout WIP; only the retained checkout's
current handoff pointers are deliberately replaced. Source/Git, historical
records and participant artifacts remain; owned disposable scratch is cleaned
through its prospective receipts. Final delivery/cleanup status is in `FINAL.md`.

## Open frontier

Mission1 remains active;0187's minimal-replacement NO-GO and0190/0191
non-adoption remain valid.0192 adds a disjoint actual recovery defect and caller
compatibility check, but again saturates completion. Seek an independently
supplied field task for gate15 or a disjoint natural task with discriminating
compatibility/failure-recovery interactions. Freeze scope, fidelity and failure
semantics before calls; rank full request completion before inclusive time/cost.
Keep exposed0187/0190/0191/0192 tasks out of unbiased confirmation.
