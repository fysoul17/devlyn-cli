# Shared — Codex Invocation

Single source of truth for how every skill calls Codex. **MCP is not used.** Skills shell out to the local `codex exec` CLI (shipped by the `openai-codex` Claude Code plugin).

## Canonical invocations

**Read-only critique / adversarial review / debate** (ideate CHALLENGE, auto-resolve CRITIC security sub-pass, preflight code-audit):

```bash
codex exec \
  -C <project-root> \
  -s read-only \
  -c model_reasoning_effort=xhigh \
  "<inlined-prompt>"
```

**Workspace-write implementation** (auto-resolve BUILD, FIX LOOP, and codex-routed ideate phases):

```bash
codex exec \
  -C <project-root> \
  --full-auto \
  -c model_reasoning_effort=xhigh \
  "<inlined-prompt>"
```

Notes:
- `-C` — project root so Codex's working directory matches.
- `-s read-only` / `--full-auto` — sandbox policy. `--full-auto` = `-s workspace-write` with auto-approval of sandboxed commands.
- `-c model_reasoning_effort=xhigh` — config override for reasoning depth. Required for deep critique; skills may choose `high` or `medium` when thoroughness doesn't warrant xhigh.
- **Omit `-m <model>`** — Codex CLI uses its configured flagship (currently `gpt-5.4`, automatically whatever ships next). This is the zero-touch mechanism. Only name `-m` when a role explicitly needs a different model (e.g., `gpt-5.3-codex` for SWE-bench-heavy coding tasks, `gpt-5.3-codex-spark` for speed).

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

> Run `codex exec -C <state.base_ref.repo_root> --full-auto -c model_reasoning_effort=xhigh "<FIX LOOP prompt>"`. Omit `-m` so the CLI flagship is auto-selected. Capture stdout as the fix-round reply; non-zero exit → treat as subagent failure.
