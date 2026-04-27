# Shared — Codex Invocation

Single source of truth for how every skill calls Codex. **MCP is not used.** Skills shell out to the local `codex exec` CLI (shipped by the `openai-codex` Claude Code plugin).

## Canonical invocations

All long-running Codex calls go through `codex-monitored.sh` — a thin wrapper that closes stdin (codex 0.124.0 hangs when both stdin is open and a prompt arg is given), streams Codex stdout fully (no `tail -n` truncation), and prints a `[codex-monitored] heartbeat` line every 30s so the outer `claude -p` byte-watchdog stays fed during long reasoning gaps. The wrapper passes its arguments verbatim to `codex exec`, so the canonical flag set is unchanged from a raw `codex exec` call — only the launcher differs.

**Read-only critique / adversarial review / debate** (ideate CHALLENGE, preflight code-audit). The auto-resolve CRITIC security sub-pass is NOT Codex — it's delegated to the native `security-review` Claude Code skill; see `devlyn:auto-resolve/references/phases/phase-3-critic.md` Sub-pass 2.

```bash
bash .claude/skills/_shared/codex-monitored.sh \
  -C <project-root> \
  -s read-only \
  -c model_reasoning_effort=xhigh \
  "<inlined-prompt>"
```

**Workspace-write implementation** (auto-resolve BUILD, FIX LOOP, and codex-routed ideate phases):

```bash
bash .claude/skills/_shared/codex-monitored.sh \
  -C <project-root> \
  --full-auto \
  -c model_reasoning_effort=xhigh \
  "<inlined-prompt>"
```

Notes:
- `-C` — project root so Codex's working directory matches.
- `-s read-only` / `--full-auto` — sandbox policy. `--full-auto` = `-s workspace-write` with auto-approval of sandboxed commands.
- `-c model_reasoning_effort=xhigh` — config override for reasoning depth. Required for deep critique; skills may choose `high` or `medium` when thoroughness doesn't warrant xhigh.
- **Omit `-m <model>`** — Codex CLI uses its configured flagship (currently `gpt-5.5`, automatically whatever ships next). This is the zero-touch mechanism. Only name `-m` when a role explicitly needs a different model (e.g., `gpt-5.3-codex` for SWE-bench-heavy coding tasks, `gpt-5.3-codex-spark` for speed).
- Raw `codex exec ...` invocations are **forbidden** in skill prompts. The benchmark variant arm runs a PATH shim (`scripts/codex-shim/codex`) that transparently re-routes any raw `codex exec` to the wrapper as a safety net, but skills should always emit the wrapper form directly so the orchestrator's first-attempt has the right shape. Two prior iterations (iter-0006 universal foreground ban, iter-0008 prompt-level kill-shape contract) failed because the orchestrator picked starvation-prone shapes (`codex exec ... 2>&1 | tail -200`) from its own pattern prior — the wrapper plus the shim is the runtime binding layer those iters lacked. See `autoresearch/iterations/0009-wrapper-and-hook.md`.

## Availability check

Before the first `codex exec` call in a run, verify the CLI is on PATH:

```bash
command -v codex >/dev/null 2>&1
```

If the check fails, the skill follows the `_shared/engine-preflight.md` downgrade rule — silently switch to Claude for this run and log `engine downgraded: codex-unavailable` in the final report. Never prompt, never abort.

## Why CLI over other paths

The `codex exec` CLI is the primary (and only) integration. It beats alternatives on three dimensions: the model is inherited from the CLI's own default so no skill edits are needed when OpenAI ships a new flagship; flags compose on the command line and the skill docs stay grep-friendly; the invocation has one failure mode (the binary is on PATH or it isn't), which the shared availability check covers cleanly.

## Invocation from inside a skill prompt

Skills write the invocation as a Bash command the runtime executes. Example from `devlyn:auto-resolve`:

> Run `bash .claude/skills/_shared/codex-monitored.sh -C <state.base_ref.repo_root> --full-auto -c model_reasoning_effort=xhigh "<FIX LOOP prompt>"`. Omit `-m` so the CLI flagship is auto-selected. Capture stdout as the fix-round reply; non-zero exit → treat as subagent failure. The wrapper emits `[codex-monitored]` heartbeat and lifecycle lines on **stderr** — stdout stays clean for Codex output, so the orchestrator can parse the reply without filtering. Heartbeat-on-stderr keeps the orchestrator's combined-output stream non-silent (defeats the iter-0008 byte-watchdog kill) without polluting the codex-reply view of stdout.
