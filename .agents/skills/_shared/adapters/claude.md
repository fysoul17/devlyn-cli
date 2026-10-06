# Claude adapter

## Invocation

A Claude executor starts as
`claude -p "<prompt>" --dangerously-skip-permissions --add-dir "<common git dir>"`,
where `<common git dir>` is `git rev-parse --path-format=absolute --git-common-dir`:
a linked task worktree commits there.

**Availability probe**: `command -v claude >/dev/null 2>&1`; record
`claude --version` as evidence. The probe is necessary, not sufficient:
`claude -p` needs network access to the Anthropic API, so a network-denying
sandbox (e.g. Codex CLI's default `workspace-write`) fails the spawn even
though the binary resolves. A failed spawn is the same fail-closed class as a
failed probe: `BLOCKED:claude-unavailable` for a pinned executor.
