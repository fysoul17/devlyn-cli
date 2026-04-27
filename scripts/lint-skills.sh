#!/usr/bin/env bash
# lint-skills.sh — structural quality checks for the devlyn harness.
#
# Gates the three things that have drifted in the past:
#   1. Forbidden MCP / stale-model references in skills, README, installer.
#   2. Missing `name:` in skill frontmatter (Anthropic spec violation).
#   3. Source ↔ installed mirror drift on the harness critical path.
#
# Exit 0 = clean. Non-zero = fails; prints offending file:line per check.

set -u
cd "$(dirname "$0")/.."

red=$(printf '\033[31m'); green=$(printf '\033[32m'); dim=$(printf '\033[2m'); reset=$(printf '\033[0m')
fail=0

section() { printf '\n%s=== %s ===%s\n' "$dim" "$1" "$reset"; }
ok()      { printf '  %s✓%s %s\n' "$green" "$reset" "$1"; }
bad()     { printf '  %s✗%s %s\n' "$red"   "$reset" "$1"; fail=1; }

# ---------------------------------------------------------------------------
# 1. No MCP references in managed source or user-facing docs.
# ---------------------------------------------------------------------------
section "Check 1: No mcp__codex-cli__ outside _shared / archive"
# Legal places: config/skills/_shared/codex-config.md (explicitly says "MCP is not used"),
# archival snapshots, and tests.
offenders=$(grep -RIln 'mcp__codex-cli__' \
  config/skills \
  benchmark \
  README.md \
  CLAUDE.md \
  bin/ 2>/dev/null \
  | grep -v 'config/skills/_shared/codex-config.md' \
  | grep -v 'config/skills/roadmap-archival-workspace/' \
  | grep -v 'config/skills/devlyn:auto-resolve-workspace/' \
  | grep -v 'config/skills/devlyn:ideate-workspace/' \
  | grep -v 'config/skills/preflight-workspace/' \
  | grep -v 'benchmark/auto-resolve/PILOT-RESULTS' \
  || true)
if [ -z "$offenders" ]; then
  ok "no MCP references in managed files"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 2. No "Requires Codex MCP" prose.
# ---------------------------------------------------------------------------
section "Check 2: No 'Requires Codex MCP' prose"
offenders=$(grep -RIln 'Requires Codex MCP\|Codex MCP server\|Codex MCP available\|Codex MCP disconnected' \
  config/skills benchmark README.md CLAUDE.md bin/ 2>/dev/null \
  | grep -v 'config/skills/roadmap-archival-workspace/' \
  | grep -v 'config/skills/devlyn:auto-resolve-workspace/' \
  | grep -v 'config/skills/devlyn:ideate-workspace/' \
  | grep -v 'config/skills/preflight-workspace/' \
  | grep -v 'benchmark/auto-resolve/PILOT-RESULTS' \
  || true)
if [ -z "$offenders" ]; then
  ok "no Codex MCP prose"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 3. No stale model strings (gpt-5.0..5.4 hardcoded outside config).
# ---------------------------------------------------------------------------
section "Check 3: No hardcoded pre-5.5 model strings"
offenders=$(grep -RInE 'gpt-5\.[0-4][^.]' \
  config/skills CLAUDE.md README.md 2>/dev/null \
  | grep -v 'config/skills/_shared/codex-config.md' \
  | grep -v 'config/skills/roadmap-archival-workspace/' \
  | grep -v 'config/skills/devlyn:auto-resolve-workspace/' \
  | grep -v 'config/skills/devlyn:ideate-workspace/' \
  | grep -v 'config/skills/preflight-workspace/' \
  | grep -v 'evals\.json' \
  || true)
if [ -z "$offenders" ]; then
  ok "no hardcoded pre-5.5 strings"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 4. No stale Opus 4.6 benchmark references (should be 4.7 after P1).
# ---------------------------------------------------------------------------
section "Check 4: No stale 'Claude Opus 4.6' in routing table"
offenders=$(grep -RIln 'Claude Opus 4\.6' \
  config/skills 2>/dev/null \
  | grep -v 'config/skills/roadmap-archival-workspace/' \
  | grep -v 'config/skills/devlyn:auto-resolve-workspace/' \
  | grep -v 'config/skills/devlyn:ideate-workspace/' \
  | grep -v 'config/skills/preflight-workspace/' \
  || true)
if [ -z "$offenders" ]; then
  ok "routing table on Opus 4.7"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 5. Every devlyn:* skill has `name:` in frontmatter.
# ---------------------------------------------------------------------------
section "Check 5: devlyn:* SKILL.md has name: field"
missing=0
for skill in config/skills/devlyn:*/SKILL.md; do
  [ -f "$skill" ] || continue
  if ! head -20 "$skill" | grep -q '^name:'; then
    bad "$skill — missing 'name:' in frontmatter"
    missing=1
  fi
done
if [ $missing -eq 0 ]; then
  ok "all devlyn:* skills have name: field"
fi

