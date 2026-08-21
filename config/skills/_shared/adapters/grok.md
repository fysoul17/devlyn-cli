# Grok adapter

## Role eligibility

executor: no
pair_judge: yes

Certification status: the pair-judge seat is wired, reachable, and probe-capable, but not emission-certified; isolation has three independent invariants — tool callability, MCP connection/enumeration, and context injection — and only P-0080-C can certify them; the doctor cannot. Before this change, the shipped recipe connected 65 MCP tools and injected both an MCP reminder and a plugin-skills reminder into the judge's conversation; a durable `pair grok` pin remains gated on follow-up emission registration and the standing seat-fitness rule.

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
#   plus $ISO_HOME/hooks/anchor-guard.json. grok reads that file as JSON, not
#   through a shell, so its "command" must carry an ALREADY-EXPANDED path:
#   {"hooks":{"PreToolUse":[{"hooks":[{"type":"command",
#     "command":"python3 /abs/path/to/_shared/grok-anchor-guard.py","timeout":10}]}]}}
# $NEUTRAL  = empty dir outside any git repo
# $REPO     = absolute repo root (redirects MUST be absolute — cwd is $NEUTRAL)
cd "$NEUTRAL"
HOME="$NEUTRAL" ZDOTDIR="$NEUTRAL" GROK_HOME="$ISO_HOME" \
DEVLYN_PROBE_ANCHOR="<the bare anchor, derived exactly as the --allow rule below>" \
GROK_CLAUDE_MCPS_ENABLED=false GROK_CURSOR_MCPS_ENABLED=false \
GROK_CLAUDE_SKILLS_ENABLED=false GROK_CURSOR_SKILLS_ENABLED=false \
GROK_CLAUDE_HOOKS_ENABLED=false GROK_CURSOR_HOOKS_ENABLED=false \
GROK_CLAUDE_AGENTS_ENABLED=false GROK_CLAUDE_RULES_ENABLED=false \
GROK_MEMORY=0 \
python3 "$DEVLYN_SHARED_DIR/run-bounded.py" 600 -- grok -p "<judge prompt>" \
  --permission-mode dontAsk --no-memory \
  --tools "read_file,grep,list_dir,run_terminal_cmd" \
  --disallowed-tools "Agent,use_tool,search_tool" \
  --allow 'Bash(<the bare anchor>)' \
  --reasoning-effort medium \
  --output-format streaming-messages-json \
  > "$REPO/.devlyn/grok-judge.stdout" 2> "$REPO/.devlyn/grok-judge.stderr"
```

Copy `auth.json` into `$ISO_HOME` for every run and seed its `config.toml` with
the shown `[plugins]` and `[skills] ignore` entries and its
`hooks/anchor-guard.json` with the shown `PreToolUse` entry. Before launch, create
`$NEUTRAL/.zshenv` containing `export HOME=<the operator's real home>`.
Both overrides are needed because grok scans `~/.claude.json` from `$HOME`,
while zsh reads rc files from `$ZDOTDIR`, which is exported in some environments.
`$NEUTRAL` and `$ISO_HOME` must be on paths that do not embed a project or repo identifier.
`--permission-mode plan` is forbidden headless because it silently blocks
all tools and returns an empty review; `--always-approve` is banned because it
auto-approves writes. `--tools` and `--disallowed-tools` are headless-only (the
TUI warns and ignores them); when both are present, the disallow list wins and
removes tools entirely rather than merely gating execution.

Never use `--json-schema` for the pair judge: measured runs degraded the
tool-use loop (2/3 made zero tool calls and fabricated findings), and a
`Cancelled` run emitted a PASS-shaped payload after its schema had failed.

The judge prompt must name the exact permitted command(s). Derive the prompt
anchor and allow-list string identically from one source, in this precedence:
the solo-headroom hypothesis's backticked observable command when present;
otherwise the backticked commands in the spec's `## Verification` bullets;
otherwise the repo's existing test/CLI runner. If none exists, the probe
obligation does not arise and a static review is correct for that spec.
The documented `Bash(<command>)` form matches the exact command or its prefix;
the trailing ` *` form fails a no-argument command.
Under `dontAsk`, every allow shape tested for a chained command — including an
exact full-string rule for the chain — returned `PermissionCancelled`, so the
mandatory dominance-loss anchor must run unchained with the allow rule scoped
to that bare anchor.

Grok's deny semantics are not Claude-parity: reaching the permission mode's
auto-deny silently truncates the review at exit 0. On the configured, measured
path the `PreToolUse` hook above keeps the judge from reaching it — the hook runs
at step 1, before the rules and before the mode policy, and returns the denial as
a model-visible `tool_result`.
It admits the bare anchor and anchor-plus-argv, and vetoes any character that
could start a second command, so `verify.md`'s bounded input variations survive
while chaining does not. The hook fails open, so the collector rejection remains
the fail-closed floor: treat it as `BLOCKED` for
`verify.pair.emission-contract`, never PASS. After a non-timeout spawn, run:

```bash
python3 "$DEVLYN_SHARED_DIR/collect-codex-findings.py" \
  --devlyn-dir "$REPO/.devlyn" \
  --stdout-file grok-judge.stdout
```

On exit 124, write `.devlyn/verify.pair.timeout.json` with
`{"engine": "grok", "budget_seconds": 600}` before merge. A budget abort can
leave the stream truncated before its terminal `result` record; that capture
stays `TIMEOUT` at merge, never a pair PASS.
