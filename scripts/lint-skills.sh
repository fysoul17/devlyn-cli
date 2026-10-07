#!/usr/bin/env bash
# lint-skills.sh — structural quality checks for the devlyn harness.
#
# Gates the three things that have drifted in the past:
#   1. Forbidden MCP / stale-model references in skills, README, installer.
#   2. Missing `name:`/`description:` in skill frontmatter (Anthropic spec violation).
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

# The core skills every install writes; the mirror parity check uses this list.
core_skills="devlyn-ideate devlyn-engines _shared"

# ---------------------------------------------------------------------------
# 1. No MCP references in managed source or user-facing docs.
# ---------------------------------------------------------------------------
section "Check 1: No mcp__codex-cli__ outside _shared / archive"
# Legal places: archival snapshots and tests.
offenders=$(git grep -Il -- 'mcp__codex-cli__' -- \
  config/skills \
  benchmark \
  README.md \
  CLAUDE.md \
  bin/ \
  ':!config/skills/roadmap-archival-workspace/**' \
  ':!config/skills/devlyn:auto-resolve-workspace/**' \
  ':!config/skills/devlyn:ideate-workspace/**' \
  ':!config/skills/preflight-workspace/**' \
  ':!benchmark/auto-resolve/**' \
  ':!benchmark/ceiling/results/**' \
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
  ':!benchmark/auto-resolve/**' \
  ':!benchmark/ceiling/results/**' \
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
# 4. No model-pinned Claude references, any generation.
# ---------------------------------------------------------------------------
section "Check 4: No model-pinned Claude references"
offenders=$(grep -RInE 'Claude (Opus|Sonnet|Haiku|Fable)|claude-(opus|sonnet|haiku|fable)-[0-9]' \
  config/skills 2>/dev/null \
  | grep -v 'config/skills/roadmap-archival-workspace/' \
  | grep -v 'config/skills/devlyn:auto-resolve-workspace/' \
  | grep -v 'config/skills/devlyn:ideate-workspace/' \
  | grep -v 'config/skills/preflight-workspace/' \
  | cut -d: -f1 \
  | sort -u \
  || true)
if [ -z "$offenders" ]; then
  ok "no model-pinned Claude references"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 5. Every shipped skill's frontmatter follows the Agent Skills standard: a
#    `name` of 1-64 lowercase letters, digits and single hyphens that equals its
#    folder, plus a `description`. ':' in a folder name cannot be checked out by
#    Git for Windows (the 4.0.0 rename from `devlyn:<x>`).
# ---------------------------------------------------------------------------
section "Check 5: shipped SKILL.md frontmatter follows the Agent Skills standard"
if make_temp_file name_offenders_file /tmp/devlyn-lint-name.XXXXXX; then
python3 - >"$name_offenders_file" 2>&1 <<'PY'
import pathlib, re
standard = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
skills = sorted([*pathlib.Path('config/skills').glob('*/SKILL.md'), *pathlib.Path('optional-skills').glob('*/SKILL.md')])
if not skills:
    print('no shipped SKILL.md found')
for skill in skills:
    lines = skill.read_text(encoding='utf-8').split('\n')
    if lines[0] != '---' or '---' not in lines[1:]:
        print(f"{skill} — missing '---' frontmatter")
        continue
    front = lines[1:lines.index('---', 1)]
    names = [line[len('name:'):].strip().strip('\'"') for line in front if line.startswith('name:')]
    if len(names) != 1 or not any(line.startswith('description:') for line in front):
        print(f"{skill} — frontmatter needs exactly one name: and a description:")
        continue
    name, folder = names[0], skill.parent.name
    if not (1 <= len(name) <= 64 and standard.match(name)):
        print(f"{skill} — name {name!r} breaks the Agent Skills rule (1-64 of a-z, 0-9, single hyphens)")
    elif name != folder:
        print(f"{skill} — name {name!r} must equal its folder {folder!r}")
PY
  name_offenders=$(cat "$name_offenders_file"); rm -f "$name_offenders_file"
else
  name_offenders="could not allocate a temp file for this check"
fi
if [ -z "$name_offenders" ]; then
  ok "every shipped skill name follows the Agent Skills standard and equals its folder"
else
  while IFS= read -r f; do bad "$f"; done <<< "$name_offenders"
fi

# ---------------------------------------------------------------------------
# 5c. Live text does not use a pre-4.0.0 skill name. History (benchmark/,
#     autoresearch/, docs/), the legacy instruction fixtures and fingerprints,
#     the README legacy map, the installer's rename and removal tables and
#     comments, and the tests that plant old installs keep them.
# ---------------------------------------------------------------------------
section "Check 5c: no pre-4.0.0 skill names in live text"
old_names='devlyn:(pencil-pull|pencil-push|design-ui|resolve|ideate|engines|queue|reap)([^a-z0-9-]|$)'
offenders=$(
  {
    git grep -nIE "$old_names" -- . ':!benchmark' ':!autoresearch' ':!docs' ':!scripts/fixtures/instructions' \
      ':!bin/instruction-templates.json' ':!bin/devlyn.js' ':!README.md' ':!scripts/lint-skills.sh' \
      ':!scripts/test-windows-portability.py' || true
    sed '/<!-- legacy-surface-map:begin/,/<!-- legacy-surface-map:end/s/.*//' README.md \
      | grep -nE "$old_names" | sed 's#^#README.md:#' || true
    sed 's#//.*##' bin/devlyn.js | grep -nE "$old_names" \
      | grep -vE "^[0-9]+: *('devlyn:[a-z-]+': 'devlyn-[a-z-]+'|'skills/devlyn:[a-z-]+'),$" | sed 's#^#bin/devlyn.js:#' || true
  } | sed -E 's#$# — pre-4.0.0 skill name in live text#'
)
if [ -z "$offenders" ]; then
  ok "pre-4.0.0 skill names appear only in history and the rename table"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 5d. DEPRECATED_DIRS never names a shipped skill: hyphen-era entries matched
#     the 4.0.0 names and would have removed an opted-in optional skill on
#     every later install.
# ---------------------------------------------------------------------------
section "Check 5d: DEPRECATED_DIRS never names a shipped skill"
offenders=$(
  sed -n '/^const DEPRECATED_DIRS = \[/,/^\];/p' bin/devlyn.js | grep -oE "'skills/[^']+'" | tr -d "'" | sed 's#^skills/##' |
    while IFS= read -r name; do
      if [ -f "config/skills/$name/SKILL.md" ] || [ -f "optional-skills/$name/SKILL.md" ]; then
        echo "DEPRECATED_DIRS names shipped skill $name"
      fi
    done
)
if [ -z "$offenders" ]; then
  ok "DEPRECATED_DIRS removes only retired skills"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 5a. resolve, design-ui and queue are retired: every skill root gets the same
#     core bundle without them, and upgrades remove their 3.x and 4.x folders
#     (Check 5d keeps a removed name from shipping again).
# ---------------------------------------------------------------------------
section "Check 5a: resolve, design-ui and queue are retired"
if grep -Fq "const DEVLYN_CORE_SKILLS = ['devlyn-ideate', 'devlyn-engines', '_shared'];" bin/devlyn.js \
   && grep -Fq "for (const skillName of DEVLYN_CORE_SKILLS) {" bin/devlyn.js; then
  ok "every skill root install gets the shared DEVLYN_CORE_SKILLS bundle, without resolve, design-ui or queue"
else
  bad "DEVLYN_CORE_SKILLS must be exactly devlyn-ideate, devlyn-engines and _shared, installed by its shared loop"
fi
offenders=$(
  for name in devlyn-resolve devlyn:resolve devlyn-design-ui devlyn:design-ui devlyn-queue devlyn:queue; do
    sed -n '/^const DEPRECATED_DIRS = \[/,/^\];/p' bin/devlyn.js | grep -Fq "'skills/$name'," \
      || echo "DEPRECATED_DIRS must remove skills/$name from downstream skill roots"
  done
)
if [ -z "$offenders" ]; then
  ok "DEPRECATED_DIRS removes resolve, design-ui and queue under their 3.x and 4.x names"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 5e. Shipped and CI files name resolve's skill, helpers and flags only where
#     removal or migration needs them: the installer's removal table and
#     retired Stop-hook command, the README legacy map, the tests that plant
#     old installs, and the historical instruction fixtures and fingerprints.
# ---------------------------------------------------------------------------
section "Check 5e: retired resolve names appear only in removal and migration text"
retired_names='devlyn[-:]resolve|resolve-stop-hook|archive_run|collect-codex-findings|finish-gate|grok-anchor-guard|judge-output-parser|judge-role-evidence|phase-prompt-render|process-evidence|resolve-bootstrap|spec-verify-check|state-phase-write|terminal-claim-check|verify-merge-findings|codex-config\.md|run-bounded|--pair-verify|--no-pair|--risk-probes|--no-risk-probes|--role-config|--verify-only'
offenders=$(
  {
    git grep -nIE "$retired_names" -- bin config .agents scripts .github CLAUDE.md AGENTS.md package.json \
      ':!scripts/lint-skills.sh' ':!scripts/test-windows-portability.py' ':!scripts/fixtures/instructions' \
      ':!bin/instruction-templates.json' ':!bin/devlyn.js' || true
    sed '/<!-- legacy-surface-map:begin/,/<!-- legacy-surface-map:end/s/.*//' README.md \
      | grep -nE "$retired_names" | sed 's#^#README.md:#' || true
    grep -nE "$retired_names" bin/devlyn.js \
      | grep -vE "^[0-9]+: *'skills/devlyn[-:]resolve',$|^[0-9]+:const RETIRED_STOP_HOOK = " | sed 's#^#bin/devlyn.js:#' || true
  } | sed -E 's#$# — retired resolve name outside removal or migration text#'
)
if [ -z "$offenders" ]; then
  ok "resolve's skill, helpers and flags appear only in removal and migration text"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 5b. Every completed managed-skills install writes its own version marker.
# ---------------------------------------------------------------------------
section "Check 5b: Installed skill roots carry exact version markers"
if make_temp_dir tmp_install_marker /tmp/devlyn-install-marker.XXXXXX; then
  marker_home="$tmp_install_marker/home"
  marker_project="$tmp_install_marker/project"
  timeout_low="$tmp_install_marker/timeout-low"
  timeout_high="$tmp_install_marker/timeout-high"
  installer="$PWD/bin/devlyn.js"
  mkdir -p "$marker_home" "$marker_project" "$timeout_low/.claude" "$timeout_high/.claude"
  printf '{"env":{"BASH_MAX_TIMEOUT_MS":"600000"}}\n' > "$timeout_low/.claude/settings.json"
  printf '{"env":{"BASH_MAX_TIMEOUT_MS":"7200000"}}\n' > "$timeout_high/.claude/settings.json"

  if (cd "$marker_project" \
      && HOME="$marker_home" node "$installer" -y --claude >"$tmp_install_marker/project.log" 2>&1 \
      && HOME="$marker_home" node "$installer" -y --global --claude >"$tmp_install_marker/global.log" 2>&1) \
      && (cd "$timeout_low" && HOME="$marker_home" node "$installer" -y --claude >"$tmp_install_marker/timeout-low.log" 2>&1) \
      && cp "$timeout_low/.claude/settings.json" "$tmp_install_marker/timeout-low-first.json" \
      && (cd "$timeout_low" && HOME="$marker_home" node "$installer" -y >"$tmp_install_marker/timeout-low-second.log" 2>&1) \
      && cmp -s "$timeout_low/.claude/settings.json" "$tmp_install_marker/timeout-low-first.json" \
      && (cd "$timeout_high" && HOME="$marker_home" node "$installer" -y --claude >"$tmp_install_marker/timeout-high.log" 2>&1); then
    if python3 - "$installer" "$marker_home" "$marker_project" "$timeout_low" "$timeout_high" <<'PY'
import json
import pathlib
import stat
import sys

installer = pathlib.Path(sys.argv[1])
home = pathlib.Path(sys.argv[2])
project = pathlib.Path(sys.argv[3])
timeout_low = pathlib.Path(sys.argv[4])
timeout_high = pathlib.Path(sys.argv[5])
package = json.loads((installer.parent.parent / "package.json").read_text())
expected = {"schemaVersion": 1, "package": package["name"], "version": package["version"]}
roots = [
    project / ".agents" / "skills",
    project / ".claude" / "skills",
    home / ".agents" / "skills",
    home / ".codex" / "skills",
    home / ".claude" / "skills",
]
for root in roots:
    marker = root / ".devlyn-install.json"
    actual = json.loads(marker.read_text())
    if actual != expected:
        raise SystemExit(f"{marker}: expected {expected}, got {actual}")
    if stat.S_IMODE(marker.stat().st_mode) != 0o600:
        raise SystemExit(f"{marker}: expected mode 0600")
    if list(root.glob(".devlyn-install.json.*.tmp")):
        raise SystemExit(f"{root}: stale marker temp file")
for target, expected_timeout in (
    (project, "3600000"),
    (timeout_low, "3600000"),
    (timeout_high, "7200000"),
):
    env = json.loads((target / ".claude" / "settings.json").read_text())["env"]
    if env.get("BASH_MAX_TIMEOUT_MS") != expected_timeout:
        raise SystemExit(f"{target}: expected BASH_MAX_TIMEOUT_MS={expected_timeout}")
    if "BASH_DEFAULT_TIMEOUT_MS" in env:
        raise SystemExit(f"{target}: BASH_DEFAULT_TIMEOUT_MS must not be installed")
PY
    then
      if grep -Fxq '.claude/skills/.devlyn-install.json' "$marker_project/.gitignore" \
         && grep -Fxq '.agents/skills/.devlyn-install.json' "$marker_project/.gitignore"; then
        ok "managed roots have exact 0600 markers; Bash max is installed, raised, preserved, and idempotent"
      else
        bad "project installs must ignore their local markers"
      fi
    else
      bad "completed installs must write the exact per-root marker"
    fi
  else
    bad "isolated managed-skills install failed"
  fi

  incomplete="$tmp_install_marker/incomplete"
  mkdir -p "$incomplete/package" "$incomplete/home/.agents/skills" "$incomplete/project/.agents/skills"
  cp -R bin config package.json AGENTS.md CLAUDE.md "$incomplete/package/"
  rm -rf "$incomplete/package/config/skills/devlyn-engines"
  printf '{"version":"stale"}\n' > "$incomplete/home/.agents/skills/.devlyn-install.json"
  printf '{"version":"stale"}\n' > "$incomplete/project/.agents/skills/.devlyn-install.json"
  if ! (cd "$incomplete/project" \
      && HOME="$incomplete/home" node "$incomplete/package/bin/devlyn.js" -y >"$incomplete/project.log" 2>&1) \
      && ! (cd "$incomplete/project" \
      && HOME="$incomplete/home" node "$incomplete/package/bin/devlyn.js" -y --global >"$incomplete/global.log" 2>&1) \
      && grep -Fq 'Incomplete devlyn skill install; missing: devlyn-engines' "$incomplete/project.log" \
      && grep -Fq 'Incomplete devlyn skill install; missing: devlyn-engines' "$incomplete/global.log" \
      && [ -d "$incomplete/project/.agents/skills/devlyn-ideate" ] \
      && [ -d "$incomplete/home/.agents/skills/devlyn-ideate" ] \
      && [ ! -e "$incomplete/project/.agents/skills/.devlyn-install.json" ] \
      && [ ! -e "$incomplete/home/.agents/skills/.devlyn-install.json" ]; then
    ok "incomplete project and global copies fail visibly without stale or replacement markers"
  else
    bad "incomplete project and global copies must fail visibly without an install marker"
  fi
  rm -rf "$tmp_install_marker"
else
  bad "could not allocate install-marker smoke directory"
fi

# ---------------------------------------------------------------------------
# 6. Source ↔ mirror parity. The tracked .agents/skills mirror equals
#    config/skills; an installed .claude/skills (present only after the
#    installer ran in this checkout) holds the same core skills. The shell
#    wrapper must stay executable in both: bash refuses a non-executable one.
# ---------------------------------------------------------------------------
section "Check 6: Source ↔ mirror parity"
mirror_drift=$(diff -rq -x __pycache__ config/skills .agents/skills 2>&1 || true)
if [ -d .claude/skills ]; then
  for skill in $core_skills; do
    mirror_drift="${mirror_drift}"$'\n'"$(diff -rq -x __pycache__ "config/skills/$skill" ".claude/skills/$skill" 2>&1 || true)"
  done
fi
for tree in .agents/skills .claude/skills; do
  if [ -f "$tree/_shared/codex-monitored.sh" ] && [ ! -x "$tree/_shared/codex-monitored.sh" ]; then
    mirror_drift="${mirror_drift}"$'\n'"$tree/_shared/codex-monitored.sh is not executable"
  fi
done
mirror_drift=$(printf '%s\n' "$mirror_drift" | sed '/^$/d')
if [ -z "$mirror_drift" ]; then
  ok "config/skills, .agents/skills and any installed .claude/skills core skills are in parity"
else
  while IFS= read -r f; do bad "$f"; done <<< "$mirror_drift"
fi

section "Check 6b: Retained helper self-tests"
for helper in _shared/role-config.py _shared/task-complete.py _shared/expected-contract.py _shared/invocation-receipt.py \
  devlyn-ideate/scripts/queue.py devlyn-ideate/scripts/acceptance.py; do
  if python3 "config/skills/$helper" --self-test; then
    ok "$helper self-test passed"
  else
    bad "$helper self-test failed"
  fi
done

section "Check 6f: ideate validates loop packages and keeps its normative policies"
if ! grep -Fq 'scripts/queue.py" check' config/skills/devlyn-ideate/SKILL.md \
  || ! grep -Fq 'Ask only when the unresolved answer changes authorized behavior, scope, data semantics, acceptance or delivery.' config/skills/devlyn-ideate/SKILL.md \
  || ! grep -Fq 'Material ambiguity means competing readings with materially different intended outcomes, unresolved persistent data or state semantics, or public surface beyond the request; stop affected work as needs-review with a concrete question' config/skills/devlyn-ideate/SKILL.md \
  || ! grep -Fq 'add one compound check that exercises the interaction end to end' config/skills/devlyn-ideate/references/elicitation.md; then
  bad "ideate must validate packages with queue.py check, keep its question and autonomous policies, and require compound checks for interacting requirements"
else
  ok "ideate validates packages, keeps its question and autonomous policies, and requires compound checks for interacting requirements"
fi

section "Check 6g: ideate gives the exact drain executor argv"
# A Codex executor denied its commit in the linked worktree (e2e smoke, then again with the common Git directory
# writable): workspace-write keeps .git read-only, and the worktree's own Git directory unless listed exactly. It
# also denies network, so a Codex executor could not install a new dependency (phase B audit H9).
claude_argv='claude -p "<prompt>" --dangerously-skip-permissions --add-dir "<git dir>"'
codex_roots="-c 'sandbox_workspace_write.writable_roots=[\"<git dir>\",\"{worktree_git_dir}\"]'"
adapter_roots="-c 'sandbox_workspace_write.writable_roots=[\"<git dir>\",\"<worktree git dir>\"]'"
codex_network="-c 'sandbox_workspace_write.network_access=true'"
if ! grep -Fq -- "$claude_argv" config/skills/devlyn-ideate/SKILL.md \
  || ! grep -Fq -- "--skip-git-repo-check -s workspace-write $codex_roots $codex_network \"<prompt>\"" config/skills/devlyn-ideate/SKILL.md \
  || ! grep -Fq -- "$adapter_roots $codex_network" config/skills/_shared/adapters/codex.md; then
  bad "ideate SKILL.md must give the exact Claude and Codex executor argv, and the Codex adapter the common and worktree Git directories as writable roots and network access"
else
  ok "ideate gives the exact Claude and Codex executor argv; the Codex adapter makes the common and worktree Git directories writable and allows network"
fi

section "Check 6h: No undocumented spec.expected.json.browser_flows field"
browser_flow_refs=$(grep -RInF 'spec.expected.json.browser_flows' \
  config/skills README.md bin/ package.json 2>/dev/null || true)
if [ -z "$browser_flow_refs" ]; then
  ok "active docs do not advertise unsupported browser_flows schema field"
else
  while IFS= read -r f; do bad "$f"; done <<< "$browser_flow_refs"
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
#     Excludes: codex-monitored.sh (its comments name the shapes it
#     prevents), workspace/, archive snapshots.
# ---------------------------------------------------------------------------
section "Check 10: No raw codex exec invocation in skill prompts"
offenders=$(grep -RInE 'codex exec[[:space:]]+[^[:space:]]' \
  config/skills 2>/dev/null \
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
# 10a. codex-monitored.sh rejects invalid numeric settings before any launch.
# ---------------------------------------------------------------------------
section "Check 10a: codex-monitored.sh rejects invalid numeric settings"
wrapper_env_ok=1
if make_temp_dir tmp_env /tmp/codex-monitored-env.XXXXXX; then
  if CODEX_MONITORED_HEARTBEAT=0 CODEX_BIN=/bin/true \
    bash config/skills/_shared/codex-monitored.sh prompt \
    >"$tmp_env/heartbeat.stdout" 2>"$tmp_env/heartbeat.stderr"; then
    bad "codex-monitored.sh accepted CODEX_MONITORED_HEARTBEAT=0"
    wrapper_env_ok=0
  elif ! grep -F 'CODEX_MONITORED_HEARTBEAT must be > 0' "$tmp_env/heartbeat.stderr" >/dev/null 2>&1; then
    bad "codex-monitored.sh heartbeat validation emitted wrong error"
    wrapper_env_ok=0
  fi
  if CODEX_MONITORED_TIMEOUT_SEC=abc CODEX_BIN=/bin/true \
    bash config/skills/_shared/codex-monitored.sh prompt \
    >"$tmp_env/timeout.stdout" 2>"$tmp_env/timeout.stderr"; then
    bad "codex-monitored.sh accepted non-numeric CODEX_MONITORED_TIMEOUT_SEC"
    wrapper_env_ok=0
  elif ! grep -F 'CODEX_MONITORED_TIMEOUT_SEC must be a non-negative integer' "$tmp_env/timeout.stderr" >/dev/null 2>&1; then
    bad "codex-monitored.sh timeout validation emitted wrong error"
    wrapper_env_ok=0
  fi
  rm -rf "$tmp_env"
else
  wrapper_env_ok=0
fi
if [ $wrapper_env_ok -eq 1 ]; then
  ok "codex-monitored.sh rejects a zero heartbeat and a non-numeric timeout"
fi

section "Check 10a1: Shared helper paths resolve from the invoked skill"
shared_path_offenders=$(grep -RInF '.claude/skills/_shared' config/skills 2>/dev/null \
  | grep -v 'roadmap-archival-workspace/' \
  | grep -v 'devlyn:auto-resolve-workspace/' \
  | grep -v 'devlyn:ideate-workspace/' \
  | grep -v 'preflight-workspace/' \
  || true)
if [ -z "$shared_path_offenders" ]; then
  ok "no project-relative .claude/skills/_shared paths in managed skills"
else
  while IFS= read -r f; do bad "$f"; done <<< "$shared_path_offenders"
fi

section "Check 10a1b: Skill paths come from the loaded SKILL.md, not a substitution"
# Only Claude Code and Grok render ${CLAUDE_SKILL_DIR}; any other use breaks the other readers.
# The inert hint line and generate-skill's substitution table are the allowed occurrences.
skill_dir_offenders=$(grep -RInE 'CLAUDE_SKILL_DIR|__DEVLYN_SKILL_DIR__' config/skills optional-skills bin 2>/dev/null \
  | grep -vE '^[^:]+:[0-9]+:\$\{CLAUDE_SKILL_DIR\}$' \
  | grep -vE '^optional-skills/generate-skill/REFERENCE\.md:[0-9]+:\| `\$\{CLAUDE_SKILL_DIR\}` \|' \
  || true)
if [ -z "$skill_dir_offenders" ]; then
  ok "skill resources resolve from the loaded SKILL.md on every reader"
else
  while IFS= read -r f; do bad "$f"; done <<< "$skill_dir_offenders"
fi

# ---------------------------------------------------------------------------
# 10b. Shared routing docs must describe the current skill surface.
#      A stale auto-resolve/preflight/ideate-CHALLENGE reference can misroute
#      bounded pair work back into unisolated or retired Codex paths.
# ---------------------------------------------------------------------------
section "Check 10b: Shared routing docs avoid retired skill surfaces"
offenders=$(grep -RInE 'auto-resolve/SKILL\.md|preflight/SKILL\.md|challenge-rubric\.md|ideate CHALLENGE phase|does NOT consume this file|cross-model challenge phases when configured|phase-1-build\.md|phase-2-evaluate\.md|phase-3-critic\.md' \
  config/skills/_shared 2>/dev/null || true)
if [ -z "$offenders" ]; then
  ok "shared routing docs reference the current devlyn-ideate/devlyn-engines surface"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi

# ---------------------------------------------------------------------------
# 10c. User-facing current docs must not advertise retired skills.
#      Historical archive mentions are allowed, but install/package copy
#      must not describe ideate -> auto-resolve -> preflight or ideate CHALLENGE.
# ---------------------------------------------------------------------------
section "Check 10c: User-facing current docs avoid retired skill surfaces"
offenders=$(
  {
    sed '/<!-- legacy-surface-map:begin/,/<!-- legacy-surface-map:end/s/.*//' README.md 2>/dev/null \
      | grep -nE '/devlyn:auto-resolve|ideate CHALLENGE|--with-codex|Quick Start pointing to ideate → auto-resolve → preflight|auto-resolve'\''s build agent|Core pipeline skills \(`ideate`, `auto-resolve`, `preflight`\)' || true
    grep -nE '"description": .*auto-resolve|"description": .*preflight' package.json 2>/dev/null || true
    grep -nE 'so auto-resolve doesn'\''t prompt' bin/devlyn.js 2>/dev/null || true
  } | sed -E 's#^#user-facing retired-surface reference: #'
)
if [ -z "$offenders" ]; then
  ok "README/package/installer copy avoids retired skill surfaces"
else
  while IFS= read -r f; do bad "$f"; done <<< "$offenders"
fi


# ---------------------------------------------------------------------------
# 9. Engine availability fails closed; stale silent-downgrade wording is forbidden.
# ---------------------------------------------------------------------------
section "Check 9: Engine availability fails closed"
offenders=$(grep -RInE 'codex-ping failed|codex-ping fail|engine downgraded: codex-unavailable|downgrades to Claude-only|silently downgrades|silently downgrade|silently switch to Claude|Codex CLI availability downgrade' \
  config/skills CLAUDE.md README.md bin/ 2>/dev/null \
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
# 12. The canonical block — North Star, the seven principles and the three
#     discipline rules — is identical in CLAUDE.md, AGENTS.md and
#     _shared/runtime-principles.md (the copy for a context without an
#     installed instruction block).
# ---------------------------------------------------------------------------
section "Check 12: Canonical principles block parity"
canonical_block() { awk '/^## North Star$/{f=1} /^## Quick Start$/{f=0} f' "$1"; }
canonical=$(canonical_block CLAUDE.md)
principles_missing=0
for heading in '1. **No workaround**' '2. **No overengineering**' '3. **No guesswork**' '4. **Worldclass**' \
  '5. **Best practice**' '6. **Optimized**' '7. **Production ready**' '- **Root cause via flexible why-chain.**' \
  '- **First-principles thinking.**' '- **Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away.**'; do
  if ! printf '%s\n' "$canonical" | grep -Fq -- "$heading"; then
    bad "CLAUDE.md — canonical block is missing: $heading"
    principles_missing=1
  fi
done
for f in AGENTS.md config/skills/_shared/runtime-principles.md; do
  if [ "$(canonical_block "$f")" != "$canonical" ]; then
    bad "$f — North Star and core principles differ from CLAUDE.md"
    principles_missing=1
  fi
done
if [ $principles_missing -eq 0 ]; then
  ok "North Star, seven principles and three discipline rules are identical in CLAUDE.md, AGENTS.md and runtime-principles.md"
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
