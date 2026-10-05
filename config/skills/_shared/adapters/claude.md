# Claude adapter

## Invocation

**Availability probe**: `command -v claude >/dev/null 2>&1`; record
`claude --version` as evidence. The probe is necessary, not sufficient:
`claude -p` needs network access to the Anthropic API, so a network-denying
sandbox (e.g. Codex CLI's default `workspace-write`) fails the spawn even
though the binary resolves. A failed spawn is the same fail-closed class as a
failed probe: `BLOCKED:claude-unavailable` for a pinned executor.
