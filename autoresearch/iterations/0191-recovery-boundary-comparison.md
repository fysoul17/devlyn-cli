# 0191 — natural recovery-directory repair and actual workflow comparison

2026-09-20. Root worked directly; actual resolve ran only in experimental C.
Source base `981c55ea7014c507e7d83c44f32f92d91a80c86e`; preregistration
commit `1560ea1`. Evidence root `.devlyn/0191/`; participants retained at
`/Users/aipalm/.local/share/nx01/0191-participants`. Delivery and cleanup evidence
belong in `.devlyn/0191/FINAL.md`, separate from the accepted source result.

## Result and decision

All six fresh draws completed the registered request, including scope and claim
review; all passed 42 external functional checks. Every arm reached the ceiling of this
completion measure (2/2 each); this does not establish quality or reliability
equivalence. Minimal met the registered time screen, but showed no incremental
completion benefit over native. No instruction, model,
default or routing promotion follows. This permits further disjoint confirmation
only; it does not reverse 0187's NO-GO or close Mission1 gate15.

The task exposed a real installer defect: a pre-existing directory symlink at
`.devlyn` or `.devlyn/instructions` redirected recovery writes to its target.
Root separately fixed the production helper and verified the packed npm artifact.
No npm release was performed by this iteration.

| Draw | Workflow | Completion | External checks | Public + added tests | Elapsed seconds |
|---|---|---|---:|---:|---:|
| 01-A | native | PASS | 42/42 | 9 | 123.677 |
| 02-B | unchanged minimal | PASS | 42/42 | 7 | 142.854 |
| 03-C | actual resolve, solo | PASS | 42/42 | 8 | 840.405 |
| 04-C | actual resolve, solo | PASS | 42/42 | 8 | 1021.020 |
| 05-B | unchanged minimal | PASS | 42/42 | 6 | 115.456 |
| 06-A | native | PASS | 42/42 | 7 | 130.941 |

Two-draw totals: A254.618s, B258.311s, C1861.426s. B took86.1% less
time than C. Its total was3.7s above A, while A/B within-arm ranges were7.3s/27.4s;
these two repeats do not support an A-versus-B speed ranking. These are supervisor `wrapper_return_seconds`,
including internal phase work and failures, not parent-reported phase duration.
All draws returned normally; no timeout, replacement, root repair or reroll.
Research preparation, external assessment and independent source review are
excluded from this workflow measure. Whole-run C usage and dollar cost are
UNKNOWN: structured parent/worker counters omit the plain-output primary judges.
See `METRICS.json`, `TELEMETRY.json` and each `runs/<draw>/result.json`.

## Frozen design and calibration

This is one maintainer-selected real-module extraction with two repeats per arm,
not an independent developer field trial, difficulty-calibrated sample, whole-repo
task, or population reliability estimate. The defect was naturally present before
the study; root supplied its observed trigger and explicit compatibility boundaries.
Real module, CLI caller, digest catalog and template bytes were copied from the
base commit under `package/`. The caller was inspection context, not a runnable
complete package. Template AGENTS/CLAUDE files were explicitly inert data shared
by all arms; their prose makes this a workflow-package comparison, not semantic
absence/presence of Devlyn advice.

The [protocol](../experiments/0191/PROTOCOL.md) predicted that B would complete
both repairs within scope, match C, and take at most50% of C's total time. Any B
requirement/scope failure meant NO-GO; a native tie would not demonstrate B value.
Registration froze68 files before serial A/B/C/C/B/A dispatch, requested
`gpt-6-astra/high`, Codex0.155.1 and1800s/workflow. C explicitly used current
canonical `--spec --no-pair --no-risk-probes` with an independent same-model
primary judge. It is not the default paired production cost.

Original code scored26/42; the independent positive reference42/42. Named faulty
variants scored26/42 (follows links),30/42 (leaf guard only),40/42 (suppressed
incoming defaults),40/42 (eager unused-path guard),34/42 (allows internal links),
and10/42 (deletes obstruction). Every exact failure set was asserted before calls.
Product-only external assessment was arm-blind; root transcript/diff review was
not blind. Diagnostics were evaluated separately for an identified obstruction
and actionable guidance, without reference-specific vocabulary scoring.

Fable5.1 reviewed the protocol/checker before dispatch. Accepted changes included
diagnostic decoupling, internal-link/deletion mutants, exact failure sets, template
isolation, deadline semantics, seals including modes/links, and actual canonical
acceptance. Raw review and adjudication remain in `runs/protocol-review/` and
`REVIEW-ADJUDICATION.json` (330.106s, reported estimate$1.61701525).

The local0183 launcher copy needed one control-fidelity correction: stamp only
the `${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}` assignment, as the real installer
does. Whole-token replacement also changed the sentinel comparison and made the
runtime block reject its own stamped default. `STAMP-CALIBRATION.json` records
old exit1 versus corrected exit0; `launch-delta.patch` retains the exact change.
Historical0183 sources/results were neither edited nor rescored.

## Workflow, scope and claim audit

`ASSESSMENT.json` records protected bytes/modes, allowed product paths, tests,
external checks and actual `task-complete.pipeline_acceptance` for both C archives.
`EXECUTION-AUDIT.json` completes the deliberately pending manual fields: root
reviewed217 structured tool records, every production diff line and tests, plus
the primary judges'4 and7 non-mutating commands. All six diagnostics identified
both obstructing components and gave a usable move/replace/retry instruction.
Only the authorized module and focused regression file changed as product files;
fixtures and module operations stayed inside disposable participant directories.
No observed out-of-checkout task operations or publication; this is transcript
evidence, not exhaustive syscall monitoring or an OS confinement guarantee.

