Two HIGH findings remain from round 0.

1. **HIGH — The table still makes unsupported cleanup claims.**  
   [DESIGN.md:50](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/DESIGN.md:50)–58 treats retention statuses as proof that resources were kept. That is not what the helper establishes:

   - Scratch `RETAINED` includes “owned scratch missing or redirected” ([helper:543](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/config/skills/_shared/task-complete.py:543)). “Kept the task scratch” can therefore be false.
   - Workspace retention can occur before the remote branch is inspected. GitHub may already have deleted it after merge; “Kept … branches” is unsupported.
   - Bound `LOCAL_ONLY` and `FAILED` returns do not establish current worktree/ref presence. A read-only probe confirmed `LOCAL_ONLY` with an absent worktree and zero ref observations.
   - An already-`COMPLETE` receipt records **workspace** cleanup complete; scratch cleanup may still be pending. The unqualified historical sentence overstates that checkpoint.

   **Fix:** Use “Workspace cleanup deferred/skipped: …” and “Scratch cleanup incomplete: …” unless resource presence was observed. Say “The receipt already records **workspace** cleanup complete.” For `FAILED`, use “Publication skipped by this call.” Preserve deletion claims only for recorded actions, and test absent/replaced resources. This closes the remaining round-0 truthfulness findings under **No guesswork** and **Production ready**, without changing cleanup control flow.

2. **HIGH — ADOPT still permits a measured cost regression.**  
   [DESIGN.md:160](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/experiments/rp-d4-helper-report/DESIGN.md:160) permits 10% higher arm totals. It also omits the required per-success denominator and zero-success rules. Round-0 Astra finding 3 remains unresolved; [NORTH-STAR.md:68](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d4/autoresearch/NORTH-STAR.md:68) requires wall/input/output accounting per correctly completed task, including failed attempts.

   Concrete counterexample: X cleanup 1/4, Y cleanup 3/4; verification and merge both 4/4; reconciliation and full-report success both 1/4; all deliveries and Claude guards pass. Give Y 109% of X’s costs. **ADOPT fires despite 9% higher cost per success.**

   **Fix:** Define success and zero-success handling, include all dispatched attempts’ costs, and require each comparable Y cost per success ≤ X. Alternatively, retain the coarse band for routing but remove automatic patch-release adoption.

The cleanup-only mechanism, final-result formatting, frozen instruction edit, smoke qualification, and bounded Claude guard address their corresponding round-0 concerns. Leaving `BLOCKED` unchanged is a sound explicit deferral. No files changed.

VERDICT: REVISE
