# Dependent native children: one bounded, untested replacement candidate

Offline design audit, 2026-10-10. Evidence is limited to finished f02, its retained lifecycle audit, the current completion guide, and 0232/0235 history. No implementation, model call, active-cell inspection or new measurement.

**Recommendation:** the evidence licenses a narrow prospective candidate, not adoption or an open-ended additional solo program. The existing obligation was read and disobeyed; the remaining testable distinction is an explicit native execution/wait choice. **No overengineering** favors replacing that duty in place; **No guesswork** requires observed native behavior and delivery before claiming improvement. If that distinction does not change observed execution and delivery in a bounded test, retain the current guide and proceed with the remaining research decision.

## Exact replacement and scope

In `config/skills/_shared/task-completion.md:170–171`, replace only:

> Wait for your children, stop your dev servers and task writers, then leave the task tree.

with:

> For a child whose result is needed to complete this request, use an explicitly foreground call or a supported native wait until its terminal result arrives; handle that result before the final response. Wait for any remaining task children, stop your dev servers and task writers, then leave the task tree.

Keep the following `Make the FIRST completion call...` instruction and writer attestation unchanged. If later implemented, update the existing installed mirror through the normal packaging workflow; add no root-principle paragraph, setting, helper, new review requirement or guide. This location replaces the existing child-wait duty instead of appending a new definition of done. f02 actually read this complete guide before spawning, so lack of initial visibility is not the observed issue; its distance from launch remains a compliance risk.

The candidate does not require a child or review. A child can still run concurrently with useful owner work when its result is awaited through a supported native mechanism before the final response. Where no such wait is exposed, the completion dependency should use supported foreground execution. In the retained f02 documentation, `claude -p` permits explicit `Agent.run_in_background: false`; merely omitting the field is insufficient. Do not invent `TaskOutput` for its absent tool catalog. Interactive sessions with different foreground capabilities must use their supported native behavior.

## Why this is a distinct hypothesis, and why it may fail

f02 read the generic wait requirement, explicitly launched a background reviewer, and promised to return after reviewing it. The native CLI subsequently enforced `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`: ten minutes after the owner's last turn it stopped the unfinished review. This is the post-final-turn ceiling, not child inactivity or the apparatus watchdog. Source checks passed but no task commit existed. See `f02-child-lifecycle-audit.md` and `confirmation-source-audit.md` for raw locations.

0232 `harness-ladder.md:276–279,396–399` already preserved lost final reviews as possible evidence for a later challenger. 0235's rejected sentence concerned verification of requested/failure/compatibility behavior before removal; it did not specify dependent-child scheduling. Its rejection still argues against assuming more prose improves compliance.

The strongest counterargument is that the current guide already requires waiting and finishing; another sentence may be ignored, or may serialize reviews without improving delivery. The review itself was owner-selected and might have been unnecessary. This candidate does not solve review cost, interruption recovery or false confidence, and a completed child can still return unusable work. Forcing all children into foreground, disabling background execution, changing the native ceiling, or deleting useful delegation would exceed this demonstrated failure.

## Smallest falsifiable development gate

Only after the existing CF block and baseline decision are complete; its registered arms, inputs and verdicts remain unchanged. Register a separate baseline/T comparison and criteria before dispatch.

1. **Native mechanism smoke, separate research cost:** one explicitly foreground native child returns a distinct answer that the parent must consume before a small local commit. Record actual launch mode, terminal child result, subsequent owner action and commit binding. This validates the supported route, not spontaneous compliance, long-review performance or product benefit. The retained f02 trace already supplies the negative ceiling evidence; do not shorten/disable its timer or manufacture ten minutes of idle work.
2. **Compliance and delivery:** one matched baseline/T pair on an unchanged known failure-path development fixture, with the ordinary implementation request and no instruction to spawn or foreground a review. Freeze exact package/model/effort/source and order. Record guide loading; whether an owner-selected child becomes a completion dependency; actual foreground/native-wait behavior; child terminal result; owner consumption; source checks and attributable commit. If no relevant dependency occurs, label the lifecycle hypothesis **not triggered**, while preserving each ordinary product outcome. Do not equate non-activation with apparatus failure or claim a gain from baseline/C outcomes elsewhere.
3. **Negative control:** one matched baseline/T pair on an easy request without a necessary child. Watch for newly manufactured reviews, lost useful parallelism, extra tool work, quality/delivery regressions and total cost. Passing this small gate licenses only further confirmation; it cannot establish cross-engine or broad bare-performance gains. Any cross-engine shared-guide admission still requires the corresponding engine's delivery/compliance check.

Retain all owner/child wall time and input/output, including failed work; missing native identity/usage remains an apparatus gap. Source success without delivery fails the product endpoint. A repeated final-response-while-dependent-child-pending path in T, invalid native wait, source/delivery regression, or clear unnecessary-work regression rejects this candidate at the development gate. No trigger or equal successful lifecycle behavior is inconclusive for benefit: stop this bounded gate rather than rerun until an apparent win. Even a favorable four-cell development comparison needs prospectively registered replication/confirmation before adoption; no cost saving or sentence efficacy is asserted here.
