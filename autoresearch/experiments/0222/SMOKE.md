# 0222 route smoke

Six cells on the trivial SMOKE task ([cells](smoke/cells.tsv)), one per route that has never run in this container. They run only after every model-free check passes. A failed row is fixed in the apparatus before any registration, never mid-screen.

## Predictions (written before dispatch)

1. Every cell: teardown CLEAN, no stop, identity MATCH, SMOKE oracle and public check pass. Usage COMPLETE, except where a nested judge's usage is structurally unavailable; that is recorded as PARTIAL, never 0.
2. smoke-A-claude: result.modelUsage contains claude-opus-5-5. The one requested native subagent's usage appears either in result.modelUsage or only in its transcript. The result and transcript sums for claude-opus-5-5 output agree within 5% if the subagent is included.
3. smoke-A-codex: the owner session is gpt-6-astra, one native child session is gpt-6-sol, no model_reroute.
4. smoke-C-claude: at least one review call; reviewer identity gpt-6-astra MATCH with usage recorded. smoke-C-codex: at least one review call; reviewer claude-opus-5-5 MATCH with usage recorded.
5. smoke-F-claude and smoke-F-codex: 3.2.1 resolve runs PLAN through VERIFY and archives. A pair-judge run appears (a Codex gpt-6-astra session for the Claude config; a Claude claude-opus-5-5 CLI run for the Codex config) and its usage is recorded, or explicitly UNKNOWN when the judge persists nothing. The F-codex worker sessions are gpt-6-sol and the judge sessions gpt-6-astra.
6. Wall time: each A/C cell under 15 minutes, each F cell under 60 minutes.

## Results

Pending.
