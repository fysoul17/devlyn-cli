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

make_temp_file() {
  local __var="$1"
  shift || true
  local path
  if ! path=$(command mktemp "$@"); then
    bad "mktemp failed: ${*:-<default>}"
    return 1
  fi
  printf -v "$__var" '%s' "$path"
}

make_temp_dir() {
  local __var="$1"
  shift || true
  local path
  if ! path=$(command mktemp -d "$@"); then
    bad "mktemp -d failed: ${*:-<default>}"
    return 1
  fi
  printf -v "$__var" '%s' "$path"
}

section "Check 0a: Temp allocation fails closed"
direct_mktemp=$(grep -nE '(^|[ =])mktemp( |$)|\$\([[:space:]]*mktemp' scripts/lint-skills.sh \
  | grep -v 'command mktemp' \
  | grep -v 'make_temp_' \
  | grep -v 'direct_mktemp=' || true)
if [ -z "$direct_mktemp" ]; then
  ok "lint-skills.sh uses temp allocation helpers instead of direct mktemp"
else
  while IFS= read -r f; do bad "$f"; done <<< "$direct_mktemp"
fi

# iter-0034 Phase 4 cutover (2026-05-03): legacy skill paths dropped.
# Surface is the 2-skill product (`/devlyn:resolve` + `/devlyn:ideate`)
# plus the `_shared/` kernel. Keep this list single-source so all installed
# mirror parity checks cover the same files.
critical_path_files=$(cat <<'EOF'
_shared/spec-verify-check.py
_shared/collect-codex-findings.py
_shared/verify-merge-findings.py
devlyn:ideate/SKILL.md
devlyn:ideate/references/spec-template.md
devlyn:ideate/references/elicitation.md
devlyn:ideate/references/project-mode.md
devlyn:ideate/references/from-spec-mode.md
devlyn:resolve/SKILL.md
devlyn:resolve/references/state-schema.md
devlyn:resolve/references/free-form-mode.md
devlyn:resolve/references/phases/plan.md
devlyn:resolve/references/phases/probe-derive.md
devlyn:resolve/references/phases/implement.md
devlyn:resolve/references/phases/build-gate.md
devlyn:resolve/references/phases/cleanup.md
devlyn:resolve/references/phases/verify.md
_shared/expected.schema.json
_shared/adapters/README.md
_shared/adapters/opus-4-7.md
_shared/adapters/gpt-5-5.md
_shared/codex-config.md
_shared/codex-monitored.sh
_shared/engine-preflight.md
_shared/pair-plan-schema.md
_shared/runtime-principles.md
EOF
)

check_skill_mirror_parity() {
  local target_dir="$1"
  local skip_msg="$2"
  local missing_prefix="$3"
  local differ_suffix="$4"
  local ok_msg="$5"
  local drift=0
  local rel src dst

  if [ ! -d "$target_dir" ]; then
    ok "$skip_msg"
    return
  fi

  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    src="config/skills/$rel"
    dst="$target_dir/$rel"
    if [ ! -f "$src" ] || [ ! -f "$dst" ]; then
      bad "$missing_prefix: $rel"; drift=1; continue
    fi
    if ! diff -q "$src" "$dst" >/dev/null 2>&1; then
      bad "$rel — $differ_suffix"
      drift=1
    fi
  done <<< "$critical_path_files"

  # iter-0009: codex-monitored.sh must be executable in installed mirrors
  # (skills trees get copied into work dirs for variant arms; bash refuses to
  # run a non-executable wrapper).
  if [ -f "$target_dir/_shared/codex-monitored.sh" ] \
     && [ ! -x "$target_dir/_shared/codex-monitored.sh" ]; then
    bad "_shared/codex-monitored.sh — not executable in ${target_dir} mirror"
    drift=1
  fi
  if [ $drift -eq 0 ]; then
    ok "$ok_msg"
  fi
}

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
# 2a. Packaged root instruction files must not contain pyx-memory secrets.
# ---------------------------------------------------------------------------
section "Check 2a: No pyx-memory secrets in packaged root instructions"
offenders=$(grep -RInE 'memory\.api\.pyxmate\.com|Authorization: Bearer pyx_[A-Za-z0-9]{12,}|X-API-Key: pyx_[A-Za-z0-9]{12,}|pyx_[A-Za-z0-9]{16,}' \
  AGENTS.md CLAUDE.md 2>/dev/null || true)
if [ -z "$offenders" ]; then
  ok "AGENTS.md and CLAUDE.md contain no pyx-memory secret material"
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
# 5a. devlyn:design-ui is a required skill, not an optional addon.
# ---------------------------------------------------------------------------
section "Check 5a: devlyn:design-ui is required"
if [ -f "config/skills/devlyn:design-ui/SKILL.md" ]; then
  ok "devlyn:design-ui source lives in config/skills"
else
  bad "devlyn:design-ui must be a required skill under config/skills"
fi
if [ ! -e "optional-skills/devlyn:design-ui" ]; then
  ok "devlyn:design-ui is not in optional-skills"
else
  bad "devlyn:design-ui must not be installed as an optional addon"
fi
if grep -Fq "skillsToInstall: ['devlyn:resolve', 'devlyn:ideate', 'devlyn:design-ui', '_shared']" bin/devlyn.js; then
  ok "Codex install includes devlyn:design-ui"
else
  bad "Codex skillsToInstall must include devlyn:design-ui"
fi
if ! grep -F "name: 'devlyn:design-ui'" bin/devlyn.js >/dev/null 2>&1; then
  ok "devlyn:design-ui is absent from OPTIONAL_ADDONS"
else
  bad "devlyn:design-ui must not be listed in OPTIONAL_ADDONS"
fi

# ---------------------------------------------------------------------------
# 6. Source ↔ installed mirror parity on critical path.
# Only runs if .claude/skills exists (i.e. installer has been run).
# ---------------------------------------------------------------------------
section "Check 6: Source ↔ installed mirror parity (critical path)"
check_skill_mirror_parity \
  ".claude/skills" \
  "no .claude/skills (fresh checkout) — skipping parity check" \
  "missing file on critical path" \
  "source and installed differ" \
  "critical path parity clean"

# Codex / agent runtimes in this repo can also expose a project-local
# `.agents/skills` mirror. If it exists, keep the same critical path in parity;
# otherwise a session can read stale pair/risk-probe contracts even while the
# source and `.claude/skills` mirrors are clean.
section "Check 6a: Source ↔ .agents mirror parity (critical path)"
check_skill_mirror_parity \
  ".agents/skills" \
  "no .agents/skills — skipping parity check" \
  "missing .agents critical-path file" \
  "source and .agents mirror differ" \
  ".agents critical path parity clean"

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
if ! grep -Fq 'def pair_trigger_skip_contract_violation' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'def pair_trigger_missing_contract_violation' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'def pair_trigger_reason_completeness_violation' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'def pair_trigger_present' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'KNOWN_PAIR_TRIGGER_REASONS = {' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'mode.pair-verify' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'state.get("pair_verify") is True' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'def pair_flag_contract_violation' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'verify-pair-trigger-conflicting-pair-flags' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq -- '--pair-verify and --no-pair are mutually exclusive' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'def has_known_pair_trigger_reason' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'def all_known_pair_trigger_reasons' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'return reason in KNOWN_PAIR_TRIGGER_REASONS' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq '"reasons": ["risk.high", 3]' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq '"reasons": ["risk.high", "looks-hard"]' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq '"reasons": ["risk high"]' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq '"reasons": ["risk_profile.high_risk", "risk_probes_enabled"]' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'verify-pair-trigger-reasons-unknown' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'verify-pair-trigger-reasons-incomplete' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'pair_trigger.reasons is missing applicable canonical reason(s)' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'pair_trigger.reasons must include a known pair-trigger reason' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'pair_trigger.reasons must only include known pair-trigger reasons' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'verify-pair-trigger-ineligible-unjustified' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'VERIFY state requires a pair decision' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'verify-pair-trigger-user-no-pair-unsupported' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'risk_profile.pair_default_enabled false from an explicit --no-pair opt-out' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'def risk_profile_contract_violation' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'verify-risk-profile-malformed' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'risk_profile.risk_probes_enabled must be a boolean' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'risk_profile.reasons must be a list of strings' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'def spec_frontmatter_complexity' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq '"complexity": "large"' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'complexity.large' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'spec.complexity.high' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'spec.complexity.large' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'verify-pair-trigger-required-missing' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'verify-pair-trigger-skipped-reason-unsupported' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'verify-pair-trigger-mechanical-blocker-unsupported' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'verify-pair-trigger-primary-judge-blocker-unsupported' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'eligible:false` with no supported skip reason' config/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'Canonical eligible reasons are `mode.verify-only`' config/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq '`mode.pair-verify`' config/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'Eligible triggers must contain only canonical' config/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'include every applicable canonical reason' config/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq '`mode.pair-verify`' config/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq '"pair_verify": false' config/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'requires a non-empty reasons list containing every applicable canonical eligible reason' config/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'containing every applicable canonical eligible reason' config/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'state.pair_verify == true' config/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'pair_verify: true` only when `--pair-verify` was passed' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'include every applicable canonical reason' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq '`--pair-verify` and `--no-pair` are mutually exclusive' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'mutually exclusive with `risk_profile.pair_default_enabled == false`' config/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'if both are present, stop with `BLOCKED:invalid-flags`' config/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'Contradictory, incomplete, or unknown trigger state is a VERIFY contract violation' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'user_no_pair` is valid only when `risk_profile.pair_default_enabled == false`' config/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'def reject_json_constant' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'loads_strict_json(raw)' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'invalid JSON numeric constant: NaN' config/skills/_shared/verify-merge-findings.py; then
  bad "verify-merge-findings.py must block missing pair_trigger and unsupported skip reasons"
fi
verify_merge_risk_profile_guard_missing=0
for file in \
  config/skills/_shared/verify-merge-findings.py \
  .claude/skills/_shared/verify-merge-findings.py \
  .agents/skills/_shared/verify-merge-findings.py; do
  if ! grep -Fq 'def risk_profile_contract_violation' "$file" \
    || ! grep -Fq 'verify-risk-profile-malformed' "$file" \
    || ! grep -Fq 'risk_profile.risk_probes_enabled must be a boolean' "$file" \
    || ! grep -Fq 'risk_profile.reasons must be a list of strings' "$file"; then
    bad "$file — verify-merge-findings.py must fail closed on malformed risk_profile"
    verify_merge_risk_profile_guard_missing=1
  fi
done
if [ $verify_merge_risk_profile_guard_missing -eq 0 ]; then
  ok "verify-merge-findings.py risk_profile shape guard is mirrored"
fi

section "Check 6c: Codex stdout collection writes canonical pair findings"
if python3 config/skills/_shared/collect-codex-findings.py --self-test >/dev/null 2>&1; then
  ok "collect-codex-findings.py self-test passed"
else
  bad "collect-codex-findings.py self-test failed"
fi
if ! grep -Fq 'def reject_json_constant' config/skills/_shared/collect-codex-findings.py \
  || ! grep -Fq 'loads_strict_json(raw)' config/skills/_shared/collect-codex-findings.py \
  || ! grep -Fq 'NaN Codex stdout finding must not normalize' config/skills/_shared/collect-codex-findings.py; then
  bad "collect-codex-findings.py must reject non-standard JSON constants in pair-JUDGE stdout"
fi

section "Check 6c1: Archive preserves pair/risk-probe artifacts safely"
if python3 config/skills/_shared/archive_run.py --self-test >/dev/null 2>&1; then
  ok "archive_run.py self-test passed"
else
  bad "archive_run.py self-test failed"
fi
if ! grep -Fq 'SAFE_RUN_ID_RE' config/skills/_shared/archive_run.py \
  || ! grep -Fq 'run_id must match [A-Za-z0-9_.-]+' config/skills/_shared/archive_run.py \
  || ! grep -Fq 'Archive devlyn:resolve run artifacts' config/skills/_shared/archive_run.py \
  || grep -Fq 'Archive auto-resolve run artifacts' config/skills/_shared/archive_run.py \
  || ! grep -Fq 'invalid JSON numeric constant: NaN' config/skills/_shared/archive_run.py \
  || ! grep -Fq '"verify.pair.findings.jsonl"' config/skills/_shared/archive_run.py \
  || ! grep -Fq '"verify-merge.summary.json"' config/skills/_shared/archive_run.py \
  || ! grep -Fq '"codex-judge.*"' config/skills/_shared/archive_run.py; then
  bad "archive_run.py must safely archive pair/risk-probe evidence and reject unsafe run ids"
fi

section "Check 6d: Spec verification executes hidden-blind risk probes"
if python3 config/skills/_shared/spec-verify-check.py --self-test >/dev/null 2>&1; then
  ok "spec-verify-check.py risk-probe and expected-contract self-test passed"
else
  bad "spec-verify-check.py risk-probe / expected-contract self-test failed"
fi
if ! grep -Fq 'def validate_present_spec_complexity' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'SPEC_COMPLEXITY_VALUES = {"trivial", "medium", "high", "large"}' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'frontmatter complexity must be one of' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def validate_sibling_spec_complexity' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'unsupported spec complexity was accepted' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'unsupported sibling spec complexity was accepted by --check-expected' config/skills/_shared/spec-verify-check.py; then
  bad "spec-verify-check.py checks must reject unsupported spec complexity values"
else
  ok "spec-verify-check.py checks reject unsupported spec complexity values"
fi
if ! grep -Fq 'generated criteria carrier was not staged into .devlyn/spec-verify.json' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'spec source with mismatched source.spec_sha256 was accepted' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'spec source with matching source.spec_sha256 was not staged' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'source.spec_sha256 mismatch' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'generated criteria without a JSON carrier was accepted' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'generated criteria without source.criteria_sha256 was accepted' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'generated criteria with mismatched source.criteria_sha256 was accepted' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def source_integrity_error' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'source.criteria_sha256 mismatch' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'Generated criteria were written without one' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'generated criteria carrier was not staged into .devlyn/spec-verify.json' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'spec source with mismatched source.spec_sha256 was accepted' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'spec source with matching source.spec_sha256 was not staged' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'source.spec_sha256 mismatch' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'generated criteria without a JSON carrier was accepted' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'generated criteria without source.criteria_sha256 was accepted' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'generated criteria with mismatched source.criteria_sha256 was accepted' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def source_integrity_error' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'source.criteria_sha256 mismatch' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'Generated criteria were written without one' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'generated criteria carrier was not staged into .devlyn/spec-verify.json' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'spec source with mismatched source.spec_sha256 was accepted' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'spec source with matching source.spec_sha256 was not staged' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'source.spec_sha256 mismatch' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'generated criteria without a JSON carrier was accepted' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'generated criteria without source.criteria_sha256 was accepted' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'generated criteria with mismatched source.criteria_sha256 was accepted' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def source_integrity_error' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'source.criteria_sha256 mismatch' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'Generated criteria were written without one' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '"criteria_sha256": generated_hash' .agents/skills/_shared/spec-verify-check.py; then
  bad "spec-verify-check.py self-test must cover generated criteria source extraction"
else
  ok "spec-verify-check.py covers generated criteria source extraction"
fi
if ! grep -Fq 'def validate_present_solo_headroom_hypothesis' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def state_requires_risk_probes' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def risk_probes_state_error' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq -- '--include-risk-probes accepted missing required risk-probes.jsonl' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq -- '--include-risk-probes accepted non-boolean risk_probes_enabled' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq -- '--include-risk-probes accepted non-object risk_profile' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def validate_risk_probes_cover_solo_headroom_hypothesis' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def has_backticked_observable_miss_command' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'backticked command/observable line that exposes the miss' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'weak solo-headroom hypothesis was accepted by --check' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'descriptive backtick solo-headroom hypothesis was accepted by --check' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'risk probe missing solo-headroom command coverage was accepted' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'risk probe with unrelated solo-headroom derived_from was accepted' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'risk-probes[0].derived_from must reference the solo-headroom hypothesis bullet' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'solo-headroom command in a later risk probe was accepted' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'solo-headroom command prefix match was accepted' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '(?<![A-Za-z0-9_.:/=-])' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'risk-probes[0].cmd must contain a solo-headroom hypothesis observable command' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'weak sibling solo-headroom hypothesis was accepted by --check-expected' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'docs-style solo-headroom hypothesis was rejected by --check' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'docs-style sibling solo-headroom command was rejected by --check-expected' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def validate_present_solo_headroom_hypothesis' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def state_requires_risk_probes' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def risk_probes_state_error' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq -- '--include-risk-probes accepted missing required risk-probes.jsonl' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq -- '--include-risk-probes accepted non-boolean risk_probes_enabled' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq -- '--include-risk-probes accepted non-object risk_profile' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def validate_risk_probes_cover_solo_headroom_hypothesis' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def has_backticked_observable_miss_command' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'backticked command/observable line that exposes the miss' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'weak solo-headroom hypothesis was accepted by --check' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'descriptive backtick solo-headroom hypothesis was accepted by --check' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'risk probe missing solo-headroom command coverage was accepted' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'risk probe with unrelated solo-headroom derived_from was accepted' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'risk-probes[0].derived_from must reference the solo-headroom hypothesis bullet' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'solo-headroom command in a later risk probe was accepted' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'solo-headroom command prefix match was accepted' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '(?<![A-Za-z0-9_.:/=-])' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'risk-probes[0].cmd must contain a solo-headroom hypothesis observable command' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'weak sibling solo-headroom hypothesis was accepted by --check-expected' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'docs-style solo-headroom hypothesis was rejected by --check' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'docs-style sibling solo-headroom command was rejected by --check-expected' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def validate_present_solo_headroom_hypothesis' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def state_requires_risk_probes' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def risk_probes_state_error' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq -- '--include-risk-probes accepted missing required risk-probes.jsonl' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq -- '--include-risk-probes accepted non-boolean risk_probes_enabled' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq -- '--include-risk-probes accepted non-object risk_profile' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def validate_risk_probes_cover_solo_headroom_hypothesis' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def has_backticked_observable_miss_command' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'backticked command/observable line that exposes the miss' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'weak solo-headroom hypothesis was accepted by --check' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'descriptive backtick solo-headroom hypothesis was accepted by --check' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'risk probe missing solo-headroom command coverage was accepted' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'risk probe with unrelated solo-headroom derived_from was accepted' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'risk-probes[0].derived_from must reference the solo-headroom hypothesis bullet' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'solo-headroom command in a later risk probe was accepted' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'solo-headroom command prefix match was accepted' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '(?<![A-Za-z0-9_.:/=-])' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'risk-probes[0].cmd must contain a solo-headroom hypothesis observable command' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'weak sibling solo-headroom hypothesis was accepted by --check-expected' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'docs-style solo-headroom hypothesis was rejected by --check' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'docs-style sibling solo-headroom command was rejected by --check-expected' .agents/skills/_shared/spec-verify-check.py; then
  bad "spec-verify-check.py --check and --check-expected must reject weak solo-headroom hypotheses"
else
  ok "spec-verify-check.py rejects weak solo-headroom hypotheses"
fi
if ! grep -Fq 'requires `.devlyn/risk-probes.jsonl`' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'requires `.devlyn/risk-probes.jsonl`' .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'requires `.devlyn/risk-probes.jsonl`' .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'missing `.devlyn/risk-probes.jsonl` is a CRITICAL mechanical blocker' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'missing `.devlyn/risk-probes.jsonl` is a CRITICAL mechanical blocker' .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'missing `.devlyn/risk-probes.jsonl` is a CRITICAL mechanical blocker' .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'requires that file when `state.risk_profile.risk_probes_enabled == true`' config/skills/devlyn:resolve/references/phases/build-gate.md \
  || ! grep -Fq 'requires that file when `state.risk_profile.risk_probes_enabled == true`' .claude/skills/devlyn:resolve/references/phases/build-gate.md \
  || ! grep -Fq 'requires that file when `state.risk_profile.risk_probes_enabled == true`' .agents/skills/devlyn:resolve/references/phases/build-gate.md \
  || ! grep -Fq 'Malformed `state.risk_profile` is also CRITICAL because it can hide enabled risk probes' config/skills/devlyn:resolve/references/phases/build-gate.md \
  || ! grep -Fq 'Malformed `state.risk_profile` is also CRITICAL because it can hide enabled risk probes' .claude/skills/devlyn:resolve/references/phases/build-gate.md \
  || ! grep -Fq 'Malformed `state.risk_profile` is also CRITICAL because it can hide enabled risk probes' .agents/skills/devlyn:resolve/references/phases/build-gate.md \
  || ! grep -Fq 'When `state.risk_profile.risk_probes_enabled == true`, missing `.devlyn/risk-probes.jsonl` is also CRITICAL' config/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'When `state.risk_profile.risk_probes_enabled == true`, missing `.devlyn/risk-probes.jsonl` is also CRITICAL' .claude/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'When `state.risk_profile.risk_probes_enabled == true`, missing `.devlyn/risk-probes.jsonl` is also CRITICAL' .agents/skills/devlyn:resolve/references/phases/verify.md; then
  bad "BUILD_GATE and VERIFY must fail closed when enabled risk probes are missing"
else
  ok "BUILD_GATE and VERIFY require enabled risk probes"
fi
if grep -Fq 'or any(char.isspace() for char in stripped)' config/skills/_shared/spec-verify-check.py \
  || grep -Fq 'or any(char.isspace() for char in stripped)' .claude/skills/_shared/spec-verify-check.py \
  || grep -Fq 'or any(char.isspace() for char in stripped)' .agents/skills/_shared/spec-verify-check.py \
  || grep -Fq 'or any(char.isspace() for char in stripped)' config/skills/_shared/verify-merge-findings.py \
  || grep -Fq 'or any(char.isspace() for char in stripped)' .claude/skills/_shared/verify-merge-findings.py \
  || grep -Fq 'or any(char.isspace() for char in stripped)' .agents/skills/_shared/verify-merge-findings.py \
  || grep -Fq 'or any(char.isspace() for char in stripped)' benchmark/auto-resolve/scripts/pair_evidence_contract.py; then
  bad "solo-headroom command detection must not treat descriptive whitespace as a command"
else
  ok "solo-headroom command detection rejects descriptive whitespace"
fi
if ! grep -Fq '"printf",' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '"printf",' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '"printf",' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '"printf",' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq '"printf",' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq '"printf",' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq '"printf",' benchmark/auto-resolve/scripts/pair_evidence_contract.py; then
  bad "solo-headroom command detection must keep explicit printf command support"
else
  ok "solo-headroom command detection keeps explicit printf command support"
fi
if python3 - <<'PY'
import ast
import pathlib
import sys

files = [
    pathlib.Path("benchmark/auto-resolve/scripts/pair_evidence_contract.py"),
    pathlib.Path("config/skills/_shared/spec-verify-check.py"),
    pathlib.Path(".claude/skills/_shared/spec-verify-check.py"),
    pathlib.Path(".agents/skills/_shared/spec-verify-check.py"),
    pathlib.Path("config/skills/_shared/verify-merge-findings.py"),
    pathlib.Path(".claude/skills/_shared/verify-merge-findings.py"),
    pathlib.Path(".agents/skills/_shared/verify-merge-findings.py"),
]
names = [
    "COMMAND_PREFIXES",
    "RESERVED_BACKTICK_TERMS",
    "OBSERVABLE_COMMAND_MARKERS",
]

def extract(path: pathlib.Path, name: str) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                value = ast.literal_eval(node.value)
                return tuple(sorted(value))
    raise AssertionError(f"{path}: missing {name}")

baseline = {name: extract(files[0], name) for name in names}
for path in files[1:]:
    for name in names:
        value = extract(path, name)
        if value != baseline[name]:
            print(f"{path}: {name} drifted from {files[0]}", file=sys.stderr)
            print(f"expected={baseline[name]!r}", file=sys.stderr)
            print(f"actual={value!r}", file=sys.stderr)
            sys.exit(1)
PY
then
  ok "solo-headroom command detection constants stay in parity"
else
  bad "solo-headroom command detection constants must stay in parity"
fi
if ! grep -Fq 'required.add("rollback_state")' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'rollback verification text did not require rollback_state probe tag' config/skills/_shared/spec-verify-check.py; then
  bad "spec-verify-check.py must require rollback_state risk probes for rollback/all-or-nothing verification text"
fi
if ! grep -Fq 'spec.expected.json top-level array produced a traceback' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'invalid spec.expected.json produced a traceback' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'NaN spec.expected.json did not report invalid numeric constant' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'NaN risk-probes JSONL did not report invalid numeric constant' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def reject_json_constant' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'loads_strict_json(line)' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'loads_strict_json(expected_path.read_text())' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'top-level must be a JSON object' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'has invalid JSON' config/skills/_shared/spec-verify-check.py; then
  bad "spec-verify-check.py self-test must fail malformed spec.expected.json cleanly without traceback"
fi
if ! grep -Fq 'required.add("error_contract")' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'error_contract without exit-code evidence was accepted' config/skills/_shared/spec-verify-check.py; then
  bad "spec-verify-check.py must require error_contract risk probes for invalid/stderr/JSON-error/exit-2 verification text"
fi
if ! grep -Fq '"asserts_named_stream_output"' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '"asserts_error_payload_or_stderr"' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '"asserts_nonzero_or_exit_2"' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'error_contract without exit-code evidence was accepted' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'stdout_stderr_contract without stream evidence was accepted' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '`stdout_stderr_contract`: `asserts_named_stream_output`' config/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq '`error_contract`: `asserts_error_payload_or_stderr`' config/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq '`asserts_nonzero_or_exit_2`' config/skills/devlyn:resolve/SKILL.md; then
  bad "risk-probe error/stdout-stderr tags must require concrete tag_evidence markers in validator and prompt contract"
fi
if ! grep -Fq '"http_error_contract"' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'asserts_http_error_status' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'http error text did not require http_error_contract tag' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'http_error_contract without payload evidence was accepted' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'exact error body shape_contract without exact object evidence was accepted' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'exact error body shape_contract with exact object evidence was rejected' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '`http_error_contract`: `asserts_http_error_status`' config/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq '`http_error_contract` must include `asserts_http_error_status`' config/skills/devlyn:resolve/SKILL.md; then
  bad "risk-probe HTTP error contracts must require concrete status and payload markers"
fi
if ! grep -Fq '"uses_visible_input_key_names"' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '"asserts_visible_output_key_names"' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '"asserts_no_unexpected_output_keys"' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'JSON error object text did not require shape_contract tag' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'JSON error object shape_contract with exact object evidence was rejected' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'INLINE_JSON_OBJECT_RE' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'inline JSON object text did not require shape_contract tag' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'inline JSON object shape_contract with key evidence was rejected' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'inline JSON error text did not require shape_contract tag' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'inline JSON error shape_contract with exact object evidence was rejected' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'shape_contract without exact key evidence was accepted' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '`shape_contract` when the visible text names exact keys' config/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq '`shape_contract` must' config/skills/devlyn:resolve/SKILL.md; then
  bad "risk-probe shape contracts must require exact visible input/output key evidence when visible text names shape"
fi
if ! grep -Fq "forbidden[ -]+window" config/skills/_shared/spec-verify-check.py \
  || grep -Fq "r'blocked|overlap|forbidden|window'" config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'generic forbidden-pattern verification text incorrectly required boundary_overlap' config/skills/_shared/spec-verify-check.py; then
  bad "risk-probe boundary_overlap must trigger for forbidden windows / blocked overlap, not generic forbidden pattern text"
fi
if ! grep -Fq '(?:stock|inventory|balance|availability).{0,80}(?:later|remaining|after failures)' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'stock validation error text incorrectly required prior_consumption' config/skills/_shared/spec-verify-check.py; then
  bad "risk-probe prior_consumption must trigger on later/remaining state consumption, not plain stock validation errors"
fi
if ! grep -Fq '"auth_signature_contract"' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '"idempotency_replay"' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'asserts_signature_over_exact_bytes' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'duplicate_id_rejected_regardless_of_body' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'webhook signature/replay text did not require auth/idempotency probe tags' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '`auth_signature_contract`: `asserts_signature_over_exact_bytes`' config/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq '`idempotency_replay`: `first_delivery_then_duplicate`' config/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq '`auth_signature_contract` must include `asserts_signature_over_exact_bytes`' config/skills/devlyn:resolve/SKILL.md; then
  bad "risk-probe webhook/signature/replay contracts must require concrete auth_signature_contract and idempotency_replay tags"
fi
if ! grep -Fq 'signing|signed' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'same.{0,40}`?id`?' config/skills/_shared/spec-verify-check.py; then
  bad "risk-probe webhook signature/replay trigger must catch signing/signed and same accepted id wording"
fi
if ! grep -Fq 'duplicate[ -]+(?:delivery|event|id)' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'duplicate SKU verification text incorrectly required idempotency_replay' config/skills/_shared/spec-verify-check.py; then
  bad "risk-probe idempotency_replay must trigger on duplicate delivery/event/id, not duplicate SKU aggregation"
