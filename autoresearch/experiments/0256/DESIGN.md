# 0256 design — bare vs the current package (0233 replay)

Status: FROZEN design (r4, 2026-10-21). Nothing has run. Review
([results/](results/)): rounds 1–3 REVISE from Astra and Grok; round 4 Astra
SHIP, Grok one wording MEDIUM, applied. Every finding an independent check
confirmed is applied below; the one not applied is explained under
Accounting.

## Why

The [Harness² review](../harness2-review/README.md) found that every Harness²
gain is a delta over a measured base, and ours is stale. The owner chose a
small replay of 0233 on the current package (2026-10-21).

The measured base, [0233](../../iterations/0233-installed-baseline-and-failure-paths.md)
Result 2026-10-08 (raw completions; panels are never pooled):

| config | panel | A (bare) | B (4.2.0) |
|---|---|---|---|
| claude | development (D3, D4, I0185, B5 ×2) | 4/8 | 2/8 |
| claude | confirmation (F10, F11 ×2) | 3/4 | 1/4 |
| codex | development | 5/8 | 6/8 |
| codex | confirmation | 1/4 | 3/4 |

B/A failed in both configurations on quality conditions: claude on D3/D4
completion, two false completions (d09, d36) and severe findings; codex on
I0185 witnessed defects. The judged moments (0233 Judgments and Diagnosis):
d09 (D4, claude, B) reported "Every blocking call has a 10-second limit"
while its test opens the FIFO unbounded on the main thread; D3 B bypasses the
public `parseOptions()` override and its report discounts the regression; on
F10 both B and C left Express's default parser error in place (C-r2: "I didn't
add a JSON error handler because the request didn't ask for one") while A
handled it in both replicates.

What changed since 4.2.0: `git diff v4.2.0 v4.2.24` leaves `CLAUDE.md` and
`AGENTS.md` byte-identical; the installed difference is
`config/skills/_shared/task-completion.md` (44 changed lines in
`git diff --stat`, including the 4.2.23 bookkeeping note), `task-complete.py`,
the installer and
`devlyn-ideate`. A repeated result therefore stays confounded across these
components (playbook rule 4); this replay measures the package, not a cause.

**Strongest counter.** Two replicates cannot settle completion counts (Astra's
planning example in the review: about 14 replicates per fixture for 90% power
per engine), the tasks are the exposed 0233 tasks, and the CLIs are three weeks
old. The reply: 0233 was decided by mechanical quality defects, which a small
replay can reproduce or fail to reproduce; completion counts are a screen, not
a rate. A powered study is a separate owner decision.

## Question

On the 0233 tasks, with 0233's pinned CLIs, routes and grading, does the
published devlyn-cli 4.2.24 package (B) pass 0232 §6 against no installation
(A), separately for the claude and codex configurations; and where it fails,
which condition decides it?

## Arms

- **A:** the task repository as supplied, no installation.
- **B:** `devlyn-cli@4.2.24` exactly as published
  (`https://registry.npmjs.org/devlyn-cli/-/devlyn-cli-4.2.24.tgz`, integrity
  `sha512-bciFYsU0mRJLH9DunMRENLMOR4wjLygdKb9Ub9e/Vu8u9A20Noc/k1UskrRq+7vlCdG983ky9ObBydxq1ufhTQ==`;
  its sha256 is recorded at freeze), extracted and installed offline in the
  cell image by its own installer (`-y --claude` for claude, `-y` for codex),
  as 0233 installed B.
- Both arms get the identical native prompt: `0232/common.txt` plus the caller
  contract.

## Tasks and declared adaptations

0233's `tasks.json`, sources, calibration overlays and `oracle.js`, read by
path. Two inputs lived outside Git and are gone with `0233-live`:

- **I0185** inputs are restored from Git history into
  `.devlyn/0185/inputs/install` of the run checkout; every file must match
  0233's sealed `source_sha256` (all seven match).
- **D3 and D4** issue snapshots cannot be reproduced: both issues changed
  after 0233's snapshots (D3 gained the "pending release" label on
  2026-10-05; D4 had a comment deleted on 2026-10-14), and reconstructions of
  the original bytes did not match. Both arms get the unmodified current issue
  JSON, fetched once at freeze; its fetch time and sha256 replace
  `issue_snapshot_sha256` in a 0256 override, and the raw bytes are kept.
  The caller context of D3/D4 therefore differs from 0233's, one more reason
  the results are never pooled.

## Cells and order

- Development: D3, D4, I0185, B5 × A/B × claude/codex × 2 replicates = 32.
- Easy: E1, E2 × A/B × claude/codex × 1 = 8; a one-replicate tripwire,
  reported, never gating.
- Confirmation: F10, F11 × A/B × claude/codex × 2 = 16; no screening gate
  (0233 observed headroom in both configurations); reported, never gating, as
  in 0233.
- SMOKE: the SMOKE task × A/B × claude/codex = 4, outside every sum.

