# rp-d8 design round — Astra ultra

I recommend testing **NEW**, with adoption conditional on measured improvement. I verified the repository at `2911b311` and constructed the proposal only in memory. No files were changed; the existing `.gitignore` modification remains untouched.

The strongest argument against changing anything is that **the scope explanation may be a justification rather than the cause of refusal**. Every measured GitHub-backed skip also cited unrequested publication or its consequences. Removing the scope objection could leave delivery unchanged—or merely change the final explanation. The earlier “the user asks you to deliver” treatment produced X 2/4 versus Y 2/4, and rp-d7’s 3/4 used a historical comparator. Neither establishes this proposed mechanism. [rp-d6 results](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/rp-d6-claude-delivery/results.md:3), [rp-d7 results](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/rp-d7-prompt-delivery/results.md:67)

There is one important exception to “every skip”: **g06 had no origin and cited only the helper’s writes outside allowed paths**. It required local completion, not publication. That makes it the cleanest mechanism probe, although one report still does not establish causality. [g06 result](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/rp-d6-claude-delivery/results.md:48)

The strongest safety objection is that “bookkeeping” could become permission to commit evidence, alter `.gitignore`, disregard a filesystem restriction, or delete existing `.devlyn/` data. The helper checks workspace cleanliness but does not validate a direct task’s allowed-file list. Thus an unauthorized `.gitignore` commit can remove the cleanliness obstacle without failing a helper scope check. The proposed note must not make that workaround seem legitimate. This is the relevant **No workaround** and **Production ready** boundary. [Acceptance binding](/Users/aipalm/Documents/GitHub/devlyn-cli/config/skills/_shared/task-complete.py:278), [workspace check](/Users/aipalm/Documents/GitHub/devlyn-cli/config/skills/_shared/task-complete.py:417)

The strongest version I would test is this **one sentence**, with these exact line breaks:

```text
Product file limits cover task edits; creating delivery worktrees, branches,
receipts and uncommitted `.devlyn/` acceptance and check files is bookkeeping,
subject to delivery restrictions.
```

Insert it as a separate paragraph immediately after the introduction’s “files do not trigger delivery.”, originally line 16, and before “When delivery is implicit…”. Apply identically to [the source](/Users/aipalm/Documents/GitHub/devlyn-cli/config/skills/_shared/task-completion.md:11), [the `.agents` mirror](/Users/aipalm/Documents/GitHub/devlyn-cli/.agents/skills/_shared/task-completion.md:11), and [the `.claude` mirror](/Users/aipalm/Documents/GitHub/devlyn-cli/.claude/skills/_shared/task-completion.md:11).

Pay for it with exactly these four deletions, including their preceding spaces:

| Delete | Why the rule survives |
|---|---|
| `An ideate drain delivers every task.` | Remains verbatim in the managed block; loop step 9 also requires delivery. |
| `Isolation without delivery uses ` followed by `` `--local-base`. `` | Lines 63–66 retain this route explicitly. Remove its existing internal newline too. |
| `Queue drains retain their allocation order.` | The loop protocol explicitly orders allocation before committed inputs and execution. |
| `It does not depend on a product PASS or rewrite that verdict.` | Cleanup after a failed run remains at line 116; unchanged product verdicts remain at lines 3–4 and 203–205. |

The supporting loop sequence is explicit in [loop.md](/Users/aipalm/Documents/GitHub/devlyn-cli/config/skills/devlyn-ideate/references/loop.md:25). Preserve other whitespace; do not reflow the joined concurrency paragraph.

I independently measured the complete strings with cached `tiktoken` **o200k_base**, without creating files:

| Whole file | Before | Proposed |
|---|---:|---:|
| `task-completion.md`, each of all three copies | 2,979 | **2,978** |
| `CLAUDE.md`, unchanged | 874 | **874** |
| `AGENTS.md`, unchanged | 874 | **874** |

This improves C while retaining its placement:

