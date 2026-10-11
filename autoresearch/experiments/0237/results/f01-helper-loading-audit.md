# f01 fixed-B helper loading audit

Completed cell only: `f01-CF-CONFIG-codex-B-r1`. Read-only inspection of public assistant messages, tool arguments/results, installed documentation and timestamps. No active owner inspection, model calls, new tests, product changes, or cost subtraction.

**The reason for the broad implementation read is not explicitly stated in the public record.** The caller forbids Git-configuration changes ([prompt.txt:1](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f01-CF-CONFIG-codex-B-r1/prompt.txt:1)); installed documentation requires the helper for delivery after source checks, and explains the local-only invocation ([task-completion.md:47](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f01-CF-CONFIG-codex-B-r1/cell/work/.agents/skills/_shared/task-completion.md:47), [line 61](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f01-CF-CONFIG-codex-B-r1/cell/work/.agents/skills/_shared/task-completion.md:61)). The documentation promises no fetch/push on that route; it does not promise no Git-configuration mutation. Both are concrete context for inspection, but neither proves why this owner chose the broad read.

The [public message at trace line 12](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f01-CF-CONFIG-codex-B-r1/home/.codex/sessions/2026/10/10/rollout-2026-10-10T04-29-16-01a12412-8759-7c03-a15d-e2709140fe65.jsonl:12) plans caller/instruction/source reading and local delivery. Messages at lines 34 and 49 discuss the config defects and regression tests. None declares a helper failure, missing invocation contract, or reason for implementation inspection. The [actual query at line 38](/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f01-CF-CONFIG-codex-B-r1/home/.codex/sessions/2026/10/10/rollout-2026-10-10T04-29-16-01a12412-8759-7c03-a15d-e2709140fe65.jsonl:38) is:

```sh
rg --files --hidden -g '!\.git/**' -g '!visible/**' . && rg -n 'git config|config\b|local.only|local.base|mkdir|receipt|worktree' .agents/skills/_shared/task-complete.py
```

It visibly searches both configuration and invocation/allocation concepts. Calling its motive “unsupported exploration,” or asserting that the no-config restriction caused it, would go beyond these observations. There was no helper execution before it: allocation occurs at trace line 142 and completion at line 164. The earlier discovery exit 2 at line 15 only reports an absent `.claude` directory; it is not a helper failure.

| Read | Trace line | Raw command output bytes | Decoded output bytes delivered to the owner |
| --- | ---: | ---: | ---: |
| Harness artifact discovery | 15 | 194 | 194 |
| `AGENTS.md` + complete delivery reference | 25 | 18,718 | 18,718 |
| Artifact inventory + broad helper query | 38; result 40 | 43,504 | 35,551, including a truncation marker |
| Separate literal caller contract read | 16 | 1,495 | 1,495 |
| Later local-route helper sections + `.gitignore` | 83; result 87 | 13,136 | 13,136 |

“Raw command output” is UTF-8 bytes of the recorded `CommandExecution.aggregated_output`. “Delivered output” is UTF-8 bytes of the decoded command `output` string inside the native tool result, excluding JSON envelopes and other commands' outputs. The broad read produced 520 raw lines: 24 inventory lines (1,026 bytes) and 496 numbered helper matches. Its batch was truncated by the tool-output limit. These are observed text-volume counts, **not model token counts, billed costs, or estimated savings**.

Before the first task edit, the three harness-reading commands delivered 54,463 bytes; adding the separate caller read gives 55,958. The first task edit adds regression tests at trace line 51, 157.820 seconds after owner start; the first production-module patch is emitted at line 70, 200.601 seconds after start. Neither interval is attributable to helper reading. The later helper read occurs after the core patch. Both implementation-reading commands together delivered 48,687 bytes, including inventory, `.gitignore`, and truncation text.

**Implication:** this trace does not establish an unjustified helper read that a selective-loading clause would safely prevent. A clause allowing inspection for unresolved caller restrictions might allow exactly this read; its behavioral prediction remains ambiguous. The narrower observed issue is excessive search breadth: results include `remote_url`, `validate_pr`, push and PR-creation code despite a local-only task, and the output truncates before a subsequent route-focused read. Question/route-scoped retrieval has a falsifiable text-volume prediction, but this audit supplies no evidence that it preserves the same assurance or improves correctness, time, or tokens. It is not a registered or admitted candidate.

Original full costs remain unchanged: 478.96282658400014 owner seconds, 760,948 input tokens including cache, and 19,140 output tokens including reasoning. No whole-context usage is assigned as the marginal cost of these reads.
