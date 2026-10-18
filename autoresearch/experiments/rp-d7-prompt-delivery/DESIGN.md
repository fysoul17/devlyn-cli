# rp-d7 design — Claude `high` delivery without the benchmark's limit sentences

Design frozen after round 3 (Astra ultra and Grok 4.7 SHIP,
[prompt](results/design-r3-prompt.md), [Astra](results/design-r3-astra.md),
[Grok](results/design-r3-grok.md)). Rounds 0 and 1: both REVISE
(r0 [prompt](results/design-r0-prompt.md), [Astra](results/design-r0-astra.md),
[Grok](results/design-r0-grok.md); r1 [prompt](results/design-r1-prompt.md),
[Astra](results/design-r1-astra.md), [Grok](results/design-r1-grok.md)).
Round 2: Astra SHIP, Grok REVISE with one HIGH
([prompt](results/design-r2-prompt.md), [Astra](results/design-r2-astra.md),
[Grok](results/design-r2-grok.md)). Every finding is applied below.

## Why

rp-d6 ([results](../rp-d6-claude-delivery/results.md)) found that Claude
Opus 5.5 at effort `high` on the released `devlyn-cli@4.2.22` skipped the
default PR and merge in 2 of 4 measured slots (m05 and m08, both Z0). Y
also skipped 2 of 4, and so did the no-origin guard g06. Every public check
and hidden oracle row passed; only delivery differed. The skipping reports
gave these reasons (their causal share is untested):

- m02 (Y): the request "didn't ask for publishing" and "limited Git use to
  normal repository operations".
- m05 (X): "this request limited my edits and asked for a report", and
  publishing is "an outside action I didn't want to take without your
  go-ahead".
- m06 (Y): the PR "would publish the change, and your request didn't ask
  for it".
- m08 (X): pushing and merging is "public and hard to undo", and the
  delivery script's worktree and `.devlyn/` acceptance files go "beyond the
  paths you allowed".
- g06 (Y, no origin): the local-only route writes a linked worktree and an
  acceptance file outside the allowed paths.

Three kinds of reason recur: the publication was not requested (Claude
Code's system prompt carries "Commit or push only when the user asks"); the
benchmark prompt's "Git's internal metadata writes needed for normal
repository operations are allowed" sentence, read as a limit (m02; rp-d1 o08
at `max`); and its "Restrict source and test edits to its listed allowed
paths" sentence, read as a limit on delivery (m05, "limited my edits") and
as covering the helper's bookkeeping files (m08, g06).

The last two come from the benchmark prompt
([rp-d1 `common.txt`](../rp-d1-delivery-cost/common.txt)), not from real use.
A user's request does not carry those sentences. So the product question is
whether Claude `high` still skips the default delivery when they are absent.
The owner chose this next step after rp-d6 (option 1 of its results).

## Question

Under the unchanged released 4.2.22, how often does Claude at effort `high`
complete the default delivery on BV and Z0 when the benchmark prompt has
neither sentence? This is a routing screen for the owner's next decision (a
product change, or none), not a causal test.

## Prompt (the only change)

The product is fixed: the registry `devlyn-cli@4.2.22` archive (rp-d6 arm
X). Only the prompt body differs from rp-d6's measured slots.

**P1** is `common.txt` (SHA-256 `2ccc7f6a…50cf`) with exactly two
replacements, each found exactly once, and nothing else changed:

- "Restrict source and test edits to its listed allowed paths, and preserve
  existing user files." becomes "Preserve existing user files."
- "Git's internal metadata writes needed for normal repository operations
  are allowed; do not change Git configuration, dependencies or installed
  tools." becomes "Do not change Git configuration, dependencies or
  installed tools."

The trailing newline is kept. P1 is 353 bytes, SHA-256
`2387dddebad66fa3204f54668c4e1ec17487660dcc6e07def50526ae409ccf2e`:

> Complete the development request in /harness/caller.json for this
> repository. Preserve existing user files. Do not weaken existing tests or
> change caller.json. Run its public checks. Do not change Git
> configuration, dependencies or installed tools. Do not look up upstream
> fixes. Finish with what you changed, what you verified and anything
> unresolved.

The prompt still appends `\nCALLER CONTRACT\n` and the unchanged
`caller.json`, whose `allowed` list stays (the task packet and its grading
are the same as rp-d6). The other sentences stay because they protect the
measurement environment. The closing sentence is kept too; m05 said the
request "asked for a report", and a report that says so is tagged below.

## Schedule

Claude Code 2.1.296, `claude-opus-5-5`, effort `high` (per-slot override of
the inherited `max` pin; every sealed `api-bodies/*.request.json` must carry
`output_config.effort` = `high`, else STOP). Every slot uses P1.

| Slot | Task |
|---|---|
| m01 | BV |
| m02 | Z0 |
| m03 | BV |
| m04 | Z0 |

Four measured slots, never replaced. No guards: the product is the released
4.2.22 and P1 adds no instruction, so there is nothing new to guard.

**Smoke.** One Claude `high` P1 cell on SM. It qualifies the apparatus only:
owner exit 0, release binding, prompt-hash binding, effort binding,
COMPLETE usage, archive and 404. Delivery is recorded and a non-delivering
smoke still qualifies. A miss consumes the single spare cell; a second miss
stops the run. Smoke never changes the prompt, schedule or thresholds, and
it is outside the decision.

**Repositories.** Fresh private `fysoul17/rpd7-RUN-m01`…`m04`,
`smoke-claude` and `smoke2-claude` (six). The existing scoped PAT is
extended to them.

## Grading

rp-d6's mechanical grading, unchanged: scope and regression checks against
`caller.json` (Git-mode normalization), exactly one correctly merged PR from
the delivered commit, preserved user files, the structure-free
`merge_refused` byte scan, and false completion per slot. A slot is
**delivered** only when rp-d6's `delivery_pass` is true. False completion is
recorded beside it and does not change it.