fi
if ! grep -Fq '"concurrent_state_consistency"' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'overlapping_mutations_exercised' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'concurrent state text did not require concurrent_state_consistency tag' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '`concurrent_state_consistency`: `overlapping_mutations_exercised`' config/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq '`concurrent_state_consistency` must' config/skills/devlyn:resolve/SKILL.md; then
  bad "risk-probe concurrent state contracts must require concrete concurrent_state_consistency markers"
fi
if ! grep -Fq '"atomic_batch_state"' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'mixed_valid_invalid_batch' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'atomic batch text did not require atomic_batch_state tag' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'atomic_batch_state without success-order evidence was accepted' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq '`atomic_batch_state`: `mixed_valid_invalid_batch`' config/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq '`atomic_batch_state` must include `mixed_valid_invalid_batch`' config/skills/devlyn:resolve/SKILL.md; then
  bad "risk-probe atomic batch contracts must require concrete mixed-failure and success-order markers"
fi

section "Check 6f: ideate validates sibling spec.expected.json"
expected_check_missing=0
for file in \
  config/skills/devlyn:ideate/SKILL.md \
  config/skills/devlyn:ideate/references/elicitation.md \
  config/skills/devlyn:ideate/references/from-spec-mode.md \
  config/skills/devlyn:ideate/references/project-mode.md \
  config/skills/devlyn:ideate/references/spec-template.md
do
  if ! grep -Fq -- '--check-expected <expected-path>' "$file"; then
    bad "$file — missing spec.expected.json mechanical validation command"
    expected_check_missing=1
  fi
done
if [ $expected_check_missing -eq 0 ]; then
  ok "ideate docs require --check-expected for sibling expected contracts"
fi
if ! grep -Fq 'any present actionable solo-headroom hypothesis' config/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'any present actionable solo-headroom hypothesis' .claude/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'any present actionable solo-headroom hypothesis' .agents/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'any present actionable solo-headroom hypothesis' config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'any present actionable solo-headroom hypothesis' .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'any present actionable solo-headroom hypothesis' .agents/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'any present actionable solo-headroom hypothesis' config/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'any present actionable solo-headroom hypothesis' .claude/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'any present actionable solo-headroom hypothesis' .agents/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'any present actionable solo-headroom hypothesis' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'any present actionable solo-headroom hypothesis' .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'any present actionable solo-headroom hypothesis' .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq "legacy inline \`## Verification\` JSON carrier" config/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq "legacy inline \`## Verification\` JSON carrier" .claude/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq "legacy inline \`## Verification\` JSON carrier" .agents/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq "legacy inline \`## Verification\` JSON carrier" config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq "legacy inline \`## Verification\` JSON carrier" .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq "legacy inline \`## Verification\` JSON carrier" .agents/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq "legacy inline \`## Verification\` JSON carrier" config/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq "legacy inline \`## Verification\` JSON carrier" .claude/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq "legacy inline \`## Verification\` JSON carrier" .agents/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq "inline \`## Verification\` JSON carrier" config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq "inline \`## Verification\` JSON carrier" .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq "inline \`## Verification\` JSON carrier" .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' config/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' .claude/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' .agents/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' .agents/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' config/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' .claude/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' .agents/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' .agents/skills/devlyn:resolve/SKILL.md; then
  bad "ideate/resolve docs must describe mechanical solo-headroom validation"
else
  ok "ideate/resolve docs describe mechanical solo-headroom validation"
fi
if ! grep -Fq 'def validate_expected_against_sibling_spec' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'empty verification_commands should fail for runtime specs' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'empty verification_commands should be valid for pure-design specs' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'backticked_observable_miss_commands(spec_text)' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'observable command must match spec.expected.json' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'observable command must match `## Verification` JSON carrier' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'mismatched inline solo-headroom command was accepted by --check' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'matched inline solo-headroom command was rejected by --check' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'mismatched sibling solo-headroom command was accepted by --check-expected' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'matched sibling solo-headroom command was rejected by --check-expected' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def validate_present_solo_ceiling_avoidance' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'weak solo ceiling avoidance was accepted by --check' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'actionable solo ceiling avoidance was rejected by --check' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'weak sibling solo ceiling avoidance was accepted by --check-expected' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'actionable sibling solo ceiling avoidance was rejected by --check-expected' config/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'backticked_observable_miss_commands(spec_text)' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'observable command must match spec.expected.json' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'observable command must match `## Verification` JSON carrier' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'mismatched inline solo-headroom command was accepted by --check' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'matched inline solo-headroom command was rejected by --check' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'mismatched sibling solo-headroom command was accepted by --check-expected' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'matched sibling solo-headroom command was rejected by --check-expected' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def validate_present_solo_ceiling_avoidance' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'weak solo ceiling avoidance was accepted by --check' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'actionable solo ceiling avoidance was rejected by --check' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'weak sibling solo ceiling avoidance was accepted by --check-expected' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'actionable sibling solo ceiling avoidance was rejected by --check-expected' .claude/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'backticked_observable_miss_commands(spec_text)' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'observable command must match spec.expected.json' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'observable command must match `## Verification` JSON carrier' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'mismatched inline solo-headroom command was accepted by --check' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'matched inline solo-headroom command was rejected by --check' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'mismatched sibling solo-headroom command was accepted by --check-expected' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'matched sibling solo-headroom command was rejected by --check-expected' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'def validate_present_solo_ceiling_avoidance' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'weak solo ceiling avoidance was accepted by --check' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'actionable solo ceiling avoidance was rejected by --check' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'weak sibling solo ceiling avoidance was accepted by --check-expected' .agents/skills/_shared/spec-verify-check.py \
  || ! grep -Fq 'actionable sibling solo ceiling avoidance was rejected by --check-expected' .agents/skills/_shared/spec-verify-check.py; then
  bad "spec-verify-check.py must reject empty expected runtime contracts, weak solo ceiling avoidance, and preserve pure-design escape"
fi
if ! grep -Fq 'Verification includes at least one compound scenario that exercises the interaction end-to-end' \
  config/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'Verification includes at least one compound scenario that exercises the interaction end-to-end' \
    .claude/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'Verification includes at least one compound scenario that exercises the interaction end-to-end' \
    .agents/skills/devlyn:ideate/references/spec-template.md; then
  bad "ideate spec template must require compound interaction verification for pair-relevant high-risk specs"
else
  ok "ideate spec template requires compound interaction verification for pair-relevant specs"
fi
if ! grep -Fq 'ask for one concrete compound' config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'ask for one concrete compound' .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'ask for one concrete compound' .agents/skills/devlyn:ideate/references/elicitation.md; then
  bad "ideate elicitation must ask for compound interaction scenarios when pair-relevant risks appear"
else
  ok "ideate elicitation asks for compound interaction scenarios when pair-relevant risks appear"
fi
if ! grep -Fq 'solo-headroom hypothesis inside `## Verification`' config/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'solo-headroom hypothesis inside `## Verification`' .claude/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'solo-headroom hypothesis inside `## Verification`' .agents/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'ask for one solo-headroom hypothesis' config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'ask for one solo-headroom hypothesis' .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'ask for one solo-headroom hypothesis' .agents/skills/devlyn:ideate/references/elicitation.md; then
  bad "ideate must require a visible solo-headroom hypothesis for benchmark and pair-evidence specs"
else
  ok "ideate requires solo-headroom hypothesis for benchmark and pair-evidence specs"
fi
if ! grep -Fq 'must literally contain `solo-headroom hypothesis`' config/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'must literally contain `solo-headroom hypothesis`' .claude/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'must literally contain `solo-headroom hypothesis`' .agents/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'backticked line itself must contain `miss`' config/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'backticked line itself must contain `miss`' .claude/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'backticked line itself must contain `miss`' .agents/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq '`solo_claude`, `miss`, and a backticked observable command' config/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq '`solo_claude`, `miss`, and a backticked observable command' .claude/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq '`solo_claude`, `miss`, and a backticked observable command' .agents/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'command/observable' config/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'command/observable' .claude/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'command/observable' .agents/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'must literally contain `solo-headroom hypothesis`' config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'must literally contain `solo-headroom hypothesis`' .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'must literally contain `solo-headroom hypothesis`' .agents/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'line itself must contain `miss`' config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'line itself must contain `miss`' .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'line itself must contain `miss`' .agents/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'Do not write a benchmark/risk-probe/pair-evidence spec until this' config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'Do not write a benchmark/risk-probe/pair-evidence spec until this' .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'Do not write a benchmark/risk-probe/pair-evidence spec until this' .agents/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'spec not ready — solo-headroom hypothesis required' config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'spec not ready — solo-headroom hypothesis required' .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'spec not ready — solo-headroom hypothesis required' .agents/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq '`solo_claude`, `miss`, and a backticked observable command' config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq '`solo_claude`, `miss`, and a backticked observable command' .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq '`solo_claude`, `miss`, and a backticked observable command' .agents/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'command/observable' config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'command/observable' .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'command/observable' .agents/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'Verification literally contains `solo-headroom hypothesis`, `solo_claude`' config/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'Verification literally contains `solo-headroom hypothesis`, `solo_claude`' .claude/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'Verification literally contains `solo-headroom hypothesis`, `solo_claude`' .agents/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'backticked line itself must contain `miss`' config/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'backticked line itself must contain `miss`' .claude/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'backticked line itself must contain `miss`' .agents/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'command/observable' config/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'command/observable' .claude/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'command/observable' .agents/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' config/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' .claude/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' .agents/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq "source for VERIFY's canonical \`spec.solo_headroom_hypothesis\` trigger reason" config/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq "source for VERIFY's canonical \`spec.solo_headroom_hypothesis\` trigger reason" .claude/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq "source for VERIFY's canonical \`spec.solo_headroom_hypothesis\` trigger reason" .agents/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' config/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' .claude/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'spec.expected.json.verification_commands[].cmd' .agents/skills/devlyn:ideate/references/spec-template.md; then
  bad "ideate solo-headroom hypothesis prompt must match the actionable checker contract"
else
  ok "ideate solo-headroom hypothesis prompt matches checker contract"
fi
if ! grep -Fq 'quick mode must not infer a solo-headroom hypothesis' config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'quick mode must not infer a solo-headroom hypothesis' .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'quick mode must not infer a solo-headroom hypothesis' .agents/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'do not infer a solo-headroom hypothesis' config/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'do not infer a solo-headroom hypothesis' .claude/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'do not infer a solo-headroom hypothesis' .agents/skills/devlyn:ideate/SKILL.md; then
  bad "ideate quick mode must not invent solo-headroom hypotheses"
else
  ok "ideate quick mode does not invent solo-headroom hypotheses"
fi
if ! grep -Fq 'solo ceiling avoidance' config/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'solo ceiling avoidance' .claude/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'solo ceiling avoidance' .agents/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'rejected or solo-saturated controls such as `S2`-`S6`' config/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'rejected or solo-saturated controls such as `S2`-`S6`' .claude/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'rejected or solo-saturated controls such as `S2`-`S6`' .agents/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'Solo ceiling avoidance' config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'Solo ceiling avoidance' .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'Solo ceiling avoidance' .agents/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'spec not ready — solo ceiling avoidance required' config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'spec not ready — solo ceiling avoidance required' .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'spec not ready — solo ceiling avoidance required' .agents/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'pair-evidence not ready — Pair-candidate headroom is unproven until the spec states solo ceiling avoidance' config/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'pair-evidence not ready — Pair-candidate headroom is unproven until the spec states solo ceiling avoidance' .claude/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'pair-evidence not ready — Pair-candidate headroom is unproven until the spec states solo ceiling avoidance' .agents/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'also do not infer solo ceiling avoidance' config/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'also do not infer solo ceiling avoidance' .claude/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'also do not infer solo ceiling avoidance' .agents/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'per-feature Verification must also include a solo ceiling avoidance note' config/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'per-feature Verification must also include a solo ceiling avoidance note' .claude/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'per-feature Verification must also include a solo ceiling avoidance note' .agents/skills/devlyn:ideate/references/project-mode.md; then
  bad "ideate must require solo ceiling avoidance for new unmeasured pair candidates"
else
  ok "ideate requires solo ceiling avoidance for new unmeasured pair candidates"
fi
if ! grep -Fq 'complexity: medium' config/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'complexity: medium' .claude/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'complexity: medium' .agents/skills/devlyn:ideate/references/spec-template.md \
  || ! grep -Fq 'Complexity signal' config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'Complexity signal' .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'Complexity signal' .agents/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'downstream VERIFY pair-trigger signal' config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'downstream VERIFY pair-trigger signal' .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'downstream VERIFY pair-trigger signal' .agents/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'complexity=medium default' config/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'complexity=medium default' .claude/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'complexity=medium default' .agents/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'supported `complexity` frontmatter' config/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'supported `complexity` frontmatter' .claude/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'supported `complexity` frontmatter' .agents/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'supported `complexity` frontmatter' config/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'supported `complexity` frontmatter' .claude/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'supported `complexity` frontmatter' .agents/skills/devlyn:ideate/references/elicitation.md \
  || ! grep -Fq 'supported `complexity` frontmatter' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'supported `complexity` frontmatter' .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'supported `complexity` frontmatter' .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'sibling spec `complexity` frontmatter' config/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'sibling spec `complexity` frontmatter' .claude/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'sibling spec `complexity` frontmatter' .agents/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'sibling spec `complexity` frontmatter' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'sibling spec `complexity` frontmatter' .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'sibling spec `complexity` frontmatter' .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'Frontmatter has `id`, `title`, `kind`, `status: planned`, `complexity`' config/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'Frontmatter has `id`, `title`, `kind`, `status: planned`, `complexity`' .claude/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'Frontmatter has `id`, `title`, `kind`, `status: planned`, `complexity`' .agents/skills/devlyn:ideate/SKILL.md; then
  bad "ideate specs must emit complexity frontmatter for resolve pair triggers"
else
  ok "ideate specs emit complexity frontmatter for resolve pair triggers"
fi
if ! grep -Fq 'warning: Verification may need one compound end-to-end scenario before pair-relevant risks are measurable' \
  config/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'warning: Verification may need one compound end-to-end scenario before pair-relevant risks are measurable' \
    .claude/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'warning: Verification may need one compound end-to-end scenario before pair-relevant risks are measurable' \
    .agents/skills/devlyn:ideate/references/from-spec-mode.md; then
  bad "ideate from-spec mode must warn when preserved high-risk specs lack compound verification"
else
  ok "ideate from-spec mode warns on pair-relevant specs with weak verification"
fi
if ! grep -Fq 'pair-evidence not ready — Pair-candidate headroom is unproven until the spec states a solo-headroom hypothesis' \
  config/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'pair-evidence not ready — Pair-candidate headroom is unproven until the spec states a solo-headroom hypothesis' \
    .claude/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'pair-evidence not ready — Pair-candidate headroom is unproven until the spec states a solo-headroom hypothesis' \
    .agents/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'Do not call' config/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'Do not call' .claude/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'Do not call' .agents/skills/devlyn:ideate/references/from-spec-mode.md \
  || ! grep -Fq 'announcement must say `pair-evidence not ready`' config/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'announcement must say `pair-evidence not ready`' .claude/skills/devlyn:ideate/SKILL.md \
  || ! grep -Fq 'announcement must say `pair-evidence not ready`' .agents/skills/devlyn:ideate/SKILL.md; then
  bad "ideate from-spec mode must warn when pair-candidate specs lack solo-headroom hypothesis"
else
  ok "ideate from-spec mode warns on missing solo-headroom hypothesis"
fi
if ! grep -Fq 'per-feature Verification must' config/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'per-feature Verification must' .claude/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'per-feature Verification must' .agents/skills/devlyn:ideate/references/project-mode.md; then
  bad "ideate project mode must require compound verification inside each pair-relevant feature spec"
else
  ok "ideate project mode keeps compound verification inside pair-relevant feature specs"
fi
if ! grep -Fq 'per-feature Verification must include a solo-headroom' config/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'per-feature Verification must include a solo-headroom' .claude/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'per-feature Verification must include a solo-headroom' .agents/skills/devlyn:ideate/references/project-mode.md \
  || rg -q 'Context or Verification' config/skills/devlyn:ideate/references .claude/skills/devlyn:ideate/references .agents/skills/devlyn:ideate/references; then
  bad "ideate project mode must keep solo-headroom hypothesis inside each pair-candidate feature spec"
else
  ok "ideate project mode keeps solo-headroom hypothesis inside each pair-candidate feature spec"
fi
if ! grep -Fq 'feature spec must literally contain' \
  config/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'feature spec must literally contain' \
    .claude/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'feature spec must literally contain' \
    .agents/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq '`solo-headroom hypothesis`, `solo_claude`, `miss`, and a backticked' \
    config/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq '`solo-headroom hypothesis`, `solo_claude`, `miss`, and a backticked' \
    .claude/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq '`solo-headroom hypothesis`, `solo_claude`, `miss`, and a backticked' \
    .agents/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'behavior a capable' config/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'behavior a capable' .claude/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'behavior a capable' .agents/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'backticked line itself must' config/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'backticked line itself must' .claude/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'backticked line itself must' .agents/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'command/observable' \
    config/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'command/observable' \
    .claude/skills/devlyn:ideate/references/project-mode.md \
  || ! grep -Fq 'command/observable' \
    .agents/skills/devlyn:ideate/references/project-mode.md; then
  bad "ideate project mode solo-headroom prompt must keep the actionable checker contract"
else
  ok "ideate project mode solo-headroom prompt keeps checker contract"
fi

if ! grep -Fq 'If the visible spec includes a solo-headroom hypothesis, the first probe must' \
  config/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq 'If the visible spec includes a solo-headroom hypothesis, the first probe must' \
    .claude/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq 'If the visible spec includes a solo-headroom hypothesis, the first probe must' \
    .agents/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq 'When the visible spec includes a solo-headroom hypothesis, the first probe must' \
    config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'When the visible spec includes a solo-headroom hypothesis, the first probe must' \
    .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'When the visible spec includes a solo-headroom hypothesis, the first probe must' \
    .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'its `cmd` must contain the hypothesis'\''s backticked' \
    config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'its `cmd` must contain the hypothesis'\''s backticked' \
    .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'its `cmd` must contain the hypothesis'\''s backticked' \
    .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'its `derived_from` must reference the hypothesis bullet' \
    config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'its `derived_from` must reference the hypothesis bullet' \
    .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'its `derived_from` must reference the hypothesis bullet' \
    .agents/skills/devlyn:resolve/SKILL.md; then
  bad "resolve risk-probe prompts must consume solo-headroom hypothesis before pair-evidence work"
else
  ok "resolve risk-probe prompts consume solo-headroom hypothesis"
fi
if ! grep -Fq 'the behavior the spec says `solo_claude` is expected to miss' \
  config/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq 'the behavior the spec says `solo_claude` is expected to miss' \
    .claude/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq 'the behavior the spec says `solo_claude` is expected to miss' \
    .agents/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq 'exercise the stated `solo_claude` miss' \
    config/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq 'exercise the stated `solo_claude` miss' \
    .claude/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq 'exercise the stated `solo_claude` miss' \
    .agents/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq 'with a `cmd` containing the hypothesis'\''s' \
    config/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq 'with a `cmd` containing the hypothesis'\''s' \
    .claude/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq 'with a `cmd` containing the hypothesis'\''s' \
    .agents/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq '`derived_from` pointing at the hypothesis' \
    config/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq '`derived_from` pointing at the hypothesis' \
    .claude/skills/devlyn:resolve/references/phases/probe-derive.md \
  || ! grep -Fq '`derived_from` pointing at the hypothesis' \
    .agents/skills/devlyn:resolve/references/phases/probe-derive.md; then
  bad "resolve risk-probe solo-headroom prompt must target the stated solo_claude miss"
else
  ok "resolve risk-probe solo-headroom prompt targets the stated solo_claude miss"
fi
if ! grep -Fq 'If the spec includes a solo-headroom hypothesis, one of the two targeted' \
  config/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'If the spec includes a solo-headroom hypothesis, one of the two targeted' \
    .claude/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'If the spec includes a solo-headroom hypothesis, one of the two targeted' \
    .agents/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'If the spec includes a solo-headroom hypothesis, one of those targeted probes must' \
    config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'If the spec includes a solo-headroom hypothesis, one of those targeted probes must' \
    .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'If the spec includes a solo-headroom hypothesis, one of those targeted probes must' \
    .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'using the hypothesis'\''s backticked observable command as its command anchor' \
    config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'using the hypothesis'\''s backticked observable command as its command anchor' \
    .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'using the hypothesis'\''s backticked observable command as its command anchor' \
    .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'hypothesis'\''s backticked observable command as its command anchor' \
    config/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'hypothesis'\''s backticked observable command as its command anchor' \
    .claude/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'hypothesis'\''s backticked observable command as its command anchor' \
    .agents/skills/devlyn:resolve/references/phases/verify.md; then
  bad "resolve pair-JUDGE prompts must prioritize solo-headroom hypothesis"
else
  ok "resolve pair-JUDGE prompts prioritize solo-headroom hypothesis"
fi
if ! grep -Fq 'current free-form `state.complexity` is `"large"`' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'current free-form `state.complexity` is `"large"`' .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'current free-form `state.complexity` is `"large"`' .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'legacy/external spec `complexity: large` is accepted for compatibility' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'legacy/external spec `complexity: large` is accepted for compatibility' .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'legacy/external spec `complexity: large` is accepted for compatibility' .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'current free-form `state.complexity` of `"large"`' config/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'current free-form `state.complexity` of `"large"`' .claude/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'current free-form `state.complexity` of `"large"`' .agents/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'Legacy/external spec `complexity: large` remains accepted for compatibility' config/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'Legacy/external spec `complexity: large` remains accepted for compatibility' .claude/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'Legacy/external spec `complexity: large` remains accepted for compatibility' .agents/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'Current free-form `state.complexity` is `"large"`' config/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'Current free-form `state.complexity` is `"large"`' .claude/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'Current free-form `state.complexity` is `"large"`' .agents/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'legacy/external spec' config/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'legacy/external spec' .claude/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'legacy/external spec' .agents/skills/devlyn:resolve/references/phases/verify.md; then
  bad "resolve VERIFY docs must distinguish current large complexity, legacy high state, and legacy large spec compatibility"
else
  ok "resolve VERIFY docs distinguish current large complexity, legacy high state, and legacy large spec compatibility"
fi
if ! grep -Fq 'def spec_has_solo_headroom_hypothesis' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'spec.solo_headroom_hypothesis' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'and "solo_claude" in lower' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'and "miss" in lower' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'OBSERVABLE_COMMAND_MARKERS = ("command", "observable", "expose")' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'def is_command_like_backtick' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'for key in ("spec_path", "criteria_path")' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'has_backticked_observable_command(text)' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'Observable command: `node check.js` exposes behavior' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'observable `SOLO_CLAUDE` exposes the miss' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'observable `priority rollback` exposes the miss' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'implementation token `rollback`' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq '`SOLO_CLAUDE` should miss' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq '{"source": {"criteria_path": str(criteria_path)}}' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'spec_has_solo_headroom_hypothesis(' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq ') is False' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq ') is True' config/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'def spec_has_solo_headroom_hypothesis' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'spec.solo_headroom_hypothesis' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'and "solo_claude" in lower' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'and "miss" in lower' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'OBSERVABLE_COMMAND_MARKERS = ("command", "observable", "expose")' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'def is_command_like_backtick' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'for key in ("spec_path", "criteria_path")' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'has_backticked_observable_command(text)' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'Observable command: `node check.js` exposes behavior' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'observable `SOLO_CLAUDE` exposes the miss' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'observable `priority rollback` exposes the miss' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'implementation token `rollback`' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq '`SOLO_CLAUDE` should miss' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq '{"source": {"criteria_path": str(criteria_path)}}' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'spec_has_solo_headroom_hypothesis(' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq ') is False' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq ') is True' .claude/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'def spec_has_solo_headroom_hypothesis' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'spec.solo_headroom_hypothesis' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'and "solo_claude" in lower' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'and "miss" in lower' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'OBSERVABLE_COMMAND_MARKERS = ("command", "observable", "expose")' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'def is_command_like_backtick' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'for key in ("spec_path", "criteria_path")' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'has_backticked_observable_command(text)' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'Observable command: `node check.js` exposes behavior' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'observable `SOLO_CLAUDE` exposes the miss' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'observable `priority rollback` exposes the miss' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'implementation token `rollback`' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq '`SOLO_CLAUDE` should miss' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq '{"source": {"criteria_path": str(criteria_path)}}' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'spec_has_solo_headroom_hypothesis(' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq ') is False' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq ') is True' .agents/skills/_shared/verify-merge-findings.py \
  || ! grep -Fq 'The spec includes an actionable solo-headroom hypothesis.' \
    config/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'The spec includes an actionable solo-headroom hypothesis.' \
    .claude/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'The spec includes an actionable solo-headroom hypothesis.' \
    .agents/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'actionable solo-headroom hypotheses' config/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'actionable solo-headroom hypotheses' .claude/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'actionable solo-headroom hypotheses' .agents/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'same actionable solo-headroom hypothesis is a VERIFY pair-trigger reason' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'same actionable solo-headroom hypothesis is a VERIFY pair-trigger reason' .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'same actionable solo-headroom hypothesis is a VERIFY pair-trigger reason' .agents/skills/devlyn:resolve/SKILL.md; then
  bad "resolve VERIFY pair trigger must include actionable solo-headroom hypothesis specs"
else
  ok "resolve VERIFY pair trigger includes actionable solo-headroom hypothesis specs"
fi
if ! grep -Fq 'pair_evidence_intent' config/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'pair_evidence_intent' .claude/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'pair_evidence_intent' .agents/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'has_actionable_solo_headroom' config/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'has_actionable_solo_headroom' .claude/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'has_actionable_solo_headroom' .agents/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'state.source.type = "generated"' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'state.source.type = "generated"' .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'state.source.type = "generated"' .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'state.source.criteria_path = ".devlyn/criteria.generated.md"' config/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'state.source.criteria_path = ".devlyn/criteria.generated.md"' .claude/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'state.source.criteria_path = ".devlyn/criteria.generated.md"' .agents/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'state.source.criteria_sha256' config/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'state.source.criteria_sha256' .claude/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'state.source.criteria_sha256' .agents/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'state.source.criteria_sha256` for generated free-form mode' config/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'state.source.criteria_sha256` for generated free-form mode' .claude/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'state.source.criteria_sha256` for generated free-form mode' .agents/skills/devlyn:resolve/references/phases/verify.md \
  || ! grep -Fq 'Free-form mode sets `type: "generated"`' config/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'Free-form mode sets `type: "generated"`' .claude/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'Free-form mode sets `type: "generated"`' .agents/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq 'backticked observable command line that itself contains `miss`' config/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'backticked observable command line that itself contains `miss`' .claude/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'backticked observable command line that itself contains `miss`' .agents/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'BLOCKED:solo-headroom-hypothesis-required' config/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'BLOCKED:solo-headroom-hypothesis-required' .claude/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'BLOCKED:solo-headroom-hypothesis-required' .agents/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'pair-evidence intent without an actionable solo-headroom hypothesis must halt' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'pair-evidence intent without an actionable solo-headroom hypothesis must halt' .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'pair-evidence intent without an actionable solo-headroom hypothesis must halt' .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'preserve that literal hypothesis in `.devlyn/criteria.generated.md`' config/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'preserve that literal hypothesis in `.devlyn/criteria.generated.md`' .claude/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'preserve that literal hypothesis in `.devlyn/criteria.generated.md`' .agents/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'emit the canonical `spec.solo_headroom_hypothesis` pair trigger reason' config/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'emit the canonical `spec.solo_headroom_hypothesis` pair trigger reason' .claude/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'emit the canonical `spec.solo_headroom_hypothesis` pair trigger reason' .agents/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq '/devlyn:ideate` guidance for `BLOCKED:solo-headroom-hypothesis-required`' config/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq '/devlyn:ideate` guidance for `BLOCKED:solo-headroom-hypothesis-required`' .claude/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq '/devlyn:ideate` guidance for `BLOCKED:solo-headroom-hypothesis-required`' .agents/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq '/devlyn:ideate` guidance after `BLOCKED:solo-headroom-hypothesis-required`' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq '/devlyn:ideate` guidance after `BLOCKED:solo-headroom-hypothesis-required`' .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq '/devlyn:ideate` guidance after `BLOCKED:solo-headroom-hypothesis-required`' .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'Free-form goals that ask for benchmark evidence, pair-evidence, risk-probe' README.md \
  || ! grep -Fq '`/devlyn:resolve` stops with `BLOCKED:solo-headroom-hypothesis-required`' README.md \
  || ! grep -Fq 'points you to `/devlyn:ideate` instead of inventing a weak hypothesis' README.md; then
  bad "resolve free-form mode must block pair-evidence goals without actionable solo-headroom hypothesis"
