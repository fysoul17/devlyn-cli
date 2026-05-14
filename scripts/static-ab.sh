#!/usr/bin/env bash
# static-ab.sh — Measure prompt-size delta between baseline HEAD and working tree.
#
# Answers: "did our harness changes shrink or grow the cold-start prompt budget
# that a typical /devlyn:resolve run actually loads?"
#
# Files measured (current two-skill resolve load set):
#   - devlyn:resolve/SKILL.md
#   - devlyn:resolve/references/{state-schema.md, free-form-mode.md}
#   - devlyn:resolve/references/phases/{plan,probe-derive,implement,build-gate,cleanup,verify}.md
#   - _shared/codex-config.md
#   - _shared/engine-preflight.md
#   - _shared/runtime-principles.md
#   - CLAUDE.md
#
# Uses word count ~= 1.3 tokens/word as the rough conversion. This is a static
# prompt-budget measurement, NOT a real pipeline token count (harness-level
# token exposure is not available to a running skill).

set -u
cd "$(dirname "$0")/.."

FILES=(
  CLAUDE.md
  config/skills/_shared/codex-config.md
  config/skills/_shared/engine-preflight.md
  config/skills/_shared/runtime-principles.md
  config/skills/devlyn:resolve/SKILL.md
  config/skills/devlyn:resolve/references/state-schema.md
  config/skills/devlyn:resolve/references/free-form-mode.md
  config/skills/devlyn:resolve/references/phases/plan.md
  config/skills/devlyn:resolve/references/phases/probe-derive.md
  config/skills/devlyn:resolve/references/phases/implement.md
  config/skills/devlyn:resolve/references/phases/build-gate.md
  config/skills/devlyn:resolve/references/phases/cleanup.md
  config/skills/devlyn:resolve/references/phases/verify.md
)

WORDS_A=0
WORDS_B=0
LINES_A=0
LINES_B=0
MAX_GROWTH_PCT="${DEVLYN_STATIC_AB_MAX_GROWTH_PCT:-15}"

if ! awk "BEGIN { exit !($MAX_GROWTH_PCT >= 0) }" >/dev/null 2>&1; then
  echo "error: DEVLYN_STATIC_AB_MAX_GROWTH_PCT must be a non-negative number" >&2
  exit 2
fi

printf '%-60s %10s %10s %10s\n' 'file' 'lines(A)' 'lines(B)' 'Δ_lines'
printf '%-60s %10s %10s %10s\n' '----' '--------' '--------' '-------'

for f in "${FILES[@]}"; do
  # A = baseline at HEAD (last committed state).
  if git show "HEAD:$f" >/dev/null 2>&1; then
    a_text=$(git show "HEAD:$f")
  else
    a_text=""
  fi
  # B = working tree (what will ship after commit).
  if [ -f "$f" ]; then
    b_text=$(cat "$f")
  else
    b_text=""
  fi
  la=$(printf '%s' "$a_text" | wc -l | tr -d ' ')
  lb=$(printf '%s' "$b_text" | wc -l | tr -d ' ')
  wa=$(printf '%s' "$a_text" | wc -w | tr -d ' ')
  wb=$(printf '%s' "$b_text" | wc -w | tr -d ' ')
  LINES_A=$((LINES_A + la))
  LINES_B=$((LINES_B + lb))
  WORDS_A=$((WORDS_A + wa))
  WORDS_B=$((WORDS_B + wb))
  diff=$((lb - la))
  printf '%-60s %10d %10d %10d\n' "$f" "$la" "$lb" "$diff"
done

# Rough token estimate: ~1.3 tokens per word.
tokens_a=$(awk "BEGIN { printf \"%d\", $WORDS_A * 1.3 }")
tokens_b=$(awk "BEGIN { printf \"%d\", $WORDS_B * 1.3 }")
delta_words=$((WORDS_B - WORDS_A))
delta_tokens=$((tokens_b - tokens_a))
delta_lines=$((LINES_B - LINES_A))

echo
printf '%-60s %10s %10s %10s\n' 'TOTAL'   "$LINES_A"  "$LINES_B"  "$delta_lines"
printf '%-60s %10s %10s %10s\n' 'words'   "$WORDS_A"  "$WORDS_B"  "$delta_words"
printf '%-60s %10s %10s %10s\n' 'tokens≈' "$tokens_a" "$tokens_b" "$delta_tokens"
echo
if [ "$delta_tokens" -le 0 ]; then
  echo "✓ Bare-case guardrail: prompt budget did NOT grow (Δ≈${delta_tokens} tokens)."
else
  pct=$(awk "BEGIN { printf \"%.1f\", ($delta_tokens / $tokens_a) * 100 }")
  over_limit=$(awk "BEGIN { exit !($pct > $MAX_GROWTH_PCT) }"; echo $?)
  if [ "$over_limit" -eq 0 ]; then
    echo "⚠ Bare-case guardrail: prompt budget grew by ≈${delta_tokens} tokens (+${pct}%, limit +${MAX_GROWTH_PCT}%)."
  else
    echo "✓ Bare-case guardrail: prompt budget growth is within limit (Δ≈${delta_tokens} tokens, +${pct}%, limit +${MAX_GROWTH_PCT}%)."
  fi
fi
