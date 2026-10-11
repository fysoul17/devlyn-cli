# Confirmation source and evidence audit

Read-only inspection after f01 finalized on 2026-10-10. No evaluator rerun, model call, or verdict change. The fixed CONFIG block is incomplete (1/12); no arm comparison or admission conclusion follows.

## f01 — CF-CONFIG / Codex B / repetition 1

Original [verdict](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/verdict-f01-CF-CONFIG-codex-B-r1.json): CHECKS_PASS, COMPLETE usage, 478.96282658400014 owner seconds, 760,948 input tokens including cache, 19,140 output tokens including reasoning. [Checks](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f01-CF-CONFIG-codex-B-r1/checks.json) record 19 public tests and all 12 registered oracle rows passing, no scope violations. These costs are charged unchanged; they are not billed-token or dollar figures.

[The derived ledger](confirmation-cells.json) binds all 54 sealed inputs and 5 prepared metadata files, the checked snapshot, checks and delivery files, and the hidden oracle. All match. The visible baseline matches the selected task registration. The baseline's legacy `tasks_sha256` still labels sibling `tasks.json`; the actual confirmation task file is separately bound by `seal.inputs`.

Only `visible/beacon/{loader,manager,merge,paths}.py` changed among original files. The existing QA files are byte- and mode-identical (all mode 0644):

| Existing file | SHA-256 |
| --- | --- |
| `visible/checks/helpers.py` | `2373801c0e1de90c10489cfb0a9089c8e2e70cdf7e947245ec634370aa17f11a` |
| `visible/checks/run_checks.py` | `89da316d92c61568f7224f22774807668ea5053132a9bf22178fed0ab822d107` |
| `visible/checks/test_format.py` | `b82f886e5a8b709350d7aaa127e1b7cd8ac508c6b20c05b4701abe24e2a633ff` |
| `visible/checks/test_smoke.py` | `815d4fde5374fddf3de1a5c65e4ec1892afc657542a2e89e0eb3af9e1e5429a4` |

Added `test_loader.py`, `test_merge.py`, and `test_reload.py` contribute 14 tests. They cover diamonds/canonical aliases, independent roots, cycle/error recovery, recursive merge and input detachment, unchanged-metadata replacement, semantic generations, detached snapshots, failed deployment recovery, and first-load failure. Existing test discovery and helpers are unchanged. This audit does not claim universal correctness beyond the visible obligations and recorded checks.

The actual source addresses the visible contracts:

| Visible obligation | Evaluated source |
| --- | --- |
| Declaring-file-relative includes, canonical cycles, shared-file reads once per load, ordered diamonds, exact sorted dependencies ([format.md](../confirmation/CF-CONFIG/visible/docs/format.md:10)) | [loader.py](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f01-CF-CONFIG-codex-B-r1/snapshot/visible/beacon/loader.py:8): per-call cache and active recursion set; cached subtrees are merged in each branch position; relative parent and chain propagated; dependencies accumulated per invocation. |
| Current contents each load and recovery after failure ([reload.md](../confirmation/CF-CONFIG/visible/docs/reload.md:3)) | `Loader` no longer retains cache across calls. A failed visit discards its invocation-local state. |
| Recursive object merge, replacement of other values, no mutable input sharing ([format.md](../confirmation/CF-CONFIG/visible/docs/format.md:12)) | [merge.py](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f01-CF-CONFIG-codex-B-r1/snapshot/visible/beacon/merge.py:4): recursive object merge and deep copies. |
| Publish only a valid graph; preserve old snapshot on failure; semantic generation; detached returned state ([reload.md](../confirmation/CF-CONFIG/visible/docs/reload.md:10)) | [manager.py](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f01-CF-CONFIG-codex-B-r1/snapshot/visible/beacon/manager.py:13): load completes before state assignment, generation increments only for value changes, stored and returned values copied. |
| Useful ConfigError path/chain ([format.md](../confirmation/CF-CONFIG/visible/docs/format.md:7)) | [paths.py](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f01-CF-CONFIG-codex-B-r1/snapshot/visible/beacon/paths.py:5) adds an optional chain argument and wraps resolution errors; the existing document parser and exported API files are unchanged. |

