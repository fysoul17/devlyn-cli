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
      devlyn:auto-resolve/references/build-gate.md \
      devlyn:auto-resolve/references/pipeline-state.md \
      devlyn:auto-resolve/references/phases/phase-1-build.md \
      devlyn:auto-resolve/references/phases/phase-2-evaluate.md \
      devlyn:auto-resolve/references/phases/phase-3-critic.md \
      devlyn:auto-resolve/scripts/spec-verify-check.py \
      devlyn:auto-resolve/scripts/forbidden-pattern-check.py \
      devlyn:auto-resolve/scripts/build-gate-verifiers.sh \
      devlyn:ideate/SKILL.md \
      devlyn:ideate/references/codex-critic-template.md \
      devlyn:preflight/SKILL.md \
      devlyn:preflight/references/report-template.md \
      devlyn:preflight/references/auditors/code-auditor.md \
      devlyn:preflight/references/auditors/browser-auditor.md \
      devlyn:team-resolve/SKILL.md \
      devlyn:team-review/SKILL.md \
      _shared/codex-config.md \
      _shared/codex-monitored.sh \
      _shared/pair-plan-schema.md \
      _shared/runtime-principles.md; do
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
  # iter-0028 R1: build-gate-verifiers.sh likewise — invoked by the
  # BUILD_GATE Agent via `bash .../build-gate-verifiers.sh`, fails silently
  # to exit-127 if the bit is missing.
  if [ -f ".claude/skills/devlyn:auto-resolve/scripts/build-gate-verifiers.sh" ] \
     && [ ! -x ".claude/skills/devlyn:auto-resolve/scripts/build-gate-verifiers.sh" ]; then
    bad "devlyn:auto-resolve/scripts/build-gate-verifiers.sh — not executable in installed mirror"
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
# 10. No raw `codex exec` invocation in skill prompts (iter-0010).
#     iter-0009 wrapper + iter-0010 production rollout require every Codex
#     invocation in skill SKILL.md / references to use codex-monitored.sh.
#     Raw `codex exec ...` in a prompt re-introduces the iter-0008 byte-watchdog
#     starvation: orchestrator pattern-primes from the doc and emits the raw
#     shape, which can collapse into `... | tail -200` and starve the outer API
#     stream. Descriptive phrases like "passes args through to `codex exec`
#     verbatim" are allowed — only invocation-shaped uses are forbidden.
#
#     Pattern: `codex exec[[:space:]]+\S` — catches any invocation shape
#     (whitespace then a non-space character after `exec`). Passes backtick-
#     closed descriptive prose like `` `codex exec` `` because the closing
#     backtick is non-whitespace adjacent to `exec`, not whitespace.
#     Concrete shapes caught:
#       - single-line flag:    `codex exec -C ...`
#       - resume form:         `codex exec resume --last`
#       - multi-line cont.:    `codex exec \` (space + `\` at EOL)
#       - quoted prompt:       `codex exec "prompt"`           ← iter-0011
#       - variable expansion:  `codex exec $PROMPT`            ← iter-0011
#       - literal token:       `codex exec prompt`             ← iter-0011
#     Excludes: _shared/codex-config.md (canonical doc may discuss the rule
#     itself), workspace/, archive snapshots.
# ---------------------------------------------------------------------------
section "Check 10: No raw codex exec invocation in skill prompts"
offenders=$(grep -RInE 'codex exec[[:space:]]+[^[:space:]]' \
  config/skills 2>/dev/null \
  | grep -v 'config/skills/_shared/codex-config.md' \
  | grep -v 'config/skills/_shared/codex-monitored.sh' \
  | grep -v 'roadmap-archival-workspace/' \
  | grep -v 'devlyn:auto-resolve-workspace/' \
  | grep -v 'devlyn:ideate-workspace/' \
  | grep -v 'preflight-workspace/' \
  || true)
if [ -z "$offenders" ]; then
  ok "no raw codex exec invocations in skill prompts (wrapper-form everywhere)"
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
# 12. CLAUDE.md ↔ _shared/runtime-principles.md per-section excerpt parity (iter-0019.A).
# Sub-agent prompts inline the runtime contract from runtime-principles.md; that file
# must mirror the corresponding CLAUDE.md sections. Drift in one source-of-truth without
# the other produces silent behavioral divergence between session-level and sub-agent
# enforcement. Per-section markers `<!-- runtime-principles:section=NAME:begin/end -->`
# wrap each of the 4 sections (subtractive-first, goal-locked, no-workaround, evidence)
# in BOTH files. Check 12 extracts each named block from both files and diffs.
# ---------------------------------------------------------------------------
section "Check 12: CLAUDE.md ↔ runtime-principles.md per-section excerpt parity"
rp_src="config/skills/_shared/runtime-principles.md"
claude_src="CLAUDE.md"
rp_drift=0
expected_sections="subtractive-first goal-locked no-workaround evidence"

if [ ! -f "$rp_src" ]; then
  bad "$rp_src — missing"
  rp_drift=1
elif [ ! -f "$claude_src" ]; then
  bad "$claude_src — missing"
  rp_drift=1
