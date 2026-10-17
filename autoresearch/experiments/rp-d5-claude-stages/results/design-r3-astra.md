The round-2 findings are resolved, and replacing automatic nomination with a descriptive repeats table is sound (**No overengineering**). No HIGH findings remain. Two MEDIUM attribution ambiguities should be fixed before freezing the implementation.

1. **MEDIUM — Reads in the first-write row have no defined classification.**  
   [DESIGN.md:149](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/DESIGN.md:149) tests `look-before-first-write` and `look-after-first-write`, but defines the first write as a **row**. For a first-write response containing both `Read` and `Edit`, the read is neither before nor after that row. The implementation must invent an equality rule, potentially classifying combined exploration/editing as pure Edit.

   **Fix:** detect Mixed using the base `look` predicate alongside write/check/deliver/orient; apply the Explore/Verify boundary afterward to look-only rows. Freeze fixtures for Read+Edit and `cat x && sed -i ... x` (**No guesswork**).

2. **MEDIUM — Repeat occurrences lack an operation-level token counter.**  
   [DESIGN.md:166](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/DESIGN.md:166) requests occurrences’ marginal tokens, while accounting supplies one usage vector per message. A message can contain several tool calls. Assigning its full tokens to each operation produces overlapping costs; splitting them invents an allocation.

   **Fix:** report occurrence row IDs and explicitly label the displayed tokens as **enclosing-row, shared, non-additive**, or omit tokens from the repeats table. Keep exclusive row accounting for stage totals (**No guesswork**).

Each round-2 finding was checked:

| Round-2 finding | Resolution |
|---|---|
| Astra HIGH: heredoc writes and shell-read classification | Resolved: executable payload retained, execution distinguished from filename mentions, instruction reads recognized. |
| Astra MEDIUM: operation equivalence and unsupported redundancy claims | Resolved: full arguments/content/cwd identify operations; necessity and provenance claims removed. |
| Grok HIGH: underdetermined nomination, exemptions and ranking | Resolved by deleting nomination entirely. Descriptive repetition needs no proof of unchanged dependencies. |
| Grok MEDIUM: pathless searches and false write matches | Resolved explicitly, with required pre-run fixtures. |

The question and scope are appropriate. Existing receipts already establish the thinking/cache composition; they cannot recover operation identity or the max/high comparison. Four Claude-only slots are a reasonable minimum diagnostic. Effort is the relevant second factor, and Codex slots would not answer this narrowed question. The design correctly avoids claiming it explains the entire cross-engine gap or estimates a stable effort effect.

The cited numbers check out: retained receipt sums reproduce **23/28 turns and every token counter**; rp-d4 summaries and rp-d1 costs/effort pins match. [0254/audit.py:245](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/0254/audit.py:245) supports authoritative rows, effort checks and child reconciliation; [0251/cell.py:52](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/0251/cell.py:52) supports monotonic slot wall; [0234/diagnostics.py:108](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/0234/diagnostics.py:108) supports tool-result joins and exit scraping. Removing stage-wall attribution avoids relying on unvalidated timestamp semantics. Separate candidate evaluation preserves the [owner ladder rule](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/NORTH-STAR.md:68).

No files changed or live experiments ran.

VERDICT: REVISE
