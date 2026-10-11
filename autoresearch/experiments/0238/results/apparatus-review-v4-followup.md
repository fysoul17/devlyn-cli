# 0238 v4 staging correction — bounded second-round review

2026-10-10. SHIP. The prior MEDIUM finding is resolved; no remaining HIGH or MEDIUM finding in this narrow follow-up scope.

stage.py now requires exactly the three registered 0234 cell.py, evidence.py and record_usage.py bindings in pair_native_dependencies and checks their bytes before creating the destination. Missing/incomplete bindings and dependency drift fail explicitly. This closes the gap between reviewed native dependencies and the later runtime seal without changing owner, peer, accounting or product classification code.

Prediction before verification: the three fixture tests would pass, establishing valid offline staging, independent rejection of drift in each dependency and missing-binding rejection before destination creation. Independently ran `python3 -B test_stage_native_dependencies.py` from this results directory. Exit 0; raw outcome:

```text
test_each_native_dependency_drift_is_rejected_before_destination (__main__.NativeDependencyTests.test_each_native_dependency_drift_is_rejected_before_destination) ... ok
test_missing_native_dependency_binding_is_rejected (__main__.NativeDependencyTests.test_missing_native_dependency_binding_is_rejected) ... ok
test_valid_native_dependency_manifest_stages_offline (__main__.NativeDependencyTests.test_valid_native_dependency_manifest_stages_offline) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.026s

OK
```

Exact checked hashes:

- stage.py: 9c288dd37a20f114a9ef2d6167da23502748b634b0d6b08870a95c4626d17500
- test_stage_native_dependencies.py: 97fe00153f2059a50decfec62a183faae7fd293fb0a2ecd7b8aeec704be6c2e2
- apparatus-review-manifest-v4.json: e85487aa88210d7caac68ccaf190386559026af8e604bb286267bb3c75a959fd

All seven reviewed apparatus source hashes still match v4. The original fixture path-normalization failure and its test-only correction remain documented; they do not change the staging implementation reviewed here.

Only disposable synthetic staging ran. No real staging, credentials, Docker, native CLI or model call was used. Native 0238 calibration remains separate and pending; this verdict does not authorize dispatch, register an experiment or admit a product instruction. No unrelated files were re-reviewed.
