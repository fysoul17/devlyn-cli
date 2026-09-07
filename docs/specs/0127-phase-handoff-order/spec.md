# 0127 — Make phase handoff instructions agree with the existing lifecycle

## Goal

Correct the contradictory orchestration instructions exposed by installed0123 legacy-r3. Existing state operations already support the required behavior. Keep the implementation to the canonical resolve SKILL and normal mirrors; no new runtime helper, phase, schema, dispatcher or model policy.

## Observed failure and prediction

At source1b799d5, SKILL75 requires atomic transitions but CLEANUP325 says to complete separately and JUDGE342 opens VERIFY after the preceding MECHANICAL step. Native175/194/196/211 follows that conflicting order: standalone CLEANUP completion, rejected MECHANICAL startup before any commands, then VERIFY spawn. Single-phase259–260 also records implement_passed_sha before its checkpoint, unlike phase-gated268. The rendered PLAN prompt has no terminal LF; native Agent added one. These remain historical deviations under functional acceptance, not repaired evidence.

Prediction: removing local ordering conflicts gives the orchestrator one valid sequence: successful scoped implementation checkpoint then its HEAD; atomic CLEANUP→VERIFY (or existing predecessor/bypass/initial verify-only route); open VERIFY identity before MECHANICAL; render/dispatch fresh judges after sealed mechanical evidence. Clarifying exact prompt delivery may prevent the extra LF, but wording alone cannot prove native conformance.

## Requirements

- Swap the existing single-phase checkpoint and implement_passed_sha instructions. Assign only the successful checkpoint HEAD before downstream phases; preserve scoped staging and failure behavior.
- Replace standalone CLEANUP completion wording with the existing atomic handoff, retaining post-sha and all required completion/session/next-phase identity arguments. Preserve bypass, initial verify-only and repair-round routing.
- Move frozen primary selection and VERIFY span opening ahead of MECHANICAL. A phase span is lifecycle state, not a judge invocation. No rendered judge prompt or fabricated mechanical result is required at that opening; actual fresh judges still receive completed sealed evidence afterward.
- Replace the existing PLAN exact-byte phrase with equally direct wording that forbids adding a terminal LF. Keep literal rendered contents, digest meaning and native fresh-worker route; no path handoff or evidence normalization.
- No changes to customer AGENTS/CLAUDE, grading, pair policy, role controls, report guard, old runs,0124 frozen inputs or0125 proposal.

## Verification and acceptance

Inspect all touched workflow branches against the existing writer/renderer/spec verifier. Run required `bash scripts/lint-skills.sh`; normal mirrors must match. No tests merely restating prose. Preserve source review and raw results. Source acceptance establishes coherent instructions only; the next independently scoped ordinary task must retain actual phase ordering, checkpoint identity and Agent prompt bytes before any native-conformance claim. Do not replay the accepted README task merely to obtain a cleaner historical result.

Principles: No workaround (correct contradictory instructions), No overengineering (reuse current state operations), No guesswork (native evidence and falsifiable prediction), Optimized (remove repeated/contradictory text).
