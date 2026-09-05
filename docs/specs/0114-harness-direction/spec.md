---
id: "0114-harness-direction"
title: "Count product failures fairly and correct the harness continuation contract"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Count product failures fairly and correct the harness continuation contract

## Context

The user requested an end-to-end direction audit against the north star with exact Fable 5.1 and Grok 4.6. The confirmed immediate defect is that the layer reader treats the identical product BLOCKED before VERIFY as a scored failure in L1 but replaceable infrastructure in L2. Binding continuation documents also contain contradictory and superseded entrypoint, pair, and mission states. Fix these before completing the already authorized comparison; preserve current runtime behavior until a scoped behavioral experiment justifies a change.

## Requirements

- An attested L2 product failure that legitimately ends before a pair judge runs remains a scored non-shipment (f_ship=1), not a replaceable infrastructure row merely because unexecuted judge evidence is absent. The scorer accepts the corresponding truthful not-run representation. Genuine engine/venue/identity failures retain explicit infrastructure classification.
- Any pair evidence actually emitted remains subject to exact registered model/version/effort and stream validation. Successful pair-required runs with missing evidence, inconsistent claimed execution, wrong identity and malformed evidence remain rejected. A product failure does not license bypassing evidence of a judge that actually ran. Preserve TIMEOUT's unknown-usage semantics. Do not claim unexecuted-pair lift or success.
- Existing replacement selection refuses a second attempt for the newly retained product-failure row; it still replaces genuine infrastructure rows. The smoke gate continues to require real pair reachability and attestation; outcome retention does not weaken that gate.
- Add focused synthetic regression cases in the existing self-test surfaces, using injected launches and synthetic task contents only. Show the before failure and after success on canonical unopened VERIFY, and controls for successful/missing/wrong-identity pair, legitimate mechanical early block if supported, and infrastructure unavailability.
- Correct current NORTH-STAR/MISSIONS/HANDOFF and 0113 current-status guidance using opened code and durable decisions. Preserve historical entries as historical; preserve HANDOFF verbatim user blocks. Explicitly distinguish conversational work authorization from mandatory phases once resolve is entered; preserve executor pins. Current policy remains VERIFY pair default when available, explicit routes fail closed, and broader model/ceiling superiority remains unproven.
- Record the three-engine direction adjudication and immediate post-panel product decision branches in one concise iteration record. Honor existing 0070 direction instead of inventing a new intake/closure framework. INCONCLUSIVE/NULL do not automatically justify removing pair; quality and efficiency must both inform scoped confirmation.
- Register A15's exact outcome/attestation correction before a new scoreable collection. Recompute normalized apparatus, parameter pins and scripts seals in the existing order; product staged intervention hash, model seats, corpus, panel, reps, thresholds, and scorer arithmetic stay unchanged. Preserve old collection artifacts and identify the fresh post-amendment run for the root's relaunch.

## Constraints

- Single writer and task-scoped edits only. Intended surface: benchmark/layer-lift/run-lift-panel.py, score-lift.py, README.md, registered-params.json, scripts.sha256; autoresearch/NORTH-STAR.md, MISSIONS.md, HANDOFF.md, DECISIONS.md, iterations/0113-layer-lift-meter-STUB.md, iterations/0114-harness-direction.md.
- Product config/skills, installed mirrors, root AGENTS/CLAUDE, corpus/panel/oracles and operator drain script stay byte-identical; changing them would confound the pending intervention.
- No evaluation of real rows during implementation. Tests use synthetic ledgers/tasks and existing seams; do not open hidden registered oracle content or sealed task outcomes. Root owns old-run preservation and relaunch after full verification.
- Prefer deleting invalid unconditional requirements to adding an abstraction; any new carrier/branch must be needed to distinguish the reproduced failure from missing evidence on an executed judge.
- No new flags, external dependencies, model hardcodes, new default routes, release/publish/push or unrelated cleanup.

## Out of Scope

- Claiming the entire harness production-ready or universally superior from this corrective change.
- Changing runtime phase selection, default pair policy, SURFACE_CLOSE behavior, shipping thresholds, model seats, hidden acceptance, task panel, or study arithmetic.
- Fleet substrate, a new closure framework, new broad instrument, model release comparison, or full ceiling run.

<!-- devlyn:verification -->
## Verification

- `python3 benchmark/layer-lift/run-lift-panel.py --self-test` passes the existing and focused new injected-launcher/outcome/replacement regressions.
- `python3 benchmark/layer-lift/score-lift.py --self-test` passes the existing arithmetic and new retained-failure/invalid-attestation validation regressions.
- `python3 benchmark/layer-lift/drain-quick.py --self-test` passes unchanged.
- `shasum -a 256 -c benchmark/layer-lift/scripts.sha256` succeeds for every registered file.
- `bash scripts/lint-skills.sh` passes.
- `git diff --check` passes.
- Fresh read-only review checks the actual diff against the confirmed source conflicts, requested direction, unchanged intervention, and exact stated claim boundaries. No runtime quality lift is inferred from these deterministic tests.
