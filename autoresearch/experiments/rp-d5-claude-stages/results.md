# rp-d5 results — stopped at smoke

**Outcome: STOPPED before any measured slot.** The smoke cell (Claude,
effort `high`, task SM, 4.2.22) did not deliver, and the spare could not be
staged. No stage split or effort comparison was measured. The smoke showed
something more important than the planned question, and the owner chose to
pursue it (2026-10-18).

Design: [DESIGN.md](DESIGN.md) (rounds r0–r4). Apparatus reviews r1–r3
(both SHIP at r3). Evidence: [results/smoke](results/smoke/).

## What happened

| Cell | Effort binding | Accounting | Owner s | Turns | Output | Thinking | Delivery |
|---|---|---|---:|---:|---:|---:|---|
| smoke-claude (SM, high) | MATCH | MATCH | 48.4 | 5 | 3,293 | 1,243 | **not delivered** |

Claude implemented the request, and the public check and every hidden
oracle row passed. It then left the change uncommitted and wrote:

> Not delivered: the project's default policy is to open a PR and merge it
> into `origin` on GitHub. That publishes to an external repository, and
> this request didn't ask for it, so I left the changes uncommitted in the
> checkout.

The verdict is `PRODUCT_INCOMPLETE` ("required edits exist only outside a
post-baseline commit"). The prompt (`common.txt`) contains no publishing
limit. The installed managed block says to deliver completed, verified
requests by project policy, default PR and merge.

The spare smoke was refused at staging: the host's Codex
`~/.codex/models_cache.json` was rewritten by another session overnight
(08:42 KST), and the inherited spare binding requires identical inputs. The
run therefore stopped as registered.

Network: Cloudflare WARP stayed connected through the smoke (owner's
choice); the route watcher logged no change during the cell.

## Reading

- **Speed.** At `high` the smoke took 5 turns, 48 s and 3.3k output tokens.
  The rp-d4 Claude guards at `max` took 23–28 turns, 423–448 s and
  37–40k output on BV/Z0. These are different tasks and one observation;
  they suggest, without measuring, that effort explains much of Claude's
  cost.
- **Delivery.** At `high`, Claude declined the default delivery as an
  unrequested publication. Claude Code's own default guidance is to commit
  or push only when the user asks; devlyn's block makes PR and merge the
  default when no delivery instruction is given. At `max`, Claude delivered
  in rp-d1 (3 of 4; o08 stopped at a local commit) and in both rp-d4 guards.
  One `high` observation does not give a rate.

## Next, chosen by the owner

Make Claude follow the default delivery at `high`: first measure how often
it skips delivery under 4.2.22, then test one instruction candidate under
the ladder rule. That is a new registered experiment (rp-d6).

## Cleanup

All six `rpd5-20261017b-*` repositories are deleted and verified 404. The
local stage, auth snapshot and GitHub credential files are removed after
this write-up merges; the measurement image is kept for rp-d6.