else
  ok "resolve free-form mode blocks pair-evidence goals without actionable solo-headroom hypothesis"
fi
if ! grep -Fq 'unmeasured_pair_candidate_intent' config/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'unmeasured_pair_candidate_intent' .claude/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'unmeasured_pair_candidate_intent' .agents/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'has_solo_ceiling_avoidance' config/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'has_solo_ceiling_avoidance' .claude/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'has_solo_ceiling_avoidance' .agents/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'BLOCKED:solo-ceiling-avoidance-required' config/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'BLOCKED:solo-ceiling-avoidance-required' .claude/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'BLOCKED:solo-ceiling-avoidance-required' .agents/skills/devlyn:resolve/references/free-form-mode.md \
  || ! grep -Fq 'unmeasured pair-candidate intent without solo ceiling avoidance must halt' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'unmeasured pair-candidate intent without solo ceiling avoidance must halt' .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq 'unmeasured pair-candidate intent without solo ceiling avoidance must halt' .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq '/devlyn:ideate` guidance after `BLOCKED:solo-ceiling-avoidance-required`' config/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq '/devlyn:ideate` guidance after `BLOCKED:solo-ceiling-avoidance-required`' .claude/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq '/devlyn:ideate` guidance after `BLOCKED:solo-ceiling-avoidance-required`' .agents/skills/devlyn:resolve/SKILL.md \
  || ! grep -Fq '/devlyn:ideate` guidance for `BLOCKED:solo-ceiling-avoidance-required`' config/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq '/devlyn:ideate` guidance for `BLOCKED:solo-ceiling-avoidance-required`' .claude/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq '/devlyn:ideate` guidance for `BLOCKED:solo-ceiling-avoidance-required`' .agents/skills/devlyn:resolve/references/state-schema.md \
  || ! grep -Fq '`/devlyn:resolve` stops with `BLOCKED:solo-ceiling-avoidance-required`' README.md; then
  bad "resolve free-form mode must block new unmeasured pair candidates without solo ceiling avoidance"
else
  ok "resolve free-form mode blocks new unmeasured pair candidates without solo ceiling avoidance"
fi

section "Check 6g: resolve consumes sibling spec.expected.json"
sibling_consume_missing=0
for file in \
  config/skills/devlyn:resolve/SKILL.md \
  config/skills/devlyn:resolve/references/phases/build-gate.md \
  config/skills/devlyn:resolve/references/phases/verify.md
do
  if ! grep -Fq 'sibling `spec.expected.json`' "$file"; then
    bad "$file — missing sibling spec.expected.json consumption contract"
    sibling_consume_missing=1
  fi
done
for pattern in \
  'def stage_from_expected' \
  'stage_from_expected(' \
  'expected_found, expected_staged, expected_error, expected_path' \
  'def expected_contract_findings' \
  'correctness.forbidden-pattern' \
  'scope.max-deps-added-exceeded' \
  'SPEC_VERIFY_FINDINGS_FILE'
do
  if ! grep -Fq "$pattern" config/skills/_shared/spec-verify-check.py; then
    bad "spec-verify-check.py missing sibling expected staging implementation: $pattern"
    sibling_consume_missing=1
  fi
done
if [ $sibling_consume_missing -eq 0 ]; then
  ok "resolve self-stages and mechanically checks sibling spec.expected.json"
fi

section "Check 6i: VERIFY mechanical findings are merge-visible"
verify_mech_missing=0
for pattern in \
  'SPEC_VERIFY_PHASE=verify_mechanical' \
  'SPEC_VERIFY_FINDINGS_FILE=verify-mechanical.findings.jsonl' \
  'SPEC_VERIFY_FINDING_PREFIX=VERIFY-MECH'
do
  if ! grep -Fq "$pattern" config/skills/devlyn:resolve/SKILL.md \
     || ! grep -Fq "$pattern" config/skills/devlyn:resolve/references/phases/verify.md \
     || ! grep -Fq "$pattern" config/skills/_shared/spec-verify-check.py; then
    bad "VERIFY mechanical output contract missing: $pattern"
    verify_mech_missing=1
  fi
done
if ! grep -Fq '("mechanical", "verify-mechanical.findings.jsonl")' \
  config/skills/_shared/verify-merge-findings.py; then
  bad "verify-merge-findings.py does not consume verify-mechanical.findings.jsonl"
  verify_mech_missing=1
fi
if grep -Fq 'All paths emit a CRITICAL finding to' config/skills/_shared/spec-verify-check.py; then
  bad "spec-verify-check.py has stale single-output CRITICAL finding wording"
  verify_mech_missing=1
fi
if [ $verify_mech_missing -eq 0 ]; then
  ok "spec-verify VERIFY output routes into verify-merge-findings.py"
fi

section "Check 6j: VERIFY pair trigger runs after primary JUDGE"
pair_trigger_order_missing=0
for file in \
  config/skills/devlyn:resolve/SKILL.md \
  .claude/skills/devlyn:resolve/SKILL.md \
  .agents/skills/devlyn:resolve/SKILL.md
do
  if ! grep -Fq 'Pair-mode (cross-model JUDGE) is eligible only after MECHANICAL and the primary JUDGE have no verdict-binding findings' "$file" \
    || ! grep -Fq 'After MECHANICAL and the primary JUDGE finish, compute `pair_trigger' "$file" \
    || ! grep -Fq '`risk_profile` is strict typed state' "$file" \
    || ! grep -Fq 'malformed `risk_profile` is also a VERIFY contract violation' "$file" \
    || ! grep -Fq 'If MECHANICAL or the primary JUDGE has a verdict-binding finding' "$file"; then
    bad "$file — VERIFY pair trigger order must be after primary JUDGE"
    pair_trigger_order_missing=1
  fi
done
for file in \
  config/skills/devlyn:resolve/references/phases/verify.md \
  .claude/skills/devlyn:resolve/references/phases/verify.md \
  .agents/skills/devlyn:resolve/references/phases/verify.md
do
  if ! grep -Fq 'Pair-mode is eligible only after MECHANICAL and the primary JUDGE have no' "$file" \
    || ! grep -Fq 'After MECHANICAL and the primary JUDGE finish, compute and persist this before' "$file" \
    || ! grep -Fq 'Malformed `state.risk_profile` is a VERIFY contract violation' "$file" \
    || ! grep -Fq 'primary_judge_blocker' "$file"; then
    bad "$file — VERIFY phase body must compute pair_trigger after primary JUDGE"
    pair_trigger_order_missing=1
  fi
done
for file in \
  config/skills/devlyn:resolve/references/state-schema.md \
  .claude/skills/devlyn:resolve/references/state-schema.md \
  .agents/skills/devlyn:resolve/references/state-schema.md
do
  if ! grep -Fq 'MECHANICAL and the primary JUDGE have no verdict-binding blockers' "$file" \
    || ! grep -Fq 'may set only `user_no_pair`, `mechanical_blocker`, `primary_judge_blocker`, or null' "$file" \
    || ! grep -Fq '`risk_profile` must remain an object with boolean' "$file" \
    || ! grep -Fq 'state implies a pair decision is required but `pair_trigger` is missing' "$file"; then
    bad "$file — state schema must document pair_trigger blocker and missing-trigger enforcement"
    pair_trigger_order_missing=1
  fi
done
if [ $pair_trigger_order_missing -eq 0 ]; then
  ok "VERIFY pair trigger order waits for primary JUDGE evidence"
fi

section "Check 6h: No undocumented spec.expected.json.browser_flows field"
browser_flow_refs=$(grep -RInF 'spec.expected.json.browser_flows' \
  config/skills README.md bin/ package.json 2>/dev/null || true)
if [ -z "$browser_flow_refs" ]; then
  ok "active docs do not advertise unsupported browser_flows schema field"
else
  while IFS= read -r f; do bad "$f"; done <<< "$browser_flow_refs"
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
# 10a. Bounded Codex probe/judge calls must run isolated.
#      Pair/risk-probe paths are measured read-only judges, not implementation
#      phases. They must not inherit user config, AGENTS.md, hooks, pyx-memory,
#      or other local rules that can add hidden context or transcript side
#      effects. The wrapper owns the flag expansion; skill docs own requiring
#      CODEX_MONITORED_ISOLATED=1 for probe-derive and pair-JUDGE.
# ---------------------------------------------------------------------------
section "Check 10a: Bounded Codex calls use isolated wrapper mode"
isolation_missing=0
for needle in \
  'CODEX_MONITORED_ISOLATED=1 bash "$CODEX_MONITORED_PATH"' \
  'CODEX_MONITORED_ISOLATED=1` and `-c model_reasoning_effort=medium' \
  'CODEX_MONITORED_ISOLATED=1 bash .claude/skills/_shared/codex-monitored.sh'
do
  if ! grep -RInF "$needle" config/skills >/dev/null 2>&1; then
    bad "missing isolated Codex invocation contract: $needle"
    isolation_missing=1
  fi
done
for flag in \
  '--ignore-user-config' \
  '--ignore-rules' \
  '--ephemeral' \
  '--disable codex_hooks' \
  '--disable hooks'
do
  if ! grep -F -- "$flag" config/skills/_shared/codex-monitored.sh >/dev/null 2>&1; then
    bad "codex-monitored.sh missing isolation flag expansion: $flag"
    isolation_missing=1
  fi
done
for helper in require_positive_int require_nonnegative_int; do
  if ! grep -F "$helper" config/skills/_shared/codex-monitored.sh >/dev/null 2>&1; then
    bad "codex-monitored.sh missing numeric env validator: $helper"
    isolation_missing=1
  fi
done

if make_temp_dir tmp_env /tmp/codex-monitored-env.XXXXXX; then
  if CODEX_MONITORED_HEARTBEAT=0 CODEX_BIN=/bin/true \
    bash config/skills/_shared/codex-monitored.sh prompt \
    >"$tmp_env/heartbeat.stdout" 2>"$tmp_env/heartbeat.stderr"; then
    bad "codex-monitored.sh accepted CODEX_MONITORED_HEARTBEAT=0"
    isolation_missing=1
  elif ! grep -F 'CODEX_MONITORED_HEARTBEAT must be > 0' "$tmp_env/heartbeat.stderr" >/dev/null 2>&1; then
    bad "codex-monitored.sh heartbeat validation emitted wrong error"
    isolation_missing=1
  fi
  if CODEX_MONITORED_TIMEOUT_SEC=abc CODEX_BIN=/bin/true \
    bash config/skills/_shared/codex-monitored.sh prompt \
    >"$tmp_env/timeout.stdout" 2>"$tmp_env/timeout.stderr"; then
    bad "codex-monitored.sh accepted non-numeric CODEX_MONITORED_TIMEOUT_SEC"
    isolation_missing=1
  elif ! grep -F 'CODEX_MONITORED_TIMEOUT_SEC must be a non-negative integer' "$tmp_env/timeout.stderr" >/dev/null 2>&1; then
    bad "codex-monitored.sh timeout validation emitted wrong error"
    isolation_missing=1
  fi
  rm -rf "$tmp_env"
else
  isolation_missing=1
fi

if make_temp_dir tmp_iso /tmp/codex-monitored-isolated.XXXXXX; then
cat > "$tmp_iso/codex" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$CODEX_FAKE_ARGS_OUT"
EOF
  chmod +x "$tmp_iso/codex"
  CODEX_FAKE_ARGS_OUT="$tmp_iso/args.txt" \
  CODEX_MONITORED_ISOLATED=1 \
  CODEX_MONITORED_HEARTBEAT=999 \
  CODEX_BIN="$tmp_iso/codex" \
    bash config/skills/_shared/codex-monitored.sh -s read-only prompt \
    >"$tmp_iso/stdout.txt" 2>"$tmp_iso/stderr.txt"
  iso_exit=$?
  if [ $iso_exit -ne 0 ]; then
    bad "codex-monitored.sh isolated fake invocation exited $iso_exit"
    isolation_missing=1
  else
    for expected in exec --ignore-user-config --ignore-rules --ephemeral --disable codex_hooks --disable hooks -s read-only prompt; do
      if ! grep -Fx -- "$expected" "$tmp_iso/args.txt" >/dev/null 2>&1; then
        bad "codex-monitored.sh isolated fake invocation missing arg: $expected"
        isolation_missing=1
      fi
    done
    if ! grep -F '[codex-monitored] isolated=1' "$tmp_iso/stderr.txt" >/dev/null 2>&1; then
      bad "codex-monitored.sh isolated fake invocation missing lifecycle marker"
      isolation_missing=1
    fi
  fi
  rm -rf "$tmp_iso"
else
  isolation_missing=1
fi
if [ $isolation_missing -eq 0 ]; then
  ok "bounded Codex probe/judge calls require isolated wrapper mode"
fi

# ---------------------------------------------------------------------------
# 10b. Shared routing docs must describe the current 2-skill surface.
#      A stale auto-resolve/preflight/ideate-CHALLENGE reference can misroute
#      bounded pair work back into unisolated or retired Codex paths.
# ---------------------------------------------------------------------------
section "Check 10b: Shared routing docs avoid retired skill surfaces"
offenders=$(grep -RInE 'auto-resolve/SKILL\.md|preflight/SKILL\.md|challenge-rubric\.md|ideate CHALLENGE phase|does NOT consume this file|cross-model challenge phases when configured|phase-1-build\.md|phase-2-evaluate\.md|phase-3-critic\.md' \
  config/skills/_shared 2>/dev/null || true)
if [ -z "$offenders" ]; then
  ok "shared routing docs reference current devlyn:ideate/devlyn:resolve surface"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 10c. User-facing current docs must not advertise retired skills.
#      Historical archive mentions are allowed, but install/package copy and
#      active helper scripts should describe ideate -> resolve, not
#      ideate -> auto-resolve -> preflight or ideate CHALLENGE.
# ---------------------------------------------------------------------------
section "Check 10c: User-facing current docs avoid retired skill surfaces"
offenders=$(
  {
    grep -nE '/devlyn:auto-resolve|ideate CHALLENGE|--with-codex|Quick Start pointing to ideate → auto-resolve → preflight|auto-resolve'\''s build agent|Core pipeline skills \(`ideate`, `auto-resolve`, `preflight`\)' README.md 2>/dev/null || true
    grep -nE '"description": .*auto-resolve|"description": .*preflight' package.json 2>/dev/null || true
    grep -nE 'so auto-resolve doesn'\''t prompt' bin/devlyn.js 2>/dev/null || true
    grep -nE 'devlyn:auto-resolve|phase-1-build\.md|phase-2-evaluate\.md|phase-3-critic\.md' scripts/static-ab.sh 2>/dev/null || true
  } | sed -E 's#^#user-facing retired-surface reference: #'
)
if [ -z "$offenders" ]; then
  ok "README/package/helper copy describes current ideate -> resolve surface"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 10d. Prompt adapters cite the current official model guidance.
#      Prompt edits must be model-specific where tactics differ: OpenAI guidance
#      for GPT/Codex, Anthropic guidance for Claude. This check keeps that
#      contract from becoming oral tradition.
# ---------------------------------------------------------------------------
section "Check 10d: Prompt adapters cite official model guidance"
adapter_missing=0
if ! grep -Fq 'https://developers.openai.com/api/docs/guides/prompt-guidance?model=gpt-5.5' \
  config/skills/_shared/adapters/gpt-5-5.md; then
  bad "gpt-5-5 adapter missing official OpenAI prompt guidance URL"
  adapter_missing=1
fi
if ! grep -Fq 'https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices' \
  config/skills/_shared/adapters/opus-4-7.md; then
  bad "opus-4-7 adapter missing official Claude prompting best-practices URL"
  adapter_missing=1
fi
for pattern in 'Use Markdown only where it carries structure' 'metaprompter for itself'; do
  if ! grep -Fq "$pattern" config/skills/_shared/adapters/gpt-5-5.md; then
    bad "gpt-5-5 adapter missing official-guidance tactic: $pattern"
    adapter_missing=1
  fi
done
for pattern in 'high` or `xhigh` effort' 'report every issue you find' 'do not filter for importance or confidence' 'prefer concise positive examples' '<example>'; do
  if ! grep -Fq "$pattern" config/skills/_shared/adapters/opus-4-7.md; then
    bad "opus-4-7 adapter missing official-guidance tactic: $pattern"
    adapter_missing=1
  fi
done
for file in config/skills/devlyn:resolve/SKILL.md config/skills/devlyn:ideate/SKILL.md; do
  if ! grep -Fq '_shared/adapters/<model>.md' "$file"; then
    bad "$file — missing per-engine adapter injection contract"
    adapter_missing=1
  fi
done
if [ $adapter_missing -eq 0 ]; then
  ok "adapters cite official GPT/Claude guidance, carry model-specific tactics, and both skills inject them"
fi

# ---------------------------------------------------------------------------
# 10d1. Opus sidecar must fail closed on score-source mapping before provider calls.
# ---------------------------------------------------------------------------
section "Check 10d1: Opus judge sidecar validates blind mapping before provider calls"
if ! grep -Fq 'judge blind mapping missing arm(s)' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'scores_by_arm without blind mapping' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'scores_by_arm malformed score(s)' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'gpt judge.json _blind_mapping must be an object' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'def is_score(value):' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'not isinstance(value, bool) and 0 <= value <= 100' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'invalid opus score value(s)' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'invalid opus disqualifier value(s)' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'opus-invalid-generated-dq' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'def blind_mapping(j):' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'def mapped_arm_set(j):' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq '{"solo_claude", "bare"}.issubset(mapped_arms)' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'def mapped_scores(j):' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'if arm in mapped_arms and is_score(score)' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'def margin_from_scores(scores, left, right):' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'def mapped_winner(j, scores):' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'def fmt_metric(value):' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'g_l1_l0 = margin_from_scores(g_scores, "solo_claude", "bare")' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'g_v_l0 = margin_from_scores(g_scores, "variant", "bare")' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'g_winner = mapped_winner(g, g_scores)' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq '"winner_agree":   g_winner is not None and o_winner is not None and g_winner == o_winner' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq '"gpt_scores":   g_scores' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq '"opus_scores":  o_scores' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'opus-bad-mapping' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'opus-malformed-mapping' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'opus-malformed-score' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'opus-invalid-generated-score' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'arg-parse-opus-summary-mapping' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'arg-parse-opus-summary-null-margin' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'assert row["gpt_margin_l1_l0"] == 10' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'assert row["gpt_winner"] is None' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq "gpt_l1_l0_avg=na" benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'solo_claude-bare={chosen' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'variant-solo_claude={chosen' benchmark/auto-resolve/scripts/judge-opus-pass.sh; then
  offenders="${offenders}"$'\n'"judge-opus-pass.sh must validate _blind_mapping locally before invoking Claude"
fi

