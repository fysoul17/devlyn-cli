# Prospective owner-init v1 source review

2026-10-10. SHIP — no actionable HIGH or MEDIUM finding in this bounded research-apparatus change. This is not product admission or authorization to dispatch a model.

Read-only review covered cell-init-v1.py, runner-init-v1.py, test_runner_init_v1.py and the owner-init-v1 prediction/results records. Verified that removing only Docker --init makes the new run-body AST equal the inherited 0233 function. Actual dispatched create arguments equal both retained argument records. New source identity and both new source files enter the prospective seals. Task rebinding reaches inherited identity checks; auth, accounting, watchdog, teardown, cancellation behavior and source/delivery verdict logic remain inherited. No source files were edited or external model calls made.

Prediction stated before verification: AST parity and four offline tests would pass; seals would gain exactly the new runner/owner files while old policy/accounting methods stayed unchanged.

Independent command, from autoresearch/experiments/0237:

```sh
python3 -B -m unittest -v test_runner_init_v1
```

Raw test result (exit 0):

```text
test_identity_gap_stays_visible (test_runner_init_v1.InitRunnerTests.test_identity_gap_stays_visible) ... ok
test_inputs_bind_new_owner_without_changing_legacy_inputs_or_routes (test_runner_init_v1.InitRunnerTests.test_inputs_bind_new_owner_without_changing_legacy_inputs_or_routes) ... ok
test_only_owner_creation_argument_changes (test_runner_init_v1.InitRunnerTests.test_only_owner_creation_argument_changes) ... ok
test_recorded_argv_exit_timeout_and_teardown_are_preserved (test_runner_init_v1.InitRunnerTests.test_recorded_argv_exit_timeout_and_teardown_are_preserved) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.162s

OK
```

Independent hash verification against owner-init-v1-prediction.json returned:

```text
sources 3 mismatches []
historical_inputs 54 mismatches []
```

Exact checked candidate hashes:

- `cell-init-v1.py`: `1312168b0125cedd80f5aefc16f09befc54d05d3fd1177dfa2fcdd9e100ead02`
- `runner-init-v1.py`: `351d1f2d3e4960d5f49162124bb55880281e6a91fd49a521a657935b0dbdcc91`
- `test_runner_init_v1.py`: `54460bd78a7cbf788a6b7f7c989095ada28d9f3f9f0ac031b7f2b1563791f384`

The complete 54-entry historical hash map is retained in owner-init-v1-prediction.json; every entry matched when reviewed, including the frozen runner and imported apparatus. No historical input was rewritten.

Limitation: offline parity does not establish real orphan reaping or native CLI behavior under init. The separately predicted real no-model calibration was still pending this review; its outcome is not included in this SHIP verdict. Cancellation and early setup-failure behavior are inherited, not newly strengthened by this patch. Any later claim about process behavior or resource effects must use the real calibration evidence.
