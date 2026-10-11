# f05-CF-CONFIG-codex-C-r1 — finalized source and lifecycle audit

2026-10-10. Read-only inspection; no tests/oracle rerun, regrade, external call or product change. This preserves **raw CHECKS_PASS**, not admission: CF-CONFIG/CF-LEASE admission remains withheld for the known environment/oracle issues. No comparison treats f04's disputed assertion as a validated source defect.

Artifact root: `/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f05-CF-CONFIG-codex-C-r1/`. Sibling raw verdict: `verdict-f05-CF-CONFIG-codex-C-r1.json`. It records all 12 oracle rows PASS, 21 public tests PASS, local delivery PASS, identity MATCH, COMPLETE usage (621,831 input / 15,940 output), 435.63498337499914 owner seconds, `EXITED_0`, CLEAN teardown. The public and oracle commands both exited 0 without timeout; oracle stderr is empty.

## Original QA and submitted source

All four original QA files are byte-identical to baseline and the frozen visible fixture: `checks/helpers.py`, `run_checks.py`, `test_format.py`, `test_smoke.py`. Three additive suites contain 16 tests (includes 7, merge 2, reload 7); they import production APIs and contain no hidden/gold reference. No original assertion or runner was weakened.

Four production modules changed. `snapshot/visible/beacon/loader.py` keeps cache state within each call, detects current-stack cycles, reapplies cached branches at their include positions, and returns sorted canonical dependencies. `merge.py` recursively combines objects and copies mutable retained/replacement values. `manager.py` resolves before publication, copies values on storage/return and updates generation based on merged-value equality. `paths.py` adds contextual ConfigError handling for resolution failures; existing calls remain supported through an optional chain argument. Exported definitions, parser, error/model types and examples remain unchanged. These observations support the bounded recorded checks; they are not a general correctness proof.

The eighth changed path is `visible/docs/format.md`: it adds one sentence explaining that a failed path-resolution diagnostic uses the attempted absolute path. No original contract sentence was removed. Added tests exercise this failure behavior. The oracle was evaluated from the frozen external fixture, not from the submitted documentation; this sentence does not alter its requirements. The added direct merge-detachment test documents this implementation choice, not independent proof that f04 violated a required direct-helper contract.

## Integrity and commit binding

Prediction before inspection: zero finalized evidence/input/snapshot/commit mismatches and original QA unchanged. [Raw audit results and hashes](f05-source-audit-raw.json) show:

- All **1,018** evidence files match; failures empty. Evidence manifest SHA256 `a3754077dda02443aa44b5650565f16137e9869bb091d45ddb1ebdfde9c18a8f` matches the verdict.
- All **54** sealed inputs and **5** prepared bindings match. All **46** snapshot files/modes match `checked.json`; checks/delivery hashes match their checked bindings.
- Read-only Git object inspection (`GIT_OPTIONAL_LOCKS=0`) finds all **46** committed file contents/modes equal the assessed snapshot. HEAD/delivery commit is `390baf7966042242f1718737b5ba6e1f71c0182f`, parent baseline `277fb5d0f758a2e7b709f01335f5ea211dbfaa0d`.
- Raw checks SHA256 `02b7aaeada71476a3a9affdf0abb69e82342a40a3c6d178aeb65c0d24eac369a`; delivery SHA256 `e812253704cbb0c4957de9ab14c6029ad6a1c19671ef575aea59d8d36f739bd2`.

## Cell completion precedes dispatcher termination

The parent journal `/Users/aipalm/.local/share/nx01/0237-live/dispatch-confirmation-cf-config-resume-v1.jsonl:7` has f05 START at **08:50:35.132928Z**, with no f05 FINISH. That absence is distinct from the cell's retained native completion:

| UTC evidence | Recorded boundary |
| --- | --- |
| 08:57:51.525 | Native `task_complete`, `home/.codex/sessions/2026/10/10/rollout-2026-10-10T08-50-37-01a12501-cb14-7fc1-9c07-dc17969080f8.jsonl:180`. |
| 08:57:52.853397 | `run/result.json` filesystem mtime; file records `EXITED_0` and CLEAN teardown. |
| 08:57:53.627681 / .921742 / .924151 | Filesystem mtimes of checks, delivery and final raw verdict respectively. |
| 10:14:25.050018 | [Recorded stop request](confirmation-environment-stop.json): stopped dispatcher PID 95669 receives SIGTERM then SIGCONT after f05 final, to prevent subsequent dispatch. |
| 10:16:23.481554 | [Recorded exit observation](confirmation-dispatcher-exit.json): parent exec session reports exit 143 and process query finds it absent. This is observation time, **not an exact exit timestamp**. |

Thus the parent termination did not interrupt f05's native execution, evaluator or finalized verdict. The empty parent per-cell stdout log and missing FINISH do not override those independent artifacts. The journal was left unchanged; no final event was invented. Only this derived report and its audit JSON were written.
