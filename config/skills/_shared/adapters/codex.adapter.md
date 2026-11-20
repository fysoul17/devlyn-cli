# Codex adapter

## Invocation

A Codex executor runs through `_shared/codex-monitored.sh`, never a raw or piped
`codex exec`: `bash "$DEVLYN_SHARED_DIR/codex-monitored.sh" <arguments for codex exec> "<prompt>"`.
The `workspace-write` sandbox keeps `.git` read-only, so an executor that commits adds as
writable roots the common Git directory (`git rev-parse --path-format=absolute --git-common-dir`)
plus, in a linked worktree, its own Git directory (`git rev-parse --path-format=absolute --git-dir`),
listed exactly because the sandbox protects it even under a listed parent. It also
denies network, which installing a new dependency needs:
`-s workspace-write -c 'sandbox_workspace_write.writable_roots=["<git dir>","<worktree git dir>"]' -c 'sandbox_workspace_write.network_access=true'`.
Deliver a multiline prompt as exact file bytes: set `DEVLYN_CODEX_PROMPT_FILE=<file>`
and pass the sole prompt argument `-`. When the pin names them, add `--model=<model>` (one
argument: a model's name is then never read as a program or a sandbox) and
`-c 'model_reasoning_effort="<effort>"'`. Its prompt says it was started to implement: such a run is the executor and never hands the implementation on.

Every monitored child applies `_shared/unattended-tools.py` before recording its
effective argv: account/plugin and browser/computer features are disabled, then
listed desktop servers are disabled. Policy switches precede all exec arguments;
feature states and MCP overrides are read back before launch. A still-enabled
target, malformed output or discovery failure refuses the launch; an unsupported feature error names the installed Codex version.
Interactive Codex and user configuration files are unchanged.
If an exec-only configuration option (such as `--ignore-user-config` on Codex
0.164.0) cannot be applied to `mcp list`, discovery refuses the launch; it never
falls back to listing a different configuration.

## Review

A fresh read-only run, given the requirement and the change, never the working conversation:
`bash "$DEVLYN_SHARED_DIR/codex-monitored.sh" -C <repo> -s read-only --ignore-rules "<prompt>"`, with stdout to a
file, plus `-m <model>` and `-c 'model_reasoning_effort="<effort>"'` when pinned; a long prompt as
`DEVLYN_CODEX_PROMPT_FILE=<file>` (outside the checkout: its transport record is written beside it) with the sole
argument `-`. `<prompt>` is passed as one literal argument: the shell must not evaluate anything in it. The user's own configuration (hooks, connected tools) still applies.
