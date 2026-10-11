# 0243 registration preparation review v1

Verdict: **SHIP-for-registration-preparation**. No CRITICAL, HIGH, or MEDIUM finding in the reviewed draft and bindings. This is not a registration freeze, transport acceptance, native dispatch authorization, or adoption decision.

The review covered registration-draft.md, startup-catalogs-v1.json, package-integrity-v1.json, controls-v1.json, runtime-measured.json, the inherited 0238 proposal and relevant frozen apparatus. No tests, models, authentication, stage, or native calls were made. Only this report was written. The parent reports s02 raw CHECKS_PASS/COMPLETE with its independent audit ongoing; this review does not certify that audit or the still-required s03 Codex-to-Claude transport gate.

## Fairness and decision scope

The ten-cell serial order matches the 0238 proposal exactly. The same ordinary F23 task is used across A/B/S/H/P, with no explicit pair request added. B is the new integrated 4.2.4 solo baseline; A is reported alongside. S separates extra owner checking from H's fresh same-primary session; P must justify its route against S and H. The explicit Claude/Codex tool asymmetry prevents interpreting P as a pure model-diversity intervention.

The draft preserves the proposal's per-engine screen and stricter later admission rules. One exposed F23 run per arm is diagnostic, not confirmation. Fresh harder cases, repeated confirmation, and easy/orphan controls remain mandatory after a signal. No signal closes this mechanism without declaring a global ceiling. No automatic adoption, favorable reroll, post-result oracle change, or gate relaxation is allowed.

The outcome definitions distinguish automatic activation, peer completion, findings, owner execution, and repair from correct source delivery. No activation earns no independent-check credit but does not redefine correct source as incorrect. Recovered failed attempts retain their costs. Whole-run wall, cached input, output, native children, and all attempts remain counted; unknown usage is not zero, failed-arm per-correct ratios remain undefined, and machinery/identity/accounting faults stop the sequence. These preserve **No workaround** and **Production ready**.

## Read-only verification results

Before verification I predicted matching order/task/package hashes and native startup evidence. Actual results:

- All four selected archive hashes match package-integrity-v1.json. Their 969 regular payloads match packages.json member hashes and the staged extraction. Staged and selected package metadata hashes agree. The prior reviewed builder's explicit full 4.2.4 base and seven integration inputs remain the baseline, rather than a partial overlay onto 4.2.3.
- All 24 installed delivery helper bindings match. All eight installations contain exactly the two devlyn skill entrypoints. B has no pair guide/helper, S has its exact reviewed guide and no peer helper, and H/P contain their exact 0242 guides/helper.
- Staged tasks.json is byte-identical to 0242 tasks-smoke.json, SHA-256 `0f8f531228bbe4e29e3c58b51d226b3c3fe21cbf01ae8ecf7d6b7ca6e86a6e93`. F23 source hashes match. Public/oracle manifests equal 0242's and all their referenced files match. The four oracle rows remain priority-rollback, single-warehouse-fefo, submillisecond-order, and offset-equivalence. Allowed source remains bin/cli.js and tests/cli.test.js. Existing evaluator controls are explicitly reused, not claimed rerun.
- The 53 files bound by the reviewed 0242 manifest have no drift. The new measured output directory does not yet exist. controls-v1.json's runtime hash correctly binds runtime-smoke.json, the installation-validation runtime; runtime-measured.json is a new artifact requiring final freeze.
- Both startup sources are actual system/init events with the expected primary model. Their line hashes match after excluding the newline, and their seal hashes match. Native A has 19 skills; installed P has 21; both report three builtin plugins and an explicit empty MCP list. The recorded catalogs match those native rows after the same sorting used by the runner. Runtime expectations equal startup-catalogs-v1.json, and both evidence sources name the pinned runtime image.

The installed catalog is observed from 0242 and transferred as an expectation to the new baseline using the inspected identical skill-entrypoint set; it is not claimed to be a completed 0243 native observation. The inherited measured runner requires explicit Claude catalog fields, exactly one valid init, and exact normalized catalog equality, so a changed 0243 observation stops rather than being accepted silently. Codex lacks that Claude init format and continues to use its native session evidence. This respects **No guesswork**.

## Bound review snapshot and remaining conditions

SHA-256 at review:

- registration-draft.md: `819ff5d4ea8df452bfa469190491bfb6d8da46ec3dcafd791d66ce3d21486a81`
- startup-catalogs-v1.json: `5ace8865cc01df56ddc40843641ea3cbdcb5fb6945188ad14cbf125d21b86ba6`
- package-integrity-v1.json: `3974e6eca29c9a7ad3cda0ded7172759abdd1527ed2a32c981c06e4d7b107dd8`
- controls-v1.json: `7ccbe4b6d04c52834a03f82bef61891c81fba517c69463f8ca2d24ac420b7f13`
- runtime-measured.json: `8740c48a66b1971e051d1827f8e6d212ba23dbd0f41bec9c61c72c76e9ddd41f`

All registered 0242 operational gates, including independent audits and s03, must pass before the parent creates the dated registration and immutable input freeze. The final freeze must bind the new runtime, packages, controls, source/oracle provenance, exact imported apparatus/dependencies, and startup evidence. No historical outcome or cost is changed by this preparation review.
