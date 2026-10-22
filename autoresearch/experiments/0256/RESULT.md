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

## Addendum 2026-10-22 (post hoc; changes no reading)

Written after the result, at the owner's request to review the K7 reading. The token, decisions and predictions above
stand as recorded.

**K7 stays binding.** Astra ultra and Grok 4.7 reviewed it read-only ([prompt](results/k7-r1-prompt.md),
[Astra](results/k7-r1-astra.md), [Grok](results/k7-r1-grok.md)). Both find it a correct reading of I0185
requirement 3, which excludes another installation to the same destination with no condition on its environment.
Both hold that 0256's frozen reading cannot be changed after measurement. The shipped installer keys its lock to the
destination (`bin/devlyn.js` `DEVLYN_INSTALL_LOCK`), so it would pass this witness.

**Sensitivity.** K7 reproduces once in each codex arm, in opposite replicates: on A's d12 (r1) and on B's d22 (r2).
The registered rule compares each B replicate with the same A replicate, so only r2 fails. Pooled over both
replicates, B's reproducing witnesses on codex I0185 ({K3, K7, X1}) are a subset of A's ({K2, K3, K7, X1, X2}), and
the same decisions would read `DEVELOPMENT_PASS`. This is a limit of the per-replicate pairing, not evidence that
the package adds the K7 defect.

**For the next registration** (to be frozen before it measures; nothing changes here): keep K7 binding, and
replace the per-replicate subset condition with a per-task, per-configuration comparison. Astra proposes comparing
reproduction counts per witness; Grok proposes `union(B) ⊆ union(A)` with per-replicate deltas reported, not gating.
Both accept a swap like this one, where each arm shows the witness once; equal counts hide which replicate failed.
Both reject a witness that B shows and A never does. The union rule also accepts a higher B count whenever A shows
the witness at least once; counts reject that.

**I0185 carried no principles in B.** On a checkout whose `package.json` is named `devlyn-cli` and that has
`bin/devlyn.js`, the 4.2.24 installer writes no instructions: `-y --claude` writes skills and settings but no `CLAUDE.md`
("Skipping CLAUDE.md; shipped instruction template in devlyn-cli source checkout"), and `-y` writes skills but no
`AGENTS.md`; root reproduced this on the I0185 base. The
I0185 B cells are therefore bare Claude Code or Codex plus skills, and their B-vs-A witness gaps cannot be attributed to
the principles text. Neither can d23's false completion; d24 (A) makes the same claim. A future registration that attributes results to the
principles must check that the instructions were loaded and keep such fixtures out of that attribution.

**Claude: no principles change now.** The owner asked for a fix to the Claude-side result. A read-only diagnosis of
the transcripts ([results/claude-diagnosis.md](results/claude-diagnosis.md)) found no single mechanism:

- The principles are never cited as the reason for a failure.
- Narrow evidence generalized into a general claim produces false completions in both arms: d28 in B, and d24 in A,
  which repeats d23's I0185 claim. On D4 itself, A's d27 diagnosed the hang that d28 explained away.
- d23 had no principles text (above).
- Delivery and executor bookkeeping contributed to B's extra wall time on F tasks; mutation-test stalls of about
  two minutes dominated three of those gaps, and no quality effect of those lines was established.
- The only arm-specific pattern also seen in 0233: on F10/F11, c02 and c12 leave malformed JSON to Express's default
  HTML 400; c02 reports that the request did not cover it, c12 that it did not list it. All four A cells
  handle it, as does c05 (B). c15 was cut off by its own `kill` and gave no report.

Astra ultra and Grok 4.7 reviewed it in two read-only rounds
([r1 prompt](results/claude-fix-r1-prompt.md), [Astra](results/claude-fix-r1-astra.md),
[Grok](results/claude-fix-r1-grok.md); [r2 prompt](results/claude-fix-r2-prompt.md),
[Astra](results/claude-fix-r2-astra.md), [Grok](results/claude-fix-r2-grok.md)). In round 1, Astra proposed
deleting one principles clause for an eight-cell screen; Grok found the evidence too thin to target. In round 2, both
recommended leaving the canonical text unchanged:

- Two reported B omissions against none of four A cells, with c15 censored (one-sided Fisher p ≈ 0.14; counting
  c15's missing handler, 3 against 0, p ≈ 0.07), cannot pick out one sentence.
- A parser witness chosen after seeing B fail it would be outcome-shaped on these cells.

The observation goes to the powered study as a secondary endpoint on fresh F10/F11 cells: malformed JSON handled or
left as HTML 400, in both arms. It must be frozen before that study measures. Astra proposes a directional prediction
(lower parser pass rate in principles-exposed Claude B than in A); Grok proposes a descriptive, non-gating tally. Any
later ablation needs the owner's approval of the exact deletion.
