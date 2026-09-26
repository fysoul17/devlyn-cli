# 0224 — result

2026-09-26. Registration: [DESIGN.md](DESIGN.md), frozen before dispatch (Astra R1 FREEZE), plus Amendment 1 after two shared infrastructure faults. The rules were computed by [analyze.py](analyze.py), committed before the first verdict. Raw evidence is in `.devlyn/0224/` (screen-out, analysis.json, decisions.json, logs); Grok inputs and outputs are in `.devlyn/0221/s6-design/grok/`.

**Outcome token: `SCREEN:B'=claude;C=claude`.** B′ and C continue to the Session 7 confirmation in the Claude config only. In the Codex config, neither shows a signal over native A or F, so both stop there.

## Cells

Wall is owner seconds. OUTPUT is total output tokens across every recorded model, and it is a lower bound when usage is PARTIAL (the isolated Codex judges in F and B′). ✓ = COMPLETE.

| Task | Config | A | B′ | C | F |
|---|---|---|---|---|---|
| I0185 | claude | ✗ 370 s / 39.8k | ✗ 1430 s / ≥92.0k | ✗ 740 s / 41.6k | ✗ 1270 s / ≥108.0k |
| I0185 | codex | ✗ 314 s / 9.6k | ✗ 2394 s / ≥126.3k | ✗ 2730 s / 198.6k | ✗ 1059 s / ≥46.5k |
| D4 | claude | ✗ 434 s / 10.6k | ✓ 493 s / ≥25.8k | ✓ 628 s / 23.5k | ✗ 1278 s / ≥93.1k |
| D4 | codex | ✓ 172 s / 4.4k | ✓ 1065 s / ≥45.3k | ✓ 603 s / 36.7k | ✗ 527 s / ≥21.2k |

- **I0185:** no cell is COMPLETE. Every product passes the public acceptance check, and every product fails the `release` replay (lock release after the backups are gone, the same class as 0185). Some also fail `terminal-alias` (A-codex, F ×2), `absence-lock` (A-claude) or the heldout suite (F-codex).
- **D4:** every product passes the public checks and all oracle rows. The incomplete cells were decided by the assessors:
  - A-claude: the Codex assessor found 1 severe issue; the assessors disagreed.
  - F-claude: ended `BLOCKED:verify-exhausted`; the Codex assessor said incomplete; the assessors disagreed.
  - F-codex: ended `BLOCKED:required-tools-unavailable` (no mypy/pyright in the image); the assessors disagreed.
- There are no ADJUDICATE rows. After re-dispatch, cell 7 has no NOT_TRIGGERED row, so `decisions.adjudicated` is empty.
- **Final-report audit:** 0 false completions. Cells that report success (A ×2 on I0185, C-claude on I0185) fail only hidden oracle rows. The B′ NEEDS_WORK runs quote the gate verbatim, and the F runs report their BLOCKED verdicts. There are 0 scope violations and 0 reproduced HIGH/CRITICAL findings.

## Rules

| Candidate / config | quality | efficiency | loss | block | continues |
|---|---|---|---|---|---|
| B′ / claude | yes (D4: B′ ✓, A ✗) | no (F-claude D4 ✗) | no | no | **yes** |
| C / claude | yes (D4: C ✓, A ✗) | no | no | no | **yes** |
| B′ / codex | no (A ✓ on D4) | no (F ✗) | no | no | no |
| C / codex | no | no | no | no | no |

- The Claude signal is thin. It rests on one draw of D4, where A-claude's product passes every check and every oracle row and is incomplete only because the Codex assessor reported one severe finding while the Claude assessor called it complete.
- The registration counts this as a signal. Session 7 must test whether it survives unexposed tasks, and must not cite this screen as evidence of quality.

## Grok static checks (4 calls, grok-4.7)

| Episode | Call | Result |
|---|---|---|
| B′, cell 2 (first binding primary review: MEDIUM, FIFO fixtures not removed on timeout, obligation 6) | defect diff | `NONE`, 598 s |
| | repair diff | `NONE`, 567 s |
| C, cell 3, call-1 (MEDIUM: EXDEV/EACCES when the workspace is in the parent directory) | defect diff | timeout, 600 s |
| | repair diff | timeout, 600 s |

- Nothing to reproduce, so nothing counts toward block.
- The C packet lists new untracked files by name but not their content. The C repair diff therefore shows the final test file as a whole new file.
- The first dispatch of the four calls never reached a model: the prompt path was wrong. The second hung waiting for tool approval in headless mode; it is kept as `*.timeout-1`. The recorded calls deny tools (`--permission-mode dontAsk`). The two C timeouts stand as rows and were not retried with other settings.

## Predictions

1. **Falsified as stated.** No STOP row was written, but two shared faults invalidated nine cells' execution and two cells' grading (Amendment 1). After the fixes and the re-dispatch, every cell has a verdict and clean teardown.
2. **Half held.** A is not COMPLETE on I0185 in either config (held). But no arm completes I0185 in either config (falsified).
3. **Held.** One A cell (codex) is COMPLETE on D4.
4. **Falsified.** F has the largest wall in 1 of 4 groups (D4-claude). B′'s wall is ≤ 0.7 × F's in 1 of 4 groups (D4-claude, 0.39); elsewhere the ratio is 1.13, 2.26 and 2.02.
5. **Held.** The B′ gates ended PASS (cells 2, 9) or NEEDS_WORK (cells 5, 14); none ended BLOCKED.
6. **Held.** Both candidates continue in one config (claude).
7. **Falsified.** Grok named no defect on the B′ defect diff, and the C defect call timed out.

## Observations (descriptive, not rules)

- B′ on Codex costs wall time. On D4 it completed in 1065 s against native A's 172 s. On I0185 it ran 2394 s, used all four primary review rounds, and ended NEEDS_WORK with two open binding findings, which it reported honestly.
- B′-claude on D4 was the fastest complete run in its config (493 s), faster than F (1278 s, incomplete) and C (628 s).
- F (3.2.1) ended BLOCKED in all 4 cells: verify exhaustion 3 times, missing type checkers once. Both of its D4 products pass every check and oracle row, yet neither run completed.
- Recorded OUTPUT over all 16 valid cells is ≥ 923k tokens. The first-pass rows and the re-assessments are not included.

## Limitations

- I0185 and D4 are exposed tasks, and each cell is a single draw. This is a screen, not holdout evidence.
- Assessors disagreed in 3 cells: A-claude D4, F-claude D4 and F-codex D4. The D4-claude signal depends on the first of these.
- Cells 7–9 and 11–16 ran on a second Claude account, and cells 6 and 10 were re-assessed on it; their executions stay on the registered account (Amendment 1). Models and routes are unchanged.
- Seals: cell 1 records `2fc4a67e`. Cells 2–6 and 10 record `9fdc9d10`, which adds only `analyze.py` (apparatus hashes identical to cell 1). The re-dispatched cells record `df9548ef`, which adds the two Amendment 1 fixes (tmpfs `CODEX_HOME/tmp`, assessor-failure stop).
