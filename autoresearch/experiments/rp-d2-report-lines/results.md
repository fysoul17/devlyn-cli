# rp-d2 results — report lines

## Rerun 20261015a (2026-10-16)

**Outcome: INCONCLUSIVE again. Y is not adopted; no product file changes.**

The unchanged rerun ([registration](registration.md#rerun-20261015a-registered-2026-10-15-before-exposure),
[registration-20261015a.json](registration-20261015a.json), both reviewers
SHIP) stopped at m08 under the registered STOP rule. Evidence:
[results/rerun-20261015a](results/rerun-20261015a/), with `summary.json`
from the registered summarizer and both reviewers' report reviews.

| Slot | Arm | Engine / task | Status | Report review (Astra / Grok) | Owner s | Input | Output |
|---|---|---|---|---|---:|---:|---:|
| m01 | X | Claude / BV | SUCCESS | PASS / PASS | 396.6 | 1,176,039 | 37,071 |
| m02 | Y | Claude / BV | SUCCESS | PASS / PASS | 472.5 | 1,775,426 | 44,341 |
| m03 | Y | Codex / BV | FAILED | cleanup, reconciliation fail (both) | 120.2 | 353,835 | 4,508 |
| m04 | X | Codex / BV | FAILED | cleanup, reconciliation fail (both) | 198.4 | 597,689 | 6,162 |
| m05 | X | Codex / Z0 | FAILED | cleanup fails (both) | 208.4 | 518,828 | 5,428 |
| m06 | Y | Codex / Z0 | FAILED | cleanup, reconciliation fail (both) | 162.7 | 534,537 | 6,094 |
| m07 | Y | Claude / Z0 | SUCCESS | PASS / PASS | 393.0 | 1,255,035 | 38,236 |
| m08 | X | Claude / Z0 | STOP (`NOT_ASSESSED`) | not graded | 741.5 | UNKNOWN | UNKNOWN |
| m09–m16 | — | — | NOT_RUN | — | — | — | — |

- **Every graded slot delivered correctly.** Checks passed and the PR
  merged. All eight dispatched repositories, m08's included, were archived,
  deleted and confirmed 404. All eight slots ran on the registered Claude
  account pair and Codex account.
- **The two reviewers agreed on the pass or fail of every category of every
  graded slot.** On m03, m04 and m06 reconciliation, Astra recorded `MISSING`
  and Grok `AMBIGUOUS`; both fail.
- **m08 stopped on a dropped connection.** Its last transcript row before a
  gap is at 23:41:12Z. The only `api_error`, ECONNRESET, came at 23:44:13Z and
  was retried once, so usage is UNKNOWN. The route watcher (`sleep 5` polls)
  logged the host default route moving from `en0` to the tunnel interface
  `utun4` at 23:41:44Z, during that silence, and back to `en0` at 23:46:45Z.
  The drop came while `utun4` held the route. No other `api_error` and no
  other route change occurred during any cell.
- **Credential renewal.** The auth manifest is `cd4fa3d3…` for m01–m06 and
  `190251d6…` for m07–m08, so the renewal fell between pairs 3 and 4. By the
  operator's account (not in the saved logs), the host's shared Claude login
  had switched accounts mid-run and `stage.py --renew` refused that account.
  The renewal snapshot is on the same registered account pair.

### Descriptive signal (not an adoption result)

- **Codex failed the report in all four slots, in both arms.** Every Codex
  report omitted cleanup. In m03, m04 and m06, reconciliation was only a clean
  checkout; m05 (X) reported a fast-forward. Each report closes with the merge,
  a clean checkout and nothing unresolved, in both arms. Y's paragraph did not
  change that shape.
- **Claude passed every graded report**, in both arms.
- **This matches rp-d1 (Codex 0/4) and smoke 20261014a.** It is consistent with
  Grok's recorded dissent: the prompt's closing sentence may set Codex's
  report shape.

### Diagnosis update and next candidate

This is the third Claude drop in rp-d2. It is the first logged while a
route change was in effect, and it supports the diagnosis below. Hard rule 5
now also says to quit the VPN client for the run.

With the Y paragraph showing no effect on Codex in 2 of 2 Y slots, the
remaining candidate is Grok's prompt ablation (candidate 2 below).

### Cleanup (rerun)

- **Repositories.** All 24 `rpd2-20261015a-*` repositories are verified 404.
  The apparatus archived and deleted the 12 used ones; the 12 unused, empty
  ones were deleted by hand.
- **Image and live directory.** The image and its saved copy are removed, as
  are the credential snapshots. The live directory is removed after merge.
- **PAT.** The owner deletes the fine-grained PAT `rpd2-20261015b` (and the
  unused `rpd2-20261015a`) in the GitHub UI.

## Run 20261014a

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
- **rp-d1, earlier the same date.** Its final freeze was at 01:15 KST, and
  the two drops came at 20:20 and 23:05 KST. It used the same image
  definition, CLI, model and effort; the image was rebuilt for rp-d2, with a
  different ID. Every rp-d1 Claude cell recorded COMPLETE usage, with no
  drop.

The cause is not established. One hypothesis is that something on the path
between the cell and the API resets long-silent streaming connections. The
path runs through the Docker bridge, the host network and upstream.

The 0254 accounting cannot count such a retry. The withdrawn continuation rule
(DESIGN.md, Schedule) would not have changed the outcome either. The real
case also fails the unchanged audit, on unindexed request bodies. In addition,
a compared UNKNOWN cost row blocks adoption.

## Diagnosis (added 2026-10-15, after merge)

The owner chose candidate 1. Host route changes made by a VPN client are the
likely cause. On the morning of 2026-10-15, failures followed each VPN change
within about a minute. For 2026-10-14 the match rests on timing alone. Docker is not needed
for a drop, because host sessions dropped as well. One retry remains
unexplained. The text above is unchanged. "Silent" there means no transcript
row was written; it does not mean the connection carried no bytes.

- **Host sessions outside Docker dropped the same way.** Host Claude Code
  transcripts record nine `api_error` ECONNRESET retries on 2026-10-14, from
  18:54 to 23:26 KST. Each came 82–160 s after the previous row. Three more
  followed on the morning of 2026-10-15, by 08:48 KST. From 2026-09-29 until
  18:54 KST on 2026-10-14 there were none, across about 600 requests that
  waited 80 s or more. Successful requests on the same evening waited up to
  1,020 s, so a fixed limit on total request time does not explain the drops.
  Transcript gaps do not measure idle time on the wire.
- **Codex dropped in the same morning window.** Three Codex streams failed with
  `Can't assign requested address` (EADDRNOTAVAIL), which fits a local
  address that is no longer available.
- **This morning's logs pair VPN changes with failures.**
  - Cisco Secure Client brought up a full-tunnel VPN, with a VPN default
    route, at 08:22:55 KST.
  - A user-requested disconnect ended it at 08:29:10–08:29:12.
  - Codex streams then failed with EADDRNOTAVAIL at 08:29:59, 08:30:08 and
    08:31:20. A fourth, at 08:30:08, failed with `error decoding response
    body`.
  - A host Claude request that began at 08:28:09, inside the tunnel window,
    failed with ECONNRESET at 08:30:20.
  - The tunnel came up again at 08:46:38. A host Claude request failed with
    ECONNRESET at 08:47:47.
  - One more host retry came at 08:45:01. The system log from 08:44:30 to
    08:45:05 has no VPN, tunnel or route event. Its cause is not established.
- **Yesterday matches on timing (inferred).** The detailed agent log for
  2026-10-14 has rotated out, and only process stamps remain.
  - The Cisco Secure Client app started at 18:53:35 KST.
  - VPN agent helper processes appeared at 18:51–18:53, 19:49, 20:18, 23:02
    and 23:21.
  - The first host drop followed at 18:54:20. Smoke attempt 1 dropped at about
    20:20 and m01 at about 23:05, each about two minutes after a stamp.
- **Docker cells share the host's routes.** Docker Desktop opens container
  connections from the host, so a host route change can break them as well.

**Consequence.** A live run needs a fixed host network. No VPN may connect or
disconnect, and the host may not switch networks, while a cell runs.
[benchmark/README.md](../../../benchmark/README.md) now states this as a hard
rule. The rule avoids the likely trigger. It does not prove that every drop
goes away, and a drop during a cell still stops the run as registered.
Candidates 2 and 3 remain for the owner.

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

Cleanup is done after this write-up merges. The PR records each removal once
it is verified:

- the 18 never-used, empty `rpd2-20261014a-*` repositories: m02–m16 and the
  three attempt-1 smoke cells that did not run. The apparatus had already
  archived and deleted the other six, smoke-claude-X, the four smoke2 cells
  and m01, each confirmed 404;
- the measurement image and its saved copy;
- the live directory, `~/.local/share/nx01/rp-d2-live`;
- the worktree, after merge.

The owner deletes the fine-grained PAT (`rpd1-20261013a`, regenerated for
rp-d2) in the GitHub UI.
