# DECISIONS — append-only

One line per iteration. Format: `NNNN | ACCEPT/REVERT/DEFER | one-line description | iterations/NNNN-<slug>.md`

Read top-to-bottom for the trajectory. Newest entries at the bottom — append, never reorder, never edit a past entry.

---

0001 | ACCEPT | v3.6→v3.7 skill changes (scope-first, tests-as-contract, trivial→fast routing, DOCS Job 2 verbatim-named, origin/HEAD setup); suite margin +7.3 → +10.6, 4 big wins, 2 false regressions later resolved in 0002 | iterations/0001-v3.7-skill-fix.md
0002 | ACCEPT | F6/F7 spec annotation — DOCS lifecycle status flip declared not-a-scope-violation; F6 recovered (-3 → +7); F7 invalidated by codex MCP race (separate issue, queued as iteration 0003) | iterations/0002-f6f7-spec-annotation.md
