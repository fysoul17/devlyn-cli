# Shared — Codex Invocation

Single source of truth for how every skill calls Codex. **MCP is not used.** Skills shell out via the wrapper at `$CODEX_MONITORED_PATH`, resolved from the invoked skill's sibling `_shared/codex-monitored.sh`, which fronts the local Codex CLI.

## Canonical invocations

All long-running Codex calls go through `codex-monitored.sh` — a thin wrapper that closes stdin (codex 0.124.0 hangs when both stdin is open and a prompt arg is given), streams Codex stdout fully (no `tail -n` truncation), and prints a `[codex-monitored] heartbeat` line every 30s so the outer `claude -p` byte-watchdog stays fed during long reasoning gaps. The wrapper passes its arguments through verbatim to the underlying CLI, so the canonical flag set is unchanged from a raw call — only the launcher differs.

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
CODEX_MONITORED_ISOLATED=1 bash "$CODEX_MONITORED_PATH" \
  -C <project-root> \
  -s read-only \
  -c model_reasoning_effort=xhigh \
  "<inlined-prompt>"
```

**Workspace-write implementation** (`/devlyn:resolve` IMPLEMENT phase when `--engine codex` or `--engine auto` routes to Codex, plus codex-routed `/devlyn:ideate` phases):

```bash
bash "$CODEX_MONITORED_PATH" \
  -C <project-root> \
  -s workspace-write \
  -c model_reasoning_effort=xhigh \
  "<inlined-prompt>"
```

Notes:
- `-C` — project root so Codex's working directory matches.
- `-s read-only` / `-s workspace-write` — sandbox policy. Use workspace-write for implementation/probe phases that write tracked files or `.devlyn` artifacts.
- `-c model_reasoning_effort=xhigh` — config override for reasoning depth. Required for deep critique; skills may choose `high` or `medium` when thoroughness doesn't warrant xhigh.
- **Omit `-m <model>`** — Codex CLI uses its configured flagship (currently `gpt-5.5`, automatically whatever ships next). This is the zero-touch mechanism. Only name `-m` when a role explicitly needs a different model (e.g., `gpt-5.3-codex` for SWE-bench-heavy coding tasks, `gpt-5.3-codex-spark` for speed).
- `CODEX_MONITORED_ISOLATED=1` — required for bounded read-only critique/probe/judge calls. The wrapper adds `--ignore-user-config --ignore-rules --ephemeral --disable codex_hooks --disable hooks` so user config, AGENTS.md, hooks, and project rules cannot add hidden context, tool calls, or transcript side effects. Do not set it for workspace-write implementation phases.
- Wrapper calls are **foreground-blocking**. Never launch them via a backgrounded shell (`run_in_background`, `&`, `nohup`) and never end the orchestrator message while one runs: a headless print-mode session kills backgrounded children at wind-down (observed 2026-07-07: an FS1 A-arm IMPLEMENT codex call was killed at turn end → 0-byte delivery). The heartbeat stream is the observability channel; block on the call.
- Raw `codex exec ...` invocations are **forbidden** in skill prompts. The benchmark variant arm runs a PATH shim (`scripts/codex-shim/codex`) that transparently re-routes any raw `codex exec` to the wrapper as a safety net, but skills should always emit the wrapper form directly so the orchestrator's first-attempt has the right shape. Two prior iterations (iter-0006 universal foreground ban, iter-0008 prompt-level kill-shape contract) failed because the orchestrator picked starvation-prone shapes (`codex exec ... 2>&1 | tail -200`) from its own pattern prior — the wrapper plus the shim is the runtime binding layer those iters lacked. See `autoresearch/iterations/0009-wrapper-and-hook.md`.

## Availability check

Before the first Codex call in a run, verify the CLI is on PATH:

```bash
command -v codex >/dev/null 2>&1
```

If the check fails while Codex is explicitly selected or conditionally required by pair/risk-probe VERIFY, follow `_shared/engine-preflight.md`: stop with `BLOCKED:codex-unavailable`, preserve run evidence, and print setup guidance. Do not convert the run to Claude. `--no-pair` and `--no-risk-probes` are explicit user opt-outs for reruns, not automatic fallbacks.

## Why CLI over other paths

The local Codex CLI (fronted by `codex-monitored.sh`) is the primary (and only) integration. It beats alternatives on three dimensions: the model is inherited from the CLI's own default so no skill edits are needed when OpenAI ships a new flagship; flags compose on the command line and the skill docs stay grep-friendly; the invocation has one failure mode (the binary is on PATH or it isn't), which the shared availability check reports explicitly.

## Invocation from inside a skill prompt

Skills write the invocation as a Bash command the runtime executes. Example shape from `/devlyn:resolve` PHASE 2 IMPLEMENT when routed to Codex:

> Run `bash "$CODEX_MONITORED_PATH" -C <state.base_ref.repo_root> -s workspace-write -c model_reasoning_effort=xhigh "<IMPLEMENT prompt>"`. Omit `-m` so the CLI flagship is auto-selected. Capture stdout as the IMPLEMENT reply; non-zero exit → treat as subagent failure. The wrapper emits `[codex-monitored]` heartbeat and lifecycle lines on **stderr** — stdout stays clean for Codex output, so the orchestrator can parse the reply without filtering. Heartbeat-on-stderr keeps the orchestrator's combined-output stream non-silent (defeats the iter-0008 byte-watchdog kill) without polluting the codex-reply view of stdout. Do not pipe the wrapper; direct capture or file redirection preserves streaming and avoids the pipe-refusal exit.
