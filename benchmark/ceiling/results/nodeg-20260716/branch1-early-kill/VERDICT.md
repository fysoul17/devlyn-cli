# nodeg-20260716 — KILLED by iter-0072 branch-1 early gate (2026-07-16)

Cohort initialized at runner commit `03c3e4b` (Amendment 1 lever landed), CLI pin
`CEILING_TEST_CLAUDE_BIN=~/.local/share/claude/versions/2.1.211`. Row F7
(`DR-byte-preservation-f7-out-of-scope-trap`, first in CONTROL_ORDER) reached PLAN;
the regenerated artifacts decided falsifier-ladder branch 1 before any judge wall
was spent, and the run was killed per the Amendment-1 gate protocol. No row
completed; this run-id is DEAD — never resume it.

## Branch-1 predictions vs regenerated artifacts (amendment loaded — workspace
`.claude/skills/devlyn:resolve/references/free-form-mode.md` carries the new
quality-bar line; `pipeline.state.json` `complexity: medium` as expected)

| Prediction (must hold to pass) | Observed | Verdict |
|---|---|---|
| criteria/PLAN include the USAGE update | criteria.generated.md `## Out of Scope`: "Any other subcommand (`hello`, `--help`)"; plan.md Risks: "do not update `USAGE` to mention `--format` — that's unrequested scope expansion … even though it would look 'more complete'" | FAIL |
| criteria/PLAN include the unsupported-format error-path test | plan.md Risks: "do not add an exit-1/`--format yaml` test to `tests/cli.test.js`, since that isn't requested" | FAIL |

**Lever wording FALSIFIED (valid-negative). STOP per ladder branch 1; Stage 2 stays
locked; fresh pre-registration required.**

Key diagnostic: the refusals quote the always-loaded anti-drift vocabulary
("unrequested scope expansion", "subtractive-first / no-overengineering") — the
narrowing agent obeys the always-loaded field over a same-file reference rule.
The reverted lever line and full receipts live in
`autoresearch/iterations/0072-changed-surface-closure.md` (Amendment 1 + Branch-1
record) and DECISIONS 0072.1/0072.2.
