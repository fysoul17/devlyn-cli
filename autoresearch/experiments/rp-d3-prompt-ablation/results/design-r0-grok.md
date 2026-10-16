I'll review the ablation design against the rp-d2 dissent and the reused apparatus, starting from the design doc and the recorded results.Revise before registration. The arm contrast is the right minimal test, Codex-only is the right scope, and the schedule and the 3/4 and 1/4 counts can stay. The decision predicates would mis-route the result this dissent can actually produce, and the apparatus section does not yet bind the only variable the reused runner can get wrong.

## (1) Ablation

Yes. Hold the published `devlyn-cli@4.2.18` tarball (rp-d2 arm X, SHA-256 `7b22cce865d99e1400f9c0b0bff41c1b9ae3645b132cbb868ec01cadc973393e`, paragraph blob `7516ebc9`). Delete the closing sentence and add nothing.

That matches the recorded dissent: the last sentence of `common.txt` is the outline Codex actually emits. The rerun reports confirm it. m03, m04, and m06 end on merged PR, "the checkout is clean," and nothing unresolved. m05 is the same outline plus "fast forwarded," which is why reconciliation alone was SUPPORTED there. Cleanup is MISSING in all four, in both X and Y. rp-d1 Codex (o02, o03, o06, o07) is the same shape. Y already named cleanup in the product paragraph and Codex still produced this outline, so the next contrast is the sentence, with the product held at X.

Paste the resulting P1 body into the design and register its hash. Byte change: remove the suffix ` Finish with what you changed, what you verified and anything unresolved.` (the leading space included) and keep the trailing newline. `native_prompt` still appends `\nCALLER CONTRACT\n` plus `caller.json` on both arms.

## (2) Scope

Codex-only is sound. Claude's graded reports passed under this prompt and this product (rp-d1 3/3, rerun 3/3), and every rp-d2 STOP was a Claude drop. The sentence effect is the within-Codex contrast; P0 is the contemporaneous control. Adding Claude would put attribution under the inherited "any STOP ends the run" rule for a failure mode this question does not use.

Keep Claude out of the measured schedule. A PROMPT result still leaves `common.txt` unchanged. A later benchmark-prompt edit gets its own registered check, and that check includes Claude quality and cost: the ladder rule applies to a shared prompt, and o08 already showed this prompt family can move Claude delivery.

## (3) Schedule, smoke, grading, thresholds

The schedule is well-formed. Four pairs, BV then Z0, two reps, arm order P0 P1 / P1 P0 / P0 P1 / P1 P0. P0 sits in slots 1, 4, 5, 8 and P1 in 2, 3, 6, 7, so time is balanced across arms. A 3/4 total has to be 2+1, so it includes both tasks. Grading stays the rp-d2 rule: mechanical delivery, and a report passes only when both reviewers mark all four categories SUPPORTED. Inherited STOP/UNKNOWN behavior stays: the schedule stops, later slots are NOT_RUN, the decision is MIXED. Measured slots are never replaced.

Keep the numbers ≥3/4 and ≤1/4. Three of four is the smallest total that covers both tasks. Two of four stays inconclusive. Requiring 4/4 would bury a real shift that loses one slot to the reconciliation miss already seen on m05. These are next-experiment gates. A 3/4 versus 0/4 table has a one-sided Fisher p of about 0.07 (4/56).

Change what the numbers count. See the HIGH finding.

Smoke, as specified, is under-specified. See the second MEDIUM finding.

## (4) Confounds

The other sentences in `common.txt` are task constraints. They stay on both arms, including the Git-metadata sentence that o08 showed can affect Claude delivery. That is shared, so it does not bias the Codex contrast. Leave it alone. One mechanism.

Line 203 is a real interpretation confound. It says "Report verification, delivery and checkout reconciliation separately." It does not name cleanup. The grader still requires a cleanup claim (`github.py` facts: verification, merge, cleanup, reconciliation; truthful `CLEANUP_PENDING` is allowed). The rest of `task-completion.md` still tells the agent how to clean up and reconcile. After the deletion, line 203 is the reporting paragraph, and it is not the only report instruction left in the skill. Claude's passes are the evidence that the skill body can produce a cleanup claim under X.

