# f03-CF-CONFIG-codex-A-r1 — finalized source audit

2026-10-10. Bounded read-only inspection; no new consequential contradiction found
between submitted source and the recorded visible obligations. This preserves the
existing CHECKS_PASS result; it is not a rerun, regrade, general correctness proof
or candidate-admission decision. No other cell, including active f04, was inspected.

Artifact root:
`/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f03-CF-CONFIG-codex-A-r1/`.
The sibling `verdict-f03-CF-CONFIG-codex-A-r1.json` records CHECKS_PASS, source and
local-delivery pass, all 12 oracle rows PASS, 19 public tests PASS, identity MATCH,
COMPLETE usage (305590 input / 13357 output), 371.9056895410031 s owner wall and
CLEAN teardown. These are retained results, not newly executed tests. No independent
model assessment was requested in the recorded verdict.

## Original QA and change scope

All four original QA files remain byte-identical both to `baseline.json` and the
frozen CF-CONFIG visible fixture: `checks/helpers.py`, `checks/run_checks.py`,
`checks/test_format.py`, `checks/test_smoke.py` (paths under `snapshot/visible/`).
No existing assertion or runner was weakened. Three new suites contain 14 test
methods: test_includes.py 4, test_merge.py 2, test_reload.py 8. They exercise
relative diamonds/canonical aliases/read-once behavior, recursive replacement and
input isolation, fresh dependency reads, detached publication, semantic generation,
failure preservation/repair, first-load failure and diagnostic include chains.
They test production exports; no hidden oracle, gold data or alternate production
module is imported. Source edits are confined to beacon/loader.py, manager.py,
merge.py and paths.py. The seven changed/added paths match checks and delivery.
All original docs, examples, schema reader, error/model types and exports remain
unchanged in the checked snapshot.

## Visible contract → concrete source

Line references below are relative to `snapshot/visible/` in the artifact root.

| Visible obligation | Submitted implementation |
| --- | --- |
| Format docs `:10-23`: declaring-file-relative canonical identity, legal diamonds, current-stack cycles, one read per distinct document per call, sorted Path dependencies. | `beacon/loader.py:8-35` keeps cache/active/dependencies local to each call; checks active before cache, visits each include in order, removes active entries in finally, and returns sorted Path dependencies. `paths.py:6-15` canonicalizes relative to each declaring parent and converts resolution failures into contextual ConfigError. |
| Format docs `:11-16`: recursive objects; otherwise later replacement including lists/null; no input mutation. | `beacon/merge.py:4-12` deep-copies base and replacement values, recursively merges only two dict values. Cached resolved branches are merged at every include position rather than skipped globally. |
| Reload docs `:3-14`: current bytes on every load, failure preserves last successful state, later repair recovers. | `loader.py:8-10` has no cross-call memo or metadata shortcut. `manager.py:16-24` resolves the whole graph before assigning `_current`; loader exceptions cannot partially publish. Active/cache state belongs only to the failed invocation. |
| Reload docs `:16-25`: semantic generations, refreshed dependencies, nested caller isolation, None before first success. | `manager.py:10-24` starts at None, compares merged values for generation, copies values on publication and deep-copies every current/reload return. Loader calls also build independent values. Exported definitions in `__init__.py` and `model.py` are unchanged. |
| Format docs `:3-8` plus request: keep useful ConfigError diagnostics. | Unchanged `document.py:4-17` checks JSON/schema and wraps read errors; loader propagates the root-to-child chain and canonical cycle path (`loader.py:16-26`); `paths.py:12-15` wraps unresolvable names. Added include/reload tests cover error paths and recovery. |

The goal explicitly asks for focused coverage. New tests supplement the original
QA rather than replacing it. Public-path validity does not rely only on the added
tests: the retained independent 12-row oracle is also PASS. Its expectations or
implementation were not changed or rerun in this audit.

## Finalized artifact and commit binding

Before the integrity read, the recorded prediction was zero finalized-evidence,
checked-snapshot and commit-object mismatches, with original QA unchanged. Results:

- All **847** files named by `evidence.manifest.json` match their retained SHA256;
  its failures list is empty and its own digest matches the verdict
  (`11ac35c69c4e88c2d7424e6f70e804cc9ee915f53276f7368e1ad11bb8181131`).
- Prepared files match the seal; all **22** snapshot file digests/modes equal
  `checked.json`. checks.json and delivery.json hashes also match checked.json.
- Read-only Git object inspection (`ls-tree`, `cat-file`, `rev-parse`, with
  GIT_OPTIONAL_LOCKS=0) finds all **22** committed file contents/modes exactly equal
  to the evaluated snapshot. HEAD is delivery commit
  `a945cc6d392df33a8fad6676c3f0abb08943fbc5`, whose parent is the recorded baseline
  `5e18c5f7d040b18c11c88120d511b53083732290`.

No product/check/fixture/authentication file was written or executed. Only this
separate derived report was created; the shared confirmation ledger and audit
remain owned by evidence_audit. No new benchmark outcome is inferred beyond f03.
