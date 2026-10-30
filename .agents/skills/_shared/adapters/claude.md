# Claude adapter

## Invocation

A Claude executor starts as
`claude -p "<prompt>" --dangerously-skip-permissions --add-dir "<common git dir>"`,
where `<common git dir>` is `git rev-parse --path-format=absolute --git-common-dir`:
a linked task worktree commits there.

For drain children, `queue.py` adds `--no-chrome` and a temporary `--settings`
file (0600), sets `ENABLE_CLAUDEAI_MCP_SERVERS=false`, disables plugin sync and
every enabled plugin (including synced plugins), and verifies the overrides
before spawning. Discovery or verification failure refuses the launch. Normal
user settings, including `BASH_MAX_TIMEOUT_MS`, remain loaded; interactive and
non-drain Claude invocations are unchanged.
The launch settings also force `env.ENABLE_CLAUDEAI_MCP_SERVERS="false"` and
`disableClaudeAiConnectors=true` (recognized by Claude 2.1.314). Policy options
precede all caller arguments; server denies use `--disallowedTools=<list>`.
Drain refuses caller `--settings`, `--setting-sources`, `--plugin-dir` and
`--plugin-url` or `--chrome` tokens (including `=<value>` forms), and `--add-dir` directories
whose `.claude/settings.json` or `settings.local.json` contains `enabledPlugins`.
Wrapped Claude executors must be replaced with a direct Claude argv; a shell
command or script that starts Claude itself is not inspected.

**Availability probe**: `command -v claude >/dev/null 2>&1`; record
`claude --version` as evidence. The probe is necessary, not sufficient:
`claude -p` needs network access to the Anthropic API, so in a network-denying
sandbox (e.g. Codex CLI's default `workspace-write`) it fails even though the
binary resolves. A drain blocks when the executor cannot start, and a task
whose executor exits without a submission waits for the next drain.
