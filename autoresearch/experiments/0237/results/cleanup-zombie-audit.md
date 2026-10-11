# d03 scratch-cleanup zombie audit

2026-10-10. Read-only examination of a completed owner run. No model calls,
participant mutations, frozen product/control changes or historical regrading.

## Finding

d03 completed local delivery but retained an **empty scratch directory** after
Linux process observation encountered inaccessible `/proc` entries. The run
records defunct Git children of its sole Claude owner and permission failures
when listing those zombies' file descriptors. This is an unobservability
refusal, not evidence of a live writer using task files.

The owner subsequently reconciled its committed edit to `main` and removed the
linked worktree. The worktree allocation itself followed current delivery
policy; it was not shown to result from a mistaken concurrency diagnosis.

## Exact evidence

Cell directory:

`/Users/aipalm/.local/share/nx01/0237-live/out-discovery/d03-EQ3-UA1-claude-C-r1/`

Line references are to that directory's `run/stdout` JSONL file. These are
visible commands/results and metadata, not private reasoning content.

| Lines | Recorded observation |
| --- | --- |
| 642–643 | Process table identifies PID 1 as `claude`; Git PIDs 198, 221 and 242 also exist. |
| 651–653 | `ps -o pid,ppid,stat,etime,args -p 198,221,242` reports all three with PPID 1, status `Zs`, command `[git] <defunct>`. Their cwd links produce no target. |
| 674–675 | `task-complete.py allocate ... --worktree /tmp/devlyn-wt.lv0euh/loan-desk-renewal-hold --local-base df6bc2a27160b076e1d5cff10a94ec6ca4bb13e1` succeeds after the product edit exists in the main checkout. |
| 698–699 | `complete --receipt ... --acceptance ... --writers-stopped --local-only` exits 0 and returns `delivery_status: LOCAL_ONLY`, `status: LOCAL_ONLY`, `acceptance: direct`, `workspace_cleanup: null`; scratch is `RETAINED` with reason `unknown process access; retain tree until writer cessation can be established`. |
| 705–707 | Owner explicitly diagnoses that refusal. `ls -la` shows empty scratch. A loop over `/proc/[0-9]*/fd` reports permission denial for PIDs 198, 221, 242 and 355, all with process state `Z` and command `git`. |
| 736–738 | Owner verifies the copied edit equals the committed blob, restores only that edit and fast-forwards `main` to `e4f7b37a172d16fc8a8c34e99b568e07353ae2b4`. |
| 742–743 | Custody copies match; native `git worktree remove` succeeds and the task branch is deleted using guarded `git update-ref -d`. Only `/cell/work` remains registered. |
| 812–813 | Final report truthfully distinguishes successful local delivery from retained empty scratch. |

Persisted receipt:

`cell/work/.git/devlyn-completion/fb81a78c8a00591d9f868ed4/receipt.json`

It records `allocation: owned`, `linked: true`, `local_only: true`,
`writers_released: true`, `delivery: LOCAL_ONLY`, and the same retained-scratch
reason/resume command. Its sibling `scratch/` still exists and is empty in the
preserved cell. This was checked without changing the receipt or directory.

There is **no Python traceback or failed PID/path in the helper response**.
The exact first failing `/proc` entry at completion time is therefore not
recorded. The earlier zombie states, immediate follow-up permission failures
and matching exception branch identify the concrete failure path without
claiming unavailable per-process exception telemetry.

## Code path

Both installed cell files are byte-identical to current canonical files:

- `config/skills/_shared/task-complete.py`: SHA-256
  `bf4301f4e298305d14ec162a68a36ee6430050e3a2eaf7ab55eb99b5ee49f835`.
- `config/skills/_shared/task-completion.md`: SHA-256
  `dac27a1c4434aa059282628bdd14420ebfa59b155129e318dcdedf8cd3cd44b7`.

In `task-complete.py`:

- Lines 445–449 scan every Linux process except the helper itself. The list
  expression eagerly enumerates `process / "fd"` before examining cwd.
- Lines 453–460 handle missing/exited processes, but lines 461–462 turn any
  `PermissionError` into `WritersUnobservable` with the observed reason.
- Lines 498–504 require the owner assertion, check scratch identity/mounts and
  call that observation before enumerating scratch contents. Empty scratch is
  not a shortcut around the process scan.
- Lines 620–628 retain/report scratch when cleanup fails. Lines 630–634 keep
  `LOCAL_ONLY` as the delivery outcome; this refusal does not undo the accepted
  product or local delivery.

No live process was reported as holding task files. The distinct active-writer
branch at line 458 produces a different message naming the PID.

## Bounded cost observations

Intervals below subtract JSONL event timestamps. They include CLI/tool
transport overhead; command bundles contain several operations, so they are
not isolated CPU timings for individual helper functions.

| Interval | Lines | Observed seconds |
| --- | --- | ---: |
| Allocate command bundle to its result | 674 → 675 | 0.218 |
| Complete command bundle to its result | 698 → 699 | 0.593 |
| Scratch/process diagnostic Bash bundle to its result | 706 → 707 | 0.077 |
| Completion result to diagnostic result, including the next model response | 699 → 707 | 9.030 |
| Reconciliation command bundle to its result | 736 → 738 | 0.260 |
| Worktree-removal command bundle to its result | 742 → 743 | 0.083 |

One visible follow-up Bash call (line 706) directly investigates the cleanup
refusal. Its model request, shared by the explanatory text at line 705 and the
tool call at line 706, emitted input usage of 2 uncached + 1,557 cache-created +
134,057 cache-read = **135,616 input tokens**. Deduplicating the full stream by
message id yields 2,677,123 input tokens, exactly matching the terminal result
and saved `usage.json`, so this input attribution reconciles. The per-message
stream output field is partial; do not treat its value 6 as the response's full
output count. A complete isolated output-token figure is not established here.

The whole owner run was 809.465 seconds and 82,340 output tokens. **Those totals
are not cleanup cost.** The 9.030-second interval and diagnostic request are
observed work, not a proven counterfactual saving from any proposed fix. Later
reconciliation and worktree removal are prescribed delivery work and are not
automatically attributable to the refusal.

## Scope and follow-up boundary

`task-completion.md:42–59` requires allocation after direct edits/checks and
states that every delivery allocation owns a linked worktree, including local
work. `task-complete.py:186–229` implements that allocation. Its necessity for a
simple local commit is a separate policy question; this audit neither changes
that policy nor labels the owner noncompliant for following it.

A narrowly scoped proposed fix should distinguish a **confirmed terminated
zombie** from an inaccessible live or unknown process, with PID-reuse/race
protection. It must not exempt all owner descendants, assume that the caller's
assertion proves OS state, or weaken retention for real writers. Root assigned
that design to `entry_audit` in a scratch copy only. No fix is implemented or
admitted by this report.
