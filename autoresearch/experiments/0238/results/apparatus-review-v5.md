# Prospective 0238 accounting guard — v5 review

2026-10-10. SHIP. No actionable HIGH or MEDIUM findings in this bounded v4-to-v5 accounting review. This is prospective apparatus acceptance, not product admission, measured dispatch authorization or historical regrading.

The inherited recorder remains the cost source. The new guard reconciles native per-model session aggregates against terminal message counters, including owner/native children, independent peers and cumulative resumed sessions. Message identity prevents counting successive snapshots as separate charges. Same-request terminal evidence is required to close explicit API errors/retries; an unrelated successful request or a prior bound error cannot discharge a later anonymous retry. Every receipt-bound Claude first/resumed capture is inspected. Missing carriers, unbound interrupted messages and mismatched counters remain UNKNOWN. Thinking counters are reconciled when reported but never added on top of output.

Runner integration preserves reported counter totals, the old completeness label, null unknown residual and a known-usage lower bound, then uses the existing STOP gate before product evaluation. It does not turn accounting failure into product failure or subtract failed work. Existing recovered-but-accounted peer controls remain valid. The changed input map seals the new guard. Stage's generic files-map verification covers its v5 hash; the exact three native-dependency bindings and shared primitive check remain enforced before destination creation.

Independently verified all 11 v5 file hashes and all three native dependency hashes. Manifest SHA256 is 264cc1e494c48489479afc234b2afe232e0a05e5ad9436b8f29287345e36ac1a. Inspected the retained final replay: short/long MATCH and interrupted d01 UNKNOWN preserve the original reported costs. The tests invoke the legacy writer only on disposable copies and verify original source hashes afterward.

Prediction before independent verification: the 11 focused accounting controls would pass, preserving real control hashes and all reported costs. Ran `python3 -B -m unittest -v test_claude_accounting` from the experiment directory: 11 tests passed in 0.231 seconds, exit 0. This includes message snapshots, missing terminals, request-bound versus unbound retries, child scope, peer recovery/resumes, reasoning counters and the retained short/long/d01 controls. Inspected the supplied 26-runner-test coverage; did not repeat its suite or any unchanged Docker evaluator.

Limits: this checks retained native accounting, not provider invoices or invisible server-side work. The positive exact-request retry closure is synthetic; the pinned CLI's anonymous d01 retry remains unverifiable. Conservative STOPs are intentional when terminal native evidence cannot explain charges. Pure Codex accounting is unchanged. Native operational pair smokes and prospective registration remain separate gates. No model, authentication or Docker calls, no original-cell writes and no source edits were made during this review.

## Exact reviewed identities

- `peer.py`: `d500dc6ca46c5ab1528c6d419530ad89094f36443461979c6aa1d27933fa3294`
- `policy.py`: `d02be3a1700c0a78aab0d141580da7eacc97be97a60ea7cfc27e9bd31b154606`
- `runner.py`: `5370feb1a9e46dc5abd67e6954cb2019b1ba246d216da7254270e79b17781997`
- `test_peer.py`: `c06be9e3fa81275b420f305de76aa686d22bc250d5c165aa0aa959aefff02a27`
- `test_runner.py`: `6db017e16cf5822ed3f240834670f1bd357e84bc62210ac59b49bbb9ff013b48`
- `f23_precision.py`: `47124cac8635717d90d22cb5719579e611952e3925ec3ef28a2f678312fe9e89`
- `cell-init-v1.py`: `daa0e64da8b745746b1abb4445317b965ce1dca5d385e993379a71e20022266f`
- `claude-accounting-v1.py`: `706d56f9ec46be57abe1528d7b0c5d320bfcc8a036bcd97cf1dbe8a0f8fa2914`
- `test_claude_accounting.py`: `73aba2dd3c04457b072b65ff761630795227fc85f5dd82f2aa18599277e3f300`
- `results/stage.py`: `9c288dd37a20f114a9ef2d6167da23502748b634b0d6b08870a95c4626d17500`
- `results/test_stage_native_dependencies.py`: `97fe00153f2059a50decfec62a183faae7fd293fb0a2ecd7b8aeec704be6c2e2`
- `autoresearch/experiments/0234/cell.py`: `fabfd55829c2873e06f42abefab598ee8a717e636122a108b03faee0e9e6f0c5`
- `autoresearch/experiments/0234/evidence.py`: `595f9018b489034a38c7be61b15e046ec66a393d5ea0c12d9f7e13c8b80de691`
- `autoresearch/experiments/0234/record_usage.py`: `7692df70d31e2bbef1cec23f081e0040eeb7f58dd7b08bd99df7ff6bdb32f164`