C archives are `rs-20260920T015815Z-f008cfae66f3` and
`rs-20260920T021226Z-f3d7f848e93b`. PLAN, IMPLEMENT, BUILD_GATE, CLEANUP,
VERIFY MECHANICAL, fresh primary JUDGE, finish gate and archive completed with
receipt/source/report bindings. No repair round was needed. Worker receipts
attest requested dispatch and prompt/session identity, not provider-internal
effective models; native primary-judge headers attest Astra/high. Root verified
both canonical skill copies against frozen source plus assignment-only stamping.

Nonzero commands included intentional red tests, new-file `diff --no-index`,
a missing optional package.json, premature search for a worker's not-yet-created
test and a search excluding the state path. Final test counts and completion
claims match actual raw results. C03's PLAN reproduction was permitted by its
prompt; C04's stronger parent-added no-tests restriction applied only to C04 and
was followed. No new rule was retroactively imposed on C03.

Native logs retain nonfatal load warnings for four malformed global skill files.
Parent prompts excluded host skill cards/memory; child canonical wrappers used
their own isolated configuration and feature defaults. The audit does not claim
identical child context isolation or a prompt-only causal effect.

## Production repair and verification

**No workaround / No guesswork:** `REPRODUCTION.json` records the baseline writing
backup data through the ancestor link and replacing the instruction file. The
violated invariant was directory identity before recovery writes. In
`bin/instructions.js:37`, replacing recursive mkdir with parent-first `lstatSync`
checks rejects symlinks and other non-directories before backup/incoming output;
missing directories are created normally. Lazy placement in `retainFile` preserves
fresh, unchanged-managed and source-in-place operations that need no recovery.
The synchronous API, caller, ownership/merge logic and default instructions remain
unchanged. Scope is static pre-existing entries, not hostile concurrent swaps,
mount confinement, arbitrary hardlinks or a general filesystem sandbox. Intentional
symlinked recovery layouts now require real directories when recovery is needed.

**No overengineering / Subtractive-first:** replace the unchecked creation rather
than adding a helper, flag or wrapper. Removing either component guard reopens the
corresponding escape; removing missing-directory creation breaks normal recovery.
Only these checks, regression coverage and the user-facing recovery note are new.

Opus5 independently reviewed the production source (96.627s, reported
estimate$0.2971965). Its missing internal-link regression finding was fixed.
Its test-discovery concern was resolved against the actual production CI command;
hypothetical arbitrary-name handling and unrelated leaf diagnostics stayed out
of scope. See `SOURCE-REVIEW-ADJUDICATION.json`; root verified the final added test
case and README after that review, without claiming a second Opus verdict.

Validation: baseline packed PackageTests14/14; final packed PackageTests16/16;
against original module bytes, the new symlink method failed24 subtests
(including diagnostic failures on paths already failing for another reason),
while the non-directory/unused-path characterization method already passed. Original functional escape is separately demonstrated
by the calibrated checker. Final regression coverage reaches real CLI callers,
both filenames/components, backup/conflict, outside/inside/dangling links,
non-directory blockers and unused paths. Symlink creation is POSIX-only in the
production suite; the obstruction/unused test runs on Windows too. Full required
`bash scripts/lint-skills.sh` passed. Package identities/commands/raw red-green
streams are in `PRODUCTION-CHECKS.json`; lint output is `lint.log`. Hosted CI and
delivery status are recorded separately in `FINAL.md` once observed. Local tests
used Node25.4.0; hosted workflow selects Node24/Python3.12. The baseline already
used the same `lstatSync` option for destination inspection; no older-runtime
support claim is added.

Pre-dispatch failed calibration attempts, an invalid spec complexity value and
an interrupted baseline test pointed at the source checkout are retained. The
latter recursively copied owned scratch; it was stopped, its temporary tree was
removed, and the proper npm-pack baseline was then verified. See
`PRE-DISPATCH-FAILURE.md`, calibration versions and logs. A post-run root diagnostic
audit assertion mistakenly required “rerun”; it was removed in favor of the
registered manual criterion before writing audit results. No frozen score changed.

Original user WIP6 and1176 prior evidence files (including0190) remain byte-identical,
and original Git status is unchanged. All68 frozen input hashes and six product
seals still match; `PRESERVATION-AFTER.json` and `FINAL-INPUT-AUDIT.json` record this.

Opus5 final packet review reconciled the counts and arithmetic and raised no
blocking finding (208.321s, reported estimate$0.5641965). Root clarified saturation,
time variability, red-control methods and audit units; see
`FINAL-REVIEW-ADJUDICATION.json` and `runs/final-review-opus/`. The runtime-floor
concern was adjudicated against the already-existing destination `lstatSync` use
and actual CI configuration. This bounded review did not rerun checks.

## Next unfinished work

Keep0187/0190/0191 exposed tasks out of fresh confirmation. Seek a disjoint natural
task with interacting compatibility/failure-recovery requirements and an external
oracle, or an independently supplied field task for Mission1 gate15. Freeze scope,
resource boundaries and actual control fidelity first, then compare full request
completion before failure/repair-inclusive time and available cost. Neither the
0190 reminder nor0179 minimal contract has earned operational adoption.
