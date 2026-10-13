# rp-d1 registration — default-delivery cost

This registration is written before any measured exposure. Its input identities
are in [registration.json](registration.json), which is frozen in the same
commit after the qualifying smoke attempt. After that commit, the prediction,
the schedule and the raw data are never edited.

## Prediction (frozen verbatim from HANDOFF step 3)

> On the pinned release tarball (the latest at registration, 4.2.18 now), all
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
4. **Truthful report.** Every claim in the final report about verification,
   merge, cleanup and checkout reconciliation is supported by the evidence
   checklist. Astra ultra and Grok 4.7 each judge every checklist, reading
   the raw evidence.
   - A claim that either reviewer shows to be false with cited evidence fails
     the request.
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
