---
id: "0114-harness-direction"
title: "Count failures and per-run efficiency fairly; correct harness continuation"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Count failures and per-run efficiency fairly; correct harness continuation

## Context

The user requested an end-to-end direction audit against the north star with exact Fable 5.1 and Grok 4.6. The confirmed immediate defect is that the layer reader treats the identical product BLOCKED before VERIFY as a scored failure in L1 but replaceable infrastructure in L2. Binding continuation documents also contain contradictory and superseded entrypoint, pair, and mission states. A second synthetic reproduction shows unequal base repetitions bias the token best-of-N denominator: at reps 4/1/1, an 8× per-run L1 token load yields N1_tok=2 instead of 8. Synthetic inert-launch tests also confirm ambient L0 context leakage and a nested timeout wrapper leaving ordinary descendants alive. Fix these before completing the already authorized comparison; preserve current runtime behavior until a scoped behavioral experiment justifies a change.

## Requirements

- An attested L2 product failure that legitimately ends before a pair judge runs remains a scored non-shipment (f_ship=1), not a replaceable infrastructure row merely because unexecuted judge evidence is absent. The scorer accepts the corresponding truthful not-run representation. Genuine engine/venue/identity failures retain explicit infrastructure classification.
- Any pair evidence actually emitted remains subject to exact registered model/version/effort and stream validation. Successful pair-required runs with missing evidence, inconsistent claimed execution, wrong identity and malformed evidence remain rejected. A product failure does not license bypassing evidence of a judge that actually ran. Preserve TIMEOUT's unknown-usage semantics. Do not claim unexecuted-pair lift or success.
- Existing replacement selection refuses a second attempt for the newly retained product-failure row; it still replaces genuine infrastructure rows. The smoke gate continues to require real pair reachability and attestation; outcome retention does not weaken that gate.
- Add focused synthetic regression cases in the existing self-test surfaces, using injected launches and synthetic task contents only. Show the before failure and after success on canonical unopened VERIFY, and controls for successful/missing/wrong-identity pair, legitimate mechanical early block if supported, and infrastructure unavailability.
- Correct current NORTH-STAR/MISSIONS/HANDOFF and 0113 current-status guidance using opened code and durable decisions. Preserve historical entries as historical; preserve HANDOFF verbatim user blocks. Explicitly distinguish conversational work authorization from mandatory phases once resolve is entered; preserve executor pins. Current policy remains VERIFY pair default when available, explicit routes fail closed, and broader model/ceiling superiority remains unproven.
- Token best-of-N anchors use exact mean output tokens per base run per arm, preserving sums across models within each run. Unequal repetition counts must not change a fixed per-run ratio (4/1/1 with L1=8× L0 yields N1_tok=8, matching 4/4/4). Preserve total-token diagnostics, unknown-TIMEOUT propagation, wall anchors, top-up exclusion from anchors, monotone rules and quality arithmetic. Add focused synthetic unequal/equal-repetition and unknown-usage regressions.
- All arms use the existing isolated Claude launcher with fresh homes, frozen environment and the same model/effort/MCP contract; L0 remains goal-only and retains exact `--allowedTools` semantics, never a silent `--tools` substitution. Remove the redundant L0 environment and nested bounded-launch layer; the existing driver owns each registered 1800/3600-second deadline, including launch preparation, and ordinary process-group cleanup. Keep TIMEOUT unknown usage, preserve captured streams when available, and test hostile ambient context plus actual ordinary child/grandchild timeout and interruption behavior with inert binaries. Existing launcher callers keep their behavior. Missing metadata on a bounded expiry follows the registered unknown-attestation allowance equally; malformed or wrong identity evidence remains invalid.
- Record the three-engine direction adjudication and immediate post-panel product decision branches in one concise iteration record. Honor existing 0070 direction instead of inventing a new intake/closure framework. INCONCLUSIVE/NULL do not automatically justify removing pair; quality and efficiency must both inform scoped confirmation.
- Register A15's exact outcome/attestation correction before a new scoreable collection. Recompute normalized apparatus, parameter pins and scripts seals in the existing order; product staged intervention hash, model seats, corpus, panel, reps, thresholds, quality arithmetic and wall arithmetic stay unchanged; the sole token arithmetic amendment is the per-run normalization above. Remove the now-unused `l0_env` and external `run_bounded` registration/seal references; the historical external file stays untouched. Preserve old collection artifacts and identify the fresh post-amendment run for the root's relaunch.

## Constraints

