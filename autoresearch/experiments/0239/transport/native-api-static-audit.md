# Native API check before transport registration

2026-10-10. Read-only inspection; no CLI execution, Docker invocation, auth read
or model call. The retained measured image identifies Claude Code 2.1.296 (see
0237/results/f02-child-lifecycle-audit.md). The installed host binary at
`/Users/aipalm/.local/share/claude/versions/2.1.296` was inspected as bytes:
SHA256 `c9b5341637becbd423ddffc5b254afb645682a3868cb708bbc6cc0e7bb419937`.
This host executable is not claimed byte-identical to the Linux image binary.

Its embedded versioned JavaScript supplies these concrete anchors (byte offsets
in that exact executable, without invoking it):

- Offset 193705660: foreground defaults are 120000ms; max default 600000ms.
  `CCe` reads `BASH_MAX_TIMEOUT_MS` and takes the maximum with the default timeout.
- Offset 199557368: native Bash schema describes an optional millisecond timeout
  and a maximum for foreground commands. Offset 199558439: optional Boolean
  `run_in_background` is part of that schema (availability is contextual).
- Offset 198858022: Agent instructions expose explicit `run_in_background: false`
  for a task whose result gates the owner's next action. This is a valid API
  route to test, not proof every runtime flag combination permits it.

The official [environment reference](https://code.claude.com/docs/en/env-vars)
retrieved the same day independently documents a 600000ms default maximum for
foreground Bash, and a separate 600000ms post-final idle ceiling for background
work in `-p`. Neither setting will change. The official
[subagent guide](https://code.claude.com/docs/en/sub-agents#run-subagents-in-foreground-or-background)
says foreground children hold the parent until completion; default `-p` fork
mode is off, where foreground selection is available. Both pages are live
documentation rather than immutable source for the image.

Therefore the revised draft uses two separate 305-second native Bash calls,
each requesting 360000ms and explicit foreground execution. Their aggregate
child lifetime exceeds 600s without requiring an over-limit individual call.
One 610-second command with timeout 660000 is not retained as the active task.
No native result has been observed for the revised sequence; actual schema,
launch mode, timing, terminal child result and native identity must still be
established by the registered smoke evidence. Any unexpected tool failure is
reported on its own terms, not conflated with foreground lifetime support.
