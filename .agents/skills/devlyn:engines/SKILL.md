---
name: devlyn:engines
description: Show and pin engine roles for the devlyn pipeline (executor / pair judge). Reads and writes machine-local .devlyn/engines.json with fail-closed validation. Use when the user asks which models are configured, wants to force a specific model for pipeline work ("수동모드", "engine 고정", "use codex to implement"), or wants to clear pins back to auto-detection.
---

Utility front-end for the role-resolution contract in `_shared/engine-preflight.md#role-resolution`. It adds no semantics of its own: everything it writes is exactly what `/devlyn:resolve` PHASE 0 reads.

<args>
$ARGUMENTS
</args>

<runtime_paths>
Resolve shared scripts from this skill's installed directory, never from the project cwd, before step 2 below:

```bash
DEVLYN_SKILL_DIR="${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}"
if [ "$DEVLYN_SKILL_DIR" = "__DEVLYN_SKILL_DIR__" ] || [ ! -d "$DEVLYN_SKILL_DIR/../_shared" ]; then
  echo "BLOCKED:shared-dir-unresolved: $DEVLYN_SKILL_DIR/../_shared" >&2
  exit 1
fi
DEVLYN_SHARED_DIR="$(cd "$DEVLYN_SKILL_DIR/../_shared" && pwd)"
```
</runtime_paths>

## No args — status + how to choose

1. Run `python3 "$DEVLYN_SHARED_DIR/role-config.py" --workdir "$PWD" --default-engine <orchestrator-supported-default>` and print each resolved role's engine, requested model/effort, source and channel. Null model/effort means inherited/unresolved, not an attested identity. Show unavailable pins and requested priority even when no OTHER is available; status does not authorize dispatch. A current run can instead be inspected with `--state .devlyn/pipeline.state.json`; do not reread config as though it changed the active run. Show returned observations with their evidence basis; effective effort remains unknown when only argv is bound.
2. Run `bash "$DEVLYN_SHARED_DIR/engine-doctor.sh"` and show its availability/eligibility table. This does not prove authentication or model fitness.
3. Show the subcommands below. Status never launches a model.

## Subcommands

- `executor <name>` — pin the legacy executor; optional worker/primary profiles take their documented precedence. PLAN is orchestrator-fixed and never follows the pin. Refuse names with no `_shared/adapters/<name>.md`, or whose adapter's `## Role eligibility` section declares `executor: no` (judge-only backends), listing the valid names either way. If the engine's CLI is not currently available, still write the pin but warn: pins are promises — the run will stop with `BLOCKED:<name>-unavailable` until it is installed.
- `pair <name>[,<name>...]` — set `pair_judge_priority` (ordered; first adapter-valid, pair-judge-eligible, non-primary, available entry wins at VERIFY/risk-probe time). Refuse names with no `_shared/adapters/<name>.md`, or whose adapter declares `pair_judge: no`.
- `role <worker|primary_judge|pair_judge> <JSON object>` — write one atomic role entry, e.g. `{"engine":"codex","model":"gpt-6-astra","effort":"high"}`. Invoke `python3 "$DEVLYN_SHARED_DIR/role-config.py" --workdir "$PWD" --default-engine <orchestrator-supported-default> --set-role <role> --value '<JSON object>'` using structured argv, never shell interpolation of user text. Unknown fields/types and ineligible roles fail without changing prior bytes.
- `role <name> clear` — same command with `--value clear` removes only that override.
- `clear` — invoke the helper with `--set-role clear` to remove legacy and role pins; preserve unrelated keys and delete an empty file.

Writes preserve unrelated top-level keys already in the file; unknown fields inside roles are errors. After every change, re-print the resolved role table. Never modify anything outside `.devlyn/engines.json`, and never launch a pipeline from this skill.