- Single writer and task-scoped edits only. Intended surface: benchmark/ceiling/scripts/claude-isolation.py; benchmark/layer-lift/run-lift-panel.py, score-lift.py, README.md, registered-params.json, scripts.sha256; autoresearch/NORTH-STAR.md, MISSIONS.md, HANDOFF.md, DECISIONS.md, iterations/0113-layer-lift-meter-STUB.md, iterations/0114-harness-direction.md.
- Product config/skills, installed mirrors, root AGENTS/CLAUDE, corpus/panel/oracles and operator drain script stay byte-identical; changing them would confound the pending intervention.
- No evaluation of real rows during implementation. New tests use synthetic ledgers/tasks and existing seams; existing self-tests may mechanically execute their existing fixture assets and need no wholesale rewrite; do not open hidden registered oracle content or sealed task outcomes. Root owns old-run preservation and relaunch after full verification.
- Prefer deleting invalid unconditional requirements to adding an abstraction; any new carrier/branch must be needed to distinguish the reproduced failure from missing evidence on an executed judge.
- No new flags except the required exact `--allowed-tools-csv` launcher forwarding option; no external dependencies, model hardcodes, new default routes, release/publish/push or unrelated cleanup.

## Out of Scope

- Claiming the entire harness production-ready or universally superior from this corrective change.
- Changing runtime phase selection, default pair policy, SURFACE_CLOSE behavior, shipping thresholds, model seats, hidden acceptance, task panel, or study arithmetic beyond the explicit token normalization.
- Fleet substrate, a new closure framework, new broad instrument, model release comparison, or full ceiling run.

<!-- devlyn:verification -->
## Verification

- `python3 benchmark/layer-lift/run-lift-panel.py --self-test` passes the existing and focused new injected-launcher/outcome/replacement regressions, including false successful claims over empty/malformed/contradictory completed-pair stdout, retained truthful emission BLOCKED, genuine valid stdout, and preserved pair/whole-driver timeout controls.
- `python3 benchmark/layer-lift/score-lift.py --self-test` passes the existing arithmetic and new retained-failure/invalid-attestation and repetition-normalized token-anchor regressions.
- `python3 benchmark/ceiling/scripts/claude-isolation.py self-test` passes existing isolation checks and the narrowly added option contract.
- `python3 benchmark/layer-lift/drain-quick.py --self-test` passes unchanged.
- `shasum -a 256 -c benchmark/layer-lift/scripts.sha256` succeeds for every registered file.
- `bash scripts/lint-skills.sh` passes.
- `git diff --check` passes.
- Fresh read-only review checks the actual diff against the confirmed source conflicts, requested direction, unchanged intervention, and exact stated claim boundaries. No runtime quality lift is inferred from these deterministic tests.

## Amendment — 2026-09-05, before new collection

The user explicitly reinforced genuine quality AND efficiency ordering and prior exam defects. The synthetic scorer proof (`.devlyn/direction-20260905/token-rep-normalization-proof.log`, preserved with iteration receipts) found a favorable-to-harness repetition bias. This amendment expands the original correction before IMPLEMENT or new outcome collection; it does not react to hidden outcomes. The original PLAN-only invocation is preserved as superseded, without claiming implementation or verification.

A final pre-implementation amendment adds the existing isolation apparatus file to the surface (12 paths). Actual inert subprocess proofs confirmed caller environment leakage and the nested wrapper process-group escape. The common launcher plus existing driver deadline removes that extra layer; no new model comparison or hidden outcome informed this amendment. Prior PLAN-only runs are preserved as superseded.

## Amendment — 2026-09-05, final-review finding A15-JUDGE-001

The first completed product review in run `rs-20260905T092108Z-8e9404a2d660` returned NEEDS_WORK after BUILD_GATE and independent MECHANICAL each passed 7/7. The Codex primary found that `run-lift-panel.py:1119` copies a present pair stdout without parsing it, while :1124 validates only stderr; valid identity/usage can therefore accompany empty or malformed judge output and pass pair smoke. Fable returned PASS; supplemental Grok returned PASS, with a separately recorded freshness violation. The binding HIGH finding remains; raw review and merged evidence are archived with that run. This is findings iteration 1/3, not a hidden-outcome-driven change.

