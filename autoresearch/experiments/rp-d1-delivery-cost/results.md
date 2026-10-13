# rp-d1 results — default-delivery cost (2026-10-14)

**The prediction is refuted.** Seven of the eight requests reached a real merged
PR, and usage was COMPLETE for all eight. Under the registered success rule,
Claude succeeded 3/4 times and Codex 0/4. All four Codex failures are report
coverage: each Codex delivery itself merged correctly. The
[registration](registration.md) was frozen before exposure, and the numbers
come from the pre-registered [summarize.py](summarize.py)
([summary.json](results/measured/summary.json)).

## Per engine (all dispatched attempts)

| Engine | Success | Failed | Wall s | Input | Output | Wall / success | Input / success | Output / success |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Claude Code 2.1.296, `claude-opus-5-5` max | 3 | 1 | 2,335.4 | 7,663,992 | 223,802 | 778.5 | 2,554,664 | 74,601 |
| Codex 0.162.1, `gpt-6-sol` high | 0 | 4 | 690.9 | 2,345,158 | 22,709 | — | — | — |

Codex has no per-success cost because it had zero successes. Even so, its
four attempts together used 30% of Claude's wall time, 31% of its input and
10% of its output. This is descriptive only and is not a registered
comparison.

## Per request

| Slot | Task | Engine | Merged PR | Checks | User files | Report (Astra / Grok) | Result |
|---|---|---|---|---|---|---|---|
| o01 | BV | Claude | yes | pass | preserved | all supported / all supported | SUCCESS |
| o02 | BV | Codex | yes | pass | preserved | cleanup missing, reconciliation ambiguous (both) | FAILED |
| o03 | Z0 | Codex | yes | pass | preserved | cleanup missing, reconciliation ambiguous (both) | FAILED |
| o04 | Z0 | Claude | yes | pass | preserved | all supported / all supported | SUCCESS |
| o05 | Z0 | Claude | yes | pass | preserved | all supported / all supported | SUCCESS |
| o06 | Z0 | Codex | yes | pass | preserved | cleanup missing, reconciliation ambiguous (both) | FAILED |
| o07 | BV | Codex | yes | pass | preserved | cleanup missing, reconciliation ambiguous (both) | FAILED |
| o08 | BV | Claude | **no** (local only) | pass | preserved | not reviewed: no PR | FAILED |

- **o08.** Claude fixed the bug correctly, but it delivered `LOCAL_ONLY`. It
  read the apparatus prompt's sentences "Git's internal metadata writes needed
  for normal repository operations are allowed" and "Do not look up upstream
  fixes" as a limit on publishing. Its report said this truthfully. The
  attempt counts as a failure, with its cost.
- **Codex.** Each final report said only that the change was merged and "the
  checkout is clean". Cleanup and reconciliation actually succeeded:
  - no owned worktree or branch was left;
  - local `main` equals the merged commit.

  The 4.2.18 instructions say to "report verification, delivery and checkout
  reconciliation separately" (`task-completion.md:203`). Both reviewers
  independently judged cleanup MISSING and reconciliation AMBIGUOUS. No
  report contained a false claim.

## Disclosed deviations

1. **Post-exposure evaluator correction.** The reconciliation fact compared
   filesystem modes, so the installer's 0600 `.devlyn-install.json` markers
   made all eight slots `PENDING`.
   - The fix is the Git-mode normalization already registered for
     preservation. It was re-run read-only over the sealed evidence and
     archives ([reevaluation.json.gz](results/measured/reevaluation.json.gz)).
   - The raw census was unchanged. Only reconciliation changed:
     o01–o07 became `RECONCILED`, and o08 stayed `PENDING`.
   - No status changed. Both results reviewers confirmed this.
2. **o02 index refresh.** At 02:15 KST, after evaluation, the orchestrator ran
   `git status` inside o02's sealed checkout. That rewrote only
   `cell/work/.git/index`, so the original bytes are not recoverable.
   - Its entries still equal HEAD's tree, and it has no assume-unchanged or
     skip-worktree flags.
   - The original verdict predates the incident. Re-evaluation accepted this
     one file only as a disclosed change.
   - Reviewers found no possible effect on any result. Inspection now uses
     `GIT_OPTIONAL_LOCKS=0`.
3. **Smoke attempts and credential re-freeze** are recorded in the
   [registration](registration.md). The measured account is the one recorded
   at the final freeze.

## Decision (HANDOFF step 7)

**No removal candidate is registered; the current text is kept.**
- Repetition analysis (re-exploration, re-verification, duplicate allocation)
  and stage attribution were not performed. The receipts do not separate
  delivery from implementation without an analysis that was not registered,
  so nothing here supports a removal.
- The PR+merge default stays.

Two observations are recorded for future work, neither adopted here:
- **Product.** Codex did not follow the instruction to report reconciliation
  separately, and it omitted cleanup. Any change must follow the ladder rule
  (instruction-only, one mechanism, tokens never increase) and needs its own
  registered measurement.
- **Apparatus.** A future live-delivery prompt should drop "Git's internal
  metadata writes … are allowed". One of four Claude runs read it as a
  publishing limit.

## Review

- **Before exposure.** Astra ultra and Grok 4.7 reviewed the design, the
  apparatus (eight rounds) and the registration (two rounds). See
  [results/](results/).
- **Results review.** Both reviewers read the raw data and graded the report
  checklists ([Astra](results/results-review-astra.md),
  [Grok](results/results-review-grok.md)). Both returned
  `VERDICT: SHIP (results sound)`.