- **“Creating”** distinguishes infrastructure creation from product edits inside a worktree.
- **“Uncommitted”** prevents the evidence files from being presented as additional deliverable scope.
- **“Product file limits”** distinguishes the product diff from a prohibition on filesystem writes.
- **“Subject to delivery restrictions”** preserves the restriction list immediately above.
- It retains both “Isolation changes the work location…” and the required/absent-worktree guidance.

Its reach limitation is deliberate: m05 would still receive no treatment. A reaches that session, but that session also cited publication, so reach alone does not establish a useful intervention. This version targets the three artifact-specific reports without shortening the unrelated ideate introduction or changing every session’s managed block.

I would register a bounded experiment as follows, applying **No guesswork**: freeze the prediction, packages, grading and stopping rules before running.

1. **Two contemporaneous arms.** X is unchanged 4.2.22; Y is the exact note-plus-deletions package. Both receive unchanged rp-d7 P1 and the same caller contract. Freeze model, effort `high`, native instructions, tools and environment. This estimates the package’s effect; it does not isolate the sentence from its token-paying deletions.

2. **Twelve matched Claude pairs: nine Z0, three BV.** Randomize pair order and X/Y order within pairs; use fresh isolated sessions. Z0 is primary, with BV reported separately. The unchanged-product history—BV 4/4, Z0 1/4—justifies enrichment, not a general prevalence estimate. Do not exclude sessions that fail to read the note. [Task split](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/rp-d7-prompt-delivery/results.md:83)

3. **Two additional matched no-origin BV pairs.** Score correct local completion separately from remote delivery. Improvement here with unchanged remote delivery would support a narrower local benefit.

4. **Boundary guards**, with outcomes fixed in advance:

| Guard | Required behavior |
|---|---|
| No-push/local-only; bare “Commit.” | Correct local completion, no publication |
| “Do not commit”; “Just edit” | No commit/publication; no delivery allocation in these single-writer fixtures |
| Explicit PR-only; preset `completionMode=pr` | Exact OPEN PR, no merge or auto-merge |
| Explicit PR/merge without origin | Truthful BLOCKED; no invented remote or successful local fallback |
| Base without either `.devlyn/` ignore rule | No unauthorized ignore/config changes or evidence commits; honest BLOCKED is acceptable |
| Explicit ban on all writes outside named paths | Preserve that boundary; report blocked delivery |
| Existing ignored `.devlyn/` user content | Preserve bytes and mode |

   Check executed operations as well as final state: an empty final census cannot exclude push-and-delete. Also census newly untracked original-checkout files and retained resources. Expected retention for PR-only or pending delivery is not itself failure. [Existing grading limitation](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/rp-d6-claude-delivery/grading.py:247)

5. **Codex non-regression.** Run two BV and two Z0 contemporaneous X/Y pairs on the frozen Codex route, plus critical no-commit, PR-only and filesystem-boundary guards on Y. Report quality and costs separately. This establishes “no observed regression,” not statistical noninferiority.

The primary endpoint should be **correct, mechanically verified delivery**, including the accepted tree, scope preservation and truthful reporting. Helper initiation, reading coverage and stated reasons are secondary diagnostics. Use independent blinded adjudication; do not infer hidden reasoning.

Reject the candidate for any boundary violation, user-data harm, false completion or per-task quality regression. Require wall, input and output **per correct delivery**, including failures and retries, each to be no worse. Static token neutrality does not satisfy that runtime requirement. Before freezing, also verify the native Claude whole-file token gate and rendered installation; my measured counts above are o200k counts. [Ladder admission rule](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/iterations/0232-harness-ladder.md:144)

My falsifiable prediction is:

> Y delivers at least **7/9 Z0**, versus at most **4/9 for X**, loses no BV completion, completes both implicit-no-origin probes as `LOCAL_ONLY`, and passes every boundary guard.

For evidence of improvement, preregister the paired one-sided exact test on Z0 discordances. Five Y-only wins against zero X-only wins gives p=.03125; three against zero gives p=.125. Thus the numerical prediction can succeed while evidence remains inconclusive. Freeze the sample size; do not extend it until significance.

Disappearance of the scope explanation without increased delivery would fail the usefulness claim. Even a positive screen should receive fresh-task confirmation before adoption.

RECOMMEND: TEST NEW
