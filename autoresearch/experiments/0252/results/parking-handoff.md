# User-requested parking — 2026-10-11 02:58:58 UTC

The owner requested: “새 세션에서 이어서 할 수 있게 파킹”. Improvement work is
paused until a new continuation request. No source acceptance, commit, PR or npm
release was performed for 0251/0252. No candidate instruction is admitted.

## Read this before starting anything

The serial driver was suspended with **SIGSTOP to PID 72149 only**, while waiting
for its existing d05 child. Observed state was `Ts`. The current runner PID 49409
was still running normally. The d05 native owner was deliberately NOT interrupted:
it may finish and seal its usage/verdict/teardown independently. The suspended
driver cannot launch d06. No frozen script, input or schedule was modified.

This is a paused scheduler with one draining execution, not a claim that all
processes have stopped. Do not run an independent native owner, reviewer or heavy
test while d05 is live. Do not clean scratch or remove any worktree yet. All
delegated agents had completed before parking.

Durable process observation: `~/.local/share/nx01/0252-live/parking-v1.json`.
The former unified exec session was 99576; a new session must inspect OS/process
and on-disk evidence instead of assuming that tool session is available.

## Exact workspace and evidence

- Original repository: `/Users/aipalm/Documents/GitHub/devlyn-cli`, clean main at
  `5099300f5d1ebd41fed13afeddca24c747ab9b9b` (merged PR200).
- Owned candidate: `/Users/aipalm/.local/share/nx01/0251-fixed-auth`, branch
  `candidate/0251-fixed-auth`, task `minimal-solo-fixed-auth-0251`.
- Receipt: original repo `.git/devlyn-completion/38cf96b8998be240bebad6fd/receipt.json`.
  Its scratch is still in use by the current experiment; retain it.
- At parking, only owned changes were `autoresearch/HANDOFF.md`,
  `autoresearch/NORTH-STAR.md`, and new `autoresearch/experiments/0251/` and `0252/`.
- Retained execution source: `~/.local/share/nx01/0251-live/source/autoresearch`.
  Never replace it with the disposable publication worktree.
- Private auth and smoke evidence: `~/.local/share/nx01/0251-live`.
- Measured study: `~/.local/share/nx01/0252-live`, especially `registration/`,
  `runtime.json`, `bindings.json`, `freeze-v1.json`, `freeze-audit-v1.*`,
  `out-measured/`, `launch/` and `or2-driver.stdout`.
- The exact operator script is `0252-live/run_or2.py`; its pre-dispatch hash is
  bound in `launch/operator-binding.json`. Do not edit or restart it from slot 1.

## Completed work and current observations

0251 fixes the demonstrated shared-Keychain account-selection failure by selecting
already provisioned credentials once, then checking only the sealed snapshot.
Claude uses supported access-token auth without a refresh credential; Codex keeps
its managed, refresh-capable copy. This guarantees stable selection, not isolated
grants. No new login/account change was required. No custom renewal was performed.

The adapter passed 22 targeted tests and Astra final review with zero HIGH.
Both authentication smokes passed an independent 23-check native audit, including
complete usage and clean recorded teardown. These are operational checks only.
See `0251/results/verification-summary.json`, `smoke-native-audit.*` and
`review-and-tests-v1.json`. The review record predates the final smoke audit;
the verification summary records the audited final smoke status.

All 1,092 unique earlier-study bindings are unchanged. Prior POSIX product checks
are reused only because all 9,116 relevant inputs are unchanged. The v1 reuse
probe had a symlink-metadata formatting mistake; corrected v2 passed, preserving
both records. Logs are in candidate `.devlyn/`. No product tests were newly run
or claimed as new runs. Root instructions remain 597 words/4,049 bytes; version
4.2.5 is unchanged. Actual prior Opus Max/Grok advice is in `0237/advice`.

0252 froze 773 bindings and passed independent freeze audit. Four OR2 slots have
sealed runner verdicts; the whole block has NOT yet been independently audited
or gated:

