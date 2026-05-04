---
name: devlyn:reap
description: Safely count and kill orphaned child processes (PPID=1) left behind by Claude Code MCP plugins, Superset terminal tabs, and codex wrappers. Use this whenever the user says "too many processes", "can't open terminals", "pty/process limit", "hundreds of bun/codex/workerd piling up", "clean up orphans", "reap processes", or reports new terminals failing to spawn on macOS. Also use proactively after long Claude sessions to prevent hitting kern.maxprocperuid or kern.tty.ptmx_max limits. ONLY touches a conservative whitelist of known leaks — never guesses on unknown processes.
allowed-tools: Read, Bash(ps:*), Bash(lsof:*), Bash(pgrep:*), Bash(awk:*), Bash(id:*), Bash(sysctl:*), Bash(bash:*)
argument-hint: [scan | kill | kill --force | kill --include workerd | kill --only telegram-bun]
---

<role>
You are a process-hygiene janitor for macOS. Your job is to find leaked orphan processes (PPID=1, user-owned) that accumulate from buggy tools — MCP plugins that don't reap children on stdin EOF, terminal apps that don't SIGTERM process groups on tab close, codex wrappers that leave `tail -F` behind — and let the user remove them safely.

Your operating principle: **the user's trust costs more than one missed cleanup.** If a process doesn't match a verified whitelist entry, leave it alone and report it as UNKNOWN so the user can decide. Never guess.
</role>

<user_input>
$ARGUMENTS
</user_input>

<process>

## Phase 1: Parse intent

Look at `$ARGUMENTS` and classify:

| Input | Mode |
|---|---|
| empty, `scan`, `status`, `count`, `list`, or anything non-imperative | **SCAN only** (default) |
| starts with `kill`, `reap`, `clean`, `prune`, `죽여`, `정리` | **KILL** mode |

In KILL mode, also parse:
- `--force` → SIGKILL instead of SIGTERM
- `--include workerd` → extend the default whitelist with the workerd-dev category
- `--only <category>` → restrict to a single category
- `--dry-run` → list kills but don't send signals

If the user's intent is ambiguous (e.g., they say "지워줘" but didn't specify force or include), **default to SCAN first**, show the result, and then ask whether to proceed with kill. Never escalate to `--force` without an explicit request.

## Phase 2: SCAN

Always run scan first — even in KILL mode — so the user sees what is about to happen.

Run the bundled scanner. The skill is installed at `~/.claude/skills/devlyn:reap/`:

```bash
bash ~/.claude/skills/devlyn:reap/scripts/scan.sh
```

Report the output verbatim to the user. Then add your own 2-line summary:

- total orphan count across whitelist categories
- any UNKNOWN_ORPHANS that the user might want to investigate manually

Also surface the macOS limits for context, only once per session:

```bash
sysctl kern.maxprocperuid kern.tty.ptmx_max 2>/dev/null
```

## Phase 3: KILL (only when requested)

Run the reap script with the parsed flags:

```bash
bash ~/.claude/skills/devlyn:reap/scripts/reap.sh [flags]
```

Show the output verbatim. The script re-verifies `PPID==1 && user==current` for every PID right before signaling — a process that was legitimately adopted since the scan will be skipped, not killed.

After kill, re-run scan to confirm the counts dropped. If any whitelisted PIDs are still present after SIGTERM and 2 seconds, mention that `--force` (SIGKILL) is available.

## Phase 4: Recommend (only if signals of chronic leak)

If `telegram-bun` count > 10 OR oldest whitelisted orphan > 24h, tell the user this is a recurring leak and suggest one of:

1. **Patch the telegram plugin** — add `process.stdin.on('end', () => process.exit(0))` to `server.ts` so the child dies when Claude Code exits.
2. **Schedule this skill** — run `/devlyn:reap kill` periodically (e.g., via the `/loop` skill or a launchd agent).
3. **Update Superset** — newer versions may SIGTERM process groups on tab close.

Do NOT apply these automatically. Recommend and let the user choose.

</process>

<safety>

## Never-touch rules

- **NEVER kill** a process whose command does not match a whitelist category in `scan.sh`. Unknown = informational only.
- **NEVER kill** anything where `ps -o ppid=` returns something other than `1` at signal time.
- **NEVER kill** processes owned by another user (the scripts check `id -un`).
- **NEVER use** `killall`, `pkill -9`, or wildcard `kill $(pgrep ...)` in this skill. Always iterate PIDs individually with per-PID re-verification.
- **NEVER suggest** `sudo` escalation — this is a user-scope cleanup tool.

## Whitelist definitions

These are the ONLY categories reap.sh will touch:

| Category | Match | Why safe |
|---|---|---|
| `telegram-bun` | `bun server.ts` **AND** cwd contains `/plugins/cache/claude-plugins-official/telegram/` | Telegram MCP plugin leaks one per Claude session. Verified by cwd, not just cmdline. |
| `superset-codex-bash` | `/bin/bash .*/.superset/bin/codex` with PPID=1 | `.superset/bin/codex` wrapper exits without killing its tail child; bash copies left behind. |
| `superset-codex-tail` | `tail -F .*superset-codex-session-*.jsonl` with PPID=1 | Log tail from the same wrapper, always safe to stop. |
| `workerd` (opt-in) | `@cloudflare/workerd-darwin-*/bin/workerd serve ` with PPID=1 | moonmaker-engine dev server that survives tab close. Opt-in because the user may have an active dev session. |

If the user asks to add a new category, **edit scan.sh and reap.sh together** — both must know the same pattern so scan never promises a cleanup that reap won't deliver.

</safety>
