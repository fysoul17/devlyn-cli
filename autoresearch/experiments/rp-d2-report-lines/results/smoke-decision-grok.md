I'll read the rp-d2 contract, the ancestor results, and the candidate paragraph before deciding whether to register Y or revise the mechanism.The smoke reports match the prompt's closing sentence. I'll check how the STOP rule, the report rubric, and the design reviews treat that before deciding.Revise the mechanism before registration. Pre-register continuation after an accounting UNKNOWN.

**(1) The paragraph contrast is the wrong mechanism.** All six Codex finals share one outline: the public-check result, the merged PR, "the checkout is clean," and "nothing remains unresolved." That is rp-d1 o02, o03, o06, and o07, plus this smoke's Codex X and Codex Y. The outline is the last sentence of `autoresearch/experiments/rp-d1-delivery-cost/common.txt`: what changed, what was verified, and what remains unresolved. Smoke Y is the mechanism check for the candidate paragraph. Codex ran `cat .agents/skills/_shared/task-completion.md`, the tool result contained the full "delivery, cleanup and checkout reconciliation" paragraph, and the report stayed on that outline. Claude X and Claude Y both reported the merge, the fast-forward of local main, the clean tree, and removal of the worktree, branch, and scratch, so this closing sentence does not set Claude's report.

Keep rp-d1's four Codex FAILED grades. They are what the registered rubric scored. Charge them to this prompt together with Codex. Line 203 was present, and the wording that names cleanup was read in full, while the report still matched the prompt. Those four grades are weak evidence that the product sentence is the defect.

Measure the closing sentence. Arm X loads the current `common.txt` unchanged. Arm Y loads that same text with the final sentence removed:

```text
Complete the development request in /harness/caller.json for this repository. Restrict source and test edits to its listed allowed paths, and preserve existing user files. Do not weaken existing tests or change caller.json. Run its public checks. Git's internal metadata writes needed for normal repository operations are allowed; do not change Git configuration, dependencies or installed tools. Do not look up upstream fixes.
```

Leave the rp-d1 file byte-identical and put Y's text in a new rp-d2 prompt file. Both arms install the published `7516ebc9` paragraph, so the installed tree is shared and the arm selects only the prompt. The worktree's candidate paragraph stays out of this run. The Git-metadata sentence stays in both arms; Claude o08 already recorded that as a separate apparatus issue.

This is a suffix deletion. In o200k, a space-prefixed word is its own piece, so the prefix through "fixes." keeps its tokens and the deleted sentence only subtracts. Run the existing two-counter gate on that file before smoke. The expected result is that both counts fall. This pass did not call the counters.

Register this prediction: with the published paragraph fixed, deleting that sentence raises Codex's report success over X on the same four-condition rubric, and Claude's quality does not fall. If Codex Y still ends on "checkout is clean" and "nothing remains unresolved," the sentence is not a sufficient cause. This revision needs four fresh SM smoke cells, new repositories, and one owner PAT edit.

**(2) Continue after inherited usage UNKNOWN.** `0254/audit.py` still rejects `api_error` and `api_retry`, and whole-run token totals stay null. Change only the schedule. A cell whose defect is that accounting UNKNOWN is quality-graded on its delivery evidence, that engine's wall, input, and output rows stay UNKNOWN, and adoption stays blocked when a compared cost row is UNKNOWN. Later slots still run. The UNKNOWN cell is not retried.

A PAT UNKNOWN with `revocation_required` still stops the schedule. Archive, delete, 404, and auth failures still stop. Those are different defects from a transient `ECONNRESET`.

One accounting blip can swing a two-repetition quality count. Adoption is already blocked on that engine's cost row, so the swing cannot ship a change. The cells that continue preserve the other engine and the report grades. Stopping there records the rest as `NOT_RUN`.

DECISION: Revise rp-d2 so the only arm difference is deleting the prompt's final report-shape sentence, hold the published paragraph fixed, qualify it with four fresh smoke cells, and continue after accounting UNKNOWN with quality graded, that engine's cost UNKNOWN, and adoption blocked when a compared cost row is UNKNOWN.
