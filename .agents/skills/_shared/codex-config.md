# Shared — Codex Invocation

Single source of truth for how every skill calls Codex. **MCP is not used.** Skills shell out via the wrapper at `$CODEX_MONITORED_PATH`, resolved from the invoked skill's sibling `_shared/codex-monitored.sh`, which fronts the local Codex CLI.

## Canonical invocations

All long-running Codex calls go through `codex-monitored.sh`. It streams full stdout and emits a `[codex-monitored] heartbeat` every 30s on stderr. Write multiline prompts as exact UTF-8 bytes to a task-local file; set `DEVLYN_CODEX_PROMPT_FILE` and pass the sole prompt argument `-`. The wrapper snapshots those bytes before dispatch and seals actual argv, prompt digest and completion in `<prompt-file>.transport.json`. Missing/unreadable files, competing prompt arguments and receipt/prompt mismatches fail before launch. Without file transport, stdin remains DEVNULL (avoiding the open-stdin plus argument-prompt hang).

Before the first Codex call, resolve the wrapper from the invoked skill directory:

```bash
DEVLYN_SKILL_DIR="${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}"
if [ "$DEVLYN_SKILL_DIR" = "__DEVLYN_SKILL_DIR__" ] || [ ! -d "$DEVLYN_SKILL_DIR/../_shared" ]; then
  echo "BLOCKED:shared-dir-unresolved: $DEVLYN_SKILL_DIR/../_shared" >&2
  exit 1
fi
DEVLYN_SHARED_DIR="$(cd "$DEVLYN_SKILL_DIR/../_shared" && pwd)"
CODEX_MONITORED_PATH="$DEVLYN_SHARED_DIR/codex-monitored.sh"
if [ ! -f "$CODEX_MONITORED_PATH" ]; then
  echo "BLOCKED:shared-dir-unresolved: $CODEX_MONITORED_PATH" >&2
  exit 1
fi
```

**Read-only critique / adversarial review / debate** (`/devlyn:resolve` VERIFY pair-mode, plus any future ideate read-only critique). Security review stays native to Claude Code BUILD_GATE. Codex returns findings on stdout; the orchestrator writes files.

```bash
DEVLYN_CODEX_PROMPT_FILE="<prompt-file>" CODEX_MONITORED_ISOLATED=1 CODEX_MONITORED_TIMEOUT_SEC=600 bash "$CODEX_MONITORED_PATH" \
  -C <project-root> \
  -s read-only \
  -c model_reasoning_effort=xhigh \
  -
```

**Workspace-write implementation** (`/devlyn:resolve` IMPLEMENT phase when `--engine codex` or `--engine auto` routes to Codex, plus codex-routed `/devlyn:ideate` phases):

```bash
DEVLYN_CODEX_PROMPT_FILE="<prompt-file>" bash "$CODEX_MONITORED_PATH" \
  -C <project-root> \
  -s workspace-write \
  -c sandbox_workspace_write.network_access=false \
  -c model_reasoning_effort=xhigh \
  -
```

**CI-equivalent BUILD_GATE** keeps the same write sandbox and enables general
outbound network access inside that sandbox, including the loopback servers and
network-backed test gates that CI may exercise:

```bash
DEVLYN_CODEX_PROMPT_FILE="<prompt-file>" bash "$CODEX_MONITORED_PATH" \
  -C <project-root> \
  -s workspace-write \
  -c sandbox_workspace_write.network_access=true \
  -c model_reasoning_effort=xhigh \
  -
```

