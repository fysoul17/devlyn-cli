# f02: child review lifetime and the instructions actually read

Read-only audit, 2026-10-10. Scope: finished `f02-CF-CONFIG-claude-C-r1-auth1`, current installed product wording, retained 0232/0235 registrations, and official Claude documentation. No model call, new measurement, regrade, or product change. No active confirmation cell inspected.

**Finding:** f02 received the explicit obligation to wait for its children. The observed failure is not explained by missing that paragraph or truncating its read. The direct completion guide does not explain how a completion-dependent native child must be awaited within a headless owner's lifetime. That narrower execution-contract hypothesis differs from 0235's rejected generic definition-of-done sentence; it is not an established fix.

## Actual instructions and observed execution

Raw root: `/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f02-CF-CONFIG-claude-C-r1-auth1`. Line references below are to its `run/stdout` JSONL.

| Evidence | Observation |
| --- | --- |
| Lines 10–11, 07:11:54.920–.978Z | Owner runs `cat .claude/skills/_shared/task-completion.md` and `cat .claude/skills/_shared/runtime-principles.md`. The complete 17,853-character combined tool output contains both guides. This is not a first-60-lines read. |
| Installed `task-completion.md:3–9` | Completion belongs to the outer owner; finish the whole request; internal subtasks, messages and conversation end are not delivery boundaries. |
| Installed guide `:97–100`, `:112–114`, `:170–172` | Review/verify the candidate; wait for task writers before scratch cleanup; explicitly: “Wait for your children, stop your dev servers and task writers, then leave the task tree.” The last instruction introduces the completion-helper call and writer attestation. |
| Line 1189, 07:36:37.499Z | Owner calls native `Agent`, `subagent_type: general-purpose`, **`run_in_background: true`**, for an independent read-only contract review. This was an owner-selected review, not a separate peer CLI. |
| Line 1192 | Native launch result says a completion notification will arrive later and permits continuing other work or responding meanwhile. It forbids reporting unknown review results. |
| Line 1408, 07:39:38.502Z | Owner's final response says its implementation passes checks but it is waiting for the independent review before allocating the delivery worktree and committing, and will pick up when the review reports. Thus this child's result is explicitly on the owner's completion path. |
| Lines 1456–1471 | Reviewer continues producing progress and executing tools after that owner response. |
| Lines 1472–1475 | Reviewer is system-killed at **07:49:38.636Z**, **600.134 seconds after** the owner's response and 781.137 seconds after launch. Native final result is `success`, `is_error: false`, `terminal_reason: completed`, but child statistics report background requested/started 1, foreground 0, completed 0, system-killed 1. |

The installed completion guide is byte-identical to current `config/skills/_shared/task-completion.md` (SHA-256 `6466c18211c9bcea62dc3f72f2c4e2c745f86ce6eb08a12e1146dc4e9a0c4733`); installed runtime principles are also byte-identical to current canonical. The transcript proves the text was returned to the owner, not that it retained or correctly applied every sentence much later.

The finalized sibling `verdict-f02-CF-CONFIG-claude-C-r1-auth1.json` records all 12 oracle rows and public checks passing, `PRODUCT_INCOMPLETE`, and delivery failure because required edits exist only outside a post-baseline commit. Identity matches, usage is COMPLETE, owner is `EXITED_0`, and teardown is CLEAN. The apparatus waits for process exit (0233 `cell.py:162–169`); it did not classify this as its 5,400-second hang watchdog. Do not describe the child as killed immediately upon the owner's final response. **`run/stderr:1` identifies the cause explicitly:** background tasks were still running ten minutes after the last turn, so Claude stopped them; the message names `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`. This matches the earlier retained finding in `confirmation-source-audit.md` under f02-auth1. The initial version of this audit overlooked stderr and incorrectly left the timer unidentified; this paragraph corrects that omission.

## What the product already says

Scoped searches of `config/skills/_shared` and `config/skills/devlyn-ideate` find the generic child/writer wait above, plus a more specific instruction in **`config/skills/devlyn-ideate/SKILL.md:120`**: keep the turn alive until drain exits, use foreground or await background completion, and account for headless lifetime. This instruction governs a drain process. No owner tool invocation in f02 reads that skill or its loop reference; this was direct work. Its presence in a skill catalog does not prove its body was loaded.

The direct completion guide has no corresponding native `Agent` foreground/awaited-call instruction. Its existing child wait is presented at the delivery/cleanup boundary. The helper's writer attestation is not an enforced scheduler for review completion, and f02 never reached delivery. Repeating only “finish/wait before done” would substantially repeat an obligation already read.

## Official native semantics, checked 2026-10-10

Claude documents that foreground subagents block the main conversation until completion, while background results arrive through a later notification. Fork mode defaults off for `-p`; in that mode foreground is available when the result is needed before continuing. Interactive fork mode has different behavior, so this cannot become an unconditional statement about every Claude session. [Claude Code subagent execution](https://code.claude.com/docs/en/sub-agents#run-subagents-in-foreground-or-background)

The SDK documentation makes the native input explicit: omitting `run_in_background` defaults to background; `run_in_background: false` requests foreground when the result is needed. [AgentDefinition and execution semantics](https://code.claude.com/docs/en/agent-sdk/subagents#agentdefinition-configuration)

f02 used Claude Code 2.1.296 under `claude -p`. Its plan records no fork/background override. The explicit `true` request and native background statistics independently establish what actually happened. No foreground counterfactual was run. The advertised startup tool catalog lacks `TaskOutput`, so this audit does not prescribe an assumed wait tool. Official documentation defines `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` as the post-final-turn idle ceiling for background work in `-p`, defaulting to 600,000 ms. It restarts when the owner takes another turn to handle a background result. This is distinct from `CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS`: f02's stderr identifies the post-final-turn ceiling, while the reviewer continued progressing before termination. No timeout setting was changed in this audit. [Native timeout variables](https://code.claude.com/docs/en/env-vars)

## Comparison with prior work and the remaining hypothesis

0235 appended a general demand to verify requested behavior, failure behavior and compatibility before removal (`autoresearch/iterations/0235-definition-of-done.md:18–20`). It was rejected at `:82`: 2/4 completions for each arm and two false completions in the candidate. That result does not test native child scheduling, but it argues against reopening generic completion prose as though untested.

This failure class is also **not new to the project**: `autoresearch/iterations/0232-harness-ladder.md:276–279` records a background review lost after the owner promised to return; `:396–399` explicitly preserves that failure as possible evidence for a later challenger. Those historical CLI details must not replace f02's actual ten-minute post-response trace.

A distinct, evidence-backed hypothesis remains: for an owner-chosen child whose answer is required to complete the current request, express the dependency in the native execution mode (foreground where supported, otherwise an actual supported await that keeps the owner alive) and consume its terminal result before ending. This concerns the existing solo executor's native delegation, not mandatory pair activation or requiring every child to be foreground. It connects **Production ready** (explicit failure/lifetime behavior), **No workaround** (no global background-disable bypass), and **No overengineering** (no new orchestration framework).

This audit cannot show that a sentence changes model behavior, reduces cost, completes the review, or yields a shippable result. It also cannot attribute f02's launch decision to candidate C. A later prospective test would need actual launch mode, child terminal outcome, parent continuation, delivery and whole-run usage; source-check success alone would miss this failure again.
