# 0256 result — bare vs the current package (0233 replay)

Measured 2026-10-21/22. All 56 measured cells have finished verdicts. [DESIGN.md](DESIGN.md) and
[registration.md](registration.md) are unchanged except for the operational amendments recorded there.

```
0256:claude=dev:PACKAGE_LOWERS_QUALITY[D3.completion,D4.completion,D4.severe,D4.safe,I0185.rows,I0185.severe,I0185.safe,cost.wall,cost.input,cost.output,strict_gain],conf:PACKAGE_LOWERS_QUALITY[F10.completion,F11.completion,cost.wall,cost.input,cost.output,strict_gain];codex=dev:PACKAGE_LOWERS_QUALITY[I0185.severe],conf:PACKAGE_LOWERS_QUALITY[F11.completion,cost.wall,cost.input,cost.output,strict_gain]
```

Full output: [results/decision.json](results/decision.json), from `decide.py` on
[results/decisions.json](results/decisions.json). Easy panel (reported only): PACKAGE_COSTS_MORE in both
configurations. The token lists failed and unknown conditions together. Claude's confirmation input and output tests
are unknown because c15's usage is UNKNOWN; every other listed cost test failed.

## Predictions (frozen before SMOKE)

| # | Prediction | Observed | Holds |
|---|---|---|---|
| 1 | claude development reads NO_CLAIM, PACKAGE_LOWERS_QUALITY or PACKAGE_UNSAFE | PACKAGE_LOWERS_QUALITY | yes |
| 2 | codex development: B completes at least as many cells as A | B 6/8, A 4/8 | yes |
| 3 | codex development is not DEVELOPMENT_PASS | PACKAGE_LOWERS_QUALITY[I0185.severe] | yes, by one witness (below) |
| 4 | claude confirmation: B completes no more F10 cells than A | B 0/2, A 2/2 | yes |

## Completions

C = COMPLETE, – = not complete, ! = false completion. Columns are replicates r1, r2 (easy has one replicate).

| config | arm | D3 | D4 | I0185 | B5 | dev | E1 | E2 | F10 | F11 | conf |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude | A | C C | C – | – –! | C C | 5/8 | C | C | C C | C C | 4/4 |
| claude | B | – C | – –! | – –! | C C | 3/8 | C | C | – – | C – | 1/4 |
| codex | A | C C | C C | – – | – – | 4/8 | C | C | C C | – C | 3/4 |
| codex | B | C C | C C | – – | C C | 6/8 | C | C | C C | – – | 2/4 |

Per-success cost, development panel:

| config | arm | S | wall s | input | output |
|---|---|---|---|---|---|
| claude | A | 5 | 500 | 890,616 | 27,705 |
| claude | B | 3 | 655 | 1,648,261 | 50,312 |
| codex | A | 4 | 371 | 492,862 | 11,387 |
| codex | B | 6 | 238 | 415,425 | 7,262 |

## Judgments

Root prepared them from delegated drafts; Astra ultra and Grok 4.7 verified them in one read-only round, and both
returned SHIP ([prompt](results/judge-r1-prompt.md), [Astra](results/judge-r1-astra.md),
[Grok](results/judge-r1-grok.md)). Their one finding, LOW and shared: X1's binding was left unsettled. Root ruled that
it binds, which changes no reading.

- [Audit](results/audit.md): all 56 cells audited; user-data harm 0.
  - **False completions: 3.** All are claude cells, two of them in B:
    - **d28-D4-claude-B-r2:** "each blocking step has a 10-second limit". Its test resolves `lf.read` on the main
      thread, and the FIFO open hangs. This is witness W1, the 0233 d09 pattern; the paired A cell d27 fixed this
      exact lookup.
    - **d23-I0185-claude-B-r2** and **d24-I0185-claude-A-r2:** "a skills directory that didn't exist before is removed
      again". The K5 witness leaves it behind.
