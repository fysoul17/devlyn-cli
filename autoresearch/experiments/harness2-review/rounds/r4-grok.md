I'll review the round-4 docs diff against the round-3 findings and the cited sources, without editing anything.Round-3 findings are loaded. Next I’ll check the current playbook and README against 0232, NORTH-STAR, 0233, and the harness2 sources.Round-3 fixes hold except the residuals below. The veto is gone: a substantiated blocker is fixed, never outvoted, and root decides the freeze (`iteration-loop.md:54-57`; `NORTH-STAR.md:95`, `:98`). Harness² machinery “has not demonstrated admission,” with costs counted per correctly completed task (`harness2-review/README.md:24-26`; `0232:144-153`). The 0234 clause is only the pair result: no completion gain at about 2.3–3.5× development input (`0234:97-102`). “Installation-validation failure” matches the Codex tree that had `AGENTS.md` while the check required `CLAUDE.md` (`iteration-loop.md:61`; amendment 1 `:28-46`). The loose keep rule, efficiency axis, and general 30% gate are gone (`iteration-loop.md:7-10`; `0232:152-159`). The helper-script clause is gone. `KEEP_BASE` is `prompts.py:333-335`; the pool exclusion is `selection.py:93-105`. E1/E2 are the reported one-replicate easy panel (`0233:96`, `:146`), not an outside-sums panel (`:116`).

The README loop box matches the playbook: design; review, qualify, register, and run; raw numbers, the frozen decision, and a per-component verdict; then one `DECISIONS.md` line and a `HANDOFF.md` update (`README.md:27-37`, layout `:95`; `iteration-loop.md:49-68`).

**MEDIUM** `playbooks/iteration-loop.md:7`. §6 requires each task’s completion count and each check/oracle-row pass count to be no lower (`0232:150`). “No lower completion or check counts” still lets a cross-task trade, or an oracle-row drop with checks held, meet the playbook and fail §6.

**LOW** `iteration-loop.md:5`. §2 licenses one `intent` mechanism (`0232:35`), not any mechanism.

**LOW** `experiments/harness2-review/README.md:17`. The ledger identity is 4k rollouts; retries are separate invocations (`ledger.py:16-18`). Selection and reflection sitting outside the count is right.

REVISE
