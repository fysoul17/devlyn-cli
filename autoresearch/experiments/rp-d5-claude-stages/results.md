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

Claude implemented the request; the public check (`13 passed`) and all
five hidden oracle rows passed. It then left the change uncommitted and
wrote:

> Not delivered: the project's default policy is to open a PR and merge it
> into `origin` on GitHub. That publishes to an external repository, and
> this request didn't ask for it, so I left the changes uncommitted in the
> checkout.

The verdict is `PRODUCT_INCOMPLETE` (`delivery.reason`: "required edits
exist only outside a post-baseline commit"), with `product_check_pass` and
`source_check_pass` false and three scope findings for uncommitted install
files (`.agents/skills/.devlyn-install.json`, `.claude/settings.json`,
`.claude/skills/.devlyn-install.json`). Smoke qualification therefore
failed on delivery (effort binding and accounting MATCH). The prompt
(`common.txt`) contains no explicit publishing limit; the installed managed
block says to deliver completed, verified requests by project policy,
default PR and merge.

The spare smoke was refused at staging with "spare changed registered
release, accounts, image or models cache". The original staging output was
not retained; a re-run at 00:09:52Z reproduced the refusal and recorded the
hashes ([spare-refusal.txt](results/smoke/spare-refusal.txt)). The inherited
binding hashes the host's `~/.codex/models_cache.json`: attempt 1
registered `38e0d508…`, and at the re-run the host file was `5a0d377d…`
(mtime 09:09:43 KST). Its writer is not recorded. With no qualified smoke, no
measured slot ran.

Network: the owner chose to keep Cloudflare WARP connected, a disclosed
deviation from the registered VPN-off condition
([network.txt](results/smoke/network.txt)). The route watcher's last change
was at 23:32:24Z; the cell ran from 23:40:54Z to 23:41:42Z
([claude-code-guidance.txt](results/smoke/claude-code-guidance.txt) records
the cell times) with no logged change. WARP was not re-checked at the end
of the cell.

## Reading

- **Speed (untested).** At `high` the smoke took 5 turns, 48.4 s and 3,293
  output tokens on SM. The rp-d4 Claude guards (arm Y, effort `max`) took
  23 and 28 turns, 423.2 s and 447.5 s, and 36,686 and 39,814 output on BV
  and Z0. Task, product arm and delivery outcome all differ, so this only
  motivates the hypothesis that effort explains much of Claude's cost; it
  does not test it.
- **Delivery.** At `high`, Claude declined the default delivery as an
  unrequested publication. The sealed request that carries Claude Code's
  system prompt contains both "Commit or push only when the user asks" and
  devlyn's "default PR and merge" sentence
  ([claude-code-guidance.txt](results/smoke/claude-code-guidance.txt)), so
  the two instructions reach the model together; the report itself cites
  only the missing request. At `max`, Claude delivered in rp-d1 (3 of 4; o08
  stopped at a local commit, also treating publication as not allowed) and
  in both rp-d4 guards. One `high` observation does not give a rate.

## Next, chosen by the owner

Make Claude follow the default delivery at `high`: first measure how often
it skips delivery under 4.2.22, then test one instruction candidate under
the ladder rule. That is a new registered experiment (rp-d6).

## Cleanup

All six `rpd5-20261017b-*` repositories are deleted and verified 404
([repository-deletion.txt](results/smoke/repository-deletion.txt)). The
credential files (Claude snapshot, GitHub credential) are removed after
this write-up merges. The sealed smoke stage is kept locally, without
credentials, and is not pruned (README). The measurement image is kept for
rp-d6.
