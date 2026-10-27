1. **Root cause:** the best-supported behavioral explanation is that Claude generalizes from a mechanism’s local success to a broader guarantee. In 0260 [c012-B-r6](/Users/aipalm/.local/share/nx01/archive/reports-0256-0260/0260/c012-F10-claude-B-r6/final.txt) and [c007-C-r4](/Users/aipalm/.local/share/nx01/archive/reports-0256-0260/0260/c007-F10-claude-C-r4/final.txt), the queue lives inside `createApp`; concurrency tests exercise one instance, but reports promise process-wide protection. Removing the queue makes those tests fail—it establishes necessity within that setup, not protection across instances.

   Likewise, 0257 [d022-A-r2](/Users/aipalm/.local/share/nx01/archive/reports-0256-0260/0257/d022-D4-claude-A-r2/final.txt) claims every blocking call is timed, although writer startup performs unbounded stdin writes/readiness reads. Successful tests become whole-path claims. This violates **No guesswork** at the inference step. Bare-arm failures and unsuccessful deletions do not identify a particular principle as the cause; the model-internal explanation remains unproven.

2. **Candidate:** append this single sentence to **No guesswork**, immediately after “Retroactive prediction edits are dishonest.” in `origin/main:CLAUDE.md:15`, identically mirrored in `AGENTS.md` and `config/skills/_shared/runtime-principles.md`:

   > Limit final mechanism and guarantee claims to the resources, instances, and execution paths actually checked, explicitly naming any wider requested behavior that remains unverified.

   This targets reporting directly, unlike 0235’s deletion prerequisite. It adds no reviewer, repair turn, or mandatory experiment.

   Prediction: false completions decrease; witnessed defects and actual completions remain approximately unchanged. Total tokens are weakly predicted to remain roughly flat through shorter, scoped reporting, but the added input is real: any net increase rejects the candidate. This primarily changes claims, not defective code. Honest limits help users avoid relying on unsupported guarantees; they do not make lost writes or hanging tests acceptable under **Production ready**.

3. **Measurement:** compare the unchanged package against package-plus-sentence, Claude only, with **32 fresh replicates per task per arm on F10 and D4**—128 cells. Randomize arm order within task/account/time blocks; freeze model configuration, witnesses, adjudication rules, and analysis before dispatch.

   Primary endpoint: proportion of all dispatched cells containing at least one ordinary-trigger-falsified mechanism claim under the frozen m24 rule, stratified by task. Report uncertainty; this screens for a substantial effect, not small improvements.

   Run witnesses twice on **every applicable tree**, regardless of wording: F10 two-instance/path-alias and non-object JSON; D4 writer death, stall, and delayed startup. Separately count witnessed defects and classify reports as accurate disclosure, contradiction, or omission. Fewer false completions with unchanged defects is reporting improvement only; vaguer reports without explicit limits are metric avoidance.

   Guards: independently assessed completion, required-behavior coverage, safety, wall time, and input/output tokens per dispatched cell and per actual completion, including instruction overhead and failed attempts. Missing usage or insufficient precision cannot establish non-regression. Advance only with improvement and no worsening. Then confirm on fresh bare±sentence runs and D3/F11; check Codex before shared-text adoption. Defer I0185 until instruction exposure is verified—the historical installer cells omitted principles.

4. **Main interpretability risk:** wording-sensitive adjudication. 0260 [c005-B-r3](/Users/aipalm/.local/share/nx01/archive/reports-0256-0260/0260/c005-F10-claude-B-r3/final.txt) escapes because it says “per-app,” despite later process wording. Freeze whole-report treatment of contradictions and blind adjudicators; preserve the historical score alongside disclosure and defect counts. The 0259 erratum shows why selective witness application is unacceptable.

PROPOSAL: Test one scope-limiting sentence under No guesswork, accepting clearer reporting only when defects, completion, wall time, and tokens do not worsen.
