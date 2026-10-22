# 0257 amendment 1 — run on any host Claude account (2026-10-22)

Dated amendment to the frozen [DESIGN.md](DESIGN.md) (r5) and the
[registration](registration.md). It changes the account rule only. The
predictions, estimands, families, gates, readings and token are unchanged.

## Why

The host switches its Claude login between two of the owner's accounts when
usage fills: during SMOKE (twice) and after the measured run's first eight
cells. At 2026-10-22T08:26:54Z, after e001–e008 (E1 and E2, all eight
COMPLETE, CLEAN, MATCH, usage COMPLETE, no scope violations), the driver
stopped on `account/organization mismatch`: the login had moved from
`02b266ea50d2` to `cc43a4e02ede`. Under DESIGN's rule, the run could not
finish across weeks. The owner decided the same day: "아무 계정 다 써
가능한거" (use whichever account is logged in).

## Change

- **Replaces DESIGN Operations, "Account".** Dispatch uses whichever host
  Claude account is logged in. A change of account is not a stop or a hold.
  Each verdict records the dispatch account, the account that read the
  after-cell windows, and the assessor's account (fingerprints only).
- **Window reserve.** The block reserve rule and caps (85% / 70%) apply to
  the account logged in when a block starts. A cell's window change counts
  toward the estimates only when its before and after readings come from the
  same account. Verdicts from before this amendment ran under the account
  stop, so they count as one account.
- **Renewal.** 0256's renewal rule (DESIGN "Unchanged from 0256") is kept
  except its same-account condition: a renewal is accepted when the expiry
  advances, whatever account is then logged in.
- **Unchanged.** Readings use tokens and wall time over every attempt (0256
  accounting), never window points or the account fingerprint. Which
  account is logged in can still change a cell through its own behavior. A
  quota fault on a full account adds an archived attempt, which is charged
  as before, and latency may differ. Under one account the same kinds of
  differences arose from its windows and time of day. The deadline
  (2026-11-12T02:30:14Z), harm latch, identity checks, holds and faults are
  unchanged. An account at its limit is still not dispatched
  (`account limit reached`).
- **Replaces DESIGN Qualification, "an account mismatch stops".** It becomes
  "an account change continues, and is recorded per cell".
- **Replaces Interpretation limits, "Cells run over one to three weeks on
  one account".** It becomes: cells run over one to three weeks on whichever
  of the owner's accounts is logged in, with the same pinned CLIs and models.
  Model drift and account are not controlled. The result reports completions
  by replicate and by account as a description, and account is not balanced
  across arms or tasks.

## Cells already run

e001–e008 ran on `02b266ea50d2` under the registered apparatus and stand. No
development or confirmation cell has run. The driver resumes from their
verdicts.

## Apparatus

[Contract](results/amend-1-contract.md). The change is limited to
`driver.py`, `run_cell.py`, `test_apparatus.py` and `README.md`. Review
records are under `results/amend-1-*`.
