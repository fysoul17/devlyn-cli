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
offenders=$(git grep -Il -- 'mcp__codex-cli__' -- \
  config/skills \
  benchmark \
  README.md \
  CLAUDE.md \
  bin/ \
  ':!config/skills/_shared/codex-config.md' \
  ':!config/skills/roadmap-archival-workspace/**' \
  ':!config/skills/devlyn:auto-resolve-workspace/**' \
  ':!config/skills/devlyn:ideate-workspace/**' \
  ':!config/skills/preflight-workspace/**' \
  ':!benchmark/auto-resolve/external/**' \
  ':!benchmark/auto-resolve/results/**' \
  ':!benchmark/auto-resolve/PILOT-RESULTS*' \
  2>/dev/null || true)
if [ -z "$offenders" ]; then
  ok "no MCP references in managed files"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 2. No "Requires Codex MCP" prose.
# ---------------------------------------------------------------------------
section "Check 2: No 'Requires Codex MCP' prose"
offenders=$(git grep -Il -- 'Requires Codex MCP\|Codex MCP server\|Codex MCP available\|Codex MCP disconnected' -- \
  config/skills \
  benchmark \
  README.md \
  CLAUDE.md \
  bin/ \
  ':!config/skills/roadmap-archival-workspace/**' \
  ':!config/skills/devlyn:auto-resolve-workspace/**' \
  ':!config/skills/devlyn:ideate-workspace/**' \
  ':!config/skills/preflight-workspace/**' \
  ':!benchmark/auto-resolve/external/**' \
  ':!benchmark/auto-resolve/results/**' \
  ':!benchmark/auto-resolve/PILOT-RESULTS*' \
  2>/dev/null || true)
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
  # iter-0034 Phase 4 cutover (2026-05-03): legacy skill paths dropped.
  # Surface is the 2-skill product (`/devlyn:resolve` + `/devlyn:ideate`)
  # plus the `_shared/` kernel.
  for rel in \
      _shared/spec-verify-check.py \
      _shared/collect-codex-findings.py \
      _shared/verify-merge-findings.py \
      devlyn:ideate/SKILL.md \
      devlyn:ideate/references/spec-template.md \
      devlyn:ideate/references/elicitation.md \
      devlyn:ideate/references/project-mode.md \
      devlyn:ideate/references/from-spec-mode.md \
      devlyn:resolve/SKILL.md \
      devlyn:resolve/references/state-schema.md \
      devlyn:resolve/references/free-form-mode.md \
      devlyn:resolve/references/phases/plan.md \
      devlyn:resolve/references/phases/probe-derive.md \
      devlyn:resolve/references/phases/implement.md \
      devlyn:resolve/references/phases/build-gate.md \
      devlyn:resolve/references/phases/cleanup.md \
      devlyn:resolve/references/phases/verify.md \
      _shared/expected.schema.json \
      _shared/adapters/README.md \
      _shared/adapters/opus-4-7.md \
      _shared/adapters/gpt-5-5.md \
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
# 6b. VERIFY merge verdict binding self-test.
#     F23 full-pipeline prompt-fix rerun exposed a real failure where Codex
#     pair-JUDGE emitted HIGH findings but state kept pair_judge as
#     PASS_WITH_ISSUES. Routing severity must be deterministic, not prose.
# ---------------------------------------------------------------------------
section "Check 6b: VERIFY merge makes pair HIGH verdict-binding"
if python3 config/skills/_shared/verify-merge-findings.py --self-test >/dev/null 2>&1; then
  ok "verify-merge-findings.py self-test passed"
else
  bad "verify-merge-findings.py self-test failed"
fi

section "Check 6c: Codex stdout collection writes canonical pair findings"
if python3 config/skills/_shared/collect-codex-findings.py --self-test >/dev/null 2>&1; then
  ok "collect-codex-findings.py self-test passed"
else
  bad "collect-codex-findings.py self-test failed"
fi

section "Check 6d: Spec verification executes hidden-blind risk probes"
if python3 config/skills/_shared/spec-verify-check.py --self-test >/dev/null 2>&1; then
  ok "spec-verify-check.py risk-probe self-test passed"
else
  bad "spec-verify-check.py risk-probe self-test failed"
fi

section "Check 6e: All-or-nothing probes prove mutable rollback"
probe_doc="config/skills/devlyn:resolve/references/phases/probe-derive.md"
if grep -Fq "pre-rejected by a whole-order availability shortcut" "$probe_doc" \
   && grep -Fq "must allocate a scarce" "$probe_doc" \
   && grep -Fq "must request the same scarce first-line SKU" "$probe_doc"; then
  ok "all-or-nothing probe contract preserves mutable rollback evidence"
else
  bad "$probe_doc — missing mutable rollback probe contract"
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
# (Check 7 retired iter-0034 Phase 4 cutover: the 4 findings-producing
# standalones — evaluate / review / clean / team-review — were deleted; the
# JSONL sidecar contract no longer has a surface to enforce.)
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
# 14. F9 fixture id matches the shipped 2-skill contract (iter-0033a, 2026-04-30).
#     `/devlyn:preflight` was folded into `/devlyn:resolve`'s VERIFY phase; the
#     legacy F9 dir name (`F9-e2e-ideate-to-preflight`) is misleading once
#     preflight is gone. The retired copy lives under `fixtures/retired/` for
#     replay; the live fixture must be `F9-e2e-ideate-to-resolve`. Any other
#     non-retired reference to the old id is a stale rename.
# ---------------------------------------------------------------------------
section "Check 14: F9 fixture id matches 2-skill contract"
f9_drift=0
if [ ! -d "benchmark/auto-resolve/fixtures/F9-e2e-ideate-to-resolve" ]; then
  bad "live F9 fixture missing at benchmark/auto-resolve/fixtures/F9-e2e-ideate-to-resolve"
  f9_drift=1
fi
# Stale references outside fixtures/retired/ are bugs. Examine line content
# (not just filename) so files that legitimately mention the retired *path*
# (e.g. fixtures/F9-e2e-ideate-to-resolve/NOTES.md explaining where the OLD
# version lives) pass while genuine stale references fail. Excluded scopes:
# benchmark/auto-resolve/results/ (historical run artifacts, frozen) and
# scripts/lint-skills.sh itself (carries the pattern in this check).
stale=$(git grep -In -- 'F9-e2e-ideate-to-preflight' -- \
  config/skills \
  benchmark \
  scripts \
  CLAUDE.md \
  README.md \
  ':!benchmark/auto-resolve/results/**' \
  2>/dev/null \
  | grep -v '^benchmark/auto-resolve/fixtures/retired/F9-e2e-ideate-to-preflight/' \
  | grep -v '^scripts/lint-skills\.sh:' \
  | grep -v 'fixtures/retired/F9-e2e-ideate-to-preflight' \
  || true)
if [ -n "$stale" ]; then
  while IFS= read -r f; do bad "stale F9-e2e-ideate-to-preflight reference: $f"; done <<< "$stale"
  f9_drift=1
fi
if [ $f9_drift -eq 0 ]; then
  ok "F9 fixture id is canonical (F9-e2e-ideate-to-resolve); no stale refs outside retired/"
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