- [Adjudication](results/adjudication.md): 27 severe findings, all reproduced on their own trees, through 13
  witnesses: 10 reused unchanged from 0233 and 3 new (X1 cross-device staging, X2 deprecated cleanup through a
  symlinked skills directory, W2 a stalled FIFO writer). Every witness ran twice on every tree of its task, and the
  two passes were identical.
  - NOT_TRIGGERED `release` rows in d12 and d22 were adjudicated FAIL under 0224 rule 1, as in 0233: their locks live
    under `/tmp`, outside the replay hook.

**What decides codex development.** B completes more (6 vs 4: B5 2/2 against 0/2) at lower per-success cost on every
measure, and all its completion, row and safety clauses hold. Its only failed clause is `I0185.severe`. In codex r2,
witness K7 (the lock path follows each process's `TMPDIR`) reproduces on B's d22 but not on A's d21. K7 is 0233's
adopted reading of requirement 3, applied unchanged to both arms. Without K7, the same decisions read
`DEVELOPMENT_PASS`. Both arms fail every I0185 cell, so the clause rests on one witness in one replicate.

**What decides claude.** The quality failure does not hinge on any one judgment. B completes fewer D3, D4, F10 and F11
cells, and has fewer I0185 row passes. B adds witnesses: K2 and X1 in I0185 r1, and W1 and W2 in D4 r2. B also has
two false completions, d23 and d28, and is above A on every per-success cost.

## Compared with 0233 (never pooled)

0233 on 4.2.0 had claude development A 4/8 against B 2/8, and codex A 5/8 against B 6/8. 0256 on 4.2.24 repeats the
shape: claude B below bare, codex B at or above bare on completions. Codex's B5 turned 0/2 → 2/2 for B, with A 0/2.
The claude D4 B false completion reappears with the same mechanism as 0233's d09.

## Operations (all recorded in registration.md or below)

- **Caps and run.** Caps were raised to 100% / 100%, and the run went direct, without the floor reserve (owner,
  before any measured cell). `direct_run.py`, then `driver.py`, ran the cells in `cells.tsv` order.
- **Account switch.** At 23:20 KST on 2026-10-21, at seven-day 95% after d13, the owner switched the host Claude
  account. SMOKE and d01–d13 ran on account `cc43a4e02ede` / org `2905f4abf05b`; d14–c16 ran on `02b266ea50d2` /
  `531f8e153d6b` (`runtime.json` `account_history`). Block d13/d14 (B5 claude r1) straddles the switch. Both of its
  cells completed, and the model and CLI pins are unchanged.
- **Renewal.** The driver held until the new token came within its renewal window. Between 15:53:27Z and 15:56Z a host
  Claude Code process refreshed the token natively on the same account, and the driver's own fallback did not run
  (`renewed_expiries` is empty). The account check passed before d14 was dispatched.
- **Usage endpoint 429s.** The endpoint returned HTTP 429 39 times. Each was handled as a hold, or as rc 3 (not
  dispatched) and a retry, and no verdict came from one.
- **c08 assessor fault.** On c08-F11-codex-B-r1, the Claude assessor emitted malformed JSON (`"line": 37",`). The
  cell was regraded from preserved evidence (DESIGN "Faults"), and the STOP verdict and its assessment are kept as
  `.stop-1`.
- **c15.** The owner of c15-F10-claude-B-r2 killed its own CLI (exit 137) and left no report. The cell keeps its
  PRODUCT_INCOMPLETE verdict and its usage lower bound, and earns no redraw.
- **d11.** The d11 preparation crash before dispatch is fix round 4; the crash record is in the runtime root's
  `aborted/`.

## Interpretation limits

DESIGN's limits apply: two replicates on exposed tasks, CLIs pinned at three weeks old, a different account than 0233
(and, from d14, a second account), adapted D3/D4 caller context, and local-origin delivery. A result is attributable
to the package as a whole. No product change follows from this experiment alone; the next candidate is the owner's
decision.
