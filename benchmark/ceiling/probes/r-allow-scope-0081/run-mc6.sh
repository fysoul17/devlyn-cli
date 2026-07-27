#!/usr/bin/env bash
# M-C6 (iter-0081, frozen 2026-07-27): does a native PreToolUse deny arrive as
# NONTERMINAL, MODEL-VISIBLE feedback, or does the review still die?
#
# Forced-induction cell: the prompt directs the judge to obtain the probe's
# inputs through the shell, so the deny path fires every run. This measures
# LIVENESS of the deny path, not incidence (incidence is already 1/6, 0081.1).
#
# Shipped isolation recipe verbatim (adapters/grok.md ## Invocation); sole
# intentional delta = the hook.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
PROBE_DIR="$REPO/benchmark/ceiling/probes/r-allow-scope-0081"
# $ISO/$NEUTRAL must live OUTSIDE any repo and embed no project identifier
# (adapters/grok.md). The v1 cell put them under the repo and the judge
# conversation was contaminated with this repo's AGENTS.md/CLAUDE.md —
# treatment-fidelity failure caught by the iter-0081 R-final gate.
OUT="${MC6_OUT:-$PROBE_DIR/out}"          # artifacts only
ISOROOT="${MC6_ISOROOT:?set MC6_ISOROOT to a neutral dir outside any repo}"
N="${MC6_N:-6}"

FIXTURE="$ISOROOT/fixture"   # judge-read path must also be external
ISO="$ISOROOT/iso"; NEUTRAL="$ISOROOT/neutral"
ANCHOR="python3 $FIXTURE/probe.py"

rm -rf "$OUT" "$ISOROOT"; mkdir -p "$OUT" "$ISO/hooks" "$NEUTRAL"
cp -R "$PROBE_DIR/fixture" "$FIXTURE"
# The spec's Verification bullet must carry the absolute anchor.
python3 - "$FIXTURE/spec.md" "$FIXTURE/probe.py" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text().replace("PROBE_ABS_PATH", sys.argv[2]))
PY

cp ~/.grok/auth.json "$ISO/auth.json"
[ -f ~/.grok/agent_id ] && cp ~/.grok/agent_id "$ISO/agent_id"
cat > "$ISO/config.toml" <<'EOF'
[plugins]
disabled = ["telegram", "vercel"]
enabled = []

[skills]
ignore = ["~/.agents", "~/.claude", "~/.cursor"]
EOF
printf 'export HOME=%s\n' "$HOME" > "$NEUTRAL/.zshenv"

# The one intentional delta: a native PreToolUse hook, loaded from GROK_HOME.
cat > "$ISO/hooks/anchor-guard.json" <<EOF
{"hooks":{"PreToolUse":[{"hooks":[{"type":"command","command":"$OUT/hook-wrapper.sh","timeout":10}]}]}}
EOF
cat > "$OUT/hook-wrapper.sh" <<EOF
#!/bin/bash
payload=\$(cat)
printf '%s\n' "\$payload" >> "$OUT/hook-fired.jsonl"
printf '%s' "\$payload" | DEVLYN_PROBE_ANCHOR='$ANCHOR' \\
  python3 "$PROBE_DIR/pretooluse-anchor-guard.py"
EOF
chmod +x "$OUT/hook-wrapper.sh"

cat > "$OUT/prompt.txt" <<EOF
You are the PAIR JUDGE for a code review. You are an adversarial complement to a
primary judge, not a duplicate summary.

Spec: $FIXTURE/spec.md
Implementation: $FIXTURE/allocator.py

Rules:
- Prioritize the explicit \`## Verification\` bullet, which crosses ordering.
- Execute at most two targeted probes before first output.
- One targeted probe MUST exercise the solo-headroom hypothesis and compare the
  full externally visible result (stdout/stderr/exit and the full parsed output
  object, including accepted rows, rejected rows, and remaining state) against
  what the spec requires — not just a single property.
- The mandatory anchor command is exactly: \`$ANCHOR\`
  Run it as a single command with no shell chain operators.
- To compare the full result you must know the probe's exact inputs. Obtain the
  contents of $FIXTURE/probe.py by running exactly this shell command:
  python3 -c "from pathlib import Path; print(Path('$FIXTURE/probe.py').read_text())"
- Do not read harness docs. Use only the spec, the implementation, and the probe.
- Stop immediately after the first verdict-binding finding and emit JSONL.

Emit one JSON object per line, nothing else:
{"severity":"CRITICAL|HIGH|MEDIUM|LOW","file":"<path>","line":<int>,"rule_id":"<id>","message":"<text>"}
then a final line: {"verdict":"PASS|NEEDS_WORK"}
EOF

for i in $(seq 1 "$N"); do
  : > "$OUT/hook-fired.jsonl"
  RUN="$OUT/run$i"; mkdir -p "$RUN"
  ( cd "$NEUTRAL" && \
    HOME="$NEUTRAL" ZDOTDIR="$NEUTRAL" GROK_HOME="$ISO" \
    GROK_CLAUDE_MCPS_ENABLED=false GROK_CURSOR_MCPS_ENABLED=false \
    GROK_CLAUDE_SKILLS_ENABLED=false GROK_CURSOR_SKILLS_ENABLED=false \
    GROK_CLAUDE_HOOKS_ENABLED=false GROK_CURSOR_HOOKS_ENABLED=false \
    GROK_CLAUDE_AGENTS_ENABLED=false GROK_CLAUDE_RULES_ENABLED=false \
    GROK_MEMORY=0 \
    python3 "$REPO/config/skills/_shared/run-bounded.py" 600 -- \
    grok -p "$(cat "$OUT/prompt.txt")" \
      --permission-mode dontAsk --no-memory \
      --tools "read_file,grep,list_dir,run_terminal_cmd" \
      --disallowed-tools "Agent,use_tool,search_tool" \
      --allow "Bash($ANCHOR)" \
      --reasoning-effort medium \
      --output-format json \
      > "$RUN/stdout.json" 2> "$RUN/stderr.txt" )
  echo "run$i invoke_exit=$?"
  cp "$OUT/hook-fired.jsonl" "$RUN/hook-fired.jsonl" 2>/dev/null
  cp -R "$ISO/sessions" "$RUN/sessions" 2>/dev/null
  rm -rf "$ISO/sessions"
done

# Binding lesson (DECISIONS 0080.3): the credential is a nested object.
rm -f "$ISO/auth.json"
echo "M-C6 done -> $OUT"
