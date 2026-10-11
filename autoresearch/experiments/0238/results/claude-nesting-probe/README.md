# Claude noninteractive nesting startup probe

The preregistered prediction was confirmed. Pinned image
`sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998`
(Claude 2.1.296) reached the same native `Not logged in · Please run /login`
API-error result with `CLAUDECODE=1` and without it. Both exited 1, emitted empty
stderr, reported duration_api_ms 0 and were cleanly removed. No nested-session
refusal occurred, and no environment marker was removed to force this result.

Each process used env -i, a fresh tmpfs HOME, no credential mounts, and Docker
network none. This establishes only that the pinned noninteractive entrypoint
passes this startup guard; authenticated independent-session identity, usage,
read-only capability and resume behavior still require the authorized smoke.

Root verified the current primary [environment-variable documentation](https://code.claude.com/docs/en/env-vars),
which describes CLAUDECODE as a subprocess marker and says noninteractive
claude -p nested sessions still persist in the CLAUDE_CODE_CHILD_SESSION entry.
The [CLI reference](https://code.claude.com/docs/en/cli-reference) documents
noninteractive operation and --tools capability selection.

Historical read-only evidence audit by evidence_audit independently found
successful Claude H new/resume sessions in 0234 d04, d21 and smoke-H, with no
CLAUDECODE/unset/guard handling in their owner command streams. Those sessions
used 2.1.281, so they do not substitute for this pinned-version startup probe.
The actual inherited historical shell environment was not captured.