Notes:
- `DEVLYN_CODEX_PROMPT_FILE` — use the same file as `DEVLYN_INVOCATION_PROMPT_FILE` for receipt-bound calls. Retain the generated transport carrier with the prompt/session/argv evidence; a path or claimed environment value alone does not prove delivery. Do not use shell command substitution for prompt bytes.
- `-C` — project root so Codex's working directory matches.
- `-s read-only` / `-s workspace-write` — sandbox policy. Use workspace-write for implementation/probe phases that write tracked files or `.devlyn` artifacts.
- `-c sandbox_workspace_write.network_access=<true|false>` — required and receipt-bound for mutation phases: `true` only for BUILD_GATE and, per call, PROBE-DERIVE when the probe's visible Verification command requires a localhost service; `false` for PLAN, IMPLEMENT, CLEANUP, and PROBE-DERIVE by default. This allows CI-equivalent loopback/network tests without widening to `danger-full-access` and prevents user configuration from silently changing other phases.
- `-c model_reasoning_effort=xhigh` — config override for reasoning depth. Required for deep critique; skills may choose `high` or `medium` when thoroughness doesn't warrant xhigh.
- **For every receipt-bound Codex call, add `--json -m <model_requested>` to the recipes above**, matching the model recorded at spawn; keep the skill’s existing model-selection rules. Other routes keep their omission rules unless an explicit role profile supplies a model: normal workers may inherit user config, while unconfigured isolated VERIFY uses its CLI default. Explicit profiles use role-config.py options and the separate judge-role-evidence.py contract; they do not relax mutation receipts. Omission proves neither model identity nor role fitness. Re-certify seats after model/version changes before re-pinning them.
- `CODEX_MONITORED_ISOLATED=1` — required for bounded read-only critique/probe/judge calls. The wrapper adds `--ignore-user-config --ignore-rules --ephemeral --disable codex_hooks --disable hooks` so user config, AGENTS.md, hooks, and project rules cannot add hidden context, tool calls, or transcript side effects. Do not set it for workspace-write implementation phases.
- Wrapper calls are **foreground-blocking**. Never launch them via a backgrounded shell (`run_in_background`, `&`, `nohup`) and never end the orchestrator message while one runs: a headless print-mode session kills backgrounded children at wind-down (observed 2026-07-07: an FS1 A-arm IMPLEMENT codex call was killed at turn end → 0-byte delivery). The heartbeat stream is the observability channel; block on the call. Interactive Claude Code caps a foreground Bash call at `BASH_MAX_TIMEOUT_MS` (the installer sets at least 3600000 ms, IMPLEMENT's effective outer ceiling), so every foreground Codex wrapper call must pass the Bash `timeout` explicitly at that ceiling or the phase's own budget (for example, 600s judges) — never rely on the 120 s default.
- Raw `codex exec ...` invocations are **forbidden** in skill prompts. The benchmark variant arm runs a PATH shim (`scripts/codex-shim/codex`) that transparently re-routes any raw `codex exec` to the wrapper as a safety net, but skills should always emit the wrapper form directly so the orchestrator's first-attempt has the right shape. Two prior iterations (iter-0006 universal foreground ban, iter-0008 prompt-level kill-shape contract) failed because the orchestrator picked starvation-prone shapes (`codex exec ... 2>&1 | tail -200`) from its own pattern prior — the wrapper plus the shim is the runtime binding layer those iters lacked. See `autoresearch/iterations/0009-wrapper-and-hook.md`.

## Constrained Windows judge reads

Codex supports [native Windows sandboxing](https://learn.chatgpt.com/docs/windows/windows-sandbox). A policy-denied read selects a constrained-read route for that judge; it does not establish that Windows lacks sandbox support or denies every read. The orchestrator supplies the complete spec, sibling expected contract, accepted source SHA and cumulative diff, relevant source/tests with file:line locators, and validated sealed MECHANICAL results, manifests and required raw streams inline in the prompt file. Tell the fresh judge: "Judge only the supplied evidence; run no tools. Missing, truncated or unbound inputs require a verdict-binding BLOCKED finding." Keep `-s read-only`, isolation, freshness, selected model/effort, the 600s budget and normal findings/timeout handling. Never widen sandbox permissions or invent evidence to complete the packet.

## Availability check

Before the first Codex call in a run, verify the CLI is on PATH:

```bash
command -v codex >/dev/null 2>&1
```

If the check fails while Codex is explicitly selected or conditionally required by pair/risk-probe VERIFY, follow `_shared/engine-preflight.md`: stop with `BLOCKED:codex-unavailable`, preserve run evidence, and print setup guidance. Do not convert the run to Claude. `--no-pair` and `--no-risk-probes` are explicit user opt-outs for reruns, not automatic fallbacks.

## Why CLI over other paths

The local Codex CLI, fronted by `codex-monitored.sh`, is the integration boundary. CLI flags compose with the existing phase routes and keep invocation evidence inspectable. The shared preflight checks availability; a present binary does not establish model identity or role fitness.

## Invocation from inside a skill prompt

Skills write the invocation as a Bash command the runtime executes. Example shape from `/devlyn:resolve` PHASE 2 IMPLEMENT when routed to Codex:

> Run `DEVLYN_CODEX_PROMPT_FILE="<IMPLEMENT-prompt-file>" bash "$CODEX_MONITORED_PATH" --json -C <state.base_ref.repo_root> -s workspace-write -m <model_requested> -c sandbox_workspace_write.network_access=false -c model_reasoning_effort=xhigh -`. Capture stdout as the IMPLEMENT reply; non-zero exit → treat as subagent failure. The wrapper emits `[codex-monitored]` heartbeat and lifecycle lines on **stderr** — stdout stays clean for Codex output, so the orchestrator can parse the reply without filtering. Heartbeat-on-stderr keeps the orchestrator's combined-output stream non-silent (defeats the iter-0008 byte-watchdog kill) without polluting the codex-reply view of stdout. Do not pipe the wrapper; direct capture or file redirection preserves streaming and avoids the pipe-refusal exit.
