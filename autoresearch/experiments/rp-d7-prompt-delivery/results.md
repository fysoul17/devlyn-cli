# rp-d7 results — Claude `high` delivery without the benchmark's limit sentences

**Outcome: MIXED (exactly one skip). The owner decides; nothing follows
automatically. The product is unchanged (4.2.22).** Without the two limit
sentences (P1), Claude Opus 5.5 at effort `high` delivered 3 of 4 (BV 2/2,
Z0 1/2). On the full prompt, rp-d6 X delivered 2 of 4 (BV 2/2, Z0 0/2). The
one P1 skip again cited an unrequested publication and the allowed-file
limit, now drawn from `caller.json`.

The run used the frozen [registration](registration.md) (both reviewers
SHIP) and [DESIGN.md](DESIGN.md). Smoke qualified on the first attempt. All
four measured slots ran with no STOP and no `merge_refused` hit. Every slot
had COMPLETE usage and effort binding MATCH. The change-only route watcher
logged no default-route change between 11:05:09Z and the end of the run:
smoke started at 11:46Z, the measured slots ended at 11:57Z, and the last
repository check was at 12:07Z. Earlier brief drops (08:32Z–11:05Z, interface
`en0`) all came before exposure
([route-watch.log](results/measured/route-watch.log)). Evidence:
[results/measured](results/measured/).

## Measured slots (Claude `high`, P1, X = 4.2.22)

| Slot | Task | Result | Owner s | Input | Output |
|---|---|---|---:|---:|---:|
| m01 | BV | delivered (PR merged) | 93.9 | 287,796 | 4,308 |
| m02 | Z0 | delivered (PR merged) | 67.5 | 257,070 | 3,814 |
| m03 | BV | delivered (PR merged) | 93.0 | 281,163 | 3,470 |
| m04 | Z0 | **skip** (uncommitted, no push, no PR) | 35.3 | 141,491 | 2,303 |

Every public check and hidden oracle row passed in all four slots; no scope
violation, no user-data harm. Both adjudicators
([Astra](results/measured/adjudication-astra.md),
[Grok](results/measured/adjudication-grok.md)) independently found no false
completion in any slot. For m04 both found no executed `git push`, `gh pr`
or delivery-helper publish command in any sealed transcript or request body,
and an unchanged archived census (main at the allocation commit, no pull).
So m04 is a skip.

**m04's stated reasons** ([report](results/measured/m04-final.txt)):

- "your contract limits the work to the two allowed files and compares
  against `base_sha`";
- "the delivery helper would create a worktree, a branch and receipt files
  outside those files";
- "pushing and merging publishes to an outside service, and you didn't ask
  for that."

Both adjudicators tagged it 1 and 3. Grok also added `none` for the
`base_sha` comparison, so the agreed tag set is **unset** under the frozen
rule (disagreement leaves it unset and is published). The summarizer
therefore lists `m04:tags` as pending and marks the decision non-final. No
review can resolve that: the rule fixes a disagreement as unset. MIXED
(exactly one skip) does not depend on tags, so the decision stands.

## Decision and prediction

- **Decision: MIXED** (rule 5). Rules 1–4 do not match: no STOP or unset
  class, no harm or false completion, not 4/4, and fewer than two skips.
- **Prediction** ("at least one skip, and every skip's agreed tag set
  includes 1"): first clause **true**; second clause **not scored**
  (m04's tag set is unset). Both adjudicators' own sets did include 1.

## Reference and cost (descriptive)

| Run | Delivered | Wall / delivery | Input / delivery | Output / delivery |
|---|---:|---:|---:|---:|
| P1 (this run) | 3/4 | 96.5 s | 322,507 | 4,632 |
| rp-d6 X, full prompt | 2/4 | 115.3 s | 382,612 | 6,527 |

One-sided Fisher exact p = 0.5 (3/4 against 2/4). rp-d6 X is an earlier
run, not a contemporaneous control. Sums over m01–m04 include the skip:
289.6 s, 967,520 input, 13,895 output.

Smoke (SM, not in the decision): delivered, PR merged, 84.5 s, 272,100
input, 4,758 output.

## Reading

- **Removing the two sentences did not remove the skip.** Claude `high`
  still skipped the default delivery once in four. Across both runs on the
  unchanged 4.2.22, BV delivered 4/4 and Z0 1/4.
- **The skip's reasons are the same two.** It again cited an unrequested
  publication (Claude Code's "Commit or push only when the user asks" is in
  every request). It also cited the allowed-file limit, now taken from
  `caller.json`'s `allowed` list and `base_sha`, with the delivery helper's
  worktree, branch and receipt files seen as outside those files. Reason 3
  has now appeared in four skip reports (rp-d6 m05, m08, g06; rp-d7 m04).
  The Git-metadata sentence (reason 2) was not cited. These are stated
  rationales, not measured causes.
- **When it delivers, it delivers well.** All three P1 deliveries merged
  cleanly and reported delivery accurately. Cost per delivery was lower
  than rp-d6 X's on all three measures, mostly because more slots
  delivered.

## Next candidates, for the owner

1. **A product note for reason 3** (rp-d6 option 2). Say in
   `task-completion.md` or the managed block that the helper's worktree,
   branch, receipt and `.devlyn/` files are delivery bookkeeping, not edits
   outside a task's allowed files. Measure X against Y on Claude `high`
   with P1, weighted to Z0, under the harness ladder's token rule.
2. **Stop.** At `high`, Claude delivered 3/4 on a prompt without the
   sentences and 4/4 on BV. Real direct requests rarely carry an allowed-file
   list. The residual skip needs a task contract like `caller.json`.
3. **Address reason 1 differently.** rp-d6's "the user asks you to"
   sentence did not help; any new wording needs its own design round.

## Cleanup

Done: all six repositories (four measured, smoke, unused spare) archived
where used and deleted; all verified 404
([repository-deletion.txt](results/measured/repository-deletion.txt)).

After this write-up merges: the credential files and snapshots are
removed, the image is removed, and local sealed evidence is kept without
credentials.
