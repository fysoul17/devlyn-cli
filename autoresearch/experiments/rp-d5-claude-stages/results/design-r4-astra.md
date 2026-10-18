One **MEDIUM** attribution issue remains. No HIGH findings.

**MEDIUM — The shell parsing rules mishandle ordinary reads.** [DESIGN.md:120](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/DESIGN.md:120) specifies splitting shell separators before applying `shlex`. Applying that order to:

```sh
rg -n "def complete|merge_refused" .agents/skills/_shared/task-complete.py
```

produces two fragments, both failing with `No closing quotation`. This exact inspection command already appears in the [rp-d4 apparatus review](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d4-helper-report/results/apparatus-r2-astra.md:5).

The [path-extraction rule](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/DESIGN.md:131) also treats ordinary non-path operands as paths:

| Instruction-file read | Incorrect “path” |
|---|---|
| `sed -n '1,40p' CLAUDE.md` | `1,40p` |
| `head -n 40 CLAUDE.md` | `40` |
| `rg -e COMPLETE CLAUDE.md` | `COMPLETE` |

These become Other instead of Orient. The `sed` form was observed in an earlier smoke, documented in [0234/diagnostics.py:45](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/0234/diagnostics.py:45). This affects the stage breakdown being measured.

**Fix:** recognize separators only outside quotes/escapes; distinguish supported commands’ expressions and option operands from file paths. Freeze expected classifications for these examples. Unsupported syntax can remain Other; no general shell interpreter is needed (**No guesswork**, **No overengineering**).

Round-3 findings checked individually:

| Finding | Round-4 status |
|---|---|
| Astra: reads within the first-write row | Resolved: base `look` participates in Mixed before the boundary rule. |
| Astra: operation-level token allocation | Resolved: enclosing-row tokens are explicitly shared and non-additive. |
| Grok: unpinned write detection | Resolved: pipeline/full views, write patterns, exclusions, mutation uncertainty and fixtures are specified. |
| Grok: shell-read path extraction | Requested rule added, but the defect above remains. |
| Grok: invented cwd in repeat identity | Resolved: tool name plus canonical input only. |

The question and scope are otherwise appropriate. Existing receipts establish the thinking/cache composition but lack operation content and the max/high comparison. Four Claude-only slots are a reasonable minimum diagnostic for both tasks. Effort is the relevant second factor; Codex slots would broaden the question without resolving Claude attribution. The design appropriately limits conclusions to these observations.

Accounting is implementable: `0254/audit.py` supplies terminal-response identity, effort verification, cache counters, thinking within output, and foreground-child reconciliation; `0251/cell.py` supplies monotonic slot wall; `0234/diagnostics.py` supports tool-result joins. Removing stage-wall attribution avoids unvalidated timestamp semantics. Independent receipt sums reproduce every guard-table counter, including **23/28 turns**; the rp-d4 summary and rp-d1 costs/effort pins also match.

The removal-candidate problem is resolved by deleting nomination. Exact repeats remain descriptive, and future adoption must satisfy the [owner ladder rule](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/NORTH-STAR.md:68), including failed attempts’ costs. No other material interpretability issue found.

No files changed or live experiments ran.

VERDICT: REVISE