else
  # Topology: each marker appears exactly once per file.
  for name in $expected_sections; do
    for kind in begin end; do
      marker="<!-- runtime-principles:section=${name}:${kind} -->"
      for f in "$rp_src" "$claude_src"; do
        count=$(grep -Fxc "$marker" "$f" 2>/dev/null || echo 0)
        if [ "$count" -ne 1 ]; then
          bad "${f}: marker '${marker}' appears ${count} times (expected 1)"
          rp_drift=1
        fi
      done
    done
  done

  # Topology: in runtime-principles.md, all 4 sections must sit INSIDE the
  # outer `:contract:` block AND appear in the canonical order. CLAUDE.md
  # placement is free (sections may live in any order, anywhere in the file).
  contract_begin_line=$(grep -Fxn '<!-- runtime-principles:contract:begin -->' "$rp_src" | head -1 | cut -d: -f1)
  contract_end_line=$(grep -Fxn '<!-- runtime-principles:contract:end -->' "$rp_src" | head -1 | cut -d: -f1)
  if [ -z "$contract_begin_line" ] || [ -z "$contract_end_line" ]; then
    bad "${rp_src}: outer ':contract:begin/end' markers missing"
    rp_drift=1
  else
    prev_line=0
    for name in $expected_sections; do
      sec_begin_line=$(grep -Fxn "<!-- runtime-principles:section=${name}:begin -->" "$rp_src" | head -1 | cut -d: -f1)
      sec_end_line=$(grep -Fxn "<!-- runtime-principles:section=${name}:end -->" "$rp_src" | head -1 | cut -d: -f1)
      if [ -n "$sec_begin_line" ] && [ -n "$sec_end_line" ]; then
        if [ "$sec_begin_line" -le "$contract_begin_line" ] || [ "$sec_end_line" -ge "$contract_end_line" ]; then
          bad "${rp_src}: section '${name}' is outside the ':contract:' block"
          rp_drift=1
        fi
        if [ "$sec_begin_line" -lt "$prev_line" ]; then
          bad "${rp_src}: section '${name}' is out of canonical order (expected: ${expected_sections})"
          rp_drift=1
        fi
        prev_line=$sec_end_line
      fi
    done
  fi

  # Content: byte-compare each section block via diff over temp files.
  # awk-into-tmpfile preserves trailing newlines (command substitution strips them).
  tmp_rp=$(mktemp)
  tmp_claude=$(mktemp)
  for name in $expected_sections; do
    begin="<!-- runtime-principles:section=${name}:begin -->"
    end="<!-- runtime-principles:section=${name}:end -->"
    awk -v b="$begin" -v e="$end" '$0==b{f=1;next}$0==e{f=0}f' "$rp_src" > "$tmp_rp"
    awk -v b="$begin" -v e="$end" '$0==b{f=1;next}$0==e{f=0}f' "$claude_src" > "$tmp_claude"
    if [ ! -s "$tmp_rp" ]; then
      bad "${name}: empty/missing block in $rp_src"
      rp_drift=1
      continue
    fi
    if [ ! -s "$tmp_claude" ]; then
      bad "${name}: empty/missing block in $claude_src"
      rp_drift=1
      continue
    fi
    if ! diff -q "$tmp_rp" "$tmp_claude" >/dev/null 2>&1; then
      bad "${name}: CLAUDE.md and runtime-principles.md content differ"
      rp_drift=1
    fi
  done
  rm -f "$tmp_rp" "$tmp_claude"

  if [ $rp_drift -eq 0 ]; then
    ok "all 4 contract sections in parity (subtractive-first / goal-locked / no-workaround / evidence) — markers, topology, content"
  fi
fi

# ---------------------------------------------------------------------------
# 13. pair-plan idgen output is deterministic across consecutive runs (iter-0022).
#     Same input → byte-identical canonical_id_registry.json. Catches accidental
#     dict-order, float-printing, or timestamp-leak regressions in idgen.
#     Runs twice on F2 with --generated-at pinned and compares sha256.
# ---------------------------------------------------------------------------
section "Check 13: pair-plan-idgen.py output deterministic across runs (F2)"
idgen="benchmark/auto-resolve/scripts/pair-plan-idgen.py"
fixture="benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand"
if [ ! -x "$idgen" ] && [ ! -f "$idgen" ]; then
  bad "Check 13 prerequisite missing: $idgen"
elif [ ! -d "$fixture" ]; then
  bad "Check 13 prerequisite missing: $fixture"
else
  tmp1=$(mktemp); tmp2=$(mktemp)
  if python3 "$idgen" --fixture "$fixture" --generated-at 2026-04-29T18:30:00Z --output "$tmp1" >/dev/null 2>&1 \
     && python3 "$idgen" --fixture "$fixture" --generated-at 2026-04-29T18:30:00Z --output "$tmp2" >/dev/null 2>&1; then
    sha1=$(shasum -a 256 "$tmp1" | awk '{print $1}')
    sha2=$(shasum -a 256 "$tmp2" | awk '{print $1}')
    if [ "$sha1" = "$sha2" ]; then
      ok "F2 registry sha256 stable across two idgen runs ($sha1)"
    else
      bad "F2 registry sha256 drift: run1=$sha1 run2=$sha2"
    fi
  else
    bad "idgen invocation failed; cannot verify determinism"
  fi
  rm -f "$tmp1" "$tmp2"
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
