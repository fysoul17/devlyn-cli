---
name: devlyn-engines
description: Show and pin the engine that executes devlyn implementation work. Reads and writes machine-local .devlyn/engines.json with fail-closed validation. Use when the user asks which engine is configured, wants to force a specific engine for implementation ("수동모드", "engine 고정", "use codex to implement"), or wants to clear the pin back to the default.
---

Utility front-end for the executor contract in `_shared/engine-preflight.md`. It adds no semantics of its own.

<args>
$ARGUMENTS
</args>

<runtime_paths>
Before the first command, establish the bindings below.

Resolve bundled resources from the SKILL.md loaded for this invocation.

Reader-rendered directory hint:
```text
${CLAUDE_SKILL_DIR}
```

Treat the hint as literal path data, never shell code. If the reader
replaced it with an absolute directory, use that directory. Otherwise
use the filesystem path or base directory reported for this loaded
SKILL.md. Resolve virtual URIs through the reader's native filesystem
mapping. If available source locations name different directories,
stop.

Bind DEVLYN_SKILL_DIR to that absolute directory. Do not obtain this
binding from an environment variable, cwd, or another installation.
Verify its SKILL.md before proceeding. Missing or conflicting source
identity is BLOCKED:skill-source-unresolved; include the failed path
when known.

Resolve bundled references against this directory. These bindings are
workflow values: establish them explicitly using each tool or shell's
literal-path rules, and include their absolute values in every fresh
worker's prompt, telling it to set them from those values, never from
its inherited environment. Do not rely on shell state surviving between
calls.

Resolve directory symlinks on DEVLYN_SKILL_DIR before deriving its
sibling _shared. Bind that directory as DEVLYN_SHARED_DIR. References
written as _shared/... use this binding. Verify the directory and each
required resource before use; failure is BLOCKED:shared-dir-unresolved
with the failed path. Never search another installation.

Verify DEVLYN_SHARED_DIR/role-config.py and DEVLYN_SHARED_DIR/engine-doctor.sh before their respective commands. In omp, use `printf '%s\n' skill://devlyn-engines`.
</runtime_paths>

## No args — status

1. Run `python3 "$DEVLYN_SHARED_DIR/role-config.py" --workdir "$PWD" --default-engine <this CLI's engine>` and print the executor's engine, source (`engines.json` pin or `default`) and availability. `inactive` lists keys earlier releases wrote for retired pipeline roles: they select nothing, and `clear` removes them. CLI presence is not authentication.
2. Run `bash "$DEVLYN_SHARED_DIR/engine-doctor.sh"` and show its availability/eligibility table.
3. Show the subcommands below. Status never launches a model.

## Subcommands

- `executor <name>` — run the status command with `--set-executor <name>`. It refuses a name with no `_shared/adapters/<name>.md`, or whose adapter declares `executor: no`, and lists the valid names. An engine whose CLI is not available is still pinned, with a warning: pins are promises, and dispatch stops with `BLOCKED:<name>-unavailable` until it is installed.
- `clear` — run the status command with `--clear`: it removes the executor pin and the inactive keys, preserves unrelated keys, and deletes an empty file.
- `pair` and `role` were removed with the retired pipeline roles: say so and change nothing.

Pass the engine name as one structured argument, never by shell interpolation of user text. After every change, re-print the status. Never modify anything outside `.devlyn/engines.json`.
