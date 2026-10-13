# rp-d1 registration — default-delivery cost

This registration is written before any measured exposure. Its input identities
are in [registration.json](registration.json), which is frozen after the
qualifying smoke attempt. Its `apparatus_commit` is the commit whose files the
`inputs` hashes cover; the registration commit follows it. After that commit, the prediction,
the schedule and the raw data are never edited.

## Prediction (frozen verbatim from HANDOFF step 3)

> on the pinned release tarball (the latest at registration, 4.2.18 now), all
> requests of 2 tasks × 2 repetitions per engine (Claude, Codex; 8 observations,
> serial, pre-fixed order) finish source verification and a real merged PR with
> no human delivery instruction or repair, and every attempt's owner, child and
> in-product reviewer usage is fully counted; a failed delivery counts as a
> failed request with its cost; missing usage makes the cost conclusion UNKNOWN.

The default delivery path in 4.2.18 starts no in-product reviewer process (see
the [gate record](README.md)). The reviewer clause therefore covers whatever
the owner itself starts: native children are counted, and any independent
model launch makes usage UNKNOWN.

## What runs

- **Product.** `devlyn-cli@4.2.18`, installed in the cell by its own installer
  as arm B. The prompt is [common.txt](common.txt) plus the caller contract. It
  teaches no helper, PR or delivery step.
- **Engines.**
  - Claude Code 2.1.296 running `claude-opus-5-5` at effort `max`.
  - Codex 0.162.1 running `gpt-6-sol` at effort `high`.
  - Native children use the owner's model.
- **Tasks.**
  - BV: a boundary-value expiry bug.
  - Z0: a CLI `--limit 0` that falls back to the default.
  - Each needs a regression test. Allowed paths, public checks and oracle
    rows are in [tasks.json](tasks.json).
- **Schedule.** Serial, in this fixed order, with no replay:
  `o01 BV Claude, o02 BV Codex, o03 Z0 Codex, o04 Z0 Claude, o05 Z0 Claude, o06 Z0 Codex, o07 BV Codex, o08 BV Claude`.
- **Repositories.** Each slot gets its own empty private repository,
  `fysoul17/rpd1-20261013a-<slot>`. Before each slot, the host checks that its
  repository and every later one are still empty. After each slot, the host
  archives the repository, then deletes it.
- **Watchdogs.** 5400 s per owner and 600 s per evaluator or review. There is
  no token or cost budget.

## Success per request

A request succeeds only when all four of these hold.

1. **Requirements and scope.** The public checks and every independent oracle
   row pass on the accepted source. The added regression test must fail on
   the original source.
2. **Merged PR.** Exactly one PR in the slot repository is merged into `main`.
   Its head is the accepted commit, and the tree of its merge commit equals the
   accepted source tree.
3. **User files preserved.** Out-of-scope tracked files are unchanged by
   content and Git mode in both the anchor and the submitted tree. The ignored
   sentinel is unchanged by bytes and mode.
4. **Truthful report.** The final report covers verification, merge, cleanup
   and checkout reconciliation, and each claim is supported by the evidence
   checklist. Astra ultra and Grok 4.7 each judge every checklist, reading
   the raw evidence.
   - An `ADJUDICATE` slot counts as a success only when both reviewers find
     every claim in all four categories supported.
   - A false, missing or ambiguous claim, found by either reviewer with cited
     evidence, fails the request, as `github.py` grades it.
   - A truthful `CLEANUP_PENDING` is allowed.

An instrumentation STOP is recorded as `NOT_ASSESSED`. It is neither a success
nor a failure. The schedule stops there, and the remaining slots are recorded
as `NOT_RUN`.

## Cost

- **Counted attempts.** Every dispatched attempt counts, failures included,
  for owner wall seconds, processed input and output tokens.
  - Claude: 0254/0255 receipts, with the 2026-10-13 foreground `local_bash`
    amendment.
  - Codex: the inherited trace accounting.
- **Per engine, report:**
  - the number of successes;
  - total wall, input and output over all attempts;
  - cost per success, which is the totals divided by the successes.
- **Exceptions.**
  - With zero successes, there is no per-success cost.
  - Any attempt with UNKNOWN usage makes that engine's token totals and cost
    per success UNKNOWN. Wall seconds remain reported.
- **Stage attribution** (for example, delivery versus implementation) is
  reported only where the native receipts support it, never by estimate.
- Smoke attempts are recorded separately and are never pooled.
- All per-request and per-engine numbers come from [summarize.py](summarize.py),
  written before exposure. Reviewers fill its `--review-template` per slot.

## Decision afterwards (HANDOFF step 7)

If identical inputs show repeated re-exploration, re-verification or duplicate
allocation, register at most one removal candidate. It is adopted only when no
engine's quality or cost per success gets worse and at least one improves.
Otherwise keep the current text. The PR+merge default is not reverted for cost.

## Review

- **Before exposure:** Astra ultra and Grok 4.7 review this registration.
- **After the run:** both review the results against the raw data.
- **Stopping rule:** stop at SHIP with no HIGH finding, reading each
  reviewer's final verdict line.

## Smoke qualification (before registration)

Smoke tasks are unrelated to BV and Z0 and are never pooled with measured data.

- **Attempt 1.** Claude merged its PR, but two apparatus defects made the slot
  STOP:
  - The 0254 auditor did not recognize the foreground `local_bash` task rows
    for the delivery command.
  - GitHub's per-request `temp_clone_token` made the archive comparison fail.

  Both defects were fixed and reviewed. A re-audit of the sealed evidence
  returned MATCH. The repository was retained, not archived, and is
  deleted during final cleanup. `smoke-codex` was `NOT_RUN`.
- **Attempt 2.** Claude delivered correctly. The done-check flagged the
  installer's 0600 marker files against the committed 100644 mode, so the
  Codex slot never ran. The check now compares raw files with Git-mode
  normalization, and index flags fail it.
- **Attempt 3** qualified both engines:

  | Engine | Owner seconds | Input | Output | Done-check | Repository |
  |---|---:|---:|---:|---|---|
  | Claude | 765.2 | 2,017,930 | 72,606 | no failures; report review pending | archived, deleted (404) |
  | Codex | 181.6 | 532,069 | 6,215 | no failures; report review pending | archived, deleted (404) |

  Its verdict hashes and the recorded Claude boot catalogs are in
  [registration.json](registration.json).

## Final freeze before exposure (2026-10-14 01:15 KST)

The first freeze's Claude credential would have dropped below the 6300-second
launch floor partway through the schedule. Both registration reviewers had
already approved the plan for this case:

1. wait for the host token to renew;
2. snapshot the new token;
3. re-stage the measured run;
4. regenerate [registration.json](registration.json).

The host's Claude login had meanwhile switched accounts, so the measured
account is the one now recorded. The regenerated file differs from the first
freeze only in four places:

- the account and the auth manifest;
- the runtime hash;
- `apparatus_commit`;
- the input hashes of the reviewed `runner.py` STOP fix and the pre-registered
  `summarize.py` with its tests.
