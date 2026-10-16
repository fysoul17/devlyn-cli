The cleanup evidence gap is real, but the draft does not yet establish the smallest mechanism or a safe adoption gate. No files changed.

1. **HIGH — Successful cleanup does not support the proposed action claims.**  
   [Draft lines 33–38](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/DESIGN.md:33) promise facts observed in that call. However:
   - Scratch cleanup **empties the directory; it preserves the directory itself**. Say “emptied owned scratch,” never “removed scratch.”
   - Cleanup accepts already-absent worktrees and local/remote refs. Absence does not prove this invocation removed them.
   - In-place checkouts are preserved.
   - Already-`COMPLETE` resume verifies custody and returns without reobserving merge or workspace cleanup.

   Specify per-call outcomes or use qualified historical wording on resume: “Receipt records delivery and workspace cleanup complete.” For `NOT_OWNED`, make no scratch-cleanup claim. Sources: [scratch](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/config/skills/_shared/task-complete.py:537), [workspace cleanup](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/config/skills/_shared/task-complete.py:594), [resume](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/config/skills/_shared/task-complete.py:743). **No guesswork; Production ready.**

2. **HIGH — Several other sentences assert facts their status does not establish.**  
   [Draft lines 45–47](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/DESIGN.md:45):
   - `LOCAL_ONLY` can return without acceptance or a task commit; an existing test explicitly preserves uncommitted work. Report publication restriction, and name a commit only when established.
   - `FAILED` means a recorded task verdict, not necessarily failed verification. Say “Recorded task result FAILED; publication skipped.”
   - `BLOCKED` from `main` can follow successful merge and partial cleanup. Say “Completion stopped,” not “Delivery blocked,” unless phase evidence proves that.
   
   Scratch cleanup also runs on `PR`, `PENDING`, `LOCAL_ONLY`, and `FAILED`; retained scratch must remain visible in their reports. Sources: [return paths](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/config/skills/_shared/task-complete.py:725), [scratch handling](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/config/skills/_shared/task-complete.py:658), [error boundary](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/config/skills/_shared/task-complete.py:880). **Production ready.**

3. **HIGH — ADOPT permits regressions and omits the cost gate.**  
   [Decision lines 108–115](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/DESIGN.md:108) prohibit `FALSE`, but allow verification, merge, or reconciliation to deteriorate from `SUPPORTED` to `MISSING`/`AMBIGUOUS`. Require nondecreasing supported-category counts and overall report success against contemporaneous X. Reconciliation can be outside the improvement target while remaining protected against regression.

   Restore wall/input/output accounting and predeclare the comparison and zero-success rules. A nonincreasing instruction file does not establish nonincreasing execution cost: `report` adds tool-output and downstream-input tokens. The [owner’s ladder rule](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/NORTH-STAR.md:66) explicitly covers those costs. If this experiment only supports routing, remove automatic patch-release adoption.

4. **MEDIUM — PR reporting must happen after final result enrichment.**  
   At [helper line 826](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/config/skills/_shared/task-complete.py:826), `merge_refused` is attached **after** `completion_result()` runs. Effective mode can also come from repository policy. Pass these facts explicitly or format after enrichment.

   Prefer “PR … is open” over “Opened”: the helper can reuse an existing PR. `PENDING` does not itself prove `autoMergeRequest` exists; say “not yet merged” unless auto-merge was observed. “Kept until it merges” should become a present-state statement, without promising later deletion of an in-place or unsafe linked checkout.

5. **MEDIUM — The why-chain supports a hypothesis, not the necessity of a full report generator.**  
   [Lines 16–29](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/DESIGN.md:16) correctly identify missing explicit workspace-success data. They do not prove this causes omission rather than report selection.

   Under **No overengineering**, first consider explicit successful `workspace_cleanup`, or narrow the proposed sentence to cleanup alone; delete the new verification/commit/delivery restatements that duplicate existing fields. Choose one candidate for this rung. If retaining successful `workspace_cleanup`, do not merely remove its `pop`: [line 670](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/config/skills/_shared/task-complete.py:670) currently treats **key presence** as retention and must instead distinguish success from retention.

6. **MEDIUM — Correct the history and bound the Claude guard’s interpretation.**  
   The [opening claims](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/DESIGN.md:7) overstate evidence:
   - rp-d3 had an unmerged PR and was **INCONCLUSIVE**, not an attained NO RESCUE result.
   - rp-d2 Y had **0/2** graded Codex cleanup successes, not 0/4.
   - Claude’s historical 6/6 includes rp-d2 Y reports; they were not all X.

   Using 4.2.22 for both current arms is sound. The 4.2.18 history is motivation, not a control. **Keep the two Claude Y slots as a mandatory 2/2 all-category release guard**, with pinned CLI/model/effort. They establish observed candidate safety, not a controlled historical no-regression comparison; comparative Claude cost claims need contemporaneous X.

7. **MEDIUM — Freeze the contract and require branch coverage before live measurement.**  
   [Smoke lines 86–88](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/DESIGN.md:86) check field presence, which cannot catch the false sentences above. Extend existing isolated tests to cover those paths, both cleanup-retention reasons, and failures before publication versus after merge/removal.

   Before smoke, freeze the exact replacement paragraph, candidate commit, artifact hashes/manifests, token counts, task-to-pair mapping, and inherited apparatus rules. Restore rp-d3’s explicit smoke policy: qualified smoke precedes measurement; a failed attempt consumes the pair; only one spare pair; failed spare stops; smoke never changes thresholds. Two changed filenames alone do not exclude unrelated changes inside them.

8. **LOW — Match the statistical caveat to the paired design and actual threshold.**  
   [Line 119](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/DESIGN.md:119) gives the unpaired Fisher example for 3/4 versus 0/4, while adoption also permits 3/4 versus 1/4. Three favorable discordant pairs yield paired one-sided exact \(p=0.125\). Publish pair outcomes and describe this as a small-sample empirical gate, without implying stronger confirmation.

VERDICT: REVISE
