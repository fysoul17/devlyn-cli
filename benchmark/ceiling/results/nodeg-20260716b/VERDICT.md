# nodeg-20260716b — KILLED by Registration-v2 artifact gate (2026-07-16)

Cohort at runner `e74f00c` (v2 carve landed), CLI pin 2.1.211. Row F7 reached PLAN;
artifact gate decided before any judge wall; run killed (row exit=143 SIGTERM); run-id DEAD.

Carve LOAD VERIFIED in the workspace before judging: `CLAUDE.md`,
`.claude/skills/_shared/runtime-principles.md`, `AGENTS.md` all carry
"the named change also requests …" (grep = 1 each).

| v2 prediction | Observed (gate-fail-artifacts/) | Verdict |
|---|---|---|
| criteria do NOT freeze `--help`/USAGE | Constraints: "…`parseNameFlag`, `USAGE`, formatting/whitespace elsewhere — must remain byte-for-byte as-is"; Out of Scope: "(`hello`, `--help`/`-h`, top-level usage text)" | FAIL |
| criteria carry the error-path test | only "at least one new test … covering the `--format json` path" | FAIL |
| plan includes both carriers as work items | Risks: USAGE in refuse-list; "do not add extra tests beyond the one required for the json path; **that would be unrequested work**" | FAIL |

**Registration v2 FALSIFIED (second valid-negative of 2026-07-16). All surfaces
reverted per the frozen gate; no D2/D3 rescue; STOP.**

Diagnostic: with the carve loaded at BOTH the always-loaded field and the sub-agent
mirror, PHASE-0 criteria synthesis still classified USAGE as "unrelated" (expanding
the task's own byte-preservation sentence into an enumerated freeze list) and PLAN
still used "unrequested work" framing against the carve's explicit definition.
Two authority tiers of prose are now falsified on the same behavior. The surviving
causal observation: bare-B reads the RAW task text and closes the surface; A's
PLAN/IMPLEMENT read a criteria TRANSFORMATION in which the narrowing has already
happened — the information bottleneck is upstream of every prose lever tried.
