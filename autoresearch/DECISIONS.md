# DECISIONS — append-only

One line per iteration. Format: `NNNN | ACCEPT/REVERT/DEFER | one-line description | iterations/NNNN-<slug>.md`

Read top-to-bottom for the trajectory. Newest entries at the bottom — append, never reorder, never edit a past entry.

---

0001 | ACCEPT | v3.6→v3.7 skill changes (scope-first, tests-as-contract, trivial→fast routing, DOCS Job 2 verbatim-named, origin/HEAD setup); suite margin +7.3 → +10.6, 4 big wins, 2 false regressions later resolved in 0002 | iterations/0001-v3.7-skill-fix.md
0002 | ACCEPT | F6/F7 spec annotation — DOCS lifecycle status flip declared not-a-scope-violation; F6 recovered (-3 → +7); F7 invalidated by codex MCP race (separate issue, queued as iteration 0003) | iterations/0002-f6f7-spec-annotation.md
0003 | SHIPPED-INFRA / REFUTED-HYPOTHESIS | run-fixture.sh process-group watchdog (caps stalls at metadata.timeout, kills codex/codex-mcp-server descendants); F7 still hangs (empty variant transcript at T+1200s) — bounded but not fixed; refined hypothesis = pre-arm MCP reap, queued as iteration 0004 | iterations/0003-codex-mcp-timeout.md
0004 | SHIPPED-PARTIAL | outer claude -p MCP isolation (--strict-mcp-config + empty mcpServers + per-arm --debug-file). Removes user MCP from the outer subprocess, but inner `codex exec` still loads user codex config. F7 still times out — round 4 traced to inner Codex MCP race + backgrounded shell pattern. Diagnostic logging this iteration added is what made round 4 possible. Iter 0005 follows. | iterations/0004-mcp-isolation.md
0005 | PROPOSED | inner `codex exec` hermeticization via --ignore-user-config --ignore-rules --ephemeral on every skill invocation. Closes the leak iter 0004 left open. F7 prediction: variant completes within timeout, margin ≥ +5. | iterations/0005-codex-inner-isolation.md