[Delivery](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f01-CF-CONFIG-codex-B-r1/delivery.json) binds baseline `8e398a7cc8c003282a63b00fde927d86a4e5720a` to local commit `17337de911f7c182e1d1355bf7635b6dd387e1bc`, matching the evaluated source. This is local delivery, not PR/merge publication.

Actual cleanup evidence is narrower than “the helper removed the worktree.” The [owner trace at line 164](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f01-CF-CONFIG-codex-B-r1/home/.codex/sessions/2026/10/10/rollout-2026-10-10T04-29-16-01a12412-8759-7c03-a15d-e2709140fe65.jsonl:164) records helper completion exit 0, `LOCAL_ONLY`, `scratch_cleanup.status=CLEAN`, `logical_bytes_removed=0`, and `workspace_cleanup=null`; the [persisted receipt](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f01-CF-CONFIG-codex-B-r1/cell/work/.git/devlyn-completion/a22558cf1b63defcd8a52560/receipt.json) agrees. At [line 171](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f01-CF-CONFIG-codex-B-r1/home/.codex/sessions/2026/10/10/rollout-2026-10-10T04-29-16-01a12412-8759-7c03-a15d-e2709140fe65.jsonl:171), the owner verifies attributable bytes, reconciles the anchor with a fast-forward, then invokes Git worktree removal and branch deletion. [Line 174](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f01-CF-CONFIG-codex-B-r1/home/.codex/sessions/2026/10/10/rollout-2026-10-10T04-29-16-01a12412-8759-7c03-a15d-e2709140fe65.jsonl:174) records exit 0 and only `/cell/work` remaining. No prior `RETAINED`/unknown-process cleanup condition is observed in this completion. This single trace cannot establish the helper fix's causal time/token savings, and no costs are subtracted.

## f02 — not dispatched

[The guard record](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/not-dispatched-f02-CF-CONFIG-claude-C-r1.json) states the Claude login token had 6031 seconds remaining and required host-login refresh. Dispatcher START/FINISH events describe this guarded attempt, not an owner launch. There is no final verdict. The ledger marks `NOT_DISPATCHED` with null outcome and costs: neither failure nor success nor zero-cost completion. Remaining cells retain their recorded lifecycle; no missing result is treated as passing.

## f02-auth1 — CF-CONFIG / Claude C / repetition 1

Completed 2026-10-10, after the separately registered authentication recovery. Original [verdict](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/verdict-f02-CF-CONFIG-claude-C-r1-auth1.json) remains **PRODUCT_INCOMPLETE**: source checks pass, delivery fails; 2269.697521042006 owner seconds, 7,218,661 input tokens including cache, 240,858 output tokens including reasoning, COMPLETE usage. This counts as zero fully correct completions, with all cost retained. The complete CONFIG block is still required for comparison; no candidate admission or causal attribution follows from this cell.

All 54 sealed inputs and 4 prepared metadata bindings match. The checked snapshot, checks, delivery, selected visible baseline and hidden oracle match their recorded bindings. All four existing public QA files have the same bytes and modes listed for f01 above. Only `beacon/loader.py`, `manager.py`, and `merge.py` changed among original visible files; three additive test files provide 17 new tests. [Recorded checks](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f02-CF-CONFIG-claude-C-r1-auth1/checks.json) show 22 public tests and all 12 hidden rows passing, with no scope violations. No oracle was rerun or revised in this audit.

The evaluated source uses a per-call resolved-subtree map and active stack for canonical include traversal, wraps path resolution failures in ConfigError, merges recursively with copied values, and publishes detached snapshots after a successful load with generation based on effective values. The original parser/API files and test runner are unchanged. These observations support the recorded bounded source-check result; they do not assert correctness for every possible input.