| Slot | Arm | Runner verdict | Owner seconds | Input | Output |
| --- | --- | --- | ---: | ---: | ---: |
| d01 | Codex S | CHECKS_PASS | 669.6833574170014 | 639167 | 23386 |
| d02 | Claude B | PRODUCT_INCOMPLETE | 1719.27477012499 | 3168958 | 191043 |
| d03 | Claude S | CHECKS_PASS | 1069.8808793750068 | 4600164 | 118425 |
| d04 | Codex B | CHECKS_PASS | 708.9588165830064 | 545514 | 24557 |

All four report COMPLETE usage. d05 is Claude S repetition 2. At parking its owner
had run about 7 minutes with recent stdout. Remaining OR2 slots are d06 Codex B,
d07 Claude B, d08 Codex S. Do not infer a failure cause, quality gain or admission
from this incomplete block. The d02 quiet interval was read-only observed, then
output resumed and a normal terminal record arrived; it was not an auth STOP.

## Resume safely when the user continues

1. Search pyx-memory for devlyn-cli 0251/0252 parking and applicable corrections.
   Read the owned NORTH-STAR/HANDOFF and frozen 0252 registration/schedule.
2. Inspect `parking-v1.json`, `ps` identity/state, driver stdout and d05's
   `out-measured/verdict-d05-or2-claude-s.json`, raw result and launcher records.
   A verdict may already exist while the stopped parent still waits to reap its
   child. A missing terminal record is not zero usage or a failed product verdict.
3. If PID 72149 still has the exact recorded command and is stopped, verify the
   frozen bindings and driver hash before any resume. **Only after the user's
   continuation request**, SIGCONT that exact driver; never a reused PID. It will
   record d05 and proceed in its original sequence. If d05 is still live, do not
   run other native owners/reviewers/heavy tests in parallel. The d05 driver
   dispatch wall includes the user's scheduler pause; retain and annotate that
   fact. Registered efficacy uses the native `owner_seconds`, which did not pause.
4. If that driver no longer exists, do not replay completed slots or adopt an
   unrelated process. Audit d05's actual custody and lifecycle first. Reconcile
   only verified existing output; any resumed remaining-slot orchestrator must
   preserve the exact order, binding checks and STOP behavior. Record this user
   interruption. Missing accounting/identity/teardown closes the study as STOP;
   do not grade source/oracles/delivery after an accounting or identity STOP.
5. The fixed Claude credential expires at `2026-10-11T07:21:29.565Z`; every prepare
   and launch requires at least 6,300 seconds remaining. **Never renew, recapture,
   change account or lower the margin to rescue 0252.** A lifetime refusal closes
   this study with remaining slots NOT_RUN. Stable selection does not guarantee
   provider acceptance for the remainder of that lifetime.
6. Complete OR2 unless an apparatus STOP occurs. Then independently audit the
   block and apply its registered per-engine gate once, including failed-attempt
   costs. No per-cell design dialogue, favorable retries or wording changes.
   Advance to the frozen OR1 block only on PASS, and controls only after OR1 PASS.
   B=0/S>0 is QUALITY_GAIN/RESOURCE_NOT_COMPARABLE and does not advance. Do not
   automatically create a successor experiment or escalate to pair after closure.

## Finish after the study reaches a valid boundary

Copy the existing retained freeze audit into tracked 0252 results. Audit complete
native evidence/usage/identity/teardown and scan selected publication artifacts
for actual secrets without printing them. Preserve private originals and unknown
costs. Update reports/HANDOFF/NORTH-STAR with actual closure or qualified admission.
If only research/docs change, reuse exact unchanged product checks; changed
instruction templates require affected checks again. Review final diff, commit
only accepted paths, bind `.devlyn/acceptance.json`, then use the original bound
`.agents/skills/_shared/task-complete.py` receipt from outside the candidate with
`--writers-stopped`. Default PR+merge is authorized; no npm release. Do not release
writers or clean scratch while a runner/container uses it. Reconcile original main
only when clean and fast-forwardable. Parking itself is not source acceptance.

Preserve the locked `0250-minimal-solo` worktree and all old retained roots.
PR200 is merged and its publisher removed. PR199's old publisher has delivery
COMPLETE/scratch CLEAN but workspace cleanup pending on shared VM process 43804;
do not kill that process or force removal. Studies 0248–0250 remain closed and
their observations never count as fresh 0252 draws. Ideate stays deferred; minimal
solo first, residual pair only when earned; no global optimum/bare-superiority claim.
