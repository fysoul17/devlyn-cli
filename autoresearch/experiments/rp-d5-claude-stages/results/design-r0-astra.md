The question is appropriate, and **four Claude-only slots are a reasonable minimum for descriptive profiles across both tasks and efforts**. Given the deleted transcripts, fresh capture is justified. The prior investigation makes max/high the right second factor; it does not establish the effect on these delivery tasks. Keep Codex out if the claim is narrowed to observed Claude differences (**No overengineering, Optimized**).

The draft is not ready to freeze:

1. **HIGH — Project JSONL alone cannot supply trustworthy token totals.**  
   [DESIGN.md:56](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/DESIGN.md:56) makes it the attribution source, but this repository already documents provisional transcript output of **6 tokens versus 59 in the terminal response**. Repeated block snapshots also need deduplication. The inherited [0254 audit](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/0254/audit.py:245) addresses this.

   **Fix:** use audited terminal receipts for numbers and join transcript labels through request/message/agent identity. Define a counted turn as one unique inference. Processed input is uncached input + cache-read + cache-creation; thinking is already included in output. Reconcile stage totals with audited slot totals and retain UNKNOWN when evidence does not reconcile. Reuse existing accounting rather than creating another implementation (**No workaround, No guesswork**).

2. **HIGH — “Timestamp to next timestamp” does not define stage wall time.**  
   At [DESIGN.md:71](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/DESIGN.md:71), “next” could mean the next raw event or next assistant message. Those choices attribute different intervals. The latter can charge the next response’s generation latency to the preceding action; the former leaves intervening inference time unassigned. Startup, final-response generation and shutdown lack explicit treatment.

   **Fix:** freeze exact endpoint event types and the attribution convention for generation versus tool execution. Require a disjoint partition whose stages plus explicit residual reconcile to owner wall time. Preserve unavailable timing as unknown and avoid double-counting overlapping child intervals. Validate against captured native evidence as well as synthetic fixtures (**No guesswork**).

3. **HIGH — The promised “effort share of the gap” exceeds what this design identifies.**  
   [DESIGN.md:26](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/DESIGN.md:26) and [89](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/DESIGN.md:89) promise gap attribution, while the comparison uses historical Codex X/Y totals and one Claude observation per task/effort. Historical Claude guards used Y; the proposed runs use X. Calling the study descriptive does not resolve that mismatch.

   **Fix:** report **observed within-task max/high deltas** in wall, input, output and turns. Keep historical Codex figures as motivation, without claiming a causal fraction explained. Register a directional prediction before exposure—for example, max produces more exploration inferences while delivery outcomes remain equal. No additional Codex slots are needed for that narrower question (**No guesswork, No overengineering**).

4. **MEDIUM — The taxonomy is incomplete and sensitive to command batching.**  
   [DESIGN.md:59](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/DESIGN.md:59) leaves intermediate no-tool responses undefined. Instruction rereads after edits fit both Orient and Verify; `gh` can investigate issues as well as deliver. “Later stage wins” assigns an entire expensive mixed response to even a tiny delivery operation, changing stage shares merely because commands were bundled.

   **Fix:** freeze recognizable command/path predicates, precedence, no-tool handling and an explicit Mixed/Unclassified category. Define “after delivery” using the successful completion result, not merely a `complete` invocation. Keep mixed costs visible and exclude ambiguous attribution from removal eligibility (**No guesswork**).

5. **MEDIUM — Removal eligibility conflates an expensive stage with a removable operation.**  
   Under [DESIGN.md:79](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/DESIGN.md:79), Verify could exceed 15% even when its redundant portion is negligible. A repeated passing check may be necessary after an edit, rebase or copy. Naming a devlyn rule establishes provenance, not dispensability. “Tokens” and “largest” also leave metric selection and ranking open after exposure.

   **Fix:** nominate one concrete repeated operation, with its originating instruction and evidence spans. Require unchanged relevant state and no renewed verification obligation. Apply the threshold to that operation’s attributable cost, using the same metric in both tasks. Freeze denominators, ranking and tie-breaking. Describe the result as a **redundancy hypothesis for later ablation**, not proven recoverable savings (**No workaround, Production ready**).

6. **MEDIUM — Failure handling is missing despite a reproduced prompt failure.**  
   [DESIGN.md:38](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/DESIGN.md:38) preserves wording that previously caused Claude to stop at `LOCAL_ONLY`, documented in [rp-d1 results:36](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d1-delivery-cost/results.md:36). A shorter run that omits delivery cannot establish an efficiency improvement.

   **Fix:** preregister treatment of failed delivery, interrupted capture and UNKNOWN usage. Retain every dispatched attempt and its costs; do not silently replace failures. Report delivery outcomes beside profiles and withhold equivalent-delivery efficiency conclusions when outcomes differ. Define the new delivery-only success denominator explicitly: rp-d1’s quoted 778 seconds used report-graded successes and included failed-attempt costs (**No guesswork, Production ready**, owner ladder rule).

VERDICT: REVISE
