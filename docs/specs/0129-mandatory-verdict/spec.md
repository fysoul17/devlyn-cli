# 0129 — Make mandatory requirement findings agree with the existing verdict contract

## Goal

Correct contradictory VERIFY guidance so a concretely demonstrated violation of an applicable mandatory task clause cannot be dismissed because its impact seems small, the case is rare, the defect pre-existed, or the deliverable is documentation. Keep the existing severity/boolean/summary routing contract and respect the exact task scope.

## Evidence and decision

0123 explicit-r2 recognized the unsupported README `--engine auto` command while emitting MEDIUM/verdict_binding:false.0124 source-advice records also use apparently harmless downstream impact to justify LOW/false. These are historical evidence of classification decisions, not missing flags in the collector. Current canonical VERIFY narrows the MEDIUM path to regressions, while the inline branch wrongly describes PASS_WITH_ISSUES as LOW-only. Confidence wording also suggests a runtime threshold that finding_rank does not implement.

Root initially favored honoring strict true at every severity. Actual Fable5.1 and Grok4.6 advice identifies the decisive delta: neither observed false flag would change under that expansion; MEDIUM/true and explicit NEEDS_WORK summaries already bind, while a shared predicate edit also changes collector admission and historical replay. Choose the smaller prose-only correction. Retain disagreement about applicability and whitespace ambiguity without rewriting frozen0123/0124 judgments. A touched line or criterion_ref alone does not establish an obligation; the exact task clause and contradiction do.

## Requirements

1. Replace regression-only binding guidance with demonstrated unmet or contradictory applicable mandatory clauses, including new requirements and customer documentation. Require the exact quoted clause and concrete file:line evidence. Keep regressions covered. Impact, rarity and pre-existing origin do not excuse a demonstrated applicable violation.
2. State the existing emission contract precisely: use HIGH/CRITICAL as appropriate, or at least MEDIUM with literal boolean verdict_binding:true for a demonstrated mandatory violation; LOW/INFO true is not a binding route. Keep HIGH/CRITICAL floors, explicit source-summary floors, merge ownership and missing-coverage handling. Confidence is reported evidence uncertainty, not an additional merge threshold.
3. Preserve exact scope. Preferences/style, stronger inferred invariants, genuinely ambiguous requirements and unrelated pre-existing issues do not become mandatory violations. Explain the actual ambiguity/evidence limitation rather than substituting an impact argument. Do not infer applicability solely from a changed line or requirement reference.
4. Reconcile the duplicate pair-merge and PASS wording in canonical phases/verify.md and resolve SKILL.md. PASS_WITH_ISSUES may include nonbinding MEDIUM. Retain existing routing, models, review bounds, independent peer contexts and findings format.
5. Scope is only these two canonical instruction files and normal mirrors. No runtime helper, parser, schema, severity mapping, confidence filter, model default, customer AGENTS/CLAUDE research content or historical result changes.

## Prediction, verification and acceptance

Prediction: the instructions will provide one explicit supported binding path for recognized applicable mandatory violations and one consistent advisory path. The current merge already supports that path; no output coercion or new classifier is needed. If the final source still restricts mandatory binding to regressions or implies unsupported confidence/LOW-only routing, this correction fails.

Before source acceptance, independently review the exact diff against the current rank/parser/collector and positive/advisory boundaries; run required bash scripts/lint-skills.sh and git diff --check; confirm normal mirror parity and unchanged runtime/entry files. Do not add tests that merely restate prose. Retain actual advisor answers and source/audit limitations. Acceptance establishes coherent instructions, not fewer native misses, general accuracy, speed or token gains. Native effectiveness remains an explicit frontier for the next independently scoped task; do not replay closed0124/0125/0128 to manufacture confirmation.

Principles: No workaround (fix the judgment instruction), No overengineering (delete conflicting examples, reuse existing routing), No guesswork (actual records and a falsifiable source contract), Production ready (visible repair obligation), Optimized (minimum change toward correct completion).