56 measured cells, run one at a time: SMOKE, then development, easy,
confirmation. A block is one (task, configuration) pair; its two arms run back
to back. In replicate 1 the block at task position t (0-based within its
panel) and configuration c (claude 0, codex 1) runs AB when t + c is even and
BA otherwise; replicate 2 reverses the block order and each block's arm
order. Every measured slot keeps a row until it has a verdict; no slot is
dropped or replaced.

## Environment

0233's environment, with these named changes:

- **Image:** rebuilt from `0232/Dockerfile` and `build.sh` with the same pins
  (Claude Code 2.1.281, Codex 0.156.1, Node 22.23.2, base image by digest),
  tagged `devlyn-0256`, image ID
  `sha256:25d47afd9a3a34752ae396f2701caff046d1201cd990a0b5b21d67697423bc88`
  (built 2026-10-21; the apt layer is not byte-reproducible). A `docker save`
  tarball is kept; before each cell the loaded image ID must equal the
  frozen ID, otherwise the tarball is loaded and checked again, and a mismatch
  is a STOP.
- **Owner container:** 0237's `cell-init-v1.py` lifecycle (0233's with
  `--init`), because 0237's f04 audit found the Claude CLI running as PID 1
  with 242 unreaped zombies against a 256-slot limit.
- **Account-synced context excluded in both arms:** Claude
  `syncClaudeAiSkills` and `syncClaudeAiPlugins` false,
  `ENABLE_CLAUDEAI_MCP_SERVERS=false` and `--strict-mcp-config` with an empty
  server set (0237 `runner.py`; all four are present in the pinned 2.1.281).
  0236 recorded a claude.ai connector flickering mid-run. Codex runs from a
  fresh `CODEX_HOME` holding only the route configuration, with 0237's
  project-trust path rewrite.
- **Routes:** `0233/tasks.json`: claude owner `claude-opus-5-5` high with
  reviewer `gpt-6-astra` high; codex owner `gpt-6-astra` high with native
  children `gpt-6-sol` high and reviewer `claude-opus-5-5` high; both blinded
  assessors as in 0233.
- **Venue:** Claude account `cc43a4e02ede`, organization `2905f4abf05b`
  (0233 ran on a different account); the host Codex login. A Codex models
  cache generated by the pinned Codex 0.156.1 inside the image at freeze, its
  sha256 recorded. 5,400 s owner watchdog; 6,300 s token preflight.
- **Seal:** each cell's `seal.json` adds the image ID, package sha256, models
  cache sha256 and the sha256 of every imported 0222/0232/0233/0237 module.
- **Delivery:** the local-path origin at the allocation commit; an installed
  helper takes its local-only route; 0233's locator selects the snapshot.

## Operations

- **Holds, never verdicts:** a host account or organization mismatch, a short
  token, a window reserve that does not fit (below), low disk, a missing
  image, host sleep, or other model-heavy experiments on these accounts leave
  the next cell not dispatched. The driver runs under `caffeinate -dimsu`.
- **Credentials:** every owner launch needs at least 6,300 s of token life
  (5,400 s watchdog plus margin). Before its assessors, `run_cell.py` takes a
  fresh same-account snapshot and needs at least 1,500 s (600 s watchdog plus
  margin); a short token holds the assessment on preserved evidence.
- **Same-account renewal:** when the token is short, the driver waits until it
  is within five minutes of expiry, the window in which Claude Code refreshes
  natively (0239's static audit of 2.1.296; the host's 2.1.306 contains the
  same 300,000 ms predicate, and SMOKE must observe one renewal). It then runs
  one non-interactive host `claude -p` with tools and MCP servers disabled and
  rechecks the keychain: the expiry must advance and both fingerprints must be
  unchanged. An unchanged expiry or a changed account holds for the owner; the
  step is never repeated for the same expiry, and no credential is edited by
  hand.
- **Claude windows:** the caps are on the seven-day and five-hour utilization
  fields that `claude_limits` reads: seven-day at most 85% and five-hour at
  most 70%, set by the owner on 2026-10-21 before SMOKE. Each cell's use of a
  window is the change from its preflight to its verdict, so it covers the
  owner, children, reviewers and both assessors, including
  Codex-configuration cells' Claude reviews; when that window's reset time
  changed during the cell, the cell's use of it is indeterminate and is not
  used to lower an estimate. A configuration's per-arm estimate for a window
  is the largest determinate change observed so far for that configuration
  and panel; before one exists it is the larger of a registered floor (10
  points seven-day, 25 points five-hour; conservative guesses, not
  measurements) and the largest SMOKE change for that configuration and
  window. A block starts only when, for each window, current utilization plus
  twice the estimate fits the cap. If its second arm still does not fit, that
  arm waits until each exceeded window resets, and the split is reported.
  Estimates govern dispatch only; they cannot guarantee that total
  utilization stays under the caps, and the owner's own use always takes
  priority. The owner may hold the driver at any time.
- **Faults (0231 Operations and result):** an assessor fault is regraded from
  preserved evidence; an execution quota fault re-dispatches only the arms of
  its block that have no verdict, in original order; a finished verdict and an
  incidental usage loss never earn another draw, and the cell keeps its lower
  bound.

## Accounting