Clarify R2/R3/R4 using the existing shared judge emission/collector contract: validate completed non-timeout executed-pair stdout and reject a claimed pair sub-verdict more favorable than its normalized source outcome. Successful collection uses the maximum summary/finding rank; collector rejection normalizes to BLOCKED, matching the product contract. Thus malformed stdout with falsely claimed PASS is invalid, while the same capture and valid identity/usage with truthful pair BLOCKED remains a scored non-shipment and is not retryable. Compare the pair sub-verdict, not the harness final terminal; preserve valid normalization and stricter outcomes. Missing required captures and wrong identity remain invalid independently. A normalized binding pair outcome (rank at least NEEDS_WORK) cannot accompany a shipping overall PASS/PASS_WITH_ISSUES; reject that contradiction rather than accepting a false shipment. This additional consistency guard does not replace the pair-sub-verdict comparison. Add injected empty/whitespace/malformed/missing-verdict and binding-finding-with-PASS controls with otherwise identical valid stderr, plus the same malformed capture with truthful BLOCKED (retained/nonretryable), genuine completed-PASS and actual pair/whole-driver TIMEOUT controls. Do not require a completed terminal reply on a registered deadline; preserve unknown usage and existing identity/capture rules. Reuse the existing frozen source contract rather than a new parser or model-writable arm copy.

The twelve-file surface, seven literal commands and bounds, unchanged product staged intervention, model seats, panel, repetitions and thresholds remain fixed. Refreeze A15 apparatus, params, both pins and seven seals before any fresh scoreable collection. The owner commits only this spec amendment, preserves cumulative implementation WIP, and starts a fresh full run under the existing commit-after-full-gates/final-trio instruction; the prior NEEDS_WORK is neither rewritten nor labeled exhausted.

The successful-parse precondition in the first owner amendment is superseded before IMPLEMENT. Actual Fable R1 named `config/skills/devlyn:resolve/references/phases/verify.md:245–248`; root and an independent source audit confirmed `verify-merge-findings.py:1298–1319` and its existing malformed-output test: collector rejection is an explicit product BLOCKED. Blanket infrastructure exclusion would recreate the favorable-to-L2 failure-retry bias. The PLAN-only `rs-20260905T095801Z-392cb0a8fb6f` archive preserves that supersession (worker PASS, incomplete PLAN lifecycle after rejected standalone completion; no IMPLEMENT). This clarification retains original failure fairness and exact identity rules; it does not remove a failed result or weaken successful pair evidence.

Actual isolated Grok R1 joined Fable's GO on that rank rule (`grok-design-r1.validation.json`: empty MCP/skills and only three read tools). Root additionally opened `run-lift-panel.py:790–796,1104,1154–1157`: final-terminal acceptance and shipping arithmetic otherwise ignore an executed pair's binding outcome. The same-output control must also reject claimed pair BLOCKED with overall PASS, and valid binding pair output with an overall shipping claim; truthful nonshipping BLOCKED remains retained. This is the neighboring R2 false-success case, not a general state validator or changed quality arithmetic.

## Amendment — 2026-09-05, missing state with executed captures

Supplemental source audit and root's actual synthetic `missing-state-proof-v3` on run `rs-20260905T100953Z-dce2515635b5` found a variable-lifetime regression: non-timeout L2 with missing pipeline state but present valid pair stdout/stderr reaches `pair_verdict` before assignment (`run-lift-panel.py:1060,1132`), raising UnboundLocalError instead of returning the required infrastructure-invalid row. The focused proof changes only the existing synthetic fixture selection in memory; runtime source SHA `f29c8bb92050cf0d3c7373abb7cb5a633fd9aa317a61c262e4be35f7442260d3` remains unchanged. The broader malformed-state claim was not reproduced and is excluded.

Clarify R2/R4: initialize unavailable pair verdict before state-dependent assignment and add the missing-state plus valid captures control in existing self_test_a15. Preserve the missing-state reason, explicit infrastructure result, existing raw evidence/identity checks, completed-output rank and shipping guards, retained truthful BLOCKED and deadline behavior. Do not catch programming errors or add a new parser/branch. Actual Fable 5.1 and Grok 4.6 design GO is recorded in `.devlyn/fix-0114-pair-stream-20260905/accepted-missing-state-design.md`; Grok's prose design reply is separately transport/identity attested and is not canonical final-review evidence.

That run's seven BUILD_GATE commands all exited zero, but its overall gate failed because root omitted PHASE0's required `.devlyn/untracked.baseline`. Preserve the invalid-setup archive, without claiming CLEANUP, VERIFY, final-trio PASS or fix-loop exhaustion. The next fresh bootstrap must run the existing baseline writer before its first worker. This operator correction changes no product source. The owner amendment preserves the twelve-file surface, seven literal commands/bounds and commit-after-full-gates/final-trio instruction; refreeze only apparatus, params, both pins and seven seals before collection.
