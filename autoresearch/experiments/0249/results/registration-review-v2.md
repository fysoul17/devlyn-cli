# 0249 final registration review v2 — binding closure

## Prediction before probes

2026-10-10T23:46:27.712525+00:00

Narrow closure only: both original import-time task inventories will now be selected; all 119 execution inputs and retained selected artifact bytes will remain unchanged; 14 publisher files and accepted patch will match their immutable copies in bytes/modes; the only registration changes will select v2 and enforce complete before/after-slot binding checks. No repeated native, auth, container, test or evaluator calls.

## Input SHA-256 before

```json
{
  "autoresearch/experiments/0249/registration-v1.md": "19a5bdadf1ce305f6f53927c08254433150682c94113bc4955795a4179f37f21",
  "autoresearch/experiments/0249/registration-v2.md": "0a387f6cb2c653ba6f48531a19e00ee56d106affa3c77600215c3f055851ecf3",
  "autoresearch/experiments/0249/schedule-v1.json": "df5bb783f7810b9d36f2dd32b1b3e7bdd3448d1b60c7defdfecdcf013f223043",
  "autoresearch/experiments/0249/bindings-v1.json": "5a1cf15b25b16df8fb9e2305efe9e478ec18a75a29d6e862331208407d47ffdb",
  "autoresearch/experiments/0249/bindings-v2.json": "6bb3526654cbbf6207be436d785a4752b46d1ce47a4e35fba79f7435c9fa70e4",
  "autoresearch/experiments/0249/results/baseline-copy-v1.json": "8bc428c7ce1515bde233b47be9f41965c9996123864ed80fe85334b6d71541b1",
  "autoresearch/experiments/0249/results/registration-review-v1.md": "99688cd56f7a0b34c43d97c24d0d99f2a897332347eee00a1b630350fb95a64e",
  "autoresearch/experiments/0249/results/evaluator-report-v2.json": "f8a830fc485e918a852e289ba9b1152ab581843456bca2a9d4214df352ee2a3c",
  "autoresearch/experiments/0249/runner.py": "a2b22bac4e2847580ceb58d337be80f49d9c28d9b45942fee74c2c96638cb41c"
}
```

## Raw read-only verification

```json
{
  "input_count": 119,
  "selected_count": 502,
  "execution_inputs_identical": true,
  "execution_input_mismatches": [],
  "selected_mismatches": [],
  "retained_selected_changes": [],
  "added_original_tasks": {
    "0233": "4034b86cb44e6333c1d86a9e3a7f74bde3841500f0250f9629b0adb78a1665e3",
    "0234": "ba7e6c7b30ba51cae0b91aae960aa03be123ca84c79e8ba87d49893474050c10"
  },
  "copy_file_count": 15,
  "copy_bytes_mode_or_provenance_mismatches": [],
  "removed_publisher_files": 14,
  "removed_files_have_identical_bound_copy": true,
  "operative_live_publisher_paths": [],
  "schedule_hash_unchanged": true,
  "registration_sha256_matches": true,
  "v1_binding_preserved": true,
  "changed_review_inputs": []
}
```

## Verdict — SHIP

**H1 closed; zero remaining CRITICAL/HIGH/MEDIUM findings in the final registration and narrow v2 changes.** This closes review round two. No further routine review is needed. The registered immutable freeze and independent freeze/binding audit must still complete before native dispatch.

The two original task JSON files now belong to the operative selected-artifact set and match their current hashes. Registration v2 explicitly requires root to verify every selected binding before and after each slot, in addition to runner inputs and controls. This closes the demonstrated import-time ROWS drift gap without mutating an earlier frozen file or changing scoring (**No workaround**, **Production ready**).

All 14 publisher inputs removed from the operative set have byte-identical bound copies; the fifteenth copied file is the accepted product patch. Bytes and modes match both the equivalence report and the original publisher. The twelve verified product hashes, original upstream 4.2.5 commit/path and build/package evidence remain preserved. Later authorized publisher edits/cleanup no longer mutate the study's baseline evidence. Historical v1 binding/report bytes remain selected as history; their superseded live publisher references are not recursively operative. Study copies must remain retained.

Diff inspection confirms no outcome, zero-success, resource, accounting, STOP, block-audit, task, treatment or schedule changes. The 119 execution inputs are identical; all 502 selected hashes match; retained selected artifacts are unchanged. Prior v1 review's accepted evidence/limits remain applicable, including the matched current baseline and exact S treatment, separate engine/hard-task gates, descriptive A, per-engine controls, all attempted/child/recovered costs, unknown residuals, immediate STOP with no retry/regrade, and independent block audit before advancement. The original E1 calibration-driver STOP and no-replay reconciliation remain intact.

Only this v2 review report was written for closure. No product/source edits, native/auth/container calls, tests or evaluator repetitions occurred.

## Input SHA-256 after

```json
{
  "autoresearch/experiments/0249/registration-v1.md": "19a5bdadf1ce305f6f53927c08254433150682c94113bc4955795a4179f37f21",
  "autoresearch/experiments/0249/registration-v2.md": "0a387f6cb2c653ba6f48531a19e00ee56d106affa3c77600215c3f055851ecf3",
  "autoresearch/experiments/0249/schedule-v1.json": "df5bb783f7810b9d36f2dd32b1b3e7bdd3448d1b60c7defdfecdcf013f223043",
  "autoresearch/experiments/0249/bindings-v1.json": "5a1cf15b25b16df8fb9e2305efe9e478ec18a75a29d6e862331208407d47ffdb",
  "autoresearch/experiments/0249/bindings-v2.json": "6bb3526654cbbf6207be436d785a4752b46d1ce47a4e35fba79f7435c9fa70e4",
  "autoresearch/experiments/0249/results/baseline-copy-v1.json": "8bc428c7ce1515bde233b47be9f41965c9996123864ed80fe85334b6d71541b1",
  "autoresearch/experiments/0249/results/registration-review-v1.md": "99688cd56f7a0b34c43d97c24d0d99f2a897332347eee00a1b630350fb95a64e",
  "autoresearch/experiments/0249/results/evaluator-report-v2.json": "f8a830fc485e918a852e289ba9b1152ab581843456bca2a9d4214df352ee2a3c",
  "autoresearch/experiments/0249/runner.py": "a2b22bac4e2847580ceb58d337be80f49d9c28d9b45942fee74c2c96638cb41c"
}
```