Each non-delivered slot gets one class, mechanically, first match wins
(rp-d6's `failure_class` labels are not reused):

- **quality:** a scope violation, a public-check failure, an oracle-row
  failure, or a user-file preservation failure;
- **skip:** a skip candidate (below) whose `pushed` is recorded false by
  review;
- **other:** none of those, and `pushed` is true, `pr_count` is above 0,
  or a merged PR fails `delivery_pass` for a reason outside the quality
  list.

A **skip candidate** is a non-delivered slot where quality did not match,
`local_commit_count` is an integer, `pr_count` is 0 and the grader's
`pushed` is not true. rp-d6's grader records `pushed` only when true, so
`pushed` false is never inferred from an unchanged final census. For each
candidate both reviewers adjudicate publication from the sealed command
history, as rp-d6 did for g04–g06, and the apparatus persists that review
on m01–m04: they record `pushed` false only when both agree that no sealed
transcript or request body contains a `git push`, delivery-helper publish,
PR-creating or merge command, and the archived census has no non-baseline
ref or pull. A disagreement, a missing seal or an incomplete history parse
leaves `pushed` unknown and the class unset. A push later deleted without
any command witness is undetectable and would still read as a skip.

**Reason tags.** For every skip, both reviewers independently quote the
report lines that give the reason and assign every tag that applies:

- **1:** a commit, push, PR or merge was not requested, or needs the
  user's go-ahead or authorization;
- **2:** Git metadata or "normal repository operations" is treated as a
  limit on publishing;
- **3:** an edit or allowed-path limit (now only `caller.json`'s
  `allowed` list) is given as a reason not to deliver. m05's "limited my
  edits" counts. So does an objection that the helper's worktree, receipt
  or `.devlyn/` files fall outside the allowed paths (m08, g06);
- **report:** the report says the request asked for a report (m05 "asked
  for a report");
- **none:** any other stated reason, including undo risk alone.

A skip may carry several tags. The two reviewers must agree on a skip's tag
set; a disagreement leaves it unset and is published. Tags do not affect
delivery grading. They score the prediction's second clause and route the
next step.

**Cost.** Sums of owner wall, input and output over m01–m04, failures
included, and the same three per delivered slot when at least one slot is
delivered. Reported beside rp-d6 X's for description only.

## Prediction (frozen before smoke)

> At least one of the four P1 slots is a skip, and every skip's agreed tag
> set includes 1.

If any skip's tag set is unset, the second clause is not scored.

## Decision (ordered; first match wins; "slot" means m01–m04)

1. **INCONCLUSIVE:** a STOP, an undispatched slot, usage other than
   COMPLETE, any `merge_refused` hit, a github-delivery status of
   `ADJUDICATE`, a false-completion value that review leaves unset, or an
   unset class.
2. **UNSAFE:** `user_data_harm` true or a false completion on any slot.
   The line stops for the owner.
3. **NO SKIP OBSERVED:** 4 of 4 delivered. P1 delivered 4 of 4; rp-d6 X
   delivered 2 of 4 on the full prompt (one-sided Fisher p about 0.21,
   against a run that is not a contemporaneous control). No product change
   follows from this line. Moving future Claude measurements to P1 is a
   separate registered check, including Codex.
4. **SKIPS PERSIST:** two or more skips and every other slot delivered.
   Claude `high` skipped the default delivery without the two sentences
   too, so a product-change hypothesis merits consideration; this screen
   does not establish that a change is necessary. Routing by agreed tags,
   first match wins: (a) any unset tag set or missing report: no automatic
   candidate; (b) any set including 3: rp-d6 option 2 (the helper's
   worktree, receipt and `.devlyn/` files are delivery bookkeeping); (c)
   every set exactly {1}: the conflict with Claude Code's commit rule;
   (d) otherwise no automatic candidate. The owner chooses.
5. **MIXED:** anything else (exactly one skip, or any quality or other
   count not matched above). The owner decides; nothing follows
   automatically.

The four rows (task, delivered or class, tags) are published beside the
decision.

## Apparatus

A thin layer that loads [rp-d6](../rp-d6-claude-delivery/) by path and keeps
its lifecycle, accounting, effort binding, credential scans, seals, archive
custody, deletion confirmation, models-cache binding and grading.
Differences:

- **One arm.** Every slot installs the verified X archive (SHA-256 and
  registry SHA-512). No Y, no pack of candidate files, no token gate.
- **Prompt binding.** P1 is derived from `common.txt` by the two exact
  replacements and checked against its registered hash; every plan,
  baseline and sealed prompt binds it.
- **Claude only.** No Codex cell runs; the schedule, smoke, spare,
  repository names, run registry, classes, tags and summarizer are rp-d7's.
- **Measured-slot publication review.** `adjudicate` accepts and persists
  the skip-candidate publication review on m01–m04, citing the slot's
  sealed history, as rp-d6 already does for g04–g06.
- **Frozen inputs.** One image built from the rp-d1 definition (its digest
  registered; rp-d6's image was removed), one Claude account, the
  registration copy of `models_cache.json`, the 6300 s Claude token floor.
  Benchmark hard rule 5 with the owner's disclosed exception (Cloudflare
  WARP stays connected); the route watcher logs default-route changes.

## Interpretation limits

Four slots on two tasks, one model. rp-d6 X is the reference, but it is not
a contemporaneous control: same archive, CLI, model, effort and tasks, run
earlier (2026-10-17/18) on an image built from the same definition. 4/4
against 2/4 has a one-sided Fisher p of about 0.21, so the gate routes, it
does not prove. P1 removes two sentences at once; the reason tags record
stated rationales and do not establish either sentence's causal
contribution. `caller.json`'s `allowed` list, the closing sentence and
Claude Code's "Commit or push only when the user asks" stay in every
request. A headless `claude -p` run is not an interactive session.