[Delivery evidence](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f02-CF-CONFIG-claude-C-r1-auth1/delivery.json) selects the changed anchor and records the same baseline and final HEAD, `e594b5f668f86b217ceed2cf5c523a21b59fe183`: required edits exist only outside a post-baseline commit. No allocation, helper completion, or `git commit` invocation appears in the parent tool calls. The [parent's status command at stdout line 1395](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f02-CF-CONFIG-claude-C-r1-auth1/run/stdout:1395) confirms three modified modules, three untracked test files, and that baseline HEAD.

The native lifecycle explains the unfinished delivery. **This finding is limited to the measured noninteractive `claude -p` invocation**, recorded in [run/result.json](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f02-CF-CONFIG-claude-C-r1-auth1/run/result.json); it is not a claim about general interactive Claude background-agent behavior.

| Evidence | Observed event |
| --- | --- |
| [stdout:1189](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f02-CF-CONFIG-claude-C-r1-auth1/run/stdout:1189), 07:36:37.499Z | Parent launches an independent, read-only contract reviewer with `run_in_background=true`. |
| [stdout:1192](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f02-CF-CONFIG-claude-C-r1-auth1/run/stdout:1192) | Native launch metadata promises automatic completion notification and permits the parent to continue other work or respond meanwhile. This matters: the record does not support saying the parent ignored a completed review or knowingly abandoned it. |
| [stdout:1408](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f02-CF-CONFIG-claude-C-r1-auth1/run/stdout:1408), 07:39:38.502Z | Parent returns the waiting message preserved in `final.txt`: local checks pass, but it will allocate and commit after review. No parent wait/stop/message tool calls follow. |
| [stdout:1470](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f02-CF-CONFIG-claude-C-r1-auth1/run/stdout:1470) | Reviewer is still working, with 38 recorded tool uses; no review verdict/final text has returned. |
| [stdout:1472](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f02-CF-CONFIG-claude-C-r1-auth1/run/stdout:1472), 07:49:38.636Z | Native system marks the reviewer killed, approximately 600.134 seconds after the parent's final message. Subsequent notification says stopped. |
| [stdout:1475](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f02-CF-CONFIG-claude-C-r1-auth1/run/stdout:1475) | Native result reports `subtype=success`, `is_error=false`, `stop_reason=end_turn`, `terminal_reason=completed`; subagent statistics show one spawned, zero completed, one killed by the system. These native success fields do not mean the requested local delivery completed. |

[Native stderr](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f02-CF-CONFIG-claude-C-r1-auth1/run/stderr:1) explicitly identifies the print-mode background wait ceiling. The [official Claude Code environment-variable reference](https://code.claude.com/docs/en/env-vars) documents `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` with a default of 600,000 ms: the idle timer resets when a background result is handled, a running main-conversation background command keeps the session open, and zero waits indefinitely. The recorded launch does not override this variable.

This is an observed boundary of hands-free completion under the current native settings: the owner made delivery depend on a background review, returned while waiting, and the native session ceiling stopped the unfinished dependency. The experiment runner records `EXITED_0`, clean teardown, matching model identity, no authentication/quota faults and complete usage. The 2269.7-second run did not reach the experiment's 5400-second owner watchdog. There is no evidence here of a custom runner interruption or hidden oracle fault that would warrant regrading or retrying the cell. The default environment stays unchanged; this is a distinct future protocol concern, not an established effect of the candidate caller-discovery clause.

Accounting includes the unfinished reviewer: aggregate native `modelUsage` matches 7,218,661 input and 240,858 output, while the final result's parent `usage` alone is smaller. The difference is 1,379,200 input and 72,272 output. The ledger uses the complete aggregate; no child cost, waiting time, or delivery preparation is deducted. The original never-dispatched f02 guard remains null-cost evidence linked to this new identity through the registered recovery map.
