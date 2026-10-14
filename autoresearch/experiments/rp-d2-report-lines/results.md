# rp-d2 results — report lines

**Outcome: INCONCLUSIVE. Y is not adopted, and the paragraph is reverted.**

The registered schedule stopped at its first slot, under the registered STOP
rule. No arm comparison exists. The test used the frozen
[registration](registration.md) (commit `2c0fde6c`, both reviewers SHIP), the
[contract](DESIGN.md) and [registration.json](registration.json).

## What happened

| Slot | Arm | Engine / task | Status | Notes |
|---|---|---|---|---|
| m01 | X | Claude / BV | STOP (`NOT_ASSESSED`) | Owner exited 0 after 999.8 s. Identity MATCH. Repository archived, then deleted and confirmed 404. Usage UNKNOWN: one `api_error` (ECONNRESET) retry, so the 0254 gap is `error or retry outside scope`. |
| m02–m16 | — | — | NOT_RUN | earlier slot stopped the schedule |

- **No usage is reported for m01.** Its native aggregate was about 2.77M
  input-side tokens and 63.5k output, but those figures are observations, not
  counted usage.
- **m01 was never graded.** Its delivery and report were not assessed, as the
  STOP rule requires. Its final report claims a merged PR, a fast-forwarded
  checkout and the removal of the worktree and branches.
- **Evidence hashes.** The schedule file is `rp-schedule.json`, SHA-256
  `25d7541a…`. The m01 verdict is `verdict-m01.json`, `e3e3d083…`.
- **The image guard never had to restore the image.**

## Why it stopped (infrastructure, not product)

Both Claude cells that stopped today, m01 and smoke attempt 1 Claude X, did so
the same way:

- **Timing.** An `api_error` ECONNRESET came after a single request that had
  been silent for 150–180 s. In m01 that happened at 886 s of 987 s; in the
  smoke cell at 563 s of 879 s.
- **Smoke attempt 2.** Its Claude cells completed without a drop.
- **rp-d1, the day before.** It ran the same image, CLI, model and effort and
  recorded no drop in any Claude cell.

The cause is not established. One hypothesis is that something on the path
between the cell and the API resets long-silent streaming connections. The
path runs through the Docker bridge, the host network and upstream.

The 0254 accounting cannot count such a retry. The withdrawn continuation rule
(DESIGN.md, Schedule) would not have changed the outcome either. The real
case also fails the unchanged audit, on unindexed request bodies. In addition,
a compared UNKNOWN cost row blocks adoption.

## Descriptive signal (not measured data)

In smoke attempt 2, on SM, one observation per cell:

- **Codex Y read the new paragraph in full, untruncated.** Its report still
  had the rp-d1 shape: "PR #1 merged, and the local checkout is clean. Nothing
  remains unresolved."
- **Claude reported cleanup and reconciliation in both arms.**

This is consistent with Grok's recorded dissent: the prompt's closing sentence
("Finish with what you changed, what you verified and anything unresolved")
may set Codex's report shape. It proves nothing about BV/Z0.

## Decision and next candidates

The registered write-up rule applies: Y is not adopted, and the
`task-completion.md` paragraph and its `.agents` mirror are reverted to
`7516ebc9`. No product file changes on main.

Next candidates, for the owner to choose:

1. **Diagnose the connection drops first.** Find out whether long-silent
   streams are reset in the cell network, for example with a timed idle-stream
   probe from the same image, before any Claude-inclusive rerun. Every Claude
   cost guardrail depends on COMPLETE usage.
2. **Grok's prompt ablation.** Hold the published paragraph fixed and drop the
   prompt's closing sentence in arm Y. This tests whether the report failures
   in rp-d1 belong to the prompt rather than the product.
3. **Rerun rp-d2 unchanged after (1).** This needs a new run ID, fresh
   repositories and a PAT edit.

## Cleanup

Everything tested was removed:

- the 18 never-used, empty `rpd2-20261014a-*` repositories: m02–m16 and the
  three attempt-1 smoke cells that did not run. The apparatus had already
  archived and deleted the other six, smoke-claude-X, the four smoke2 cells
  and m01, each confirmed 404;
- the measurement image and its saved copy;
- the live directory, `~/.local/share/nx01/rp-d2-live`;
- the worktree, after merge.

The owner deletes the fine-grained PAT (`rpd1-20261013a`, regenerated for
rp-d2) in the GitHub UI.
