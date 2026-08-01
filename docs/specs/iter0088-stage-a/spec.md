---
complexity: trivial
---

# iter-0088 Stage A — PLAN route determinism

Registration: `autoresearch/iterations/0088-plan-route-startup-dedup.md` § STAGE A.

## Requirements

- R1: `config/skills/devlyn:resolve/SKILL.md` declares the PLAN route
  orchestrator-fixed — PLAN never inherits `--engine`, an executor pin, or
  `state.engine` — in both the engine-routing block and the PHASE 1 header.
- R2: No surface among `config/skills/devlyn:resolve/SKILL.md`, `CLAUDE.md`,
  `AGENTS.md`, `config/skills/devlyn:engines/SKILL.md` (and the `.agents`
  mirrors of the two skill files) enumerates PLAN inside an executor-role
  enumeration.
- R3: `scripts/lint-skills.sh` carries one check (6k) enforcing R1+R2; it
  fails on the pre-change bytes (red-tested against 9c5d1a1).
- R4: BUILD_GATE routing semantics are byte-preserved except for PLAN's
  removal from the shared default-engine list; `engine-preflight.md` is
  unchanged.
- Scope: exactly the five tracked surfaces above plus mirrors and the lint
  check. No H1-v3 bytes. This narrows user-visible pin semantics: an
  `executor` pin no longer governs PLAN.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "grep -Fq 'PLAN is orchestrator-fixed and never inherits `--engine`, an executor pin, or `state.engine`' 'config/skills/devlyn:resolve/SKILL.md'",
      "exit_code": 0
    },
    {
      "cmd": "bash -c '! grep -En \"([Ee]xecutor|Default engine: Claude for)[^[:cntrl:]]{0,80}PLAN[[:space:]]*/[[:space:]]*IMPLEMENT\" CLAUDE.md AGENTS.md config/skills/devlyn:resolve/SKILL.md config/skills/devlyn:engines/SKILL.md'",
      "exit_code": 0
    },
    {
      "cmd": "git diff --check",
      "exit_code": 0
    }
  ],
  "max_deps_added": 0
}
```
