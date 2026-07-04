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

1. Read `cwd/.devlyn/engines.json`. Absent → report "no pins — auto-detection active".
2. Run `bash "$DEVLYN_SHARED_DIR/engine-doctor.sh"` — read-only; never installs anything or writes `.devlyn/engines.json`. It detects, per target (`claude`, `codex`, `omp`, `pi`, `ollama`, `vllm`), whether its binary/server is present, whether `_shared/adapters/<name>.md` exists, and whether that makes it `pin_eligible` today. Its trailing line is either a pair-judge-diversity confirmation or a recommendation to add a second adapter-valid engine (`autoresearch/iterations/0045-model-arm-drift.md`: different model tiers hit different failure-mode blind spots, so VERIFY pair-judge/risk-probes need ≥2 to ever fire).
3. Print the role table, sourcing "Available engines" from the script's `pin_eligible` rows:

```
Role          Resolved     Source          Available engines
orchestrator  (this CLI)   not configurable — switch CLIs to change
executor      claude       default         claude ✓  codex ✓
pair judge    codex        binary rule     (pin order with: pair <name>,...)
```

4. Show the script's full detection table plus its diversity/recommendation line beneath the role table.
5. End with one usage line per subcommand below.

## Subcommands

- `executor <name>` — pin the executor (PLAN/IMPLEMENT/CLEANUP + primary VERIFY judge). Refuse names with no `_shared/adapters/<name>.md`, listing the valid names. If the engine's CLI is not currently available, still write the pin but warn: pins are promises — the run will stop with `BLOCKED:<name>-unavailable` until it is installed.
- `pair <name>[,<name>...]` — set `pair_judge_priority` (ordered; first adapter-valid, non-primary, available entry wins at VERIFY/risk-probe time). Same adapter validation.
- `clear` — remove both pins; delete `.devlyn/engines.json` when nothing else remains in it.

Writes preserve any unrecognized keys already in the file. After every change, re-print the resolved role table. Never modify anything outside `.devlyn/engines.json`, and never launch a pipeline from this skill.
