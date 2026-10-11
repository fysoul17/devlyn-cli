# Prospective 0238 owner init integration

2026-10-10. Research apparatus correction only. No product instruction, native
call, Docker execution or historical regrading occurred in this revision.

The 0238 Runner deliberately replaces 0237's owner with the matched 0234
identity/evidence/accounting set. Merely adding init to the solo adapter would
therefore leave pair owners without it. The new `../cell-init-v1.py` retains
0234's run function with only an explicit `--init` added to Docker create.
It delegates identity (including Claude native effort), evidence, Docker,
tmp preservation and final-message extraction to the original 0234 functions.
It preserves 0234's `ended_at`, inherited container/volume labels, resource
caps, auth mounts, watchdog, failed teardown behavior and native route handling.
The new source SHA and actual `--init` argv identify the changed owner; no
argument is hidden behind its recorded argv.

`../runner.py` changes two lines: load the new owner module and add its source
to `seal.inputs`. It still binds that owner's exact evidence object into usage
accounting and updates it with the registered task object. The check, delivery,
peer policy, source/drift and classification paths are unchanged. The shared
peer helper and all historical 0234 sources remain unchanged.

Before edits, all six v3 files were copied to `apparatus-v3/` and verified
against the original v3 manifest. The original manifest remains unchanged.
`apparatus-review-manifest-v4.json` now freezes seven prospective source files
and the exact inherited pair-native dependencies; it is not dispatch approval.

## Predictions and results

`owner-init-v1-prediction.json` preceded the first targeted run. Thirteen of
fourteen test methods passed, including the new run-AST, actual-argv and native
owner-effort tests. The new classification replay's positive case passed, but
its no-op/deleted cases hit the duplicate-cell guard: a loop variable `name`
inside the test helper overwrote its newly added cell-name argument. The runner
correctly refused the reused identity. Raw failure output remains in
`owner-init-v1-tests.{json,stdout,stderr}`.

Only that test helper variable was renamed to `attribute`; the reversible
`owner-init-v1-test-fix.patch` reconstructs the original predicted test hash.
`owner-init-v1-prediction-2.json` preceded the second run. All 14 targeted tests
passed in 13.515 seconds, exit 0. Raw output is in
`owner-init-v1-tests-2.{json,stdout,stderr}`. The checks cover:

- Run AST parity with 0234 after removing only `--init`, unchanged delegated
  functions, matching evidence/usage objects, task rebinding and source sealing.
- Actual mocked Docker arguments equal both retained argv records; caps and
  native arguments remain; `ended_at`, CLEAN teardown and credential cleanup
  are preserved. A real native identity parser consumes synthetic messages.
- Registered owner `max` effort passes and `high` fails; peer resumed native
  effort, child routing and complete usage accounting remain enforced.
- Seeded CLI defaults, zero activation, recovered-attempt accounting, EQ3
  routing and the F23 supplemental exit/row contract remain intact.
- The already retained positive/no-op/deleted check and delivery packets yield
  CHECKS_PASS / PRODUCT_INCOMPLETE / PRODUCT_INCOMPLETE respectively. The
  existing local deleted-product full-check test still yields four FAIL rows
  without scope violation. These are classification replay/local mock checks,
  not new pinned-image evaluation results or historical verdict changes.

Unchanged broad full-check controls were not rerun. The independently retained
0237 actual owner-boundary probe establishes Docker init adoption/reaping with
the same image/caps, but this revision has no native peer smoke and makes no
model-compatibility or efficacy claim. Bounded review of v4 and separately
registered native smoke remain necessary before a future pair comparison.