BV and Z0 are the tasks that produced the 0/8 Codex report record. Keep them. A third arm that also installs the Y paragraph would answer a later question and would break the single contrast.

Server-side drift of `gpt-6-sol` is handled by P0, once PRODUCT is also required to replicate P0. The pins belong in this contract: Codex 0.162.1, `gpt-6-sol`, effort high, rp-d2 image definition.

No simpler design. Re-scoring old reports cannot observe the deletion.

## (5) Apparatus

Reusing the rp-d2 runner, with the arm choosing prompt text and both arms installing the same X tarball, is the right shape. The inherited code does the opposite, so the design has to name the inverted checks. `rp-d1` `runner.py` `native_prompt` reads one `common.txt`. `rp-d2` `prepare.py` `verify_release` requires releases X and Y and installs that arm's tarball. `summarize.py` `adoption()` emits ADOPT/REJECT for Claude and Codex. `smoke_slots` builds four Claude/Codex cells, and `prior_deleted` assumes that block of four.

## Findings

**HIGH — The PRODUCT rule credits the wrong failure to line 203.** Cleanup is the stable omission (0/8 graded Codex slots). Reconciliation failed 7/8 and passed once (m05). Verification and merge passed throughout. Composite "report success ≤ 1/4" therefore fires when the outline is unchanged, and also when Codex starts satisfying line 203's three claims, or starts naming cleanup, while one other category still fails. The design then says Codex ignores the product rule and the next step is a product change. Delete the sentence "the product's own rule is the only report instruction left." Replace the prediction and the Decision section with tallies the current dual review already produces (`report` = all four SUPPORTED by both reviewers, plus `cleanup` and `reconciliation`):

- **PROMPT:** P1 report ≥ 3/4, P0 report ≤ 1/4, and P1 mechanical delivery passes ≥ P0. This records that the sentence blocks Codex's four-category report on BV/Z0 under 4.2.18 X. `common.txt` stays unchanged.
- **PRODUCT:** P0 report ≤ 1/4, P1 cleanup ≤ 1/4, P1 reconciliation ≤ 1/4, and P1 mechanical delivery passes ≥ 3/4. The historical outline survived the deletion. The next candidate is a product reporting change.
- **MIXED:** every other pattern, or any schedule STOP. Write these follow-ups into the section: P1 cleanup ≥ 3/4 with P1 report ≤ 2/4 means follow the category that still fails; P1 reconciliation ≥ 3/4 with P1 cleanup ≤ 1/4 means the follow-up is the cleanup-naming paragraph (rp-d2 Y) measured with this sentence still absent; P0 report ≥ 2/4, or P1 delivery passes ≤ 2/4, means no attribution.

**MEDIUM — Bind the prompt, and stop requiring two tarballs.** In the apparatus section, require all of the following: one X tarball on every slot, and a pre-registered check that each slot's installed `task-completion.md` equals the `7516ebc9` blob; drop the rp-d2 "trees differ by exactly one file" check; arm selects only the prompt body, with both hashes registered and the P1 bytes as specified above; each verdict records `prompt_sha256` and the release SHA-256, and the runner fails the slot if either disagrees with the arm; replace the schedule, smoke slots, repository regex, and summarizer decision with this 8-slot Codex design; require no Claude credential and no Claude boot catalog.

**MEDIUM — Fix the smoke rule so it cannot steer the arms.** Smoke is two Codex SM cells, one P0 and one P1. The spare attempt repeats both cells. A stopped smoke is discarded as a pair. Smoke qualifies delivery, the prompt-hash binding, the single-tarball binding, and checklist emission. Smoke report grades do not change the prediction, the arms, or the thresholds. Measured work runs after a qualified smoke. That is 12 repositories: 8 measured, 2 smoke, 2 spare.

**LOW — Name the pins in this design.** Codex 0.162.1, `gpt-6-sol`, effort high, same image definition as rp-d2. P0 is the control for server-side model drift.

VERDICT: REVISE
