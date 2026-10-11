# Staging the reviewed pair-native dependency bytes

2026-10-10. Narrow correction for Astra's v4 MEDIUM: `stage.py` checked the
manifest's apparatus files and shared process primitive, but ignored its
`pair_native_dependencies`. A changed historical identity/evidence/accounting
source could consequently pass staging and be newly sealed by the later runner.

The operational draft now requires the three registered dependency bindings
(`0234/cell.py`, `evidence.py`, `record_usage.py`) and verifies their exact bytes
against the review manifest before creating the destination. Missing bindings
and mismatches are explicit errors. The v4 manifest, seven reviewed apparatus
files, historical sources, packages, product and model configuration are unchanged.
The stage entrypoint therefore requires the dependency-bearing v4 review contract;
an older or incomplete manifest cannot silently omit those checks.

`stage-native-dependencies-prediction.json` preceded the first local test run.
Both changed/missing-dependency rejection tests passed. Valid staging completed,
but its test compared macOS's unresolved `/var` temporary path with the returned
canonical `/private/var` path and failed that assertion. Only the fixture root
was changed to resolve its path; the staging implementation was not changed.
The first raw output and reversible test-only patch are retained.

`stage-native-dependencies-prediction-2.json` preceded the corrected run:
3/3 tests pass in 0.027 seconds, exit 0. The tests stage small synthetic archives,
reject changes to each of the three native dependencies independently before
destination creation, and reject an omitted binding. Raw command, exit, timing,
stdout/stderr and unchanged-v4-file checks are in
`stage-native-dependencies-2.{json,stdout,stderr}`.

No Docker, native CLI, model, account API or real-credential access is used by
these tests. This addresses staging provenance only; it is not native smoke,
product admission or an authorization to dispatch. A bounded follow-up review
of this fix remains the next gate.
