# 0222 route smoke

Six cells on the trivial SMOKE task ([cells](smoke/cells.tsv)), one per route that has never run in this container. They run only after every model-free check passes. A failed row is fixed in the apparatus before any registration, never mid-screen.

## Predictions (written before dispatch)

1. Every cell: teardown CLEAN, no stop, identity MATCH, SMOKE oracle and public check pass. Usage COMPLETE, except where a nested judge's usage is structurally unavailable; that is recorded as PARTIAL, never 0.
2. smoke-A-claude: result.modelUsage contains claude-opus-5-5. The one requested native subagent's usage appears either in result.modelUsage or only in its transcript. The result and transcript sums for claude-opus-5-5 output agree within 5% if the subagent is included.
3. smoke-A-codex: the owner session is gpt-6-astra, one native child session is gpt-6-sol, no model_reroute.
4. smoke-C-claude: at least one review call; reviewer identity gpt-6-astra MATCH with usage recorded. smoke-C-codex: at least one review call; reviewer claude-opus-5-5 MATCH with usage recorded.
5. smoke-F-claude and smoke-F-codex: 3.2.1 resolve runs PLAN through VERIFY and archives. A pair-judge run appears (a Codex gpt-6-astra session for the Claude config; a Claude claude-opus-5-5 CLI run for the Codex config) and its usage is recorded, or explicitly UNKNOWN when the judge persists nothing. The F-codex worker sessions are gpt-6-sol and the judge sessions gpt-6-astra.
6. Wall time: each A/C cell under 15 minutes, each F cell under 60 minutes.

## Results (2026-09-25, image 84a01941, apparatus 447a1e3 then 89ec8624)

| Cell | Owner | Seconds | Teardown | Identity | Usage | Checks | Assessors (claude / codex) | Status |
|---|---|---:|---|---|---|---|---|---|
| smoke-A-claude | EXITED_0 | 34 | CLEAN | MATCH | COMPLETE | pass | complete / not complete | PRODUCT_INCOMPLETE |
| smoke-A-codex | EXITED_0 | 44 | CLEAN | MATCH | COMPLETE | pass | not / not | PRODUCT_INCOMPLETE |
| smoke-C-claude | EXITED_0 | 40 | CLEAN | MATCH | COMPLETE | pass | not / not | PRODUCT_INCOMPLETE |
| smoke-C-codex | EXITED_0 | 60 | CLEAN | MATCH | COMPLETE | pass | not / not | PRODUCT_INCOMPLETE |
| smoke-F-claude (run 1, kept as `.stop-1`) | EXITED_0 | 560 | CLEAN | MISMATCH | PARTIAL | — | — | STOP |
| smoke-F-claude | EXITED_0 | 340 | CLEAN | MATCH | PARTIAL | pass | not / not | PRODUCT_INCOMPLETE |
| smoke-F-codex | EXITED_0 | 403 | CLEAN | MATCH | PARTIAL | pass | not / not | PRODUCT_INCOMPLETE |

Against the predictions:

1. **Partly falsified, then fixed.** Run 1 stopped smoke-F-claude with an identity MISMATCH. 3.2.1 records `model_effective` as `claude-opus-5-5[1m]`, and the apparatus normalized that context suffix for transcripts but not for pipeline fields. In the same cell, the owner had to rebuild a missing Codex `models_cache.json` (which 3.2.1 role-config reads to validate the pinned Codex judge) with `codex debug models`, and the product ended `BLOCKED:implement-empty` after a pair-judge finding. Both apparatus causes were fixed (89ec8624: suffix normalization; the host cache is seeded into every cell home). The stopped row is kept, and the F cells were re-run.
   - After the fix, every cell met the prediction: clean teardown, no stop, identity MATCH, the SMOKE oracle and public check pass, usage COMPLETE for A/C and PARTIAL for F.
   - F's gap is structural: 3.2.1's isolated Codex judges run `--ephemeral` and print plain text, so their usage is UNKNOWN.
   - 11 of 12 assessments returned `complete: false`, so all six cells are PRODUCT_INCOMPLETE. The only `true` was smoke-A-claude's Claude assessor, and that disagreement is recorded. The cause is that the SMOKE request carries a process instruction ("delegate to exactly one native subagent") that no product evidence can show, and the assessors flagged it as unverifiable rather than inventing a pass. This is a property of the smoke task only; measurement requests contain product requirements.
2. **Model named, tolerance missed.** A native subagent ran (Agent tool, with its own transcript). `result.modelUsage` for claude-opus-5-5 shows 2,282 output tokens, while the owner-only top-level `usage` shows 1,378, so modelUsage includes the subagent. Transcripts sum to 2,058 output (input and cache are identical), 9.8% below modelUsage, which misses the predicted 5% agreement. **Decision, per execution:** the owner's `result.modelUsage` covers the owner and its native subagents. Each separate `claude -p` run (3.2.1's Claude judge, SURFACE_CLOSE) archives its own JSON result, and those are summed as `claude_nested`, deduplicated by session. Transcripts are only a cross-check. The smoke `usage.json` files were re-recorded with this rule from the unchanged raw evidence.
3. **Held.** The owner session ran gpt-6-astra and one native child ran gpt-6-sol, with no reroute.
4. **Held.** smoke-C-claude made one review call on gpt-6-astra (MATCH, usage recorded). smoke-C-codex made one review call on claude-opus-5-5 (MATCH, usage recorded).
5. **Held on the re-run.** Both F cells ran PLAN, IMPLEMENT, BUILD_GATE, CLEANUP, SURFACE_CLOSE and VERIFY, reached PASS and archived. The pair judge ran in both, with `claude-judge.*`, `codex-judge.*` and `pair-judge.summary.json` archived. The frozen roles equal the registration. F-codex implemented on gpt-6-sol (worker session bound to its rollout), judged on gpt-6-astra, and ran the claude-opus-5-5 pair judge, whose archived result shows 261 output tokens; SURFACE_CLOSE's shows 362, and the transcripts' 623 is their sum. F-claude's Codex pair judge ran with usage UNKNOWN, as predicted.
6. **Held.** A/C cells took 34–60 s; F cells took 340–560 s.

No container survived, no credential copy remained, and no credential bytes are in the evidence tree. The only token-like strings are inside a Codex plugin cache's source files.