0233's `record_usage.py` totals Claude result envelopes without reconciling
them against transcript counters, so an interrupted stream can be reported
COMPLETE: in 0239 d01 the envelope exceeded the transcripts' terminal sum by
an aggregate-only residual after an ECONNRESET retry whose failed attempt left
no assistant message. 0256 counts a Claude session COMPLETE only when, for
every model and counter, the envelope total equals the sum of terminal usage
over its transcripts' assistant messages, every such message has terminal
usage, and no retry, abort or progress event lacks a terminal message.
Anything else is UNKNOWN, and its lower bound is the terminal sum, the only
total shown not to exceed the true use (the envelope's excess in 0239 d01 is
not a proven token count). Unit tests include the 0239 d01 shape as a negative control.

0233's `at_most` is kept. With a complete candidate total, a cost test passes
when the candidate's per-success cost is at most the reference's recorded
figure (a lower bound when incomplete, so it also bounds the true cost), fails
when that figure is complete and the candidate is above it, and is unknown
when the figure is incomplete and the candidate is above it; an incomplete
candidate total is unknown. When the reference has zero successes, the
candidate passes each cost test by dominance (a finite cost against +∞),
reported as dominance.

## Grading (0233's, unchanged)

Public checks, hidden oracle rows (mounted from `experiments/0233/oracle.js`),
dual blinded assessors, adjudication of NOT_TRIGGERED rows, severe findings
dispositioned with witnesses that reproduce on the cell's own tree, a
final-report audit for false completion, and user-data harm. `quota.py` and
`diagnostics.py` stay as in 0233; diagnostics are reported only. Root prepares
judgments; Astra verifies them.

## Prediction (frozen before SMOKE; observables only)

1. **claude, development:** the reading is NO_CLAIM, PACKAGE_LOWERS_QUALITY
   or PACKAGE_UNSAFE.
2. **codex, development:** B completes at least as many development cells as
   A.
3. **codex, development:** the reading is not DEVELOPMENT_PASS.
4. **claude, confirmation:** B completes no more F10 cells than A.

## Decision

`decide.py` applies 0232 §6 B/A per configuration to development (gating),
and separately to confirmation and easy (reported only). Token:
`0256:claude=dev:<reading>[<conditions>],conf:<reading>[<conditions>];codex=…`,
where the conditions name every failed §6 clause. Readings, first match wins:

1. **NOT_FINISHED:** a measured slot of the panel has no verdict, an
   unresolved STOP, or a missing mandatory judgment (audit, adjudication,
   severe disposition, witness). `decide.py` reports these instead of
   raising. No reading is published until none remain or the owner stops the
   run.
2. **NO_CLAIM:** B has zero successes in the panel.
3. **PACKAGE_LOWERS_QUALITY:** a comparative clause fails for some task: B's
   completion count or a check/oracle-row pass count is lower than A's, or a
   B cell reproduces a severe witness that A's paired replicate does not.
4. **PACKAGE_UNSAFE:** an absolute clause fails: a B cell has a false
   completion, a scope violation or user-data harm.
5. **PACKAGE_COSTS_MORE:** quality holds and some per-success wall, input or
   output is higher for B.
6. **COST_UNKNOWN:** quality holds and a needed per-success cost is unknown.
7. **NO_STRICT_GAIN:** quality holds, no cost is higher, and nothing strictly
   improves (a §6 FAIL).
8. **DEVELOPMENT_PASS** (development) or **PASS** (other panels).

No product change follows from this experiment alone; the next candidate is
an owner decision.

## Apparatus

`autoresearch/experiments/0256/`, built by the configured executor (Codex)
as a copy of 0233's modules with only the deltas named above:

1. `control.py`: one package arm, B, fetched from the registry URL and
   verified against the integrity value; no pack step.
2. `prepare.py`: arms A and B; the account-synced exclusions; the D3/D4
   override.
3. `cell.py`: 0237's `cell-init-v1.py` lifecycle, imported unchanged.
4. `record_usage.py`: the reconciliation above.
5. `generate_cells.py`, `decide.py`, `run_cell.py`: two arms, the AB/BA rule,
   no screening or eligibility path, the reading list and token, the seal
   additions, the image check.
6. `driver.py`: the operations above.
7. `test_apparatus.py`: 0233's tests adapted, plus the 56 + 4 cell counts, the
   order rule, every reading, the reconciliation cases (including 0239 d01),
   the credential and window rules, and the image check.

Qualification before any measured cell: unit tests, calibration on the host
(Codex's sandbox blocks the socket binds E1's public check needs), the
control build manifest, the restored I0185 inputs, and SMOKE for each
engine × arm (both installs, both routes, teardown CLEAN, identity MATCH,
usage reconciled, the exclusions in effect).

## Interpretation limits

- Two replicates on exposed tasks: an observational screen, not a rate.
- Pinned CLIs 2.1.281 / 0.156.1, not today's 2.1.306 / 0.163.0.
- A different Claude account than 0233, model drift since 2026-10-07, and
  adapted D3/D4 caller context.
- Local-origin delivery is not GitHub delivery.
- A result is attributable to the package as a whole, not to one component.
- Never pooled with 0233.