# ---------------------------------------------------------------------------
# 6. Source ↔ installed mirror parity on critical path.
# Only runs if .claude/skills exists (i.e. installer has been run).
# ---------------------------------------------------------------------------
section "Check 6: Source ↔ installed mirror parity (critical path)"
if [ ! -d .claude/skills ]; then
  ok "no .claude/skills (fresh checkout) — skipping parity check"
else
  drift=0
  for rel in \
      devlyn:auto-resolve/SKILL.md \
      devlyn:auto-resolve/references/engine-routing.md \
      devlyn:ideate/SKILL.md \
      devlyn:preflight/SKILL.md \
      _shared/codex-config.md \
      _shared/codex-monitored.sh; do
    src="config/skills/$rel"
    dst=".claude/skills/$rel"
    if [ ! -f "$src" ] || [ ! -f "$dst" ]; then
      bad "missing file on critical path: $rel"; drift=1; continue
    fi
    if ! diff -q "$src" "$dst" >/dev/null 2>&1; then
      bad "$rel — source and installed differ"
      drift=1
    fi
  done
  # Scripts and evals must be present in installed auto-resolve
  for rel in scripts/terminal_verdict.py scripts/archive_run.py evals/evals.json; do
    if [ -f "config/skills/devlyn:auto-resolve/$rel" ] \
       && [ ! -f ".claude/skills/devlyn:auto-resolve/$rel" ]; then
      bad "installed mirror missing: devlyn:auto-resolve/$rel"
      drift=1
    fi
  done
  # iter-0009: codex-monitored.sh must be executable in the installed mirror
  # (skills tree gets cp -R'd into $WORK_DIR for the variant arm; bash will
  # refuse to run a non-executable wrapper).
  if [ -f ".claude/skills/_shared/codex-monitored.sh" ] \
     && [ ! -x ".claude/skills/_shared/codex-monitored.sh" ]; then
    bad "_shared/codex-monitored.sh — not executable in installed mirror"
    drift=1
  fi
  if [ $drift -eq 0 ]; then
    ok "critical path parity clean"
  fi
fi

# ---------------------------------------------------------------------------
# 8. CRITIC security sub-pass must be native, not Dual.
# Catches the specific drift where a section updates but a cross-reference doesn't.
# ---------------------------------------------------------------------------
section "Check 8: CRITIC security is native (no stale Dual references)"
# Match only the concrete bad patterns used when CRITIC security was routed to
# Dual (v3.4 and earlier):
#   1. Markdown table cell `| **Dual** |`
#   2. Prose  `Dual (Claude + Codex parallel, merged)`
# Retrospective mentions like "drops the Dual-model token cost" are fine.
offenders=$(grep -RInE '\|\s*\*\*Dual\*\*\s*\||Dual\s*\(Claude\s*\+\s*Codex' \
  config/skills 2>/dev/null \
  | grep -v 'roadmap-archival-workspace/' \
  | grep -v 'devlyn:auto-resolve-workspace/' \
  | grep -v 'devlyn:ideate-workspace/' \
  | grep -v 'preflight-workspace/' \
  || true)
if [ -z "$offenders" ]; then
  ok "CRITIC security uses native (no Dual stragglers)"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 9. Engine-downgrade string is canonical (codex-unavailable, not codex-ping failed).
# ---------------------------------------------------------------------------
section "Check 9: Downgrade string uses 'codex-unavailable'"
offenders=$(grep -RIln 'codex-ping failed\|codex-ping fail' \
  config/skills CLAUDE.md README.md bin/ 2>/dev/null \
  | grep -v 'roadmap-archival-workspace/' \
  | grep -v 'devlyn:auto-resolve-workspace/' \
  | grep -v 'devlyn:ideate-workspace/' \
  | grep -v 'preflight-workspace/' \
  || true)
if [ -z "$offenders" ]; then
  ok "all downgrade strings canonical"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 7. Findings-producing standalones declare pipeline-compatible sidecar.
# Ensures CLAUDE.md's "share the .devlyn/*.findings.jsonl schema" claim stays true.
# ---------------------------------------------------------------------------
section "Check 7: Findings-producing standalones declare JSONL sidecar"
missing=0
for skill in evaluate review clean team-review; do
  f="config/skills/devlyn:$skill/SKILL.md"
  [ -f "$f" ] || { bad "$f — SKILL.md missing"; missing=1; continue; }
  if ! grep -q 'Pipeline-Compatible Sidecar' "$f"; then
    bad "$f — missing 'Pipeline-Compatible Sidecar' section"
    missing=1
    continue
  fi
  if ! grep -q "\.devlyn/${skill//-/_}\.findings\.jsonl" "$f"; then
    bad "$f — sidecar section missing '.devlyn/${skill//-/_}.findings.jsonl' path"
    missing=1
  fi
done
if [ $missing -eq 0 ]; then
  ok "all 4 findings-producing standalones emit JSONL sidecar"
fi

# ---------------------------------------------------------------------------
# Summary.
# ---------------------------------------------------------------------------
echo
if [ $fail -eq 0 ]; then
  printf '%sAll checks passed.%s\n' "$green" "$reset"
  exit 0
else
  printf '%sLint failed.%s Fix the offenders above.\n' "$red" "$reset"
  exit 1
fi