# ---------------------------------------------------------------------------
# 10e. Benchmark docs must describe the current solo-vs-pair topology.
#      Pair evidence work depends on the bare/solo_claude/pair contract being current:
#      bare, solo_claude, and the selected pair arm are measured today.
# ---------------------------------------------------------------------------
section "Check 10e: Benchmark docs describe current 3-arm pair topology"
offenders=$(grep -RInE 'L1 .*queued|cannot directly verify the L1|auto-resolve → preflight|ideate → auto-resolve|all fixtures × 2 arms|9 fixtures × 2 arms|9 fixtures × 3 arms|≥ 7 of 9|7/9 fixtures|variant` / `bare|variant/\{input|preflight; bare|Audited by preflight|Variant'\''s CRITIC|future enhancement|release-blocker|Today the suite runs `variant`|/devlyn:auto-resolve|auto-resolve-ready|REAL auto-resolve|real auto-resolve|auto-resolve run|auto-resolve runs|Claude/auto-resolve|variant − bare|Margin \(variant|Ship thresholds use margin \(variant|both arms improve together|both arms|benchmark --n 3|run-suite\.sh --n 3|higher confidence for ship decisions|3 runs per fixture for ship decisions|One-command A/B benchmark|A/B randomized|A/B benchmark suite vs bare|not vs bare — bare is the opponent' \
  benchmark/auto-resolve/BENCHMARK-DESIGN.md \
  benchmark/auto-resolve/README.md \
  benchmark/auto-resolve/RUBRIC.md \
  benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  benchmark/auto-resolve/run-real-benchmark.md \
  benchmark/auto-resolve/fixtures/SCHEMA.md \
  benchmark/auto-resolve/shadow-fixtures/README.md \
	  2>/dev/null || true)
fixture_note_stale=$(git grep -InE -- 'both arms|both solo and pair arms|bare or solo consistently reaches ceiling' -- \
  'benchmark/auto-resolve/fixtures/**/NOTES.md' \
  ':!benchmark/auto-resolve/fixtures/retired/**' \
  2>/dev/null || true)
if [ -n "$fixture_note_stale" ]; then
  offenders="${offenders}"$'\n'"fixture NOTES must name bare and solo_claude explicitly instead of ambiguous arm wording:"$'\n'"$fixture_note_stale"
fi
shadow_note_stale=$(git grep -In -- 'solo headroom' -- \
  'benchmark/auto-resolve/shadow-fixtures/**/NOTES.md' \
  2>/dev/null || true)
if [ -n "$shadow_note_stale" ]; then
  offenders="${offenders}"$'\n'"shadow fixture NOTES must name solo_claude headroom explicitly:"$'\n'"$shadow_note_stale"
fi
active_doc_stale_solo_scores=$(git grep -InE -- '(^|[^[:alnum:]_])solo [0-9]+|/ solo$|, solo [0-9]+|vs solo [0-9]+' -- \
  benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  benchmark/auto-resolve/README.md \
  benchmark/auto-resolve/run-real-benchmark.md \
  2>/dev/null || true)
if [ -n "$active_doc_stale_solo_scores" ]; then
  offenders="${offenders}"$'\n'"active benchmark score evidence must name solo_claude instead of shorthand solo:"$'\n'"$active_doc_stale_solo_scores"
fi
active_stale_margin_labels=$(git grep -InE -- 'l1-l0=|v-l1=|L1-L0 disagreement|Per-axis L1-L0|Suite-level per-axis L1-L0|Suite avg L1-L0|L2-L1 margin' -- \
  benchmark/auto-resolve/BENCHMARK-DESIGN.md \
  benchmark/auto-resolve/README.md \
  benchmark/auto-resolve/RUBRIC.md \
  benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  2>/dev/null || true)
if [ -n "$active_stale_margin_labels" ]; then
  offenders="${offenders}"$'\n'"active benchmark docs/stdout must use key-aligned margin labels:"$'\n'"$active_stale_margin_labels"
fi
if grep -RInE 'gate: ≥ 7 of 9|Hard floor 3: ≥ 7 of 9|7-of-9 L1 floor|all 9 fixtures produced' \
  benchmark/auto-resolve/scripts/compile-report.py \
  benchmark/auto-resolve/scripts/ship-gate.py \
  benchmark/auto-resolve/scripts/judge-opus-pass.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark scripts must describe the current extended fixture count as an explicit selected/gated set, not stale 9-fixture wording"
fi
if grep -Fq 'PAIR_ARM="l2_gated"' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh: default pair arm must stay on current measured l2_risk_probes path"
fi
if ! grep -Fq 'for required in result.json verify.json diff.patch; do' \
  benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'reuse source missing $required' \
    benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh: calibrated-arm reuse must fail closed on missing result.json, verify.json, and diff.patch"
fi
if ! grep -Fq 'reuse destination incomplete $required' \
  benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'reuse destination is not a directory' \
    benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh: calibrated-arm reuse must fail closed on incomplete existing destination"
fi
if ! grep -Fq 'diff.patch missing' benchmark/auto-resolve/scripts/headroom-gate.py \
  || ! grep -Fq 'diff.patch missing' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py; then
  offenders="${offenders}"$'\n'"benchmark pair gates must require diff.patch artifacts for measured arms"
fi
if ! grep -Fq 'pair-arm must be l2_risk_probes or l2_gated' \
  benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'pair-arm l2_forced is retired' \
    benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh: pair arm selection must fail closed before fixture execution"
fi
if ! grep -Fq 'l2_risk_probes|l2_gated) ;;' \
  benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh: runner allowlist must remain l2_risk_probes|l2_gated only"
fi
if grep -Fq 'default="l2_gated"' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py: --pair-arm default must stay on current measured l2_risk_probes path"
fi
if ! grep -Fq 'from pair_evidence_contract import (' \
  benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'ALLOWED_PAIR_ARMS,' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'ALLOWED_PAIR_ARMS = {"l2_risk_probes", "l2_gated"}' \
    benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'pair-arm l2_forced is retired' \
    benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py: pair arm selection must fail closed inside the gate"
fi
if ! grep -Fq '"l2_risk_probes"' benchmark/auto-resolve/scripts/check-f9-artifacts.py; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/check-f9-artifacts.py: F9 skill-driven artifact check must accept current l2_risk_probes arm"
fi
if ! grep -Fq '_load_json_object' benchmark/auto-resolve/scripts/check-f9-artifacts.py \
  || ! grep -Fq 'expected JSON object' benchmark/auto-resolve/scripts/test-check-f9-artifacts.sh; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/check-f9-artifacts.py: F9 timing/state JSON must fail closed on non-object payloads"
fi
if grep -RInE 'asserts variant/solo|Variant-only artifact checks|Variant artifact check' \
  benchmark/auto-resolve/scripts/check-f9-artifacts.py \
  benchmark/auto-resolve/fixtures/F9-e2e-ideate-to-resolve/NOTES.md \
  benchmark/auto-resolve/fixtures/F9-e2e-ideate-to-resolve/spec.md >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"F9 artifact docs/checker wording must describe skill-driven arms, not variant-only checks"
fi
if grep -Fq '<variant|bare>' benchmark/auto-resolve/scripts/run-fixture.sh; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/run-fixture.sh: usage must list current benchmark arms"
fi
if grep -Fq 'l2_gated/l2_forced' benchmark/auto-resolve/scripts/run-fixture.sh; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/run-fixture.sh: comments must not omit l2_risk_probes from l2_* arm handling"
fi
if grep -Fq 'ENGINE_CLAUSE="--engine auto"' benchmark/auto-resolve/scripts/run-fixture.sh \
  || grep -Fq 'Run with `--engine auto`' benchmark/auto-resolve/scripts/run-fixture.sh; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/run-fixture.sh: smoke variant arm must use current --engine claude --risk-probes path, not retired --engine auto"
fi
if ! grep -Fq 'ENGINE_CLAUSE="--engine claude --risk-probes"' benchmark/auto-resolve/scripts/run-fixture.sh; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/run-fixture.sh: variant/l2 risk-probes path must remain available"
fi
if ! grep -Fq '{bare, solo_claude, selected pair arm}' benchmark/auto-resolve/scripts/judge.sh; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/judge.sh: blind judge topology comment must describe current pair-candidate proof runs"
fi
if grep -Fq 'blind judge scores l2_gated' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || grep -Fq 'l2_gated is clean' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py: gate docstring must describe selected pair arm, not l2_gated-only proof"
fi
if grep -Fq 'only then spends a `l2_gated` arm' benchmark/auto-resolve/README.md \
  || grep -Fq 'fresh `l2_gated` measurement' benchmark/auto-resolve/README.md; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/README.md: full-pipeline runner docs must not present l2_gated as the default measured proof path"
fi
if ! grep -Fq 'Pair arms are limited to current' benchmark/auto-resolve/README.md \
  || ! grep -Fq '`l2_forced` is' benchmark/auto-resolve/README.md; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/README.md: full-pipeline docs must state allowed pair arms and retired l2_forced"
fi
if ! grep -Fq 'Current solo<pair' benchmark/auto-resolve/RUBRIC.md \
  || ! grep -Fq 'evidence uses the full-pipeline pair gate' benchmark/auto-resolve/RUBRIC.md \
  || ! grep -Fq 'explicit selected pair arm' benchmark/auto-resolve/RUBRIC.md \
  || ! grep -Fq 'selected pair arm over `solo_claude`' benchmark/auto-resolve/RUBRIC.md; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/RUBRIC.md: rubric must distinguish legacy run-suite ship gate from current selected-pair-arm evidence"
fi
if grep -Fq 'PHASE 8' benchmark/auto-resolve/run-real-benchmark.md \
  || grep -Fq 'security_review on `--engine auto`' benchmark/auto-resolve/run-real-benchmark.md \
  || grep -Fq 'BENCHMARK-RESULTS-v3.md' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/run-real-benchmark.md: real-run docs must describe the current 5-phase resolve and pair score harness"
fi
if ! grep -Fq 'Archive note (2026-05-14): historical pre-cutover benchmark plan' benchmark/auto-resolve/v3.6-ab-plan.md \
  || ! grep -Fq 'Do not use this file for current' benchmark/auto-resolve/v3.6-ab-plan.md \
  || ! grep -Fq 'Archive note (2026-05-14): historical pre-cutover results' benchmark/auto-resolve/BENCHMARK-RESULTS-v3.md \
  || ! grep -Fq 'Do not treat these projected' benchmark/auto-resolve/BENCHMARK-RESULTS-v3.md \
  || ! grep -Fq 'Archive note (2026-05-14): historical v3.2 pilot' benchmark/auto-resolve/PILOT-RESULTS-v3.2.md \
  || ! grep -Fq 'This n=1 pilot is not current solo<pair evidence' benchmark/auto-resolve/PILOT-RESULTS-v3.2.md \
  || ! grep -Fq 'Archive note (2026-05-14): historical v3.2 strict-route pilot' benchmark/auto-resolve/PILOT-RESULTS-STRICT-v3.2.md \
  || ! grep -Fq 'This inline n=1 pilot is not current solo<pair evidence' benchmark/auto-resolve/PILOT-RESULTS-STRICT-v3.2.md \
  || ! grep -Fq 'archived static comparison helper for pre-cutover auto-resolve' benchmark/auto-resolve/measure-static.py \
  || ! grep -Fq 'is not current solo<pair evidence' benchmark/auto-resolve/measure-static.py; then
  offenders="${offenders}"$'\n'"archived v3 benchmark artifacts must be clearly marked as non-current solo<pair evidence"
fi
if ! grep -Fq 'l2_risk_probes` | current measured pair path' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'Dry-runs, lint, and shell tests prove wiring only' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/run-real-benchmark.md: real-run docs must name the measured pair arm and distinguish wiring checks from scores"
fi
if grep -RInE 'F27.*unmeasured|unmeasured.*F27' \
  benchmark/auto-resolve/README.md \
  benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  benchmark/auto-resolve/run-real-benchmark.md \
  benchmark/auto-resolve/fixtures/retired/F27-cli-subscription-proration/NOTES.md >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"F27 docs must record the measured headroom failure, not stale unmeasured-candidate wording"
fi
if [ -d benchmark/auto-resolve/fixtures/F27-cli-subscription-proration ]; then
  offenders="${offenders}"$'\n'"F27 must stay out of active golden fixtures after failing headroom; keep it under fixtures/retired/"
fi
if [ ! -f benchmark/auto-resolve/fixtures/retired/F27-cli-subscription-proration/RETIRED.md ]; then
  offenders="${offenders}"$'\n'"retired F27 must keep RETIRED.md with the measured rejection reason"
fi
if ! grep -Fq '"benchmark/auto-resolve/fixtures/retired/F*/**"' package.json; then
  offenders="${offenders}"$'\n'"package.json must include retired fixtures so replay artifacts ship in npm packages"
fi
if ! grep -Fq '20260511-f27-headroom-smoke-061401' benchmark/auto-resolve/fixtures/retired/F27-cli-subscription-proration/NOTES.md \
  || ! grep -Fq '20260511-f27-headroom-smoke-061401' benchmark/auto-resolve/fixtures/retired/F27-cli-subscription-proration/RETIRED.md; then
  offenders="${offenders}"$'\n'"F27 notes must cite the measured headroom smoke run"
fi
if grep -Fq 'better candidate for pair risk probes' benchmark/auto-resolve/fixtures/retired/F27-cli-subscription-proration/NOTES.md; then
  offenders="${offenders}"$'\n'"F27 notes must not describe rejected F27 as a better pair-risk-probe candidate"
fi
if grep -Fq 'F16-cli-quote-tax-rules F27-cli-subscription-proration' \
  benchmark/auto-resolve/README.md benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"benchmark docs must not recommend rejected F27 in headroom/full-pipeline command examples"
fi
if [ -d benchmark/auto-resolve/fixtures/F28-cli-return-authorization ]; then
  offenders="${offenders}"$'\n'"F28 must stay out of active golden fixtures after corrected-oracle reverify failed headroom; keep it under fixtures/retired/"
fi
if [ ! -f benchmark/auto-resolve/fixtures/retired/F28-cli-return-authorization/RETIRED.md ]; then
  offenders="${offenders}"$'\n'"retired F28 must keep RETIRED.md with the corrected-oracle rejection reason"
fi
if ! grep -Fq '20260511-f28-headroom-smoke-085307' benchmark/auto-resolve/fixtures/retired/F28-cli-return-authorization/NOTES.md \
  || ! grep -Fq '20260511-f28-pair-smoke-091021' benchmark/auto-resolve/fixtures/retired/F28-cli-return-authorization/NOTES.md \
  || ! grep -Fq '20260511-f28-policy-oraclefix-reverified-pair' benchmark/auto-resolve/fixtures/retired/F28-cli-return-authorization/NOTES.md \
  || ! grep -Fq '20260511-f28-policy-oraclefix-reverified-pair' benchmark/auto-resolve/fixtures/retired/F28-cli-return-authorization/RETIRED.md \
  || ! grep -Fq '20260511-f28-headroom-smoke-085307' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq '20260511-f28-pair-smoke-091021' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq '20260511-f28-headroom-smoke-085307' benchmark/auto-resolve/README.md \
  || ! grep -Fq '20260511-f28-pair-smoke-091021' benchmark/auto-resolve/README.md \
  || ! grep -Fq '20260511-f28-headroom-smoke-085307' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq '20260511-f28-pair-smoke-091021' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"F28 docs must cite measured smoke and corrected-oracle rejection run ids before anyone counts it"
fi
if grep -Fq 'F16-cli-quote-tax-rules F28-cli-return-authorization' \
  benchmark/auto-resolve/README.md benchmark/auto-resolve/run-real-benchmark.md README.md; then
  offenders="${offenders}"$'\n'"benchmark docs must not recommend unstable F28 in pair-evidence command examples"
fi
if ! bash -n benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"pair-rejected-fixtures.sh must be valid bash"
fi
if ! grep -Fq 'trivial calibration fixture' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260512-f2-medium-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260511-f3-http-error-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260512-f4-web-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260512-f5-fixloop-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260512-f6-checksum-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260512-f7-scope-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq 'known-limit ambiguity fixture' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260512-f9-e2e-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260507-f10-f11-tier1-full-pipeline' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260511-f12-webhook-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260511-f15-concurrency-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq 'bare 94 / solo_claude 98 in 20260508-f22-exact-error-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260508-f26-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260511-f27-headroom-smoke-061401' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260511-f28-policy-oraclefix-reverified-pair' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260510-f29-headroom-v2' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260511-f30-headroom-v1' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260512-f31-seat-rebalance-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260512-f32-subscription-renewal-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260513-s2-inventory-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260513-s3-ticket-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260513-s4-return-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260513-s5-credit-headroom' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq '20260514-s6-refund-headroom-v1' benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh \
  || ! grep -Fq 'source "$BENCH_ROOT/scripts/pair-rejected-fixtures.sh"' benchmark/auto-resolve/scripts/run-headroom-candidate.sh \
  || ! grep -Fq 'source "$BENCH_ROOT/scripts/pair-rejected-fixtures.sh"' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'fixture_smoke_only' benchmark/auto-resolve/scripts/run-headroom-candidate.sh \
  || ! grep -Fq 'fixture_smoke_only' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'smoke-only-s1-provider-run' benchmark/auto-resolve/scripts/test-run-headroom-candidate.sh \
  || ! grep -Fq 'smoke-only-s1-provider-run' benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'smoke-only-s1-cli-headroom' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'smoke-only-s1-cli-pair' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'declare -F rejected_pair_fixture_reason' benchmark/auto-resolve/scripts/run-headroom-candidate.sh \
  || ! grep -Fq 'declare -F rejected_pair_fixture_reason' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'rejected-f31-fixture' benchmark/auto-resolve/scripts/test-run-headroom-candidate.sh \
  || ! grep -Fq 'rejected-f32-fixture' benchmark/auto-resolve/scripts/test-run-headroom-candidate.sh \
  || ! grep -Fq 'rejected-s6-shadow-fixture' benchmark/auto-resolve/scripts/test-run-headroom-candidate.sh \
  || ! grep -Fq 'rejected-f31-fixture' benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'rejected-f32-fixture' benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'rejected-s6-shadow-fixture' benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'load_rejected_short_ids' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'load_rejected_fixture_reasons' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'rejected_excluded' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'rejected_excluded_reasons' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'rejected_excluded_reasons' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh \
  || ! grep -Fq 'selection_rule.rejected_excluded_reasons' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'rejected_excluded_reasons' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'fixtures_pair_eligible must not be empty' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'gate3_threshold_count must be a positive integer' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'selection_rule.rejected_excluded_reasons keys must match rejected_excluded' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'nan-threshold-manifest' benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh \
  || ! grep -Fq 'bad-rejected-reasons-manifest' benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh \
  || ! grep -Fq 'fixture rejected for pair-candidate runs' benchmark/auto-resolve/scripts/headroom-gate.py \
  || ! grep -Fq 'fixture rejected for pair-candidate runs' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'rejected fixture registry missing' benchmark/auto-resolve/scripts/headroom-gate.py \
  || ! grep -Fq 'rejected fixture registry missing' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq '([FS]\d+)-\*\|([FS]\d+)' benchmark/auto-resolve/scripts/headroom-gate.py \
  || ! grep -Fq '([FS]\d+)-\*\|([FS]\d+)' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq '([FS]\d+)-\*\|([FS]\d+)' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq '([FS]\d+)-\*\|([FS]\d+)' benchmark/auto-resolve/scripts/audit-headroom-rejections.py \
  || ! grep -Fq '([FS]\d+)-\*\|([FS]\d+)' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'missing-rejected-registry' benchmark/auto-resolve/scripts/test-headroom-gate.sh \
  || ! grep -Fq 'missing-rejected-registry' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'rejected-shadow-direct' benchmark/auto-resolve/scripts/test-headroom-gate.sh \
  || ! grep -Fq 'rejected-shadow-direct' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 's-only-registry' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 's-only-registry' benchmark/auto-resolve/scripts/test-audit-headroom-rejections.sh \
  || ! grep -Fq 'shadow solo ceiling' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh \
  || grep -Fq 'case "$fid" in' benchmark/auto-resolve/scripts/run-headroom-candidate.sh \
  || grep -Fq 'case "$fid" in' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh; then
  offenders="${offenders}"$'\n'"pair candidate runners, audits, and manifest builder must honor the shared rejected fixture registry, including F* fixtures and S* shadow controls, without duplicating the case table"
fi
if ! grep -Fq 'Pair-candidate status: rejected by design' benchmark/auto-resolve/fixtures/F1-cli-trivial-flag/NOTES.md \
  || ! grep -Fq 'Pair-candidate status: rejected by design' benchmark/auto-resolve/fixtures/F8-known-limit-ambiguous/NOTES.md \
  || ! grep -Fq 'rejected by design' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq 'calibration/known-limit controls' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'calibration/known-limit controls' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"F1/F8 docs must mark calibration and known-limit controls as rejected by design for pair evidence"
fi
if ! grep -Fq '20260512-f2-medium-headroom' benchmark/auto-resolve/fixtures/F2-cli-medium-subcommand/NOTES.md \
  || ! grep -Fq '20260512-f2-medium-headroom' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq '20260512-f2-medium-headroom' benchmark/auto-resolve/README.md \
  || ! grep -Fq '20260512-f2-medium-headroom' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"F2 docs must cite the measured headroom rejection before anyone counts it"
fi
if ! grep -Fq '20260511-f12-webhook-headroom' benchmark/auto-resolve/fixtures/F12-webhook-raw-body-signature/NOTES.md \
  || ! grep -Fq '20260511-f12-webhook-headroom' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq '20260511-f12-webhook-headroom' benchmark/auto-resolve/README.md \
  || ! grep -Fq '20260511-f12-webhook-headroom' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"F12 docs must cite the measured headroom rejection before anyone counts it"
fi
if ! grep -Fq '20260507-f10-f11-tier1-full-pipeline' benchmark/auto-resolve/fixtures/F10-persist-write-collision/NOTES.md \
  || ! grep -Fq '20260507-f10-f11-tier1-full-pipeline' benchmark/auto-resolve/fixtures/F11-batch-import-all-or-nothing/NOTES.md \
  || ! grep -Fq '20260507-f10-f11-tier1-full-pipeline' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq '20260507-f10-f11-tier1-full-pipeline' benchmark/auto-resolve/README.md \
  || ! grep -Fq '20260507-f10-f11-tier1-full-pipeline' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"F10/F11 docs must cite the measured headroom rejection before anyone counts them"
fi
if ! grep -Fq '20260511-f3-http-error-headroom' benchmark/auto-resolve/fixtures/F3-backend-contract-risk/NOTES.md \
  || ! grep -Fq '20260511-f3-http-error-headroom' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq '20260511-f3-http-error-headroom' benchmark/auto-resolve/README.md \
  || ! grep -Fq '20260511-f3-http-error-headroom' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"F3 docs must cite the measured headroom rejection before anyone counts it"
fi
if ! grep -Fq '20260512-f4-web-headroom' benchmark/auto-resolve/fixtures/F4-web-browser-design/NOTES.md \
  || ! grep -Fq '20260512-f4-web-headroom' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq '20260512-f4-web-headroom' benchmark/auto-resolve/README.md \
  || ! grep -Fq '20260512-f4-web-headroom' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"F4 docs must cite the measured headroom rejection before anyone counts it"
fi
if ! grep -Fq '20260512-f5-fixloop-headroom' benchmark/auto-resolve/fixtures/F5-fix-loop-red-green/NOTES.md \
  || ! grep -Fq '20260512-f5-fixloop-headroom' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq '20260512-f5-fixloop-headroom' benchmark/auto-resolve/README.md \
  || ! grep -Fq '20260512-f5-fixloop-headroom' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"F5 docs must cite the measured headroom rejection before anyone counts it"
fi
if ! grep -Fq '20260512-f6-checksum-headroom' benchmark/auto-resolve/fixtures/F6-dep-audit-native-module/NOTES.md \
  || ! grep -Fq '20260512-f6-checksum-headroom' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq '20260512-f6-checksum-headroom' benchmark/auto-resolve/README.md \
  || ! grep -Fq '20260512-f6-checksum-headroom' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"F6 docs must cite the measured headroom rejection before anyone counts it"
fi
if ! grep -Fq '20260512-f7-scope-headroom' benchmark/auto-resolve/fixtures/F7-out-of-scope-trap/NOTES.md \
  || ! grep -Fq '20260512-f7-scope-headroom' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq '20260512-f7-scope-headroom' benchmark/auto-resolve/README.md \
  || ! grep -Fq '20260512-f7-scope-headroom' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"F7 docs must cite the measured headroom rejection before anyone counts it"
fi
if ! grep -Fq '20260512-f9-e2e-headroom' benchmark/auto-resolve/fixtures/F9-e2e-ideate-to-resolve/NOTES.md \
  || ! grep -Fq '20260512-f9-e2e-headroom' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq '20260512-f9-e2e-headroom' benchmark/auto-resolve/README.md \
  || ! grep -Fq '20260512-f9-e2e-headroom' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"F9 docs must cite the measured headroom rejection before anyone counts it"
fi
if ! grep -Fq '20260511-f15-concurrency-headroom' benchmark/auto-resolve/fixtures/F15-frozen-diff-race-review/NOTES.md \
  || ! grep -Fq '20260511-f15-concurrency-headroom' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq '20260511-f15-concurrency-headroom' benchmark/auto-resolve/README.md \
  || ! grep -Fq '20260511-f15-concurrency-headroom' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"F15 docs must cite the measured headroom rejection before anyone counts it"
fi
if ! grep -Fq '20260512-f31-seat-rebalance-headroom' benchmark/auto-resolve/fixtures/F31-cli-seat-rebalance/NOTES.md \
  || ! grep -Fq '20260512-f31-seat-rebalance-headroom' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq '20260512-f31-seat-rebalance-headroom' benchmark/auto-resolve/README.md \
  || ! grep -Fq '20260512-f31-seat-rebalance-headroom' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"F31 docs must cite the measured headroom rejection before anyone counts it"
fi
if grep -Fq 'execFileSync' benchmark/auto-resolve/fixtures/F31-cli-seat-rebalance/verifiers/priority-transfer-rollback.js \
  || ! grep -Fq "assert.strictEqual(result.stderr, '')" benchmark/auto-resolve/fixtures/F31-cli-seat-rebalance/verifiers/priority-transfer-rollback.js \
  || ! grep -Fq 'assert.deepStrictEqual(parsed, {' benchmark/auto-resolve/fixtures/F31-cli-seat-rebalance/verifiers/priority-transfer-rollback.js \
  || grep -Fq 'parsed.applied' benchmark/auto-resolve/fixtures/F31-cli-seat-rebalance/verifiers/priority-transfer-rollback.js \
  || ! grep -Fq 'On success, write exactly one JSON object to stdout and no stderr. Keys: `applied`, `rejected`, `accounts`.' benchmark/auto-resolve/fixtures/F31-cli-seat-rebalance/expected.json \
  || [ "$(grep -Fc 'On success, write exactly one JSON object to stdout and no stderr. Keys: `applied`, `rejected`, `accounts`.' benchmark/auto-resolve/fixtures/F31-cli-seat-rebalance/expected.json)" -ne 1 ]; then
  offenders="${offenders}"$'\n'"F31 priority verifier must bind success stderr/no-extra-output contract"
fi
if ! grep -Fq '20260512-f32-subscription-renewal-headroom' benchmark/auto-resolve/fixtures/F32-cli-subscription-renewal/NOTES.md \
  || ! grep -Fq '20260512-f32-subscription-renewal-headroom' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq '20260512-f32-subscription-renewal-headroom' benchmark/auto-resolve/README.md \
  || ! grep -Fq '20260512-f32-subscription-renewal-headroom' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"F32 docs must cite the measured headroom rejection before anyone counts it"
fi
if ! grep -Fq 'assert.deepEqual(output, {' benchmark/auto-resolve/fixtures/F32-cli-subscription-renewal/verifiers/priority-credit-rollback.js \
  || ! grep -Fq 'Output row key names and nested `credits` key names match the visible spec exactly, with no aliased or extra keys.' benchmark/auto-resolve/fixtures/F32-cli-subscription-renewal/expected.json \
  || [ "$(grep -Fc 'Output row key names and nested `credits` key names match the visible spec exactly, with no aliased or extra keys.' benchmark/auto-resolve/fixtures/F32-cli-subscription-renewal/expected.json)" -ne 1 ]; then
  offenders="${offenders}"$'\n'"F32 priority verifier must own exact output-shape contract without duplicate-error overclaim"
fi
if ! grep -Fq 'retired_fixture_exists' benchmark/auto-resolve/scripts/run-headroom-candidate.sh \
  || ! grep -Fq 'retired_fixture_exists' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'fixture is retired and is not rerun by pair-candidate runners' benchmark/auto-resolve/scripts/test-run-headroom-candidate.sh \
  || ! grep -Fq 'fixture is retired and is not rerun by pair-candidate runners' benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'historical artifact replay' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'historical artifact replay' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"pair candidate runners must reject retired fixtures explicitly and docs must reserve retired fixtures for historical artifact replay"
fi
if ! grep -Fq 'F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"run-real-benchmark.md examples must use the current measured F16/F23/F25 pair-evidence set"
fi
if ! grep -Fq '20260510-f16-f23-f25-combined-proof' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq '20260510-f16-f23-f25-combined-proof' benchmark/auto-resolve/README.md \
  || ! grep -Fq '20260510-f16-f23-f25-combined-proof' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"benchmark docs must cite the current F16/F23/F25 pair proof run"
fi
if ! grep -Fq 'average pair margin +25.3' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq 'average pair margin +25.3' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'average pair margin was `+25.3`' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"benchmark docs must cite the F16/F23/F25 average pair margin"
fi
if ! grep -Fq 'average solo_claude headroom **8.0**' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq 'minimum solo_claude' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq '| Fixture | Bare | Solo_claude | Pair (`l2_risk_probes`) | Margin | Pair mode | Wall ratio |' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq 'include `bare` headroom and `solo_claude` headroom' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'default 5-point `bare`/`solo_claude` headroom margins' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq 'average and minimum `bare`/`solo_claude`' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'average and minimum headroom' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'fixture pass count' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'fixture pass count' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"benchmark docs must cite and explain headroom set summaries"
fi
if ! grep -Fq 'both baseline arms evidence-complete' \
  benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/headroom-gate.md \
  || ! grep -Fq 'both baseline arms evidence-complete' \
    benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/headroom-gate.json \
  || ! grep -Fq 'Fixtures passed: 3/3 (minimum required: 3)' \
    benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/headroom-gate.md \
  || ! grep -Fq 'Average solo_claude headroom: 8.0' \
    benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/headroom-gate.md \
  || ! grep -Fq '"min_solo_headroom": 5' \
    benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/headroom-gate.json \
  || ! grep -Fq '| Fixture | Bare | Bare headroom | Solo_claude | Solo_claude headroom | Status | Reason |' \
    benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/headroom-gate.md \
  || ! grep -Fq '| F16-cli-quote-tax-rules | 50 | 10 | 75 | 5 | PASS |  |' \
    benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/headroom-gate.md \
  || ! grep -Fq '"solo_headroom": 14' \
    benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/headroom-gate.json; then
  offenders="${offenders}"$'\n'"tracked F16/F23/F25 headroom report must use current evidence-complete wording and headroom columns"
fi
if ! grep -Fq 'l2_risk_probes evidence-clean' \
  benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.md \
  || ! grep -Fq 'l2_risk_probes must be evidence-clean' \
    benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.json \
  || ! grep -Fq 'Fixtures passed: 3/3 (minimum required: 3)' \
    benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.md \
  || ! grep -Fq 'Average pair margin: +25.3' \
    benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.md \
  || ! grep -Fq '"avg_pair_margin": 25.333333333333332' \
    benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.json; then
  offenders="${offenders}"$'\n'"tracked F16/F23/F25 pair report must use current l2_risk_probes evidence-clean wording and average pair margin"
fi
if ! grep -Fq 'evidence-complete `bare <= 60`' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'evidence-complete `bare <= 60`' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"benchmark docs must describe baseline headroom arms as evidence-complete, not correctness-clean"
fi
if ! grep -Fq 'min-bare-headroom' benchmark/auto-resolve/scripts/headroom-gate.py \
  || ! grep -Fq 'min-solo-headroom' benchmark/auto-resolve/scripts/headroom-gate.py \
  || ! grep -Fq 'min-bare-headroom' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'min-solo-headroom' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'headroom >= 5' benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/headroom-gate.md \
  || ! grep -Fq 'headroom >= 5' benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.md \
  || ! grep -Fq 'default minimum 5-point `bare`/`solo_claude` headroom margin' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'default minimum 5-point `bare`/`solo_claude` headroom margin' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'default 5-point `bare`/`solo_claude` headroom margins' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'default 5-point `bare`/`solo_claude` headroom margins' benchmark/auto-resolve/BENCHMARK-DESIGN.md \
  || ! grep -Fq 'bare headroom 1 < 5' benchmark/auto-resolve/scripts/test-headroom-gate.sh \
  || ! grep -Fq 'bare headroom 1 < 5' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh; then
  offenders="${offenders}"$'\n'"benchmark headroom gates must reject threshold-fragile candidates with default 5-point baseline headroom margins"
fi
if [ -d benchmark/auto-resolve/results/20260511-f28-headroom-smoke-085307/F28-cli-return-authorization ]; then
  if python3 benchmark/auto-resolve/scripts/headroom-gate.py \
    --run-id 20260511-f28-headroom-smoke-085307 \
    --min-fixtures 1 \
    --out-json /tmp/devlyn-lint-f28-headroom-gate.json \
    --out-md /tmp/devlyn-lint-f28-headroom-gate.md >/dev/null 2>&1; then
    offenders="${offenders}"$'\n'"current local F28 headroom artifact must fail the default 5-point headroom margin gate"
  elif ! grep -Fq 'bare headroom 1 < 5' /tmp/devlyn-lint-f28-headroom-gate.md; then
    offenders="${offenders}"$'\n'"current local F28 headroom failure must cite bare headroom 1 < 5"
  fi
fi
if [ -d benchmark/auto-resolve/results/20260511-f28-pair-smoke-091021/F28-cli-return-authorization ]; then
  if python3 benchmark/auto-resolve/scripts/headroom-gate.py \
    --run-id 20260511-f28-pair-smoke-091021 \
    --min-fixtures 1 \
    --out-json /tmp/devlyn-lint-f28-pair-smoke-headroom-gate.json \
    --out-md /tmp/devlyn-lint-f28-pair-smoke-headroom-gate.md >/dev/null 2>&1; then
    offenders="${offenders}"$'\n'"current local F28 pair-smoke artifact must fail before pair evidence can be counted"
  elif ! grep -Fq 'bare score 65 > 60' /tmp/devlyn-lint-f28-pair-smoke-headroom-gate.md; then
    offenders="${offenders}"$'\n'"current local F28 pair-smoke failure must cite bare score 65 > 60"
  fi
fi
if ! grep -Fq 'startup `Gate:` line' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'startup `Gate:` line' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'headroom gate passed — candidate set accepted' benchmark/auto-resolve/scripts/run-headroom-candidate.sh \
  || ! grep -Fq 'headroom gate failed — candidate set rejected' benchmark/auto-resolve/scripts/run-headroom-candidate.sh \
  || ! grep -Fq 'candidate set was accepted or rejected' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'candidate set was accepted or rejected' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'fixture score table with bare score, bare' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'headroom, solo_claude score, solo_claude headroom' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'remaining headroom against' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'pair minus `solo_claude` margin' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'Fixture                         Bare  Solo_claude  Pair  Pair-Solo_claude' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'fixture score table with bare,' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'solo_claude, pair, margin, pair-mode' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'pair above `solo_claude`' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq 'Suite average variant-solo_claude margin' benchmark/auto-resolve/BENCHMARK-DESIGN.md \
  || ! grep -Fq 'legacy `variant`-`bare` (L2-L0)' benchmark/auto-resolve/RUBRIC.md \
  || ! grep -Fq '`solo_claude`-`bare` measures solo harness value; pair-`solo_claude` measures pair value' benchmark/auto-resolve/README.md \
  || ! grep -Fq '| fixture | bare | solo_claude | solo_claude-bare |' benchmark/auto-resolve/scripts/test-run-headroom-candidate.sh \
  || ! grep -Fq '| fixture | bare | solo_claude | solo_claude-bare |' benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq '| fixture | bare | solo_claude | pair | pair-solo_claude |' benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'startup `Headroom:` and `Pair:` lines' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'startup `Headroom:` / `Pair:` lines' benchmark/auto-resolve/README.md; then
  offenders="${offenders}"$'\n'"benchmark docs must describe real-run startup gate lines and headroom score columns"
fi
if ! grep -Fq 'DEVLYN_BENCHMARK_CLI_SUBCOMMAND: benchmarkMode' bin/devlyn.js \
  || ! grep -Fq 'npx devlyn-cli benchmark headroom --run-id "$RUN_ID"' benchmark/auto-resolve/scripts/run-headroom-candidate.sh \
  || ! grep -Fq 'npx devlyn-cli benchmark pair --run-id "$RUN_ID"' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'canonical trigger, margin >= +' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'canonical trigger, margin >= +5' benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'headroom gate failed — pair arm not executed' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'pair gate failed — pair evidence rejected' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'headroom gate passed — executing $PAIR_ARM' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'pair gate passed — pair evidence accepted' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'headroom fails, the runner explicitly says the pair arm was not executed' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'pair gate fails, it explicitly says pair evidence was rejected' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'then that pair evidence was accepted' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'If headroom fails, it reports that the pair arm was not executed' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'pair gate fails, it reports that pair evidence was rejected' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'then that pair evidence was' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'accepted. When launched through' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'the replay `Command:` uses the' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'same package CLI path' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'the replay command uses' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'uses that same' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'package CLI path' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"benchmark CLI headroom/pair runs must replay as npx devlyn-cli commands and docs must state that"
fi
if ! grep -Fq 'npx devlyn-cli benchmark headroom --min-fixtures 3 F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules' README.md \
  || ! grep -Fq 'npx devlyn-cli benchmark frontier --out-md /tmp/devlyn-pair-frontier.md' README.md \
  || ! grep -Fq 'npx devlyn-cli benchmark pair --min-fixtures 3 --max-pair-solo-wall-ratio 3 F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules' README.md \
  || ! grep -Fq 'average pair margin' README.md \
  || ! grep -Fq 'default 5-point `bare`/`solo_claude` headroom margins' README.md \
  || ! grep -Fq 'Add `--dry-run` to either score runner' README.md \
  || ! grep -Fq 'fixture count, and the replay command' README.md \
  || ! grep -Fq 'Dry-runs' README.md \
  || ! grep -Fq 'and lint prove wiring only; real score claims must cite the run id and fixture' README.md; then
  offenders="${offenders}"$'\n'"README.md must expose score-focused benchmark headroom/pair CLI paths and distinguish wiring checks from real scores"
fi
if ! grep -Fq 'npx devlyn-cli benchmark pair --min-fixtures 3 --max-pair-solo-wall-ratio 3 F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules' bin/devlyn.js \
  || ! grep -Fq -- '--max-pair-solo-wall-ratio N  default: 3' bin/devlyn.js \
  || ! grep -Fq 'MAX_PAIR_SOLO_WALL_RATIO=3' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'parser.add_argument("--max-pair-solo-wall-ratio", type=positive_float, default=3.0)' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq '"max_observed_pair_solo_wall_ratio": max(ratios) if ratios else None' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'Allowed pair/solo wall ratio' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'Maximum observed pair/solo wall ratio' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'Maximum observed pair/solo wall ratio: 2.00x' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'separates the allowed pair/solo wall ratio from the maximum observed pair/solo wall ratio' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'python3 "$GATE" --results-root "$TMP_DIR" --run-id slow-pair' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq -- '--min-fixtures 3' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq -- '--min-fixtures 3' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'average pair margin' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'average pair margin' benchmark/auto-resolve/README.md \
  || ! grep -Fq -- '--dry-run          validate args/fixtures and print replay command only' bin/devlyn.js \
  || ! grep -Fq 'does not produce' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'scores. When showing' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"benchmark pair examples must explicitly gate the current F16/F23/F25 proof set with --min-fixtures 3"
fi
if ! grep -Fq 'use 3 for F16/F23/F25 proof reruns; audit requires 4 passing evidence rows' bin/devlyn.js \
  || ! grep -Fq 'use 3 for F16/F23/F25 proof reruns; audit requires 4 passing evidence rows' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh; then
  offenders="${offenders}"$'\n'"benchmark CLI help must distinguish proof reruns from the four-row release audit"
fi
if ! grep -Fq 'judge blind mapping missing' benchmark/auto-resolve/scripts/headroom-gate.py \
  || ! grep -Fq 'judge blind mapping missing' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'blind_mapping_arm_missing' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq 'def trusted_winner()' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq 'raw_findings_by_arm = judge.get("findings_by_arm")' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq 'def critical_findings_for(arm: str)' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq 'def exact_bool(value)' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq '"malformed_boolean_fields": malformed_boolean_fields' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq '"dq_judge_malformed": judge_dq_malformed' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq 'def bool_or_none(value)' benchmark/auto-resolve/scripts/ship-gate.py \
  || ! grep -Fq 'l1_dq_by_fixture: dict[str, bool]' benchmark/auto-resolve/scripts/ship-gate.py \
  || ! grep -Fq 'summary arms_present malformed' benchmark/auto-resolve/scripts/ship-gate.py \
  || ! grep -Fq 'summary arms_present.solo_claude malformed' benchmark/auto-resolve/scripts/ship-gate.py \
  || ! grep -Fq 'summary margins_avg malformed' benchmark/auto-resolve/scripts/ship-gate.py \
  || ! grep -Fq 'raw_findings_letters = chosen.get("critical_findings")' benchmark/auto-resolve/scripts/judge.sh \
  || ! grep -Fq 'raw_findings_letters = chosen.get("critical_findings")' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'raw_validation = judge.get("_axis_validation")' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq 'raw_validation = judge.get("_axis_validation")' benchmark/auto-resolve/scripts/headroom-gate.py \
  || ! grep -Fq 'raw_validation = judge.get("_axis_validation")' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'raw_scores_by_arm = judge.get("scores_by_arm")' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq 'from pair_evidence_contract import is_score, is_strict_number' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq 'loads_strict_json_object(path.read_text())' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq 'parse_constant=reject_json_constant' benchmark/auto-resolve/scripts/ship-gate.py \
  || ! grep -Fq 'if arm in mapped_arms and is_score(score)' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq 'def strict_number(value)' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq 'raw_scores = judge.get("scores_by_arm")' benchmark/auto-resolve/scripts/headroom-gate.py \
  || ! grep -Fq 'raw_scores = judge.get("scores_by_arm")' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'from pair_evidence_contract import is_score' benchmark/auto-resolve/scripts/headroom-gate.py \
  || ! grep -Fq 'return value if is_score(value) else None' benchmark/auto-resolve/scripts/headroom-gate.py \
  || ! grep -Fq 'raw_scores = judge.get("scores_by_arm")' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'from pair_evidence_contract import is_score' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'def exact_bool(value: object)' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'def disqualifier_flag(value: object' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'if not is_score(solo) or not is_score(bare):' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'if is_score(score):' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'return legacy if is_score(legacy) else None' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'raw_scores = judge.get("scores_by_arm")' benchmark/auto-resolve/scripts/iter-0033c-l1-summary.py \
  || ! grep -Fq 'raw_scores = judge.get("scores_by_arm")' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'from pair_evidence_contract import (' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'is_score,' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'is_strict_number,' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'loads_strict_json_object(p.read_text())' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'parse_constant=reject_json_constant' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'PAIR_VERDICTS = {"PASS", "PASS_WITH_ISSUES", "NEEDS_WORK", "BLOCKED", "FAIL"}' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'def is_pair_judge_verdict(value: object) -> bool:' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'def exact_bool(value: object)' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'def bool_flag(value: object' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'if is_score(sba.get(arm)):' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'return legacy if is_score(legacy) else None' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'def strict_elapsed_seconds' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'def timeout_flag(result: dict | None) -> bool:' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'raw_scores = judge.get("scores_by_arm")' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'raw_dq_by_arm = judge.get("disqualifiers_by_arm")' benchmark/auto-resolve/scripts/headroom-gate.py \
  || ! grep -Fq 'raw_dq_by_arm = judge.get("disqualifiers_by_arm")' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'raw_dq_by_arm = judge.get("disqualifiers_by_arm")' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq 'raw_by_arm = judge.get("disqualifiers_by_arm")' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'raw_dba = judge.get("disqualifiers_by_arm")' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'raw_legacy = judge.get("disqualifiers")' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'raw_dqs = judge.get("disqualifiers")' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'def is_score(value):' benchmark/auto-resolve/scripts/judge.sh \
  || ! grep -Fq 'invalid judge score value(s)' benchmark/auto-resolve/scripts/judge.sh \
  || ! grep -Fq 'invalid judge disqualifier value(s)' benchmark/auto-resolve/scripts/judge.sh \
  || ! grep -Fq 'invalid opus disqualifier value(s)' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'if arm is not None and key in chosen and is_score(chosen[key]):' benchmark/auto-resolve/scripts/judge.sh \
  || ! grep -Fq 'raw_dq_letters = chosen.get("disqualifiers")' benchmark/auto-resolve/scripts/judge.sh \
  || ! grep -Fq 'raw_dq_letters = chosen.get("disqualifiers")' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'scores_by_arm` alone is not evidence' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'without the blind slot mapping is not score evidence' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'absent from the blind mapping is not score evidence' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'wrong-pair-mapping' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'from pair_evidence_contract import (' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'ALLOWED_PAIR_ARMS,' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'loads_strict_json_object,' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'def bool_flag_failure(value: Any, true_reason: str, malformed_reason: str) -> str | None:' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'def bool_flag_failure(value: object, true_reason: str, malformed_reason: str) -> str | None:' benchmark/auto-resolve/scripts/headroom-gate.py \
  || ! grep -Fq 'return value if is_score(value) else None' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'if not is_strict_number(pair_elapsed) or not is_strict_number(solo_elapsed):' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'return is_strict_number(value) and value >= 1.0' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'value must be finite and > 0' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'overrange-score' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'boolean-score' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'boolean-wall-time' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'invalid-max-wall-ratio' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'boolean-pair-verify-score' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'malformed-pair-bool' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'malformed-judge-bool' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'wrong-mapping' benchmark/auto-resolve/scripts/test-headroom-gate.sh \
  || ! grep -Fq 'overrange-score' benchmark/auto-resolve/scripts/test-headroom-gate.sh \
  || ! grep -Fq 'boolean-score' benchmark/auto-resolve/scripts/test-headroom-gate.sh \
  || ! grep -Fq 'malformed-bare-bool' benchmark/auto-resolve/scripts/test-headroom-gate.sh \
  || ! grep -Fq 'bare judge disqualifier malformed' benchmark/auto-resolve/scripts/test-headroom-gate.sh \
  || ! grep -Fq 'variant-mapping-disqualifies' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'solo-mapping-disqualifies' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'stale-margin' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'stale judge margins must be recomputed from trusted scores' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'winner without blind-mapped trusted score must be null' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'malformed scores_by_arm must not expose' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'out-of-range scores_by_arm must not expose variant score' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'boolean scores_by_arm must not expose solo score' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'boolean result numeric fields must not appear in compile summary' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'malformed-result-bool' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'malformed-judge-bool' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'malformed-l1-dq-summary' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'malformed-arms-present-wrapper' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'malformed-arms-present' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'malformed-margins-avg-wrapper' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'F1 L1 disqualifier malformed' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'overrange C1 row fields must not promote F17' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh \
  || ! grep -Fq 'string C1 disqualifier must not promote F18' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh \
  || ! grep -Fq 'f9-overrange-scores' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh \
  || ! grep -Fq 'f9-boolean-scores' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh \
  || ! grep -Fq 'f9-string-dq-entry' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh \
  || ! grep -Fq 'overrange-scores-results' benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh \
  || ! grep -Fq 'boolean-scores-results' benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh \
  || ! grep -Fq 'boolean-wall-results' benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh \
  || ! grep -Fq 'nan-wall-results' benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh \
  || ! grep -Fq 'string-timeout-results' benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh \
  || ! grep -Fq 'malformed-pair-state-results' benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh \
  || ! grep -Fq 'non-list finding entry must become a one-item list' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'non-dict findings_by_arm must be ignored' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'non-dict _axis_validation wrapper must not crash' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'load_dict_json' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq 'measurement invalid: malformed summary.json' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'nan-summary' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'summary rows contain non-object entries' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'malformed-summary-field-types' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'variant axis count malformed' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'result.json malformed' benchmark/auto-resolve/scripts/test-headroom-gate.sh \
  || ! grep -Fq 'result.json malformed' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'non-dict variant result.json must fail closed' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'NaN variant result.json must fail closed as a disqualifier' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq '("solo_claude (L1)", "solo_claude")' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq '| Fixture | Category | variant (L2) | solo_claude (L1) | bare (L0) | variant-bare | solo_claude-bare | variant-solo_claude | Winner | Wall variant/solo_claude/bare | Wall variant/solo_claude | Wall variant/bare |' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq '| Fixture | Category | variant (L2) | solo_claude (L1) | bare (L0) | variant-bare | solo_claude-bare | variant-solo_claude | Winner | Wall variant/solo_claude/bare | Wall variant/solo_claude | Wall variant/bare |' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq '**solo_claude (L1):**' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'variant (L2) vs solo_claude (L1) margin avg' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq '**variant (L2) vs solo_claude (L1) margin avg:** +10.0' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'Wall ratio variant (L2) / solo_claude (L1)' benchmark/auto-resolve/scripts/compile-report.py \
  || ! grep -Fq '**Wall ratio variant (L2) / solo_claude (L1):** 1.0x' benchmark/auto-resolve/scripts/test-ship-gate.sh \
  || ! grep -Fq 'malformed-scores' benchmark/auto-resolve/scripts/test-headroom-gate.sh \
  || ! grep -Fq 'malformed-scores' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'malformed-dq-entry' benchmark/auto-resolve/scripts/test-headroom-gate.sh \
  || ! grep -Fq 'malformed-dq-entry' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'malformed-axis-wrapper' benchmark/auto-resolve/scripts/test-headroom-gate.sh \
  || ! grep -Fq 'malformed-axis-wrapper' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'fixture-nan-metadata' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'fixture-nan-expected' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'c1-summary malformed: expected object' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh \
  || ! grep -Fq 'f9-judge malformed: expected object' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh \
  || ! grep -Fq 'malformed C1 row fields must not promote F1' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh \
  || ! grep -Fq 'F9 must not be included when scores_by_arm is malformed' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh \
  || ! grep -Fq 'truthy malformed disqualifier entry must exclude F9' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh \
  || ! grep -Fq 'disqualifiers": ["not", "a", "dict"]' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh \
  || ! grep -Fq 'bad-mapping' benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh \
  || ! grep -Fq 'write_fixture_with_malformed_dq_entry' benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh \
  || ! grep -Fq 'write_fixture_with_malformed_legacy_dq' benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh \
  || ! grep -Fq 'write_fixture_with_string_dq_entry' benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh \
  || ! grep -Fq 'write_fixture_with_malformed_result' benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh \
  || ! grep -Fq 'disqualifiers": ["not", "a", "dict"]' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'malformed compare.json for malformed-compare' benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh \
  || ! grep -Fq 'malformed compare.json for nan-compare: invalid JSON' benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh \
  || ! grep -Fq 'malformed-compare-sections' benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh \
  || ! grep -Fq 'malformed-verdict-fields' benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh \
  || ! grep -Fq 'malformed-elapsed-fields' benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh \
  || ! grep -Fq 'string-pair-mode' benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh \
  || ! grep -Fq 'def strict_positive_number(value):' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'math.isfinite(value)' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'def strict_nonnegative_int(value):' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'def summary_findings_count(data):' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'def severity_count_sum(data):' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'def strict_greater(left, right):' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'metadata = loads_strict_json_object(pathlib.Path(sys.argv[1]).read_text())' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'metadata timeout_seconds must be a positive integer' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'state = as_dict(loads_strict_json_object(state_path.read_text())) if state_path.is_file() else {}' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'json.loads(line, parse_constant=reject_json_constant)' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'summary = loads_strict_json_object(pathlib.Path(sys.argv[1]).read_text())' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'expected = loads_strict_json_object(pathlib.Path(sys.argv[1]).read_text())' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'out[arm] = loads_strict_json_object(path.read_text()) if path.is_file() else {"missing": True}' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'def as_dict(value):' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'metadata = loads_strict_json_object(pathlib.Path(sys.argv[1]).read_text())' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'metadata timeout_seconds must be a positive integer' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'expected = loads_strict_json_object(pathlib.Path(sys.argv[1]).read_text())' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'verify = as_dict(loads_strict_json_object(pathlib.Path(result_dir, "verify.json").read_text()))' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'loads_strict_json_object(pathlib.Path(result_dir, "timing.json").read_text())' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'loads_strict_json_object(pathlib.Path(state_path).read_text())' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'phases = as_dict(state.get("phases"))' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'legacy_verify = as_dict(state.get("verify"))' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'data = raw_oracle' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'oracle artifact malformed or unreadable' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq '"type": "oracle-error"' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'verify["oracle_disqualifier"] = True' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'findings = raw_findings if isinstance(raw_findings, list) else []' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'if not isinstance(finding, dict):' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'def as_dict(value):' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'phases = as_dict(state.get("phases"))' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'legacy_verify = as_dict(state.get("verify"))' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'PAIR_VERDICTS = {"PASS", "PASS_WITH_ISSUES", "NEEDS_WORK", "BLOCKED", "FAIL"}' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'def has_pair_judge_verdict(sub_verdicts):' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'PAIR_VERDICTS = {"PASS", "PASS_WITH_ISSUES", "NEEDS_WORK", "BLOCKED", "FAIL"}' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'def has_pair_judge_verdict(sub_verdicts):' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'or verify_phase.get("pair_mode") is True' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'has_pair_judge_verdict(sub_verdicts) or verify_phase.get("pair_mode") is True' benchmark/auto-resolve/scripts/run-fixture.sh \
  || ! grep -Fq 'has_pair_judge_verdict(sub_verdicts)' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'raw_pair_sub = pair.get("sub_verdicts")' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'raw_pair_trigger = pair.get("pair_trigger")' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'pair_trigger = raw_pair_trigger if isinstance(raw_pair_trigger, dict) else {}' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'pair_mode_true = pair.get("pair_mode") is True' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq 'def fmt_trigger_reasons(value):' benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq "| Arm | Verdict | Pair mode | Triggers | Findings | Elapsed | Invoke exit | Failure |" benchmark/auto-resolve/scripts/run-frozen-verify-pair.sh \
  || ! grep -Fq '| Arm | Verdict | Pair mode | Triggers | Findings | Elapsed | Invoke exit | Failure |' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'pair_mode = pair.get("pair_mode") is True' benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  || ! grep -Fq 'parse_constant=reject_json_constant' benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  || ! grep -Fq 'loads_strict_json_object(path.read_text())' benchmark/auto-resolve/scripts/check-f9-artifacts.py \
  || ! grep -Fq 'invalid JSON numeric constant: NaN' benchmark/auto-resolve/scripts/test-check-f9-artifacts.sh \
  || ! grep -Fq 'loads_strict_json_object(path.read_text(encoding="utf8"))' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq 'def pair_trigger_failures(' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq 'def pair_trigger_reasons(pair: dict[str, Any]) -> list[str]:' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq 'pair_trigger_eligible(pair)' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq '"pair_trigger_has_canonical_reason": has_canonical_pair_trigger_reason(trigger_reasons)' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq '"pair_trigger_has_canonical_reason": true' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'failed attempt: pair trigger contract: ' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq 'has_known_pair_trigger_reason(reasons)' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq 'all_known_pair_trigger_reasons(trigger["reasons"])' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq 'has_canonical_pair_trigger_reason(trigger["reasons"])' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq 'path_has_actionable_solo_headroom_hypothesis(fixture_spec)' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq 'pair_trigger reasons missing known trigger reason' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq 'pair_trigger reasons contain unknown trigger reason' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq 'pair_trigger reasons missing canonical trigger reason' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq 'pair_trigger missing spec.solo_headroom_hypothesis' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq -- '--require-hypothesis-trigger requires --fixtures-root' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq 'swebench-missing-hypothesis-trigger-test' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq -- '--require-hypothesis-trigger requires --fixtures-root' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'has_known_pair_trigger_reason(reasons)' benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  || ! grep -Fq 'all_known_pair_trigger_reasons(reasons)' benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  || ! grep -Fq 'has_canonical_pair_trigger_reason(reasons)' benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  || ! grep -Fq 'def pair_trigger_reasons(pair: dict[str, Any]) -> list[str]:' benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  || ! grep -Fq 'path_has_actionable_solo_headroom_hypothesis(fixtures_root / fixture_id / "spec.md")' benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  || ! grep -Fq 'pair_trigger missing spec.solo_headroom_hypothesis' benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  || ! grep -Fq -- '--require-hypothesis-trigger' benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  || ! grep -Fq -- '--require-hypothesis-trigger' benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh \
  || ! grep -Fq 'missing-hypothesis-trigger' benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh \
  || ! grep -Fq '"pair_trigger_has_canonical_reason": has_canonical_pair_trigger_reason(trigger_reasons)' benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  || ! grep -Fq '"pair_trigger_has_canonical_reason": true' benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh \
  || ! grep -Fq '| Run | Fixture | Solo VERIFY | Pair VERIFY | Pair mode | Triggers | Wall ratio | External lift | Internal lift | Status | Reason |' benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  || ! grep -Fq '| Run | Fixture | Solo VERIFY | Pair VERIFY | Pair mode | Triggers | Wall ratio | External lift | Internal lift | Status | Reason |' benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh \
  || ! grep -Fq 'pair_trigger reasons missing known trigger reason' benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  || ! grep -Fq 'pair_trigger reasons contain unknown trigger reason' benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  || ! grep -Fq 'pair_trigger reasons missing canonical trigger reason' benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  || ! grep -Fq 'normalized-canonical-pair-trigger' benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh \
  || ! grep -Fq '| Fixture | Solo VERIFY | Pair VERIFY | Pair mode | Pair trigger | Triggers | Wall ratio | External lift | Internal lift | Included | Classification |' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq '| Fixture | Solo VERIFY | Pair VERIFY | Pair mode | Pair trigger | Triggers | Wall ratio | External lift | Internal lift | Included | Classification |' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'def is_true(value: Any) -> bool:' benchmark/auto-resolve/scripts/swebench-frozen-matrix.py \
  || ! grep -Fq 'swebench-bool-elapsed-test' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'runner-nan-metadata' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'runner-nan-expected' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'json.loads(line, parse_constant=reject_json_constant)' benchmark/auto-resolve/scripts/run-swebench-solver-batch.sh \
  || ! grep -Fq 'nan-instance-row' benchmark/auto-resolve/scripts/test-run-swebench-solver-batch.sh \
  || ! grep -Fq 'manifest = loads_strict_json_object(pathlib.Path(sys.argv[1]).read_text())' benchmark/auto-resolve/scripts/run-iter-0033c.sh \
  || ! grep -Fq 'manifest fixtures_pair_eligible must be a string array' benchmark/auto-resolve/scripts/run-iter-0033c.sh \
  || ! grep -Fq 'parsed = json.loads(ln, parse_constant=reject_json_constant)' benchmark/auto-resolve/scripts/iter-0033c-compare.py \
  || ! grep -Fq 'data = loads_strict_json_object(path.read_text())' benchmark/auto-resolve/scripts/judge.sh \
  || ! grep -Fq 'decoder = json.JSONDecoder(parse_constant=reject_json_constant)' benchmark/auto-resolve/scripts/judge.sh \
  || ! grep -Fq 'judge = loads_strict_json_object(judge_path.read_text())' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'gpt = loads_strict_json_object(pathlib.Path(sys.argv[2]).read_text())' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'decoder = json.JSONDecoder(parse_constant=reject_json_constant)' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'g = loads_strict_json_object(g_f.read_text())' benchmark/auto-resolve/scripts/judge-opus-pass.sh \
  || ! grep -Fq 'swebench-malformed-pair-judge-test' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'swebench-malformed-pair-trigger-test' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'swebench-unknown-pair-trigger-test' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'swebench-normalized-pair-trigger-test' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'swebench-mixed-unknown-pair-trigger-test' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq '"classification": "failed attempt: pair trigger contract: pair_trigger missing or malformed"' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq '"classification": "failed attempt: pair trigger contract: pair_trigger reasons missing known trigger reason"' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq '"classification": "failed attempt: pair trigger contract: pair_trigger reasons contain unknown trigger reason"' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq '"classification": "failed attempt: pair trigger contract: pair_trigger reasons missing canonical trigger reason"' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'historical-only-pair-trigger' benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh \
  || ! grep -Fq 'HISTORICAL_ONLY_TRIGGER_RUN_ID' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq '| Pair trigger |' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq '"verify_findings_count": "2"' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq '"pair_found_more_low_or_worse": false' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'pair-trigger eligibility/contract failures' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'swebench-string-bool-matrix-test' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'findings = raw_findings if isinstance(raw_findings, list) else []' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'oracle artifact malformed or unreadable' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'scope-tier-a-nan' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'scope-tier-b-nan' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'expected.json malformed: spec_output_files must be a string array' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'loads_strict_json_object(exp_path.read_text())' benchmark/auto-resolve/scripts/oracle-scope-tier-a.py \
  || ! grep -Fq 'loads_strict_json_object(pathlib.Path(args.expected).read_text())' benchmark/auto-resolve/scripts/oracle-scope-tier-b.py \
  || ! grep -Fq 'failed attempt: malformed compare' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'swebench-nan-matrix-test' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'parse_prepared_case' benchmark/auto-resolve/scripts/prepare-swebench-frozen-corpus.py \
  || ! grep -Fq 'loads_strict_json_object(path.read_text(encoding="utf8"))' benchmark/auto-resolve/scripts/prepare-swebench-frozen-case.py \
  || ! grep -Fq 'parse_constant=reject_json_constant' benchmark/auto-resolve/scripts/collect-swebench-predictions.py \
  || ! grep -Fq 'parse_constant=reject_json_constant' benchmark/auto-resolve/scripts/prepare-swebench-frozen-corpus.py \
  || ! grep -Fq 'loads_strict_json_object(stdout)' benchmark/auto-resolve/scripts/prepare-swebench-frozen-corpus.py \
  || ! grep -Fq 'batch-bad-timeout' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'prepare-bad-timeout' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'prepare-nan-case' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'missing patch.diff for instance ids' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'no non-empty patches collected' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'collect-nan-instances' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'batch-nan-predictions' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'invalid JSON numeric constant: NaN' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'fetch-empty-limit' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'batch-empty-limit' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'no prediction instances selected' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'manifest malformed: expected JSON object' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'corpus-manifest-nan' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'loads_strict_json_object(manifest_path.read_text())' benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh \
  || ! grep -Fq 'loads_strict_json_object(pathlib.Path(sys.argv[1]).read_text())' benchmark/auto-resolve/scripts/run-swebench-frozen-corpus.sh \
  || ! grep -Fq 'manifest malformed: prepared must be a non-empty array' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'prepared[1] expected JSON object' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'run ids malformed: no run ids' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'run ids malformed: line 2 is empty' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'run ids malformed: line 1 has unsafe run id' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq -- '--fixture must match [A-Za-z0-9_.-]+' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq -- '--run-id must match [A-Za-z0-9_.-]+' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'unsafe SWE-bench repo' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'unsafe SWE-bench base_commit' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'parse_constant=reject_json_constant' benchmark/auto-resolve/scripts/prepare-swebench-solver-worktree.py \
  || ! grep -Fq 'parse_constant=reject_json_constant' benchmark/auto-resolve/scripts/fetch-swebench-instances.py \
  || ! grep -Fq 'malformed fetched row 1: row must be object' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'solver-nan' benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh \
  || ! grep -Fq 'malformed scores_by_arm must not provide arm scores' benchmark/auto-resolve/scripts/test-iter-0033c-l1-summary.sh \
  || ! grep -Fq 'non-dict result.json must not expose result fields' benchmark/auto-resolve/scripts/test-iter-0033c-l1-summary.sh \
  || ! grep -Fq 'NaN result numeric fields must not appear in L1 summary' benchmark/auto-resolve/scripts/test-iter-0033c-l1-summary.sh \
  || ! grep -Fq 'score_for(judge' benchmark/auto-resolve/scripts/iter-0033c-l1-summary.py \
  || ! grep -Fq 'from pair_evidence_contract import is_score, is_strict_number' benchmark/auto-resolve/scripts/iter-0033c-l1-summary.py \
  || ! grep -Fq 'loads_strict_json_object(path.read_text(encoding="utf8"))' benchmark/auto-resolve/scripts/iter-0033c-l1-summary.py \
  || ! grep -Fq 'return legacy if is_score(legacy) else None' benchmark/auto-resolve/scripts/iter-0033c-l1-summary.py \
  || ! grep -Fq 'def strict_number' benchmark/auto-resolve/scripts/iter-0033c-l1-summary.py \
  || ! grep -Fq 'out-of-range scores must not appear in L1 summary' benchmark/auto-resolve/scripts/test-iter-0033c-l1-summary.sh \
  || ! grep -Fq 'boolean scores must not appear in L1 summary' benchmark/auto-resolve/scripts/test-iter-0033c-l1-summary.sh \
  || ! grep -Fq 'boolean result numeric fields must not appear in L1 summary' benchmark/auto-resolve/scripts/test-iter-0033c-l1-summary.sh \
  || ! grep -Fq 'lowercase c_score' benchmark/auto-resolve/scripts/test-iter-0033c-l1-summary.sh; then
  offenders="${offenders}"$'\n'"benchmark gates must require judge _blind_mapping before accepting score evidence"
fi
if ! grep -Fq 'solo_claude beats bare' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'mapped_score' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'parse_constant=reject_json_constant' benchmark/auto-resolve/scripts/build-pair-eligible-manifest.py \
  || ! grep -Fq 'c1-nan-score' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh \
  || ! grep -Fq 'dirty F5 L1<=L0 row must not be promoted' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh \
  || ! grep -Fq 'l1-rerun-summary must not override pre-registered C1 selection grounds' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh \
  || ! grep -Fq 'wrong mapping' benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh; then
  offenders="${offenders}"$'\n'"build-pair-eligible-manifest.py must use arm-mapped clean scores for F9 and L1<=L0 promotion"
fi
if [ -d benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/F16-cli-quote-tax-rules ] \
  && ! python3 benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
    --run-id 20260510-f16-f23-f25-combined-proof \
    --pair-arm l2_risk_probes \
    --min-fixtures 3 \
    --min-pair-margin 5 \
    --max-pair-solo-wall-ratio 3 \
    --out-json /tmp/devlyn-lint-f16-f23-f25-pair-gate.json \
    --out-md /tmp/devlyn-lint-f16-f23-f25-pair-gate.md >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"current local artifacts for 20260510-f16-f23-f25-combined-proof must re-gate as PASS"
fi
if [ -d benchmark/auto-resolve/results/20260511-f21-current-riskprobes-v1/F21-cli-scheduler-priority ] \
  && ! python3 benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
    --run-id 20260511-f21-current-riskprobes-v1 \
    --pair-arm l2_risk_probes \
    --min-fixtures 1 \
    --min-pair-margin 5 \
    --max-pair-solo-wall-ratio 3 \
    --out-json /tmp/devlyn-lint-f21-pair-gate.json \
    --out-md /tmp/devlyn-lint-f21-pair-gate.md >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"current local artifacts for 20260511-f21-current-riskprobes-v1 must re-gate as PASS"
fi
if ! grep -Fq 'bash scripts/lint-fixtures.sh' benchmark/auto-resolve/README.md; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/README.md: gate-change instructions must include fixture schema lint"
fi
if ! python3 - <<'PY'
import runpy

runtime = runpy.run_path("config/skills/_shared/verify-merge-findings.py")
benchmark = runpy.run_path("benchmark/auto-resolve/scripts/pair_evidence_contract.py")

runtime_known = set(runtime["KNOWN_PAIR_TRIGGER_REASONS"])
canonical = set(benchmark["CANONICAL_PAIR_TRIGGER_REASONS"])
aliases = set(benchmark["HISTORICAL_PAIR_TRIGGER_REASON_ALIASES"])
normalized_aliases = set(benchmark["HISTORICAL_NORMALIZED_PAIR_TRIGGER_REASON_ALIASES"])
known = set(benchmark["KNOWN_PAIR_TRIGGER_REASONS"])
expected_aliases = {"risk_profile.high_risk", "risk_probes_enabled"}
expected_normalized_aliases = {
    "complexity.high.spec.frontmatter",
    "frontmatter.complexity.high",
    "high.complexity.spec",
    "high.risk.profile",
    "spec.frontmatter.complexity.high",
    "state.complexity.high",
}

errors = []
if canonical != runtime_known:
    errors.append("benchmark canonical pair-trigger reasons must match runtime reasons")
if aliases != expected_aliases:
    errors.append("benchmark historical pair-trigger aliases changed unexpectedly")
if normalized_aliases != expected_normalized_aliases:
    errors.append("benchmark normalized historical pair-trigger aliases changed unexpectedly")
if known != canonical | aliases:
    errors.append("benchmark known pair-trigger reasons must be canonical plus aliases")
if runtime_known & aliases:
    errors.append("runtime pair-trigger reasons must not accept benchmark-only aliases")
if not benchmark["has_historical_pair_trigger_reason"](["risk_profile.high_risk"]):
    errors.append("benchmark historical alias helper must detect exact aliases")
if benchmark["has_historical_pair_trigger_reason"](["complexity.high"]):
    errors.append("benchmark historical alias helper must not count canonical reasons")
if benchmark["is_known_pair_trigger_reason"]("risk high"):
    errors.append("benchmark pair-trigger reader must reject normalized canonical reason strings")
if benchmark["is_canonical_pair_trigger_reason"]("risk high"):
    errors.append("benchmark pair-trigger canonical helper must be exact-match only")
if not benchmark["is_known_pair_trigger_reason"]("high.risk.profile"):
    errors.append("benchmark pair-trigger reader must preserve documented normalized historical aliases")
if benchmark["is_canonical_pair_trigger_reason"]("high.risk.profile"):
    errors.append("benchmark normalized historical aliases must not count as canonical reasons")
if errors:
    raise SystemExit("\n".join(errors))
PY
then
  offenders="${offenders}"$'\n'"benchmark pair-trigger aliases must stay benchmark-only and runtime canonical reasons must stay in sync"
fi
	if ! grep -Fq 'bash scripts/lint-shadow-fixtures.sh' benchmark/auto-resolve/README.md \
	  || ! grep -Fq 'The headroom and pair candidate runners' benchmark/auto-resolve/README.md \
	  || ! grep -Fq 'accept explicitly named `S*` ids for dry-run checks and candidate measurement' benchmark/auto-resolve/README.md \
	  || ! grep -Fq 'Use `run-suite.sh --suite shadow` only with `--dry-run`' benchmark/auto-resolve/README.md \
	  || ! grep -Fq 'rejected/smoke controls do not' benchmark/auto-resolve/README.md \
	  || ! grep -Fq 'npx devlyn-cli benchmark headroom --dry-run --min-fixtures 1 S1-cli-lang-flag' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || ! grep -Fq 'Use non-dry-run headroom/pair only for' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || ! grep -Fq 'explicitly named `S*` candidates with a solo-headroom hypothesis' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || ! grep -Fq 'promote a validated `S*` task to an active `F*`' benchmark/auto-resolve/shadow-fixtures/README.md \
  || ! grep -Fq 'shadow suite run-suite is dry-run only' benchmark/auto-resolve/scripts/run-suite.sh \
  || ! grep -Fq 'run-suite.sh --suite shadow --dry-run' benchmark/auto-resolve/scripts/run-suite.sh \
  || ! grep -Fq 'shadow suite refuses provider/judge runs' benchmark/auto-resolve/scripts/run-suite.sh \
  || ! grep -Fq 'npx devlyn-cli benchmark suite --suite shadow --dry-run' bin/devlyn.js \
  || ! grep -Fq 'Use benchmark headroom/pair with explicit S* candidates for real provider measurement.' benchmark/auto-resolve/scripts/run-suite.sh \
  || ! grep -Fq 'shadow-suite-provider-run' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'shadow-suite-judge-only-provider-run' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'arg-parse-shadow-cli-suite-dry-run' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'shadow suite dry-run must not invite a blocked non-dry-run suite invocation' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
	  || ! grep -Fq '`run-suite.sh --suite shadow` is dry-run only' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || ! grep -Fq 'parallel to the active golden `F*` fixtures' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || ! grep -Fq 'Active golden `F*` fixtures and pair-evidence audits control' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || ! grep -Fq 'Default `--suite golden` keeps active golden `F*` behavior' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || ! grep -Fq 'before any bare/solo/pair measurement' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || ! grep -Fq 'Do not spend' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || ! grep -Fq 'real provider calls on S1' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || ! grep -Fq 'not a solo<pair evidence candidate' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || grep -Fq 'F1-F9 still controls release' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || grep -Fq 'existing F1-F9 behavior' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || grep -Fq 'L0/L1/L2 measurement' benchmark/auto-resolve/shadow-fixtures/README.md; then
  offenders="${offenders}"$'\n'"shadow fixture docs must describe lint and S* headroom/pair candidate calibration before golden promotion"
fi
if ! grep -Fq 'write a solo-headroom hypothesis' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'each new pair-candidate shadow fixture needs a' benchmark/auto-resolve/shadow-fixtures/README.md \
  || ! grep -Fq "candidate's \`spec.md\`: name the visible behavior a capable \`solo_claude\`" benchmark/auto-resolve/README.md \
  || ! grep -Fq '`solo_claude` baseline is expected to miss' benchmark/auto-resolve/shadow-fixtures/README.md \
  || ! grep -Fq "candidate's \`spec.md\`" benchmark/auto-resolve/README.md \
  || ! grep -Fq 'solo-headroom hypothesis in `spec.md`' benchmark/auto-resolve/shadow-fixtures/README.md \
  || ! grep -Fq 'observable command from `expected.json`' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'observable command from' benchmark/auto-resolve/shadow-fixtures/README.md \
  || ! grep -Fq 'candidate runners enforce this as an actionable hypothesis' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'runners enforce this as an actionable hypothesis' benchmark/auto-resolve/shadow-fixtures/README.md \
  || ! grep -Fq 'backticked observable command matching `expected.json`' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'backticked observable command matching `expected.json`' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || ! grep -Fq 'command/observable' benchmark/auto-resolve/README.md \
	  || ! grep -Fq 'command/observable' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || ! grep -Fq 'itself containing `miss`' benchmark/auto-resolve/README.md \
	  || ! grep -Fq 'itself containing `miss`' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || ! grep -Fq '## Solo ceiling avoidance' benchmark/auto-resolve/README.md \
	  || ! grep -Fq '## Solo ceiling avoidance' benchmark/auto-resolve/shadow-fixtures/README.md \
	  || ! grep -Fq 'solo-saturated `S2`-`S6` controls' benchmark/auto-resolve/README.md \
	  || ! grep -Fq 'calibrated solo-saturated controls (`S2`-`S6`)' benchmark/auto-resolve/shadow-fixtures/README.md; then
	  offenders="${offenders}"$'\n'"benchmark shadow candidate docs must require solo-headroom hypothesis and solo-ceiling avoidance before provider spend"
	fi
if [ ! -f benchmark/auto-resolve/scripts/solo-headroom-hypothesis.py ] \
  || ! grep -Fq 'def has_actionable_solo_headroom_hypothesis_text' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq '"solo-headroom hypothesis" in lower' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'and "solo_claude" in lower' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'and "miss" in lower' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'OBSERVABLE_COMMAND_MARKERS = ("command", "observable", "expose")' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def is_command_like_backtick' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def path_has_actionable_solo_headroom_hypothesis' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'has_actionable_solo_headroom_hypothesis_text(text)' benchmark/auto-resolve/scripts/solo-headroom-hypothesis.py \
  || ! grep -Fq 'actionable_observable_commands(text)' benchmark/auto-resolve/scripts/solo-headroom-hypothesis.py \
  || ! grep -Fq -- '--expected-json' benchmark/auto-resolve/scripts/solo-headroom-hypothesis.py \
  || ! grep -Fq 'expected_commands(args.expected_json)' benchmark/auto-resolve/scripts/solo-headroom-hypothesis.py \
  || ! grep -Fq 'expected UTF-8 text' benchmark/auto-resolve/scripts/solo-headroom-hypothesis.py \
  || ! grep -Fq 'solo-headroom-hypothesis.py' scripts/lint-shadow-fixtures.sh \
  || ! grep -Fq 'has_solo_ceiling_avoidance_note' scripts/lint-shadow-fixtures.sh \
  || ! grep -Fq 'solo-ceiling-avoidance.py' scripts/lint-shadow-fixtures.sh \
  || ! grep -Fq 'SECTION_RE' benchmark/auto-resolve/scripts/solo-ceiling-avoidance.py \
  || ! grep -Fq 'CONTROL_RE' benchmark/auto-resolve/scripts/solo-ceiling-avoidance.py \
  || ! grep -Fq 'REASON_RE' benchmark/auto-resolve/scripts/solo-ceiling-avoidance.py \
  || ! grep -Fq 'expected UTF-8 text' benchmark/auto-resolve/scripts/solo-ceiling-avoidance.py \
  || ! grep -Fq 'fixture_has_solo_ceiling_avoidance_note' benchmark/auto-resolve/scripts/run-headroom-candidate.sh \
  || ! grep -Fq 'fixture_has_solo_ceiling_avoidance_note' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'solo-ceiling-avoidance.py' benchmark/auto-resolve/scripts/run-headroom-candidate.sh \
  || ! grep -Fq 'solo-ceiling-avoidance.py' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'shadow fixture NOTES.md needs ## Solo ceiling avoidance' benchmark/auto-resolve/scripts/run-headroom-candidate.sh \
  || ! grep -Fq 'shadow fixture NOTES.md needs ## Solo ceiling avoidance' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'solo-headroom-hypothesis.py' benchmark/auto-resolve/scripts/run-headroom-candidate.sh \
  || ! grep -Fq 'solo-headroom-hypothesis.py' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq -- '--expected-json "$dir/expected.json" "$dir/spec.md"' benchmark/auto-resolve/scripts/run-headroom-candidate.sh \
  || ! grep -Fq -- '--expected-json "$dir/expected.json" "$dir/spec.md"' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq -- '--expected-json "$d/expected.json" "$spec"' scripts/lint-shadow-fixtures.sh \
  || ! grep -Fq 'from expected.json before provider spend' benchmark/auto-resolve/scripts/test-run-headroom-candidate.sh \
  || ! grep -Fq 'from expected.json before provider spend' benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'unrelated-backtick-solo-headroom-hypothesis' benchmark/auto-resolve/scripts/test-run-headroom-candidate.sh \
  || ! grep -Fq 'unrelated-backtick-solo-headroom-hypothesis' benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'observable-without-miss-solo-headroom-hypothesis' benchmark/auto-resolve/scripts/test-run-headroom-candidate.sh \
  || ! grep -Fq 'observable-without-miss-solo-headroom-hypothesis' benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'missing-solo-ceiling-avoidance' benchmark/auto-resolve/scripts/test-run-headroom-candidate.sh \
  || ! grep -Fq 'missing-solo-ceiling-avoidance' benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'weak-solo-ceiling-avoidance' benchmark/auto-resolve/scripts/test-run-headroom-candidate.sh \
  || ! grep -Fq 'weak-solo-ceiling-avoidance' benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'hypothesis with unrelated backtick must fail' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
  || ! grep -Fq 'weak hypothesis without observable command must fail' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
  || ! grep -Fq 'actionable-hypothesis.md' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
  || ! grep -Fq 'docs-style-actionable-hypothesis.md' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
  || ! grep -Fq 'shadow-missing-solo-ceiling-avoidance' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
  || ! grep -Fq 'shadow-weak-solo-ceiling-avoidance' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
  || ! grep -Fq 'weak solo ceiling avoidance must fail' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
  || ! grep -Fq 'non-utf8-solo-ceiling.md' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
  || ! grep -Fq 'non-utf8-hypothesis.md' benchmark/auto-resolve/scripts/test-lint-fixtures.sh; then
  offenders="${offenders}"$'\n'"solo-headroom hypothesis provider-spend guards must share one actionable checker and test weak-vs-actionable cases"
fi
if ! grep -Fq 'pair-candidate-frontier.py' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'npx devlyn-cli benchmark frontier --out-md /tmp/devlyn-pair-frontier.md' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'npx devlyn-cli benchmark frontier --out-md /tmp/devlyn-pair-frontier.md' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'npx devlyn-cli benchmark audit --out-dir /tmp/devlyn-benchmark-audit' README.md \
  || ! grep -Fq 'npx devlyn-cli benchmark audit --out-dir /tmp/devlyn-benchmark-audit' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'npx devlyn-cli benchmark audit --out-dir /tmp/devlyn-benchmark-audit' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'npx devlyn-cli benchmark audit --require-hypothesis-trigger --out-dir /tmp/devlyn-benchmark-audit-strict' README.md \
  || ! grep -Fq 'npx devlyn-cli benchmark audit --require-hypothesis-trigger --out-dir /tmp/devlyn-benchmark-audit-strict' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'npx devlyn-cli benchmark audit --require-hypothesis-trigger --out-dir /tmp/devlyn-benchmark-audit-strict' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'npx devlyn-cli benchmark audit --require-hypothesis-trigger --out-dir /tmp/devlyn-benchmark-audit-strict' bin/devlyn.js \
  || ! grep -Fq 'npx devlyn-cli benchmark audit --require-hypothesis-trigger --out-dir /tmp/devlyn-benchmark-audit-strict' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'npx devlyn-cli benchmark frontier            Show pair candidate frontier scores/triggers without providers' bin/devlyn.js \
  || ! grep -Fq 'npx devlyn-cli benchmark frontier            Show pair candidate frontier scores/triggers without providers' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'npx devlyn-cli benchmark audit               Audit pair evidence readiness' bin/devlyn.js \
  || ! grep -Fq 'npx devlyn-cli benchmark audit               Audit pair evidence readiness' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'Show active rejected/evidence/unmeasured pair candidates, scores, and triggers without providers' bin/devlyn.js \
  || ! grep -Fq 'Show active rejected/evidence/unmeasured pair candidates, scores, and triggers without providers' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'Prints pair evidence score rows with trigger reasons; --out-md includes a Triggers column' bin/devlyn.js \
  || ! grep -Fq 'Prints pair evidence score rows with trigger reasons; --out-md includes a Triggers column' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'Prints frontier score rows plus headroom and pair quality handoff rows' bin/devlyn.js \
  || ! grep -Fq 'Prints frontier score rows plus headroom and pair quality handoff rows' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'Prints frontier score rows plus headroom_rejections=PASS/FAIL, pair_evidence_quality=PASS/FAIL, pair_trigger_reasons=PASS/FAIL, pair_evidence_hypotheses=PASS/FAIL, pair_evidence_hypothesis_triggers=PASS/WARN/FAIL, historical-alias, and hypothesis-trigger gap handoff rows' bin/devlyn.js \
  || ! grep -Fq 'Prints frontier score rows plus headroom_rejections=PASS/FAIL, pair_evidence_quality=PASS/FAIL, pair_trigger_reasons=PASS/FAIL, pair_evidence_hypotheses=PASS/FAIL, pair_evidence_hypothesis_triggers=PASS/WARN/FAIL, historical-alias, and hypothesis-trigger gap handoff rows' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq "audit: 'audit-pair-evidence.py'" bin/devlyn.js \
  || ! grep -Fq 'npx devlyn-cli benchmark audit [options]' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq -- '--min-pair-evidence N  default: 4' bin/devlyn.js \
  || ! grep -Fq -- '--min-pair-evidence N  default: 4' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq -- '--min-pair-margin N  default: 5' bin/devlyn.js \
  || ! grep -Fq -- '--min-pair-margin N  default: 5' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq -- '--max-pair-solo-wall-ratio N  default: 3' bin/devlyn.js \
  || ! grep -Fq -- '--max-pair-solo-wall-ratio N  default: 3' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq -- '--require-hypothesis-trigger' bin/devlyn.js \
  || ! grep -Fq -- '--require-hypothesis-trigger' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq -- '--require-hypothesis-trigger' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'npx devlyn-cli benchmark audit-headroom --out-json /tmp/devlyn-headroom-audit.json' README.md \
  || ! grep -Fq 'npx devlyn-cli benchmark audit-headroom --out-json /tmp/devlyn-headroom-audit.json' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'npx devlyn-cli benchmark audit-headroom --out-json /tmp/devlyn-headroom-audit.json' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'npx devlyn-cli benchmark audit-headroom      Audit failed headroom results' bin/devlyn.js \
  || ! grep -Fq 'npx devlyn-cli benchmark audit-headroom      Audit failed headroom results' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq "'audit-headroom': 'audit-headroom-rejections.py'" bin/devlyn.js \
  || ! grep -Fq 'npx devlyn-cli benchmark audit-headroom [options]' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'benchmarkMode === '\''frontier'\''' bin/devlyn.js \
  || ! grep -Fq 'test-pair-candidate-frontier.sh' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'audit-pair-evidence.py' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'PASS audit-pair-evidence' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'FAIL audit-pair-evidence' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'FAIL audit-pair-evidence' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'audit.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'audit.json' README.md \
  || ! grep -Fq 'audit.json' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'audit.json' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq '"frontier_summary": frontier_summary' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"pair_evidence_rows": pair_evidence_rows' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def load_pair_evidence_rows' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def load_frontier_stdout_metrics' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"summary_rows": summary_rows' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"aggregate_rows": aggregate_rows' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"trigger_rows": trigger_rows' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"trigger_rows_match_count": trigger_rows == expected_rows' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"hypothesis_trigger_rows_match_count": hypothesis_trigger_rows == expected_rows' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'from pair_evidence_contract import' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'from pair_evidence_contract import' benchmark/auto-resolve/scripts/audit-headroom-rejections.py \
  || ! grep -Fq 'from pair_evidence_contract import' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'def reject_json_constant' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def loads_strict_json_object' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'parse_constant=reject_json_constant' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'loads_strict_json_object(path.read_text())' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'loads_strict_json_object(path.read_text())' benchmark/auto-resolve/scripts/headroom-gate.py \
  || ! grep -Fq 'loads_strict_json_object(path.read_text())' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'loads_strict_json_object(path.read_text())' benchmark/auto-resolve/scripts/audit-headroom-rejections.py \
  || ! grep -Fq 'loads_strict_json_object(path.read_text())' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'nan-json-constant' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'nan-result-json' benchmark/auto-resolve/scripts/test-headroom-gate.sh \
  || ! grep -Fq 'nan-result-json' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'CANONICAL_PAIR_TRIGGER_REASONS = {' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'HISTORICAL_PAIR_TRIGGER_REASON_ALIASES = {' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'HISTORICAL_NORMALIZED_PAIR_TRIGGER_REASON_ALIASES = {' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'Benchmark readers accept historical aliases only for archived artifacts' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'KNOWN_PAIR_TRIGGER_REASONS = (' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'mode.pair-verify' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def normalized_pair_trigger_reason' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def is_canonical_pair_trigger_reason' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def has_known_pair_trigger_reason' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def all_known_pair_trigger_reasons' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def has_canonical_pair_trigger_reason' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'spec.solo_headroom_hypothesis' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'risk_profile.high_risk' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'has_known_pair_trigger_reason(reasons)' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'all_known_pair_trigger_reasons(reasons)' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'has_canonical_pair_trigger_reason(reasons)' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq '"pair_trigger_has_canonical_reason": has_canonical_pair_trigger_reason(' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq '"pair_trigger_has_hypothesis_reason": (' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq '"require_hypothesis_trigger": args.require_hypothesis_trigger' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq '"pair_trigger_has_canonical_reason": true' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq '"pair_trigger_has_hypothesis_reason": true' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq '"require_hypothesis_trigger": true' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'pair_trigger eligible with a canonical reason' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'pair_trigger eligible with canonical reason' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'pair_trigger reasons missing known trigger reason' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'pair_trigger reasons contain unknown trigger reason' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'pair_trigger reasons missing canonical trigger reason' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'fixture_spec_has_solo_headroom_hypothesis(fixture_dir.name)' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'pair_trigger missing spec.solo_headroom_hypothesis' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq -- '--require-hypothesis-trigger' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq -- '--require-hypothesis-trigger' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'release audit: npx devlyn-cli benchmark audit --require-hypothesis-trigger --out-dir /tmp/devlyn-benchmark-audit-strict' benchmark/auto-resolve/scripts/run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'release audit: npx devlyn-cli benchmark audit --require-hypothesis-trigger --out-dir /tmp/devlyn-benchmark-audit-strict' benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'missing-hypothesis-trigger' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'grep -Fq -- '\''--require-hypothesis-trigger'\''' benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh \
  || ! grep -Fq 'def fmt_trigger_reasons' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq 'Hypothesis trigger required: {str(report' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq '| Fixture | Bare | Bare headroom | Solo_claude | Solo_claude headroom | Pair | Margin | Pair mode | Hypothesis trigger | Triggers | Wall ratio | Status | Reason |' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq '| Fixture | Bare | Bare headroom | Solo_claude | Solo_claude headroom | Pair | Margin | Pair mode | Hypothesis trigger | Triggers | Wall ratio | Status | Reason |' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'trigger-reason, and wall-ratio columns' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'eligible with non-empty reasons and at least one canonical reason' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'fixtures with an actionable solo-headroom hypothesis must include `spec.solo_headroom_hypothesis` in the trigger reasons' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'pair trigger eligibility, trigger reasons, canonical-trigger coverage, and `spec.solo_headroom_hypothesis` coverage' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'unknown-pair-trigger-reason' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'mixed-unknown-pair-trigger-reason' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'normalized-canonical-pair-trigger-reason' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'historical-only-pair-trigger-reason' benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh \
  || ! grep -Fq 'unknown-pair-trigger' benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh \
  || ! grep -Fq 'def normalize_pair_evidence_row' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def best_pair_evidence' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'ALLOWED_PAIR_ARMS = {"l2_risk_probes", "l2_gated"}' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'pair_arm not in ALLOWED_PAIR_ARMS' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'pair_mode = row.get("pair_mode")' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'if pair_mode is not True:' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'pair_trigger_eligible = row.get("pair_trigger_eligible")' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'if pair_trigger_eligible is not True:' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'pair_trigger_reasons = row.get("pair_trigger_reasons")' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'isinstance(pair_trigger_reasons, list)' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'all_known_pair_trigger_reasons(pair_trigger_reasons)' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'has_canonical_pair_trigger_reason(pair_trigger_reasons)' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq '"pair_trigger_reasons": pair_trigger_reasons' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq '"pair_trigger_has_canonical_reason": True' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq '"pair_trigger_has_hypothesis_reason": (' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def pair_result_trigger_reasons' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'candidate_row = dict(row)' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'all_known_pair_trigger_reasons(reasons)' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'has_canonical_pair_trigger_reason(reasons)' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'candidate_row["pair_trigger_reasons"] = reasons' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq '"reasons": ["complexity.high", "looks-hard"]' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq '"reasons":["risk high"]' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'triggers={triggers}' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'hypothesis_trigger={hypothesis_trigger}' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq '| Fixture | Status | Verdict | Evidence | Pair arm | Triggers | Hypothesis trigger |' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'pair-arm, and trigger-reason columns' benchmark/auto-resolve/README.md \
  || ! grep -Fq '| Fixture | Status | Verdict | Evidence | Pair arm | Triggers | Hypothesis trigger |' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'def check_pair_evidence_hypotheses' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def pair_evidence_hypothesis_trigger_rows' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def pair_evidence_hypothesis_trigger_gap_details' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def check_pair_evidence_hypothesis_triggers' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def print_pair_evidence_hypothesis_triggers_summary' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'pair_evidence_hypotheses={status}' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'pair_evidence_hypothesis_triggers={status}' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'pair evidence hypotheses missing for fixture(s)' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'pair-evidence-hypotheses' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'pair_evidence_hypotheses=PASS documented=2 total=2' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'pair_evidence_hypothesis_triggers=WARN matched=0 documented=2 total=2' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'pair_evidence_hypothesis_trigger_gaps=F16-cli-quote-tax-rules=complexity.high;F21-cli-scheduler-priority=complexity.high,risk_profile.high_risk' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'pair_evidence_hypothesis_triggers=FAIL matched=0 documented=2 total=2' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'strict benchmark audit must not report current hypothesis-trigger gaps' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'pair_evidence_hypothesis_triggers=PASS matched=4 documented=4 total=4' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'verdict=pair_evidence_passed triggers={triggers}' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def format_trigger_reasons' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'missing-frontier-triggers' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'triggers=complexity.high' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq '"pair_trigger_reasons": pair_trigger_reasons(pair_result)' benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  || ! grep -Fq '"pair_trigger_eligible": pair_trigger_eligible' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq '"verdict": "pair_evidence_passed"' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"pair_mode": pair_mode' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def pair_result_trigger_reasons' benchmark/auto-resolve/scripts/audit-headroom-rejections.py \
  || ! grep -Fq 'candidate_row = dict(row)' benchmark/auto-resolve/scripts/audit-headroom-rejections.py \
  || ! grep -Fq 'candidate_row["pair_trigger_reasons"] = reasons' benchmark/auto-resolve/scripts/audit-headroom-rejections.py \
  || ! grep -Fq 'F16-cli-quote-tax-rules/l2_risk_probes/result.json' benchmark/auto-resolve/scripts/test-audit-headroom-rejections.sh \
  || ! grep -Fq '"reasons":["risk high"]' benchmark/auto-resolve/scripts/test-audit-headroom-rejections.sh \
  || ! grep -Fq 'def is_strict_int' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def is_score' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq '0 <= value <= 100' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def is_strict_number' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'import math' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'math.isfinite(value)' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'and value > 0' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'if pair_margin != pair_score - solo_score:' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq '"min_pair_evidence": min_pair_evidence' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"actual_rows": len(pair_evidence_rows)' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"rows_match_count": (' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"pair_evidence_quality": {' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def check_pair_evidence_quality' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def print_pair_evidence_quality' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def check_pair_trigger_reasons' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def print_pair_trigger_reasons_summary' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def pair_trigger_historical_alias_details' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'pair_evidence_quality={status} min_pair_margin_actual={actual_margin}' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'pair_trigger_reasons={status} canonical={canonical} historical_alias={historical_alias}' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"historical_alias_details": historical_alias_details' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'frontier pair_margin_min does not match pair evidence rows' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'frontier pair_solo_wall_ratio_max does not match pair evidence rows' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'is_strict_int(pair_evidence_count)' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'if not is_strict_int(count):' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'pair evidence count missing or malformed from frontier report' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'pair evidence rows {len(rows)} do not match summary count {count}' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def check_frontier_report' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'frontier verdict {verdict!r} is not PASS' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'frontier has {unmeasured_count} unmeasured candidate fixture(s)' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"frontier_report": {' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"min_pair_margin": min_pair_margin' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"max_pair_solo_wall_ratio": max_pair_solo_wall_ratio' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'not math.isfinite(args.max_pair_solo_wall_ratio)' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'max-pair-solo-wall-ratio must be finite and > 0' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'pair evidence count {count} below required minimum {minimum}' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'assert audit["checks"]["min_pair_evidence"]["actual_rows"] == len(audit["pair_evidence_rows"])' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'assert audit["checks"]["frontier_report"]["verdict"] == frontier["verdict"]' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'pair_evidence_quality=PASS min_pair_margin_actual=+21 min_pair_margin_required=+5 max_wall_actual=2.25x max_wall_allowed=3.00x' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'pair_trigger_reasons=PASS canonical=4 historical_alias=0 exposed=4 total=4 summary=4 rows_match=true' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'current benchmark audit must not report historical aliases or hypothesis-trigger gaps' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'benchmark audit must fail when min pair evidence exceeds current evidence rows' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'actual_pair_evidence=$(python3 - "$TMP/audit/audit.json"' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'required_pair_evidence=$((actual_pair_evidence + 1))' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'pair evidence count ${actual_pair_evidence} below required minimum ${required_pair_evidence}' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'pair_margin_avg=+27.25 pair_margin_min=+21 wall_avg=1.66x wall_max=2.25x' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'F16-cli-quote-tax-rules: bare=50 solo_claude=75 pair=96 arm=l2_risk_probes margin=+21' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'FAIL audit-pair-evidence' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'assert audit["checks"]["min_pair_evidence"]["required"] == required' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'assert audit["checks"]["pair_evidence_quality"]["status"] == "PASS"' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'assert audit["checks"]["pair_trigger_reasons"]["summary_pair_evidence_count"] == 4' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'assert audit["checks"]["pair_trigger_reasons"]["rows_match_count"] is True' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'assert audit["checks"]["pair_trigger_reasons"]["canonical_rows"] == 4' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'assert audit["checks"]["pair_trigger_reasons"]["historical_alias_details"] == []' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'assert len(audit["pair_evidence_rows"]) == frontier["pair_evidence_count"]' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'benchmark frontier must fail when active unmeasured candidates remain' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'PASS pair-candidate-frontier' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'FAIL pair-candidate-frontier' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'assert report["rows"][0]["status"] == "candidate_unmeasured"' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'assert row["verdict"] == "pair_evidence_passed"' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'assert row["pair_mode"] is True' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'assert row["pair_trigger_eligible"] is True' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'assert isinstance(row["pair_solo_wall_ratio"], (int, float))' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'assert report["frontier_summary"]["pair_margin_avg"] == 27' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'assert report["pair_evidence_rows"] == [' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'assert report["checks"]["min_pair_evidence"]["actual_rows"] == 2' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'assert report["checks"]["min_pair_evidence"]["rows_match_count"] is True' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'assert report["checks"]["min_pair_evidence"]["status"] == "FAIL"' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'assert report["checks"]["pair_evidence_quality"]["status"] == "PASS"' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'assert report["checks"]["pair_trigger_reasons"]["status"] == "PASS"' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'assert report["checks"]["pair_trigger_reasons"]["summary_pair_evidence_count"] == 2' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'assert report["checks"]["pair_trigger_reasons"]["rows_match_count"] is True' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'assert report["checks"]["pair_trigger_reasons"]["historical_alias_details"] == [' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'normalized-canonical-trigger-reason-rows' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'assert report["checks"]["pair_evidence_quality"]["min_pair_margin_actual"] == 21' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'pair_evidence_quality=PASS min_pair_margin_actual=+21 min_pair_margin_required=+5 max_wall_actual=1.47x max_wall_allowed=3.00x' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'pair_evidence_quality=FAIL min_pair_margin_actual=+4 min_pair_margin_required=+5 max_wall_actual=1.20x max_wall_allowed=3.00x' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'no-quality-rows-frontier.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'pair evidence quality check has no complete rows' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'low-quality-frontier.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'pair evidence margin below minimum for fixture(s): F16-cli-quote-tax-rules' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'high-wall-frontier.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'pair evidence wall ratio above maximum for fixture(s): F16-cli-quote-tax-rules' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'summary-mismatch-frontier.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'frontier pair_margin_min does not match pair evidence rows' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'summary-wall-mismatch-frontier.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'frontier pair_solo_wall_ratio_max does not match pair evidence rows' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'frontier-fail-verdict.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'frontier-unmeasured.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'frontier-malformed-unmeasured.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'frontier-incomplete-best.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq '"run_id": "lower-complete"' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'bool-frontier-count.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'malformed-pair-evidence-count' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'mismatched-frontier-rows.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'pair evidence rows 1 do not match summary count 2' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'bad-frontier-row-fields.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'nan-frontier-row-fields.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'nan-max-wall-ratio' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'mismatched-margin-row-fields.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'mismatched-margin-row-fields' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'overrange-score-row-fields.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'overrange-score-row-fields' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'invalid-pair-arm-row-fields.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'invalid-pair-arm-row-fields' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'false-pair-mode-row-fields.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'false-pair-mode-row-fields' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'zero-wall-row-fields.json' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'zero-wall-row-fields' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'pair evidence count 2 below required minimum 4' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'assert rows["F22-cli-low-margin"]["status"] == "candidate_unmeasured"' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'assert rows["F22-cli-low-margin"]["status"] == "pair_evidence_passed"' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'assert rows["F23-cli-high-wall"]["status"] == "candidate_unmeasured"' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'assert rows["F23-cli-high-wall"]["status"] == "pair_evidence_passed"' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'def print_final_verdict' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'PASS pair-candidate-frontier' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'FAIL pair-candidate-frontier' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'PASS pair-candidate-frontier' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'FAIL pair-candidate-frontier' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'requires at least four fixtures with passing pair evidence' README.md \
  || ! grep -Fq 'revalidates frontier `verdict: PASS`, zero unmeasured candidates' README.md \
  || ! grep -Fq 'requires at least four active fixtures with passing pair evidence' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'revalidates frontier `verdict: PASS`' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'requires at least four active fixtures with passing pair evidence' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'revalidates frontier `verdict: PASS`, zero unmeasured candidates' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'counted by `benchmark audit` as the fourth passing pair-evidence row' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'counted by `benchmark audit` as the fourth passing pair-evidence row' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'counted by `benchmark audit` as the fourth passing pair-evidence row' benchmark/auto-resolve/BENCHMARK-RESULTS.md \
  || ! grep -Fq 'the default 5-point pair margin' README.md \
  || ! grep -Fq -- '`--pair-verify` and `--no-pair` are mutually exclusive' README.md \
  || ! grep -Fq 'default 5-point pair margin' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'the default 5-point pair margin' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq '3x pair/solo wall ratio' README.md \
  || ! grep -Fq '3x pair/solo wall ratio' benchmark/auto-resolve/README.md \
  || ! grep -Fq '3x pair/solo wall ratio' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'audit.json` with the frontier summary' README.md \
  || ! grep -Fq 'audit.json` with the frontier summary' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'audit.json` with the frontier summary' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'artifact map' README.md \
  || ! grep -Fq 'artifact map' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'artifact map' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq '`checks.frontier_stdout` records summary, aggregate, final-verdict, expected, printed score-row, trigger-visible row, and hypothesis-trigger-visible row counts' README.md \
  || ! grep -Fq '`headroom_rejections=...`, `pair_evidence_quality=...`,' README.md \
  || ! grep -Fq '`pair_trigger_reasons=...`, `pair_evidence_hypotheses=...`, and' README.md \
  || ! grep -Fq '`pair_evidence_hypothesis_triggers=...` handoff rows' README.md \
  || ! grep -Fq '`pair_trigger_historical_aliases=...` when archived evidence includes legacy' README.md \
  || ! grep -Fq '`pair_evidence_hypothesis_trigger_gaps=...` when documented' README.md \
  || ! grep -Fq 'canonical trigger reason coverage' README.md \
  || ! grep -Fq '`checks.pair_evidence_quality` records the same quality thresholds from the compact rows' README.md \
  || ! grep -Fq '`checks.pair_trigger_reasons` records canonical/historical-alias/exposed/total trigger-reason row counts, fixture-level historical alias details, summary count, and row-match status' README.md \
  || ! grep -Fq '`checks.pair_evidence_hypotheses` records documented/total pair-evidence hypothesis row counts' README.md \
  || ! grep -Fq '`checks.pair_evidence_hypothesis_triggers` records whether documented hypotheses also appear as `spec.solo_headroom_hypothesis` trigger reasons plus fixture-level gap details' README.md \
  || ! grep -Fq 'regenerated pair evidence' README.md \
  || ! grep -Fq 'Historical trigger aliases are only reported for archived artifact review' README.md \
  || ! grep -Fq 'current pair-evidence gates fail historical-only or unknown trigger reasons' README.md \
  || ! grep -Fq '`checks.frontier_stdout`' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'aggregate, final-verdict, expected, printed score-row, trigger-visible row, and hypothesis-trigger-visible row counts' benchmark/auto-resolve/README.md \
  || ! grep -Fq '`headroom_rejections=...`,' benchmark/auto-resolve/README.md \
  || ! grep -Fq '`pair_trigger_reasons=...`, and' benchmark/auto-resolve/README.md \
  || ! grep -Fq '`pair_evidence_hypotheses=...` and' benchmark/auto-resolve/README.md \
  || ! grep -Fq '`pair_evidence_hypothesis_triggers=...` handoff rows' benchmark/auto-resolve/README.md \
  || ! grep -Fq '`pair_trigger_historical_aliases=...` when archived evidence includes legacy' benchmark/auto-resolve/README.md \
  || ! grep -Fq '`pair_evidence_hypothesis_trigger_gaps=...` when documented' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'canonical trigger reason coverage' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'records the same quality thresholds from the compact rows,' benchmark/auto-resolve/README.md \
  || ! grep -Fq '`checks.pair_trigger_reasons` records canonical/historical-alias/exposed/total trigger-reason row counts, fixture-level historical alias details, summary count, and row-match status' benchmark/auto-resolve/README.md \
  || ! grep -Fq '`checks.pair_evidence_hypotheses` records documented/total pair-evidence hypothesis row counts' benchmark/auto-resolve/README.md \
  || ! grep -Fq '`checks.pair_evidence_hypothesis_triggers` records whether documented hypotheses also appear as `spec.solo_headroom_hypothesis` trigger reasons plus fixture-level gap details' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'regenerated pair evidence' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'Historical trigger aliases are only reported for archived artifact review' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'current pair-evidence gates fail historical-only or unknown trigger reasons' benchmark/auto-resolve/README.md \
  || ! grep -Fq '`checks.frontier_stdout` records summary, aggregate, final-verdict, expected, printed score-row, trigger-visible row, and hypothesis-trigger-visible row counts' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'also prints `headroom_rejections=...`, `pair_evidence_quality=...`,' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq '`pair_trigger_reasons=...`, `pair_evidence_hypotheses=...`, and `pair_evidence_hypothesis_triggers=...` handoff rows' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq '`pair_trigger_historical_aliases=...` when archived evidence includes legacy' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq '`pair_evidence_hypothesis_trigger_gaps=...` when documented' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'canonical trigger reason coverage' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq '`checks.pair_evidence_quality` records the same quality thresholds from the compact rows' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq '`checks.pair_trigger_reasons` records canonical/historical-alias/exposed/total trigger-reason row counts, fixture-level historical alias details, summary count, and row-match status' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq '`checks.pair_evidence_hypotheses` records documented/total pair-evidence hypothesis row counts' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq '`checks.pair_evidence_hypothesis_triggers` records whether documented hypotheses also appear as `spec.solo_headroom_hypothesis` trigger reasons plus fixture-level gap details' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'regenerated pair evidence' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'Historical trigger aliases are only reported for archived artifact review' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'current pair-evidence gates fail historical-only or unknown trigger reasons' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'compact trigger-backed verdict-bearing `pair_evidence_rows`' README.md \
  || ! grep -Fq 'pair_trigger_eligible: true' README.md \
  || ! grep -Fq 'non-empty `pair_trigger_reasons`, `pair_trigger_has_canonical_reason: true`, and `pair_trigger_has_hypothesis_reason`; the audit fails rows missing trigger reasons' README.md \
  || ! grep -Fq 'pair_trigger_has_canonical_reason: true' README.md \
  || ! grep -Fq '`pair_evidence_rows`' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'compact trigger-backed verdict-bearing score rows' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'pair_trigger_eligible: true' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'non-empty `pair_trigger_reasons`, `pair_trigger_has_canonical_reason: true`, and `pair_trigger_has_hypothesis_reason`; the audit fails rows missing trigger reasons' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'pair_trigger_has_canonical_reason: true' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'compact trigger-backed verdict-bearing `pair_evidence_rows`' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'pair_trigger_eligible: true' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'non-empty `pair_trigger_reasons`, `pair_trigger_has_canonical_reason: true`, and `pair_trigger_has_hypothesis_reason`; the audit fails rows missing trigger reasons' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'pair_trigger_has_canonical_reason: true' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'revalidates `pair_mode: true`' README.md \
  || ! grep -Fq 'satisfy `pair_mode: true`' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'revalidates `pair_mode: true`' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'JSON rows expose `pair_trigger_reasons` and' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'Markdown output includes a `Triggers`' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'trigger reasons, canonical-trigger coverage, classification counts' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'Its Markdown table includes a `Triggers` column' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'compact evidence row count must match the' README.md \
  || ! grep -Fq 'compact evidence row count must match the' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'evidence row count must match the frontier evidence count' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq '"verdict": "PASS" if unmeasured_candidate_total == 0 else "FAIL"' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'assert frontier["unmeasured_count"] == 0' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'pair_margin_avg' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'from pair_evidence_contract import' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'from pair_evidence_contract import' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'from pair_evidence_contract import' benchmark/auto-resolve/scripts/audit-headroom-rejections.py \
  || ! grep -Fq 'def normalize_pair_evidence_row' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def best_pair_evidence' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'ALLOWED_PAIR_ARMS = {"l2_risk_probes", "l2_gated"}' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'pair_arm not in ALLOWED_PAIR_ARMS' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'pair_mode = row.get("pair_mode")' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'if pair_mode is not True:' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'pair_trigger_eligible = row.get("pair_trigger_eligible")' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'if pair_trigger_eligible is not True:' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq '"pair_trigger_eligible": pair_trigger_eligible' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq '"pair_mode": pair_mode' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def is_strict_int' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def is_score' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq '0 <= value <= 100' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'def is_strict_number' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'import math' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'math.isfinite(value)' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'and value > 0' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'if pair_margin != pair_score - solo_score:' benchmark/auto-resolve/scripts/pair_evidence_contract.py \
  || ! grep -Fq 'not math.isfinite(args.max_pair_solo_wall_ratio)' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'nan-wall-run' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'inflated-margin-run' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'overrange-score-run' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'invalid-arm-run' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'false-pair-mode-run' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'zero-wall-run' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'nan-max-wall-ratio' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'pair_margin_avg=+21.00 pair_margin_min=+21 wall_avg=1.28x wall_max=1.28x' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'incomplete-high-run' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'bad-pair-evidence-json' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'pair evidence artifact malformed' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'bad-pair-evidence-rows' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'pair evidence artifact rows malformed' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'assert len(rows["F16-cli-quote-tax-rules"]["passing_pair_evidence"]) == 1' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'plus row-level verdicts' README.md \
  || ! grep -Fq 'including pair arm, trigger reasons, average/minimum pair margin' README.md \
  || ! grep -Fq 'Markdown frontier artifacts include a `Triggers` column' README.md \
  || ! grep -Fq 'pair arm, margin, wall ratio, run id, verdict, and trigger reasons' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'with pair arm, verdict, and trigger reasons from the frontier step' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'pair-candidate-frontier.py --fail-on-unmeasured' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'audit-headroom-rejections.py' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'audit-headroom-rejections.py' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'unrecorded headroom rejection(s)' benchmark/auto-resolve/scripts/audit-headroom-rejections.py \
  || ! grep -Fq 'unsupported registry rejection(s)' benchmark/auto-resolve/scripts/audit-headroom-rejections.py \
  || ! grep -Fq 'solo_claude={solo_score}' benchmark/auto-resolve/scripts/audit-headroom-rejections.py \
  || ! grep -Fq 'expected_solo_claude={expected_solo_score}' benchmark/auto-resolve/scripts/audit-headroom-rejections.py \
  || ! grep -Fq 'unsupported_registry_rejections' benchmark/auto-resolve/scripts/test-audit-headroom-rejections.sh \
  || ! grep -Fq 'expected_solo_claude=98' benchmark/auto-resolve/scripts/test-audit-headroom-rejections.sh \
  || ! grep -Fq 'active registry entries whose reason cites a run id or' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'active rejected-registry reason is backed' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'invalid headroom rejections' bin/devlyn.js \
  || ! grep -Fq 'MALFORMED_JSON' benchmark/auto-resolve/scripts/audit-headroom-rejections.py \
  || ! grep -Fq 'MALFORMED_ROWS' benchmark/auto-resolve/scripts/audit-headroom-rejections.py \
  || ! grep -Fq 'F33-cli-new-candidate' benchmark/auto-resolve/scripts/test-audit-headroom-rejections.sh \
  || ! grep -Fq 'bad-json-headroom <unknown>' benchmark/auto-resolve/scripts/test-audit-headroom-rejections.sh \
  || ! grep -Fq 'malformed-headroom <unknown>' benchmark/auto-resolve/scripts/test-audit-headroom-rejections.sh \
  || ! grep -Fq 'candidate_unmeasured' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'pair_evidence_passed' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'print_summary(report)' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'fail_on_unmeasured' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'unmeasured candidate fixture(s)' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'pure JSON stdout must not include final text verdict' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'benchmark frontier pure JSON stdout must not include final text verdict' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq -- '--fail-on-unmeasured' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq -- '--fail-on-unmeasured' bin/devlyn.js \
  || ! grep -Fq -- '--fail-on-unmeasured' benchmark/auto-resolve/README.md \
  || ! grep -Fq -- '--fail-on-unmeasured' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'bare={bare} solo_claude={solo} pair={pair} arm={arm} margin={margin}' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'verdict=pair_evidence_passed' benchmark/auto-resolve/scripts/pair-candidate-frontier.py \
  || ! grep -Fq 'F16-cli-quote-tax-rules: bare=50 solo_claude=75 pair=96 arm=l2_risk_probes margin=+21' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'verdict=pair_evidence_passed' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq '[audit] frontier' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'fixtures=21 rejected=17 candidates=4 pair_evidence=4 unmeasured=0 verdict=PASS' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'F16-cli-quote-tax-rules: bare=50 solo_claude=75 pair=96 arm=l2_risk_probes margin=+21' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'frontier.stdout' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'headroom-rejections.stdout' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"frontier_stdout": "frontier.stdout"' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"headroom_rejections_stdout": "headroom-rejections.stdout"' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def load_headroom_audit_summary' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def check_headroom_audit_report' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def print_headroom_rejections_summary' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'headroom_rejections={status} verdict={verdict}' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'headroom_report_status == 0' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"report_check_exit_code": headroom_report_status' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'headroom audit unsupported registry rejection count missing or malformed' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'headroom_rejections=PASS verdict=PASS unrecorded=0 unsupported=0' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'headroom_rejections=PASS verdict=PASS unrecorded=0 unsupported=0' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'pair trigger reason rows {len(rows)} do not match summary count {count}' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'pair trigger reasons missing for fixture(s)' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'missing-trigger-reasons' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'malformed-trigger-reason-rows' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'mixed-unknown-trigger-reason-rows' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'pair_trigger_reasons=PASS canonical=2 historical_alias=1 exposed=2 total=2 summary=2 rows_match=true' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'pair_trigger_historical_aliases=F21-cli-scheduler-priority=risk_profile.high_risk' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq '"unsupported_registry_rejection_count": (' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'len(unsupported) if isinstance(unsupported, list) else None' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'headroom-missing-unsupported' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'unsupported_registry_rejection_count' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'unsupported_registry_rejection_count' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq '`checks.headroom_rejections` records child verdict plus unrecorded/unsupported counts' README.md \
  || ! grep -Fq '`checks.headroom_rejections` records the child verdict plus unrecorded and' benchmark/auto-resolve/README.md \
  || ! grep -Fq '`checks.headroom_rejections` records child verdict plus unrecorded/unsupported counts' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'def check_frontier_stdout' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq '"final_verdict_rows": final_verdict_rows' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'frontier stdout final verdict row count is not exactly 1' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'frontier stdout missing score row' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'wall={wall} run={run_id}' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'frontier stdout aggregate score row count is not exactly 1' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'frontier stdout summary score row count is not exactly 1' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'frontier stdout aggregate fields malformed' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'frontier stdout score row count' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'summary_count = stdout.splitlines().count(required_summary)' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'aggregate_count = stdout.splitlines().count(required_aggregate)' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'frontier stdout summary counts malformed' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'count_keys = {' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'pair_margin_avg={avg} pair_margin_min={min_margin}' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def format_decimal_margin' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'def format_wall_ratio' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'frontier stdout check missing summary fields' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'missing-frontier-score-row' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'missing-frontier-aggregate-row' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'duplicate-frontier-summary-row' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'duplicate-frontier-aggregate-row' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'pair_margin_avg=+27.00 pair_margin_min=+21 wall_avg=1.38x wall_max=1.47x' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'partial-frontier-score-row' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'extra-frontier-score-row' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'malformed-frontier-stdout-summary' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'malformed-frontier-stdout-counts' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'malformed-frontier-stdout-aggregate' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'audit["checks"]["frontier_stdout"]["status"] == "PASS"' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'audit["checks"]["frontier_stdout"]["summary_rows"] == 1' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'report["checks"]["frontier_stdout"]["aggregate_rows"] == 1' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'audit["checks"]["frontier_stdout"]["final_verdict_rows"] == 1' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'missing-final-frontier-verdict' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'duplicate-final-frontier-verdict' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'audit["checks"]["frontier_stdout"]["expected_rows"] == len(audit["pair_evidence_rows"])' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'audit["checks"]["frontier_stdout"]["trigger_rows"] == len(audit["pair_evidence_rows"])' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'audit["checks"]["frontier_stdout"]["hypothesis_trigger_rows"] == len(audit["pair_evidence_rows"])' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'audit["checks"]["frontier_stdout"]["trigger_rows_match_count"] is True' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'audit["checks"]["frontier_stdout"]["hypothesis_trigger_rows_match_count"] is True' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'report["checks"]["frontier_stdout"]["trigger_rows"] == 2' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'report["checks"]["frontier_stdout"]["hypothesis_trigger_rows"] == 2' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'report["checks"]["frontier_stdout"]["trigger_rows_match_count"] is True' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'report["checks"]["frontier_stdout"]["hypothesis_trigger_rows_match_count"] is True' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'report["checks"]["frontier_stdout"]["rows_match_count"] is True' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'audit["artifacts"]["frontier_stdout"] == "frontier.stdout"' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'report["artifacts"] == {' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'frontier.stdout' benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh \
  || ! grep -Fq 'frontier.stdout' benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh \
  || ! grep -Fq 'frontier summary and an artifact map (`artifacts`)' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'artifact map' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'child stdout/stderr logs' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq '| Fixture | Status | Verdict | Evidence | Pair arm | Triggers | Hypothesis trigger | Bare | Solo_claude | Pair | Margin | Wall ratio | Rejected reason |' benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh \
  || ! grep -Fq 'benchmark frontier` also prints a stdout score summary for existing complete pair' README.md \
  || ! grep -Fq 'plus row-level verdicts' README.md \
  || ! grep -Fq 'including pair arm, trigger reasons, average/minimum pair margin' README.md \
  || ! grep -Fq 'Markdown frontier artifacts include a `Triggers` column' README.md \
  || ! grep -Fq 'Full-pipeline pair gate artifacts record `require_hypothesis_trigger` in JSON' README.md \
  || ! grep -Fq 'Full-pipeline pair gate artifacts record `require_hypothesis_trigger` in JSON' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'Full-pipeline pair gate artifacts record `require_hypothesis_trigger` in JSON' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'includes a Markdown `Hypothesis trigger` column' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'includes a Markdown `Hypothesis trigger` column' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'pair arm, margin, wall ratio, run id, verdict, and trigger reasons' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'overall verdict plus row-level verdict, pair-arm, and trigger-reason columns' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'with pair arm, verdict, and trigger reasons from the frontier step' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'overall verdict plus row-level verdict, pair-arm, and trigger-reason columns' benchmark/auto-resolve/run-real-benchmark.md \
  || ! grep -Fq 'complete pair evidence rows' benchmark/auto-resolve/README.md \
  || ! grep -Fq 'complete pair evidence rows' benchmark/auto-resolve/run-real-benchmark.md; then
  offenders="${offenders}"$'\n'"benchmark docs and CLI must expose the pair-candidate frontier report before new provider spend"
fi
if ! grep -Fq '"benchmark/auto-resolve/scripts/**"' package.json \
  || ! grep -Fq 'benchmark/auto-resolve/results/20260511-f21-current-riskprobes-v1/full-pipeline-pair-gate.json' package.json \
  || ! grep -Fq 'benchmark/auto-resolve/results/20260512-f2-medium-headroom/headroom-gate.json' package.json \
  || ! grep -Fq 'benchmark/auto-resolve/results/20260512-f31-seat-rebalance-headroom/headroom-gate.json' package.json \
  || ! grep -Fq 'benchmark/auto-resolve/results/20260512-f32-subscription-renewal-headroom/headroom-gate.json' package.json; then
  offenders="${offenders}"$'\n'"package.json must include benchmark scripts, runner regression tests, current pair evidence, and rejected-headroom evidence in npm packages"
fi
if ! grep -Fq '"max_observed_pair_solo_wall_ratio": 2.2506234413965087' benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.json \
  || ! grep -Fq '"max_observed_pair_solo_wall_ratio": 1.4728476821192054' benchmark/auto-resolve/results/20260511-f21-current-riskprobes-v1/full-pipeline-pair-gate.json \
  || ! grep -Fq 'pair_trigger eligible with a canonical reason' benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.json \
  || ! grep -Fq 'pair_trigger eligible with a canonical reason' benchmark/auto-resolve/results/20260511-f21-current-riskprobes-v1/full-pipeline-pair-gate.json \
  || ! grep -Fq 'pair_trigger eligible with canonical reason' benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.md \
  || ! grep -Fq 'pair_trigger eligible with canonical reason' benchmark/auto-resolve/results/20260511-f21-current-riskprobes-v1/full-pipeline-pair-gate.md \
  || ! grep -Fq 'Allowed pair/solo wall ratio: 3.00x' benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.md \
  || ! grep -Fq 'Maximum observed pair/solo wall ratio: 2.25x' benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.md \
  || ! grep -Fq 'Allowed pair/solo wall ratio: 3.00x' benchmark/auto-resolve/results/20260511-f21-current-riskprobes-v1/full-pipeline-pair-gate.md \
  || ! grep -Fq 'Maximum observed pair/solo wall ratio: 1.47x' benchmark/auto-resolve/results/20260511-f21-current-riskprobes-v1/full-pipeline-pair-gate.md; then
  offenders="${offenders}"$'\n'"packaged pair evidence artifacts must use the current observed-vs-allowed wall-ratio schema and canonical trigger rule wording"
fi
if make_temp_dir package_results /tmp/devlyn-lint-package-results.XXXXXX \
  && make_temp_dir package_audit /tmp/devlyn-lint-package-audit.XXXXXX \
  && make_temp_file package_audit_stdout /tmp/devlyn-lint-package-audit.XXXXXX.out; then
  cp -R benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof "$package_results/"
  cp -R benchmark/auto-resolve/results/20260511-f21-current-riskprobes-v1 "$package_results/"
  for rejected_run in \
    20260507-f10-f11-tier1-full-pipeline \
    20260508-f22-exact-error-headroom \
    20260508-f26-headroom \
    20260511-f3-http-error-headroom \
    20260511-f12-webhook-headroom \
    20260511-f15-concurrency-headroom \
    20260512-f2-medium-headroom \
    20260512-f4-web-headroom \
    20260512-f5-fixloop-headroom \
    20260512-f6-checksum-headroom \
    20260512-f7-scope-headroom \
    20260512-f9-e2e-headroom \
    20260512-f31-seat-rebalance-headroom \
    20260512-f32-subscription-renewal-headroom; do
    cp -R "benchmark/auto-resolve/results/$rejected_run" "$package_results/"
  done
  if ! python3 benchmark/auto-resolve/scripts/audit-pair-evidence.py \
      --results-root "$package_results" \
      --out-dir "$package_audit" >"$package_audit_stdout" 2>&1; then
    offenders="${offenders}"$'\n'"packaged pair evidence subset must pass benchmark audit without relying on unshipped local results"
  elif ! grep -Fq 'headroom_rejections=PASS verdict=PASS unrecorded=0 unsupported=0' "$package_audit_stdout" \
    || ! grep -Fq 'pair_evidence_quality=PASS min_pair_margin_actual=+21 min_pair_margin_required=+5 max_wall_actual=2.25x max_wall_allowed=3.00x' "$package_audit_stdout" \
    || ! grep -Fq 'pair_trigger_reasons=PASS canonical=4 historical_alias=0 exposed=4 total=4 summary=4 rows_match=true' "$package_audit_stdout" \
    || ! grep -Fq 'pair_evidence_hypothesis_triggers=PASS matched=4 documented=4 total=4' "$package_audit_stdout" \
    || grep -Fq 'pair_trigger_historical_aliases=' "$package_audit_stdout" \
    || grep -Fq 'pair_evidence_hypothesis_trigger_gaps=' "$package_audit_stdout"; then
    offenders="${offenders}"$'\n'"packaged pair evidence subset audit stdout must expose headroom, pair-quality, and trigger-reason handoff rows"
  elif ! python3 - "$package_audit/audit.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf8"))
rows = report.get("pair_evidence_rows")
frontier_summary = report.get("frontier_summary", {})
frontier_report = report.get("checks", {}).get("frontier_report", {})
frontier_stdout = report.get("checks", {}).get("frontier_stdout", {})
min_pair_evidence = report.get("checks", {}).get("min_pair_evidence", {})
pair_evidence_quality = report.get("checks", {}).get("pair_evidence_quality", {})
pair_trigger_reasons = report.get("checks", {}).get("pair_trigger_reasons", {})
headroom_rejections = report.get("checks", {}).get("headroom_rejections", {})
artifacts = report.get("artifacts", {})
assert report.get("verdict") == "PASS"
assert frontier_summary.get("verdict") == "PASS"
assert frontier_summary.get("pair_evidence_count") == 4
assert frontier_summary.get("unmeasured_count") == 0
assert frontier_report.get("status") == "PASS"
assert frontier_report.get("verdict") == "PASS"
assert frontier_report.get("unmeasured_count") == 0
assert frontier_stdout.get("status") == "PASS"
assert frontier_stdout.get("report", "").endswith("frontier.stdout")
assert frontier_stdout.get("summary_rows") == 1
assert frontier_stdout.get("aggregate_rows") == 1
assert frontier_stdout.get("final_verdict_rows") == 1
assert frontier_stdout.get("expected_rows") == len(rows) == 4
assert frontier_stdout.get("stdout_rows") == len(rows) == 4
assert frontier_stdout.get("trigger_rows") == len(rows) == 4
assert frontier_stdout.get("hypothesis_trigger_rows") == len(rows) == 4
assert frontier_stdout.get("rows_match_count") is True
assert frontier_stdout.get("trigger_rows_match_count") is True
assert frontier_stdout.get("hypothesis_trigger_rows_match_count") is True
assert headroom_rejections.get("status") == "PASS"
assert headroom_rejections.get("report_check_exit_code") == 0
assert headroom_rejections.get("verdict") == "PASS"
assert headroom_rejections.get("unrecorded_failure_count") == 0
assert headroom_rejections.get("unsupported_registry_rejection_count") == 0
assert min_pair_evidence.get("rows_match_count") is True
assert min_pair_evidence.get("actual_rows") == len(rows) == 4
assert pair_evidence_quality.get("status") == "PASS"
assert pair_evidence_quality.get("min_pair_margin_actual") == frontier_summary.get("pair_margin_min")
assert pair_evidence_quality.get("max_pair_solo_wall_ratio_actual") == frontier_summary.get("pair_solo_wall_ratio_max")
assert pair_trigger_reasons.get("status") == "PASS"
assert pair_trigger_reasons.get("summary_pair_evidence_count") == 4
assert pair_trigger_reasons.get("canonical_rows") == 4
assert pair_trigger_reasons.get("historical_alias_rows") == 0
assert pair_trigger_reasons.get("historical_alias_details") == []
assert pair_trigger_reasons.get("exposed_rows") == 4
assert pair_trigger_reasons.get("total_rows") == 4
assert pair_trigger_reasons.get("rows_match_count") is True
pair_hypothesis_triggers = report.get("checks", {}).get("pair_evidence_hypothesis_triggers", {})
assert pair_hypothesis_triggers.get("status") == "PASS"
assert pair_hypothesis_triggers.get("matched_rows") == 4
assert pair_hypothesis_triggers.get("documented_rows") == 4
assert pair_hypothesis_triggers.get("gap_details") == []
assert artifacts.get("frontier_json") == "frontier.json"
assert artifacts.get("frontier_stdout") == "frontier.stdout"
assert artifacts.get("headroom_audit_json") == "headroom-audit.json"
assert artifacts.get("headroom_rejections_stdout") == "headroom-rejections.stdout"
for row in rows:
    assert row.get("verdict") == "pair_evidence_passed"
    assert row.get("pair_arm") == "l2_risk_probes"
    assert row.get("pair_mode") is True
    assert row.get("pair_trigger_eligible") is True
    assert isinstance(row.get("pair_trigger_reasons"), list)
    assert row.get("pair_trigger_reasons")
    assert row.get("pair_trigger_has_canonical_reason") is True
    assert row.get("pair_trigger_has_hypothesis_reason") is True
PY
  then
    offenders="${offenders}"$'\n'"packaged pair evidence subset audit.json must expose frontier_report, frontier_stdout, artifact map, and 4 trigger-backed verdict-bearing pair rows with trigger reasons"
  fi
  rm -rf "$package_results" "$package_audit" "$package_audit_stdout"
else
  offenders="${offenders}"$'\n'"packaged pair evidence subset could not allocate temporary audit workspace"
fi
if make_temp_file pack_json /tmp/devlyn-lint-pack.XXXXXX.json \
  && npm pack --dry-run --json > "$pack_json" 2>/dev/null; then
  if ! node - "$pack_json" <<'NODE'
const fs = require("fs");
const path = require("path");
const packPath = process.argv[2];
const pack = JSON.parse(fs.readFileSync(packPath, "utf8"))[0];
const files = new Set(pack.files.map((file) => file.path));
function listFiles(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return listFiles(full);
    if (!entry.isFile()) return [];
    return [full.split(path.sep).join("/")];
  });
}
const shadowRequired = fs
  .readdirSync("benchmark/auto-resolve/shadow-fixtures", { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && /^S/.test(entry.name))
  .flatMap((entry) => listFiles(path.join("benchmark/auto-resolve/shadow-fixtures", entry.name)));
const required = [
  "benchmark/auto-resolve/BENCHMARK-RESULTS.md",
  "benchmark/auto-resolve/run-real-benchmark.md",
  "benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/headroom-gate.md",
  "benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/headroom-gate.json",
  "benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.md",
  "benchmark/auto-resolve/results/20260510-f16-f23-f25-combined-proof/full-pipeline-pair-gate.json",
  "benchmark/auto-resolve/results/20260511-f21-current-riskprobes-v1/headroom-gate.md",
  "benchmark/auto-resolve/results/20260511-f21-current-riskprobes-v1/headroom-gate.json",
  "benchmark/auto-resolve/results/20260511-f21-current-riskprobes-v1/full-pipeline-pair-gate.md",
  "benchmark/auto-resolve/results/20260511-f21-current-riskprobes-v1/full-pipeline-pair-gate.json",
  "benchmark/auto-resolve/results/20260512-f2-medium-headroom/headroom-gate.json",
  "benchmark/auto-resolve/results/20260512-f31-seat-rebalance-headroom/headroom-gate.json",
  "benchmark/auto-resolve/results/20260512-f32-subscription-renewal-headroom/headroom-gate.json",
  "benchmark/auto-resolve/fixtures/F31-cli-seat-rebalance/NOTES.md",
	  "benchmark/auto-resolve/fixtures/F31-cli-seat-rebalance/spec.md",
	  "benchmark/auto-resolve/fixtures/F31-cli-seat-rebalance/expected.json",
	  "benchmark/auto-resolve/fixtures/F31-cli-seat-rebalance/metadata.json",
	  "benchmark/auto-resolve/fixtures/F31-cli-seat-rebalance/verifiers/priority-transfer-rollback.js",
	  "benchmark/auto-resolve/fixtures/F31-cli-seat-rebalance/verifiers/duplicate-event-error.js",
	  "benchmark/auto-resolve/fixtures/F32-cli-subscription-renewal/NOTES.md",
	  "benchmark/auto-resolve/fixtures/F32-cli-subscription-renewal/spec.md",
	  "benchmark/auto-resolve/fixtures/F32-cli-subscription-renewal/expected.json",
	  "benchmark/auto-resolve/fixtures/F32-cli-subscription-renewal/metadata.json",
	  "benchmark/auto-resolve/fixtures/F32-cli-subscription-renewal/verifiers/priority-credit-rollback.js",
	  "benchmark/auto-resolve/fixtures/F32-cli-subscription-renewal/verifiers/duplicate-renewal-error.js",
	  "benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh",
  "benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh",
  "benchmark/auto-resolve/scripts/pair_evidence_contract.py",
  "benchmark/auto-resolve/scripts/pair-candidate-frontier.py",
  "benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh",
  "benchmark/auto-resolve/scripts/audit-pair-evidence.py",
  "benchmark/auto-resolve/scripts/solo-headroom-hypothesis.py",
  "benchmark/auto-resolve/scripts/solo-ceiling-avoidance.py",
  "benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh",
  "benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh",
  "benchmark/auto-resolve/scripts/test-check-f9-artifacts.sh",
  "benchmark/auto-resolve/scripts/test-lint-fixtures.sh",
  "benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh",
	  "benchmark/auto-resolve/scripts/test-run-headroom-candidate.sh",
  "benchmark/auto-resolve/scripts/test-run-swebench-solver-batch.sh",
	  "benchmark/auto-resolve/scripts/test-ship-gate.sh",
	  "benchmark/auto-resolve/scripts/test-iter-0033c-l1-summary.sh",
  "benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh",
  "benchmark/auto-resolve/fixtures/retired/F27-cli-subscription-proration/RETIRED.md",
  "benchmark/auto-resolve/fixtures/retired/F27-cli-subscription-proration/spec.md",
  "benchmark/auto-resolve/fixtures/retired/F28-cli-return-authorization/RETIRED.md",
  "benchmark/auto-resolve/fixtures/retired/F28-cli-return-authorization/spec.md",
  "benchmark/auto-resolve/fixtures/retired/F30-cli-credit-hold-settlement/RETIRED.md",
  "benchmark/auto-resolve/fixtures/retired/F30-cli-credit-hold-settlement/spec.md",
  "benchmark/auto-resolve/fixtures/retired/F9-e2e-ideate-to-preflight/RETIRED.md",
  "scripts/lint-fixtures.sh",
  "scripts/lint-shadow-fixtures.sh",
  ...shadowRequired,
];
const missing = required.filter((file) => !files.has(file));
if (missing.length > 0) {
  console.error(missing.join("\n"));
  process.exit(1);
}
const forbidden = pack.files
  .map((file) => file.path)
  .filter((file) => file.includes("__pycache__") || file.endsWith(".pyc"));
if (forbidden.length > 0) {
  console.error(forbidden.join("\n"));
  process.exit(2);
}
NODE
  then
    offenders="${offenders}"$'\n'"npm pack dry-run must include benchmark runner/gate regression tests, all shadow fixture files, retired fixture replay docs, and exclude pycache artifacts"
  fi
else
  offenders="${offenders}"$'\n'"npm pack dry-run failed while checking benchmark runner/gate regression tests"
fi
[ -n "${pack_json:-}" ] && rm -f "$pack_json"
non_executable_shell_scripts=$(find benchmark/auto-resolve/scripts -maxdepth 1 -name '*.sh' -type f ! -perm -111 -print | sort)
if [ -n "$non_executable_shell_scripts" ]; then
  while IFS= read -r f; do
    offenders="${offenders}"$'\n'"benchmark shell script must be executable: $f"
  done <<< "$non_executable_shell_scripts"
fi
for gate_test in \
  test-benchmark-arg-parsing.sh \
  test-pair-candidate-frontier.sh \
  test-audit-pair-evidence.sh \
  test-audit-headroom-rejections.sh \
  test-build-pair-eligible-manifest.sh \
  test-ship-gate.sh \
  test-headroom-gate.sh \
  test-run-headroom-candidate.sh \
  test-check-f9-artifacts.sh \
  test-lint-fixtures.sh \
	  test-run-full-pipeline-pair-candidate.sh \
	  test-full-pipeline-pair-gate.sh \
	  test-iter-0033c-l1-summary.sh \
	  test-iter-0033c-compare.sh \
  test-run-swebench-solver-batch.sh \
  test-swebench-frozen-case.sh \
  test-frozen-verify-gate.sh
do
  if ! grep -Fq "$gate_test" benchmark/auto-resolve/README.md; then
    offenders="${offenders}"$'\n'"benchmark/auto-resolve/README.md: gate-change instructions must list $gate_test"
  fi
done
if ! bash benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-benchmark-arg-parsing.sh: failed"
fi
if ! bash benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-pair-candidate-frontier.sh: failed"
fi
if ! bash benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-audit-pair-evidence.sh: failed"
fi
if ! bash benchmark/auto-resolve/scripts/test-audit-headroom-rejections.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-audit-headroom-rejections.sh: failed"
fi
if ! bash benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-build-pair-eligible-manifest.sh: failed"
fi
if ! bash benchmark/auto-resolve/scripts/test-headroom-gate.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-headroom-gate.sh: failed"
fi
if ! bash benchmark/auto-resolve/scripts/test-run-headroom-candidate.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-run-headroom-candidate.sh: failed"
fi
if ! bash benchmark/auto-resolve/scripts/test-check-f9-artifacts.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-check-f9-artifacts.sh: failed"
fi
if ! bash benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-run-full-pipeline-pair-candidate.sh: failed"
fi
if ! bash benchmark/auto-resolve/scripts/test-ship-gate.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-ship-gate.sh: failed"
fi
if ! bash benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-full-pipeline-pair-gate.sh: failed"
fi
if ! bash benchmark/auto-resolve/scripts/test-iter-0033c-l1-summary.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-iter-0033c-l1-summary.sh: failed"
fi
if ! bash benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-iter-0033c-compare.sh: failed"
fi
if ! bash benchmark/auto-resolve/scripts/test-run-swebench-solver-batch.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-run-swebench-solver-batch.sh: failed"
fi
if ! bash benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-swebench-frozen-case.sh: failed"
fi
if ! bash benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-frozen-verify-gate.sh: failed"
fi
if ! bash scripts/lint-fixtures.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"scripts/lint-fixtures.sh: failed"
fi
if ! bash scripts/lint-shadow-fixtures.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"scripts/lint-shadow-fixtures.sh: failed"
fi
if ! bash benchmark/auto-resolve/scripts/test-lint-fixtures.sh >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/test-lint-fixtures.sh: failed"
fi
if ! python3 -m py_compile benchmark/auto-resolve/scripts/solo-headroom-hypothesis.py >/dev/null 2>&1; then
  offenders="${offenders}"$'\n'"benchmark/auto-resolve/scripts/solo-headroom-hypothesis.py: py_compile failed"
fi
if ! grep -Fq 'high-risk fixture must include a resolve risk-trigger term' scripts/lint-fixtures.sh \
  || ! grep -Fq 'SOLO_HEADROOM_CHECK="$REPO_ROOT/benchmark/auto-resolve/scripts/solo-headroom-hypothesis.py"' scripts/lint-fixtures.sh \
  || ! grep -Fq 'pair_evidence_passed fixture spec.md must document an actionable solo-headroom hypothesis with solo_claude miss and observable command from expected.json' scripts/lint-fixtures.sh \
  || ! grep -Fq -- '--expected-json "$d/expected.json" "$d/spec.md"' scripts/lint-fixtures.sh \
  || ! grep -Fq 'str(fixture_dir / "expected.json")' benchmark/auto-resolve/scripts/audit-pair-evidence.py \
  || ! grep -Fq 'hypothesis command must match expected.json verification command' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
  || ! grep -Fq 'pair-evidence-hypothesis-fail.out' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
  || ! grep -Fq 'pair-evidence-hypothesis-pass.out' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
  || ! grep -Fq 'DEVLYN_FIXTURES_DIR' scripts/lint-fixtures.sh \
  || ! grep -Fq 'DEVLYN_FIXTURE_GLOB' scripts/lint-fixtures.sh \
  || ! grep -Fq 'DEVLYN_FIXTURE_GLOB="S*"' scripts/lint-shadow-fixtures.sh \
  || ! grep -Fq 'benchmark/auto-resolve/shadow-fixtures' scripts/lint-shadow-fixtures.sh \
  || ! grep -Fq 'category") != "high-risk"' scripts/lint-fixtures.sh \
  || ! grep -Fq 'permissions?' scripts/lint-fixtures.sh \
  || ! grep -Fq 'idempoten\w*' scripts/lint-fixtures.sh \
  || ! grep -Fq 'output-shape' scripts/lint-fixtures.sh \
  || ! grep -Fq 'high-risk trigger validation' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
  || ! grep -Fq 'DEVLYN_FIXTURES_DIR="$FIXTURES_DIR" bash "$ROOT/scripts/lint-fixtures.sh"' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
  || ! grep -Fq 'DEVLYN_LINT_FIXTURES_NO_JSONSCHEMA=1' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'spec-verify-check --check-expected failed' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'unless sibling spec.md declares all Requirements are pure-design' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'verification_commands must be an array' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'expected.json must be an object' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'hidden oracle missing contract_refs' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'contract_ref not found in spec.md' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'BENCH_FIXTURE_DIR file not found' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'BENCH_FIXTURE_DIR file escapes fixture dir' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'hidden oracle must reference an explicit $BENCH_FIXTURE_DIR/... file' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'hidden oracle must assert stdout_contains includes' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'cd \"$BENCH_FIXTURE_DIR\" && node verifiers/hidden-oracle.js' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'missing-hidden-oracle.js' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq '../outside-hidden-oracle.js' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'This visible contract is not in the spec.' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'spec-verify-check --check failed' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'frontmatter complexity must be one of' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'resolve spec contract enum' benchmark/auto-resolve/fixtures/SCHEMA.md \
	  || ! grep -Fq 'metadata.difficulty' benchmark/auto-resolve/fixtures/SCHEMA.md \
	  || ! grep -Fq "grep -Fq 'Traceback'" benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'hidden oracle missing contract_refs' scripts/lint-fixtures.sh \
	  || ! grep -Fq 'contract_ref not found in spec.md' scripts/lint-fixtures.sh \
	  || ! grep -Fq 'BENCH_FIXTURE_DIR file not found' scripts/lint-fixtures.sh \
	  || ! grep -Fq 'BENCH_FIXTURE_DIR file escapes fixture dir' scripts/lint-fixtures.sh \
	  || ! grep -Fq 'hidden oracle must reference an explicit $BENCH_FIXTURE_DIR/... file' scripts/lint-fixtures.sh \
	  || ! grep -Fq 'hidden oracle must assert stdout_contains includes' scripts/lint-fixtures.sh \
	  || ! grep -Fq 'SPEC_VERIFY_CHECK="$REPO_ROOT/config/skills/_shared/spec-verify-check.py"' scripts/lint-fixtures.sh \
	  || ! grep -Fq 'python3 "$SPEC_VERIFY_CHECK" --check "$d/spec.md"' scripts/lint-fixtures.sh \
	  || ! grep -Fq 'spec-verify-check --check failed' scripts/lint-fixtures.sh \
	  || ! grep -Fq 'python3 "$SPEC_VERIFY_CHECK" --check-expected "$d/expected.json"' scripts/lint-fixtures.sh \
	  || ! grep -Fq 'spec-verify-check --check-expected failed' scripts/lint-fixtures.sh \
	  || ! grep -Fq 'REJECTED_REGISTRY="${DEVLYN_REJECTED_FIXTURE_REGISTRY:-$REPO_ROOT/benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh}"' scripts/lint-fixtures.sh \
	  || ! grep -Fq 'declare -F rejected_pair_fixture_reason' scripts/lint-fixtures.sh \
	  || ! grep -Fq 'rejected fixture registry must define rejected_pair_fixture_reason' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'malformed-rejected.sh' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'NOTES.md records pair-candidate rejection but pair-rejected-fixtures.sh has no rejected reason' scripts/lint-fixtures.sh \
	  || ! grep -Fq 'test-active-headroom' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'active-calibration-rejected-missing.out' benchmark/auto-resolve/scripts/test-lint-fixtures.sh \
	  || ! grep -Fq 'Rejected controls should remain replayable' benchmark/auto-resolve/fixtures/SCHEMA.md \
	  || ! grep -Fq 'pair-rejected-fixtures.sh' benchmark/auto-resolve/fixtures/SCHEMA.md \
	  || ! grep -Fq 'target.relative_to(fixture_root)' scripts/lint-fixtures.sh \
	  || ! grep -Fq '$BENCH_FIXTURE_DIR/...' benchmark/auto-resolve/fixtures/SCHEMA.md \
	  || ! grep -Fq 'must not escape the fixture directory' benchmark/auto-resolve/fixtures/SCHEMA.md \
	  || ! grep -Fq 'cd "$BENCH_FIXTURE_DIR"` indirection' benchmark/auto-resolve/fixtures/SCHEMA.md \
	  || ! grep -Fq 'success sentinel' benchmark/auto-resolve/fixtures/SCHEMA.md \
	  || ! grep -Fq 'def fallback_validate():' scripts/lint-fixtures.sh \
  || ! grep -Fq 'expected.json must be an object' scripts/lint-fixtures.sh \
  || ! grep -Fq 'schema_ok=0' scripts/lint-fixtures.sh \
  || ! grep -Fq 'DEVLYN_LINT_FIXTURES_NO_JSONSCHEMA' scripts/lint-fixtures.sh \
  || ! grep -Fq 'conditional pair/risk-probe triggers' benchmark/auto-resolve/fixtures/SCHEMA.md; then
  offenders="${offenders}"$'\n'"fixture lint must require high-risk fixtures to include resolve pair/risk trigger terms"
fi
unsafe_json_parser_refs=$(python3 - <<'PY'
import pathlib
import re

root = pathlib.Path("benchmark/auto-resolve/scripts")
patterns = [
    re.compile(r"json\.load\(open\("),
    re.compile(r"json\.load\(response\)"),
    re.compile(r"json\.loads\([^,\n]*(?:read_text\(\)|\bline\b|\bln\b)[^,\n]*\)"),
]
for path in sorted(root.glob("*")):
    if path.name.startswith("test-") or path.suffix not in {".py", ".sh"}:
        continue
    text = path.read_text(errors="ignore")
    for line_no, line in enumerate(text.splitlines(), 1):
        if any(pattern.search(line) for pattern in patterns):
            print(f"{path}:{line_no}:{line.strip()}")
PY
)
if [ -n "$unsafe_json_parser_refs" ]; then
  while IFS= read -r f; do
    offenders="${offenders}"$'\n'"benchmark script uses unsafe JSON parser without strict constants: $f"
  done <<< "$unsafe_json_parser_refs"
fi
if [ -z "$offenders" ]; then
  ok "benchmark docs use current bare / solo_claude / pair-arm topology"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 9. Engine availability fails closed; stale silent-downgrade wording is forbidden.
# ---------------------------------------------------------------------------
section "Check 9: Engine availability fails closed"
offenders=$(grep -RInE 'codex-ping failed|codex-ping fail|engine downgraded: codex-unavailable|downgrades to Claude-only|silently downgrades|silently downgrade|silently switch to Claude|Codex CLI availability downgrade' \
  config/skills CLAUDE.md README.md bin/ benchmark/auto-resolve/run-real-benchmark.md 2>/dev/null \
  | grep -v 'roadmap-archival-workspace/' \
  | grep -v 'devlyn:auto-resolve-workspace/' \
  | grep -v 'devlyn:ideate-workspace/' \
  | grep -v 'preflight-workspace/' \
  || true)
if [ -z "$offenders" ]; then
  ok "engine availability fail-closed wording canonical"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 9b. Release tag and package version parity.
#     v2.2.3 was tagged while package.json still said 2.2.2. A mismatched npm
#     package makes Codex/Claude installed-skill drift hard to diagnose because
#     users can be on a tag whose package metadata points at a different build.
# ---------------------------------------------------------------------------
section "Check 9b: package.json version matches exact release tag"
exact_tag=$(git describe --tags --exact-match HEAD 2>/dev/null || true)
pkg_version=$(node -p "require('./package.json').version" 2>/dev/null || true)
if [ -z "$exact_tag" ]; then
  ok "HEAD is not an exact tag — package/tag parity not applicable"
elif [ "$pkg_version" = "${exact_tag#v}" ]; then
  ok "package.json version matches $exact_tag"
else
  bad "package.json version '$pkg_version' does not match HEAD tag '$exact_tag'"
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
  if make_temp_file tmp_rp && make_temp_file tmp_claude; then
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
  else
    rp_drift=1
  fi

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
  if make_temp_file tmp1 && make_temp_file tmp2; then
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
  else
    bad "idgen temp files unavailable; cannot verify determinism"
  fi
  if make_temp_dir tmp_bad && make_temp_file idgen_nan_out /tmp/pair-plan-idgen-nan.XXXXXX.out; then
    cp -R "$fixture/." "$tmp_bad/"
    printf '{"verification_commands": NaN}\n' > "$tmp_bad/expected.json"
    if python3 "$idgen" --fixture "$tmp_bad" --generated-at 2026-04-29T18:30:00Z >"$idgen_nan_out" 2>&1; then
      bad "pair-plan-idgen.py accepted NaN in expected.json"
    elif ! grep -Fq 'invalid JSON numeric constant: NaN' "$idgen_nan_out"; then
      bad "pair-plan-idgen.py NaN failure did not cite invalid JSON numeric constant"
    fi
    rm -rf "$tmp_bad" "$idgen_nan_out"
  fi

  if make_temp_file bad_plan && make_temp_file plan_lint_nan_out /tmp/pair-plan-lint-nan.XXXXXX.out; then
    printf '{"schema_version": NaN}\n' > "$bad_plan"
    if python3 benchmark/auto-resolve/scripts/pair-plan-lint.py --plan "$bad_plan" --quiet >"$plan_lint_nan_out" 2>&1; then
      bad "pair-plan-lint.py accepted NaN in pair-plan.json"
    elif ! grep -Fq '"code": "plan_invalid_json"' "$plan_lint_nan_out" \
         || ! grep -Fq 'invalid JSON numeric constant: NaN' "$plan_lint_nan_out"; then
      bad "pair-plan-lint.py NaN failure did not report plan_invalid_json with invalid numeric constant"
    fi
    rm -f "$bad_plan" "$plan_lint_nan_out"
  fi
  rm -f "${tmp1:-}" "${tmp2:-}"
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
# 15. Current pair-evidence fixtures carry their local evidence handoff notes.
#     The audit artifacts are canonical, but fixture-level notes keep future
#     fixture edits from losing why a candidate currently counts as solo<pair
#     evidence.
# ---------------------------------------------------------------------------
section "Check 15: Pair evidence fixture notes cite current passing runs"
if python3 - <<'PY'
import importlib.util
import pathlib
import sys

script = pathlib.Path("benchmark/auto-resolve/scripts/pair-candidate-frontier.py")
spec = importlib.util.spec_from_file_location("pair_candidate_frontier", script)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

report = module.build_report(
    fixtures_root=pathlib.Path("benchmark/auto-resolve/fixtures"),
    registry=pathlib.Path("benchmark/auto-resolve/scripts/pair-rejected-fixtures.sh"),
    results_root=pathlib.Path("benchmark/auto-resolve/results"),
)
errors = []
for row in report["rows"]:
    if row.get("status") != "pair_evidence_passed":
        continue
    fixture = row["fixture"]
    best = module.best_pair_evidence(row.get("passing_pair_evidence", []))
    if best is None:
        errors.append(f"{fixture}: missing complete pair evidence")
        continue
    notes_path = pathlib.Path("benchmark/auto-resolve/fixtures") / fixture / "NOTES.md"
    try:
        notes = notes_path.read_text(encoding="utf8")
    except OSError:
        errors.append(f"{fixture}: NOTES.md missing")
        continue
    required = [
        str(best["run_id"]),
        "pair_evidence_passed",
        f"bare `{best['bare_score']}`",
        f"solo_claude `{best['solo_score']}`",
        f"pair `{best['pair_score']}`",
        f"margin `{best['pair_margin']:+d}`",
        f"wall `{best['pair_solo_wall_ratio']:.2f}x`",
        f"arm `{best['pair_arm']}`",
    ]
    missing = [item for item in required if item not in notes]
    if missing:
        errors.append(f"{fixture}: NOTES.md missing {', '.join(missing)}")
if errors:
    raise SystemExit("\n".join(errors))
PY
then
  ok "current pair-evidence fixture notes cite passing run ids"
else
  bad "current pair-evidence fixture NOTES.md files must cite passing run ids and pair_evidence_passed"
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
