---
name: devlyn:engines
description: Show and pin engine roles for the devlyn pipeline (executor / pair judge). Reads and writes machine-local .devlyn/engines.json with fail-closed validation. Use when the user asks which models are configured, wants to force a specific model for pipeline work ("수동모드", "engine 고정", "use codex to implement"), or wants to clear pins back to auto-detection.
---

Utility front-end for the role-resolution contract in `_shared/engine-preflight.md#role-resolution`. It adds no semantics of its own: everything it writes is exactly what `/devlyn:resolve` PHASE 0 reads.

<args>
$ARGUMENTS
</args>

## No args — status + how to choose

1. Read `cwd/.devlyn/engines.json`. Absent → report "no pins — auto-detection active".
2. List adapters: every `<name>.md` in the installed `_shared/adapters/` (skip README). Probe each with its availability check (`command -v <name>` unless the adapter declares another).
3. Print the role table so the user can decide at a glance:

```
Role          Resolved     Source          Available engines
orchestrator  (this CLI)   not configurable — switch CLIs to change
executor      claude       default         claude ✓  codex ✓
pair judge    codex        binary rule     (pin order with: pair <name>,...)
```

4. End with one usage line per subcommand below.

## Subcommands

- `executor <name>` — pin the executor (PLAN/IMPLEMENT/CLEANUP + primary VERIFY judge). Refuse names with no `_shared/adapters/<name>.md`, listing the valid names. If the engine's CLI is not currently available, still write the pin but warn: pins are promises — the run will stop with `BLOCKED:<name>-unavailable` until it is installed.
- `pair <name>[,<name>...]` — set `pair_judge_priority` (ordered; first adapter-valid, non-primary, available entry wins at VERIFY/risk-probe time). Same adapter validation.
- `clear` — remove both pins; delete `.devlyn/engines.json` when nothing else remains in it.

Writes preserve any unrecognized keys already in the file. After every change, re-print the resolved role table. Never modify anything outside `.devlyn/engines.json`, and never launch a pipeline from this skill.
