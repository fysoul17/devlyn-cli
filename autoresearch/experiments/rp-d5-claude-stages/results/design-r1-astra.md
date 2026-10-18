The narrowed question is right. Four Claude-only slots are a reasonable minimum for describing both tasks at both efforts. Existing receipts establish token composition; fresh traces are needed for tool identity and effort differences. Keep Codex out and retain the descriptive limits (**No overengineering, Optimized**).

The cited totals and effort pins check out. The design still needs these material fixes:

1. **HIGH — The turn definition contradicts the accounting it promises to reuse.**  
   [DESIGN.md:79](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/DESIGN.md:79) selects terminal project-transcript lines. However, [audit.py:245](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/0254/audit.py:245) obtains authoritative usage from native terminal response bodies and accepts provisional-only transcript anchors. [test_audit.py:266](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/0254/test_audit.py:266) explicitly covers that valid case. My in-memory fixture check produced **zero design-selected turns versus three native responses, totaling 139 output tokens**.

   **Fix:** create one row per audited receipt, join through message/request/agent identity, and classify the complete native response content. Use project JSONL for identity anchors and tool results. Preserve the auditor’s conflict checks instead of relying on “last copy wins” (**No workaround**).

2. **HIGH — Wall reconciliation does not validate wall attribution.**  
   [DESIGN.md:91](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/DESIGN.md:91) assumes index timestamps denote request starts. The auditor never validates timestamps; its fixture gives all three requests the same timestamp. Consecutive differences plus endpoint residuals telescope to total wall even when the attribution is wrong. Parent/child ordering is also unspecified, and the entire final inference goes into the trailing residual, leaving Report without attributed wall.

   **Fix:** verify timestamp semantics against native evidence or capture-source code before freezing. Specify global ordering and overlapping-child treatment. Explicitly label the final inference interval, separating shutdown only when supported. Test those semantics; a matching total alone is insufficient (**No guesswork**).

3. **MEDIUM — Two stage boundaries produce incorrect classifications.**  
   At [DESIGN.md:116](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/DESIGN.md:116), an Explore+Edit row becomes Mixed and therefore never establishes the “first mutation.” Subsequent reads can remain Explore after files changed. At line 112, `PR` and `PENDING` start “After delivery,” although the helper returns those while the PR remains unmerged ([task-complete.py:824](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/config/skills/_shared/task-complete.py:824)).

   **Fix:** track mutation independently of the aggregate stage label. Start After delivery only on proven completed delivery, including `CLEANUP_PENDING` with `delivery_status: COMPLETE`; keep pending-merge work in Deliver. Freeze precedence between this boundary and ordinary tool predicates.

4. **MEDIUM — Removal eligibility still permits inflated costs and discretionary selection.**  
   [DESIGN.md:127](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/DESIGN.md:127) requires a counted row to contain **a** repeated call. One redundant reread plus a necessary new test are both Verify, so the row is not Mixed and its entire cost can qualify. Paths and successful exits also do not establish equivalent operations or unchanged dependencies. “Largest marginal-token share” lacks a cross-task aggregation rule.

   **Fix:** count only rows wholly attributable to the nominated redundant operation; otherwise exclude their indivisible costs. Freeze operation identity, relevant-state equivalence, devlyn provenance, and a scalar cross-task ranking with deterministic ties. Keep output-plus-cache-write labeled as a nomination proxy: line 89’s savings estimate must not imply that removing one turn eliminates later requests’ entire cache reads. Later ablation must use the owner ladder’s separate total wall/input/output per success, including failures (**No guesswork, No workaround**).

5. **MEDIUM — The cold-cache correction removes real task work.**  
   [DESIGN.md:98](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/DESIGN.md:98) excludes “the first request’s” wall without specifying whether this means c01 or every slot. Under the wall definition, that span includes effort-dependent inference and tool execution, not isolated cache initialization. A c01-only subtraction biases BV/max.

   **Fix:** retain raw deltas as primary, disclose cache counters separately, and optionally show a clearly labeled sensitivity analysis excluding the first interval symmetrically from both paired slots. Do not describe that as measured cold-cache overhead.

Round-0 closure: **Astra #3/#6 and Grok #1/#6/#7 are resolved.** Astra #1/#2/#4/#5 and Grok #2/#3/#4 remain partially resolved through the issues above. Grok #5’s requested adjustment was added, but needs correction as finding 5 explains. Thinking containment, explicit failures, historical labels, and hypothesis-only nomination are sound improvements.

I inspected the accounting implementation and tests and ran the fixture check entirely in memory. No files changed or live experiment ran.

VERDICT: REVISE
