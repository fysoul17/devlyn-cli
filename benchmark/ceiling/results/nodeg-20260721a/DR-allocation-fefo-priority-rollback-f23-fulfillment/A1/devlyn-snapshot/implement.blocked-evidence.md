# IMPLEMENT — BLOCKED:codex-unavailable

Executor engine is pinned via `.devlyn/engines.json` (`{"executor":"codex"}`), an explicit route per `_shared/engine-preflight.md` — a pinned-but-unavailable engine must halt with `BLOCKED:<engine>-unavailable`, never downgrade to solo/Claude.

`command -v codex` (the availability probe) succeeds — the binary resolves at `/Users/aipalm/.local/share/nx01/pins/nodeg-20260721a/codex`. Per the claude-adapter precedent ("the probe is necessary but not sufficient"), actual spawn was exercised and failed:

1. Full IMPLEMENT prompt, `-s workspace-write -c model_reasoning_effort=xhigh`, 550s budget → exit 124 (timeout), zero bytes on stdout, no file changes (`git diff --stat` empty).
2. Full IMPLEMENT prompt, `-s workspace-write -c model_reasoning_effort=high`, 580s budget → exit 124, zero bytes on stdout, no file changes.
3. Diagnostic: trivial prompt ("Reply with exactly the single word: OK"), `-s read-only -c model_reasoning_effort=low`, non-isolated, 90s budget → exit 124, zero bytes on stdout.
4. Diagnostic: same trivial prompt, `CODEX_MONITORED_ISOLATED=1` (hooks/user-config disabled), 90s budget → exit 124, zero bytes on stdout. Ruling out the environment's notify-hook wrapper as the cause (isolation prevented the earlier process-explosion symptom but did not fix the hang), pointing to a lower-level spawn/connectivity failure (e.g. no reachable OpenAI API backend from this sandbox) rather than a hook bug or prompt-complexity issue.

Total: 4/4 invocations across two effort levels, two sandbox policies, and both isolated/non-isolated hook modes produced zero stdout bytes before hitting their timeout. This is decisive evidence of engine unavailability, not slowness — a functioning CLI would stream at least partial output for a one-word low-effort request well inside 90s.

Separately: an earlier ad hoc `codex --version` probe (before this run's first proper invocation) triggered a runaway self-respawn of the environment's `codex` wrapper script, spawning 2600+ duplicate processes (`--enable hooks -c notify=[...]` argument list growing on each re-exec) before being killed. This is now understood as a shell-wrapper defect distinct from (but compounding) the connectivity hang above; `codex-monitored.sh`'s `codex exec` invocation shape did not reproduce that explosion.

## Verdict

`phases.implement.verdict = "BLOCKED"`. Terminal run verdict: `BLOCKED:codex-unavailable`.

## Setup guidance

- Verify the Codex CLI can reach its backend from this sandbox/environment (network egress, auth/session validity): `codex exec -s read-only "reply OK"` should stream output within seconds.
- If the environment's `codex` shim/wrapper (`_superset_codex_args`, notify hooks) is suspected, reproduce with the hook mechanism disabled (`--ignore-user-config --disable hooks`) — in this run that did not resolve the hang, indicating the underlying issue is not the hook wrapper alone.
- Once `codex --version` and a minimal `codex exec` call both return promptly, rerun `/devlyn:resolve --goal-file .devlyn/goal.txt --pair-verify`; the pipeline is otherwise ready to continue (PLAN already produced `.devlyn/plan.md`, complexity/risk classification already computed).
- Alternative: pin the executor to a different available engine (`/devlyn:engines executor claude`) if Codex is not expected to be usable in this environment, then rerun.
