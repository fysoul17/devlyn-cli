# Grok adapter

## Role eligibility

executor: no
pair_judge: yes

Certification status: the pair-judge seat is wired, isolated, reachable, and probe-capable, but not emission-certified; P-0079-B measured 4/6, and P-0079-F failed emission because a narration preamble was welded to output line 1; a durable `pair grok` pin remains gated on follow-up emission registration and the standing seat-fitness rule.

## Invocation

**Availability probe**: `command -v grok >/dev/null 2>&1`; record
`grok --version` as evidence. The probe is necessary, not sufficient: auth or
wrapper failures after it passes are the same fail-closed availability class as
a failed probe (`BLOCKED:grok-unavailable` for an explicit route; an automatic
escalation remains a reported solo skip).

```bash
# $ISO_HOME = ephemeral dir seeded with a copied auth.json + agent_id, and a
#   config.toml containing:
#   [plugins]
#   disabled = ["telegram", "vercel"]
#   enabled = []
#
#   [skills]
#   ignore = ["~/.agents", "~/.claude", "~/.cursor"]
# $NEUTRAL  = empty dir outside any git repo
# $REPO     = absolute repo root (redirects MUST be absolute — cwd is $NEUTRAL)
cd "$NEUTRAL"
GROK_HOME="$ISO_HOME" \
GROK_CLAUDE_MCPS_ENABLED=false GROK_CURSOR_MCPS_ENABLED=false \
GROK_CLAUDE_SKILLS_ENABLED=false GROK_CURSOR_SKILLS_ENABLED=false \
GROK_CLAUDE_HOOKS_ENABLED=false GROK_CURSOR_HOOKS_ENABLED=false \
GROK_CLAUDE_AGENTS_ENABLED=false GROK_CLAUDE_RULES_ENABLED=false \
GROK_MEMORY=0 \
python3 "$DEVLYN_SHARED_DIR/run-bounded.py" 600 -- grok -p "<judge prompt>" \
  --permission-mode dontAsk --no-memory \
  --tools "read_file,grep,list_dir,run_terminal_cmd" \
  --disallowed-tools "Agent,use_tool,search_tool" \
  --allow 'Bash(<repo probe command family>)' \
  --reasoning-effort medium \
  > "$REPO/.devlyn/grok-judge.stdout" 2> "$REPO/.devlyn/grok-judge.stderr"
```

Copy `auth.json` into `$ISO_HOME` for every run and seed its `config.toml` with
the shown `[plugins]` and `[skills] ignore` entries.
`$NEUTRAL` and `$ISO_HOME` must be on paths that do not embed a project or repo identifier.
`--permission-mode plan` is forbidden headless because it silently blocks
all tools and returns an empty review; `--always-approve` is banned because it
auto-approves writes. `--tools` and `--disallowed-tools` are headless-only (the
TUI warns and ignores them); when both are present, the disallow list wins and
removes tools entirely rather than merely gating execution.

The `--allow` rule must cover the full probe-command family the judge may need,
and the judge prompt must name the exact permitted command(s). Derive the prompt
anchor and allow-list string identically from one source, in this precedence:
the solo-headroom hypothesis's backticked observable command when present;
otherwise the backticked commands in the spec's `## Verification` bullets;
otherwise the repo's existing test/CLI runner. If none exists, the probe
obligation does not arise and a static review is correct for that spec.
The documented `Bash(<command>)` form matches the exact command or its prefix;
the trailing ` *` form fails a no-argument command.

Grok's deny semantics are not Claude-parity: an out-of-allowlist command silently
truncates the review at exit 0. Treat the resulting collector rejection as
`BLOCKED` for `verify.pair.emission-contract`, never PASS. After a non-timeout
spawn, run:

```bash
python3 "$DEVLYN_SHARED_DIR/collect-codex-findings.py" \
  --devlyn-dir "$REPO/.devlyn" \
  --stdout-file grok-judge.stdout \
  --summary-out grok-judge.summary.json
```

On exit 124, write `.devlyn/verify.pair.timeout.json` with
`{"engine": "grok", "budget_seconds": 600}` before merge.
